import asyncio
import json
import urllib.request
import subprocess
import os
import time
import socket
import tempfile
import websockets

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

BASE_DIR = r"F:\NEW_MSACCESS"
TB_EXE = r"F:\Downloads\D7\twinBASIC_IDE_BETA_1017\twinBASIC.exe"
PROJ = os.path.join(BASE_DIR, "OpenAccessStudio.twinproj")
BIN_DIR = os.path.join(BASE_DIR, "bin")

def build_architecture(arch="win32"):
    out_exe = os.path.join(BIN_DIR, f"OpenAccessStudio_{arch}.exe")
    before_mtime = os.path.getmtime(out_exe) if os.path.exists(out_exe) else 0

    # Ensure no lingering twinBASIC processes
    subprocess.run(["powershell", "-Command", "Stop-Process -Name '*twinBASIC*' -Force -ErrorAction SilentlyContinue"], capture_output=True)
    time.sleep(2)

    port = get_free_port()
    data_folder = os.path.join(tempfile.gettempdir(), f"tb_wv2_data_{port}")
    os.makedirs(data_folder, exist_ok=True)

    env = os.environ.copy()
    env['WEBVIEW2_USER_DATA_FOLDER'] = data_folder
    env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = f'--remote-debugging-port={port}'

    cmd = [TB_EXE, PROJ]
    p = subprocess.Popen(cmd, env=env)
    print(f"[{arch}] twinBASIC started (PID: {p.pid}) on port {port} with isolated profile...", flush=True)

    async def run_cdp():
        target = None
        for i in range(45):
            await asyncio.sleep(1)
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json') as resp:
                    targets = json.loads(resp.read().decode())
                    for t in targets:
                        if 'main.htm' in t.get('url', ''):
                            target = t
                            break
                    if target:
                        break
            except Exception:
                pass

        if not target:
            print(f"[{arch}] Target main.htm not found!", flush=True)
            return False

        print(f"[{arch}] Connected: {target['webSocketDebuggerUrl']}", flush=True)
        async with websockets.connect(target['webSocketDebuggerUrl']) as ws:
            msg_id = 1
            pending = {}
            async def call(method, params=None):
                nonlocal msg_id
                m = {'id': msg_id, 'method': method, 'params': params or {}}
                mid = msg_id
                msg_id += 1
                fut = asyncio.get_event_loop().create_future()
                pending[mid] = fut
                await ws.send(json.dumps(m))
                return await fut

            async def listener():
                try:
                    while True:
                        raw = await ws.recv()
                        msg = json.loads(raw)
                        if 'id' in msg and msg['id'] in pending:
                            pending[msg['id']].set_result(msg.get('result', {}))
                        elif msg.get('method') == 'Runtime.consoleAPICalled':
                            args = msg.get('params', {}).get('args', [])
                            vals = [str(a.get('value', '')) for a in args]
                            line = ' '.join(vals)
                            if 'TB_' in line or 'error' in line.lower() or 'failed' in line.lower():
                                print(f"[{arch}] {line}", flush=True)
                except Exception:
                    pass

            asyncio.create_task(listener())

            await call('Console.enable')
            await call('Runtime.enable')

            # Hook debugSocket events for logging
            await call('Runtime.evaluate', {
                'expression': '''(function(){
                    var origOut = debugSocket.event_output;
                    debugSocket.event_output = function(e) {
                        var out = e.body ? e.body.output : JSON.stringify(e);
                        console.log("TB_OUT: " + out);
                        if (origOut) origOut.apply(this, arguments);
                    };
                    return "hooked";
                })()'''
            })

            print(f"[{arch}] Waiting 20s for initial compile...", flush=True)
            await asyncio.sleep(20)

            cmd_switch = 'tbBuild_SwitchToWin32' if arch == 'win32' else 'tbBuild_SwitchToWin64'
            print(f"[{arch}] Switching: {cmd_switch}...", flush=True)
            await call('Runtime.evaluate', {'expression': f'executeIdeCommand("{cmd_switch}")'})
            print(f"[{arch}] Waiting 12s for compiler to switch to {arch}...", flush=True)
            await asyncio.sleep(12)

            markers_script = """
            (function() {
                var models = monaco.editor.getModels();
                var res = [];
                for (var i = 0; i < models.length; i++) {
                    var m = models[i];
                    var marks = monaco.editor.getModelMarkers({ resource: m.uri });
                    if (marks && marks.length > 0) {
                        res.push({ uri: m.uri.toString(), markers: marks.map(x => ({ msg: x.message, line: x.startLineNumber, col: x.startColumn, severity: x.severity })) });
                    }
                }
                return res;
            })()
            """
            marks_resp = await call('Runtime.evaluate', {'expression': markers_script, 'returnByValue': True})
            model_markers = marks_resp.get('result', {}).get('value', [])
            errors = []
            for item in model_markers:
                for mark in item.get('markers', []):
                    if mark.get('severity') == 8: # Error
                        errors.append(f"{item.get('uri')}:{mark.get('line')}:{mark.get('col')} -> {mark.get('msg')}")

            if errors:
                print(f"[{arch}] COMPILER ERRORS DETECTED ({len(errors)} errors):", flush=True)
                for err in errors:
                    print(f"  {err}", flush=True)
                return False

            print(f"[{arch}] Starting build via tbBuild_Start and doBuild...", flush=True)
            await call('Runtime.evaluate', {'expression': "executeIdeCommand('tbBuild_Start')"})
            try:
                await call('Runtime.evaluate', {
                    'expression': '''debugSocket.request("doBuild", {
                        projectFullPath: projectFilePath,
                        cleanOnly: false,
                        ignoreOldBuild: false
                    })'''
                })
            except Exception:
                pass

            for w in range(50):
                await asyncio.sleep(1)
                after_mtime = os.path.getmtime(out_exe) if os.path.exists(out_exe) else 0
                if after_mtime > before_mtime:
                    print(f"[{arch}] SUCCESS! {os.path.basename(out_exe)} built in {w+1}s ({os.path.getsize(out_exe)} bytes)!", flush=True)
                    return True

            print(f"[{arch}] Timed out waiting for {out_exe} to update. Checking errors...", flush=True)
            marks_resp = await call('Runtime.evaluate', {'expression': markers_script, 'returnByValue': True})
            model_markers = marks_resp.get('result', {}).get('value', [])
            for item in model_markers:
                for mark in item.get('markers', []):
                    print(f"  MARKER: {item.get('uri')}:{mark.get('line')}:{mark.get('col')} -> {mark.get('msg')}", flush=True)

            return False

    try:
        ok = asyncio.run(run_cdp())
    finally:
        p.kill()
        subprocess.run(["powershell", "-Command", "Stop-Process -Name '*twinBASIC*' -Force -ErrorAction SilentlyContinue"], capture_output=True)

    return ok

if __name__ == "__main__":
    print("=== BUILDING OpenAccessStudio_win64.exe (NATIVE DEFAULT) ===")
    ok64 = build_architecture("win64")
    print("Result win64:", ok64)
    time.sleep(3)
    print("\n=== BUILDING OpenAccessStudio_win32.exe (NATIVE DEFAULT) ===")
    ok32 = build_architecture("win32")
    print("Result win32:", ok32)
    print(f"\nFinal Results: win32={ok32}, win64={ok64}")
    if not (ok32 and ok64):
        exit(1)

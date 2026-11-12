#!/usr/bin/env python3
"""
OpenAccess & OpenAccessStudio twinBASIC Project Binary Packer
Recursively includes ALL source files across src/ (including src/studio/**) so no module or class is missed.
Updates BOTH:
1. F:\\NEW_MSACCESS\\OpenAccessStudio.twinproj (Standard EXE - Full Studio + Engine)
2. F:\\NEW_MSACCESS\\OpenAccess.twinproj (Core Engine / CLI Project)
"""

import os
import sys
import json
import struct

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_STUDIO_TWINPROJ = os.path.join(BASE_DIR, "OpenAccessStudio.twinproj")
OUTPUT_ENGINE_TWINPROJ = os.path.join(BASE_DIR, "OpenAccess.twinproj")

FILE_EXTRA_TWIN = bytes.fromhex("04000000000000000000000000")
FILE_EXTRA_FORM_TWIN = bytes.fromhex("03000000000000000000000000")
FILE_EXTRA_TBFORM = bytes.fromhex("08000000000000000000000000")

def pack_entry_file(name, extra, content):
    data = bytearray()
    data.extend(struct.pack('<H', 1)) # File
    name_bytes = name.encode('utf-8')
    data.extend(struct.pack('<I', len(name_bytes)))
    data.extend(name_bytes)
    data.extend(extra)
    data.extend(struct.pack('<I', len(content)))
    data.extend(content)
    data.extend(struct.pack('<I', 0)) # Checksum / terminator
    return bytes(data)

def pack_entry_folder(name, extra, children_bytes_list):
    data = bytearray()
    data.extend(struct.pack('<H', 2)) # Folder
    name_bytes = name.encode('utf-8')
    data.extend(struct.pack('<I', len(name_bytes)))
    data.extend(name_bytes)
    data.extend(extra)
    data.extend(struct.pack('<I', len(children_bytes_list)))
    for c in children_bytes_list:
        data.extend(c)
    return bytes(data)

def pack_project(root_name, entries):
    data = bytearray()
    data.extend(bytes.fromhex('1ca50bea')) # twinBASIC magic header
    data.extend(struct.pack('<H', 1))      # Version 1
    name_bytes = root_name.encode('utf-8')
    data.extend(struct.pack('<I', len(name_bytes)))
    data.extend(name_bytes)
    data.extend(b'\x00' * 13)              # Root header padding
    data.extend(struct.pack('<I', len(entries)))
    for e in entries:
        data.extend(e)
    return bytes(data)

def get_file_extra(filename, full_path):
    lower = filename.lower()
    if lower.endswith(".tbform"):
        return FILE_EXTRA_TBFORM
    if lower == "mainform.twin" or os.path.isfile(os.path.splitext(full_path)[0] + ".tbform"):
        return FILE_EXTRA_FORM_TWIN
    return FILE_EXTRA_TWIN

def collect_all_src_files(include_studio=True):
    """
    Recursively walks src/ and collects every .twin, .tbform, .bas, and .cls file.
    If include_studio=False, skips files that depend on GUI Forms (MainForm.twin, MainForm.tbform, Startup.twin, StudioController.twin, CommonDialogs.twin, FormRuntime.twin).
    """
    src_root = os.path.join(BASE_DIR, "src")
    gui_only_names = {
        "mainform.twin",
        "mainform.tbform",
        "studiocontroller.twin",
        "commondialogs.twin",
        "formruntime.twin",
    }

    collected = []
    seen_names = set()

    for root, dirs, files in os.walk(src_root):
        dirs.sort()
        for f in sorted(files):
            lower = f.lower()
            if not lower.endswith((".twin", ".tbform", ".bas", ".cls")):
                continue
            if not include_studio:
                rel_dir = os.path.relpath(root, src_root).replace("\\", "/")
                if rel_dir == "studio" or rel_dir.startswith("studio/"):
                    continue
                if lower in gui_only_names:
                    continue
            full_path = os.path.join(root, f)
            if lower in seen_names:
                continue
            seen_names.add(lower)
            collected.append((f, full_path, get_file_extra(f, full_path)))

    return collected

def build_twinproj(root_name, output_path, app_title, description, project_id, startup_object, include_forms_pkg, file_tuples):
    references = []
    if include_forms_pkg:
        references.append({
            "hasBeenSplit": True,
            "id": "{F50B82D0-DCAB-43FE-9631-11959D4A4728}",
            "isCompilerPackage": True,
            "licence": "MIT",
            "name": "[COMPILER PACKAGE] twinBASIC - VB Compatibility Package (Forms)",
            "path32": "/Packages/WindowsControlsPackage",
            "path64": "/Packages/WindowsControlsPackage",
            "publishedDate": "09-FEB-2022",
            "publishedTime": "15:48:54",
            "publisher": "TWINBASIC-COMPILER",
            "symbolId": "VB",
            "versionBuild": 0,
            "versionMajor": 0,
            "versionMinor": 0,
            "versionRevision": 31
        })
    references.append({
        "id": "{00020430-0000-0000-C000-000000000046}",
        "lcid": 0,
        "name": "OLE Automation",
        "path32": "C:\\Windows\\SysWow64\\stdole2.tlb",
        "path64": "C:\\Windows\\System32\\stdole2.tlb",
        "symbolId": "stdole",
        "versionMajor": 2,
        "versionMinor": 0
    })

    settings_obj = {
        "configuration.inherits": "Defaults",
        "project.appTitle": app_title,
        "project.buildPath": "${SourcePath}\\bin\\${ProjectName}_${Architecture}.${FileExtension}",
        "project.buildType": "Standard EXE",
        "project.description": description,
        "project.exportPathIsV2": True,
        "project.id": project_id,
        "project.name": root_name,
        "project.optionExplicit": True,
        "project.startupObject": startup_object,
        "project.references": references,
        "project.settingsVersion": 1,
        "project.warnings": {
            "errors": [],
            "ignored": []
        },
        "runtime.useUnicodeStandardLibrary": True
    }
    settings_content = json.dumps(settings_obj, indent="\t").encode("utf-8")

    first_editor = "MainForm.twin" if include_forms_pkg else (file_tuples[0][0] if file_tuples else "DaoEngine.twin")
    meta_obj = {
        "rootFolder": f"/{root_name}",
        "fs_expandedFolders": [
            f"/{root_name}",
            f"/{root_name}/Sources"
        ],
        "openEditors": [
            {
                "uri": f"/{root_name}/Sources/{first_editor}",
                "state": {
                    "cursorState": [
                        {
                            "inSelectionMode": False,
                            "selectionStart": {"lineNumber": 1, "column": 1},
                            "position": {"lineNumber": 1, "column": 1}
                        }
                    ],
                    "viewState": {
                        "scrollLeft": 0,
                        "firstPosition": {"lineNumber": 1, "column": 1},
                        "firstPositionDeltaTop": 0
                    }
                },
                "isSelected": True
            }
        ],
        "debugConsoleEntryHistory": [],
        "variables_expandedCache": {"/Locals": True},
        "watches": [],
        "watches_expandedCache": {},
        "outlinePanelOptions": {
            "showClassFields": True,
            "showModuleVariables": True,
            "showEnumerations": True,
            "showUDTs": True,
            "showDLLs": True,
            "showConstructors": True,
            "showProperties": True,
            "showProcedures": True,
            "showVariables": True,
            "showParameters": True
        },
        "debugPanelOptions": {"invertDirection": False, "showTimestamps": True},
        "problemsPanelOptions": {"showErrors": True, "showWarnings": True, "showHints": False, "showInfos": False},
        "history": [],
        "toolWindows": [],
        "bookmarks": {},
        "searchInsidePackages": False,
        "searchCaseSensitive": False,
        "searchWholeWordOnly": False,
        "objectExplorerExpandedNodes": [65535, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "findReplaceHistory": {},
        "findReplaceOptions": {
            "InsidePackages": False,
            "WholeWordOnly": False,
            "MatchCase": False,
            "PatternMatching": False,
            "RegularExpressions": False
        }
    }
    meta_content = json.dumps(meta_obj, indent="\t").encode("utf-8")

    source_entries = []
    for sname, spath, sextra in file_tuples:
        with open(spath, "rb") as sf:
            scontent = sf.read()
        source_entries.append(pack_entry_file(sname, sextra, scontent))

    entries = [
        pack_entry_file(".meta", bytes.fromhex("19000000000000000000000000"), meta_content),
        pack_entry_file("Settings", bytes.fromhex("430a0000000000000000000004"), settings_content),
        pack_entry_folder("Sources", bytes.fromhex("00000000000000000000000003"), source_entries),
        pack_entry_folder("Resources", bytes.fromhex("00000000000000000000000002"), []),
        pack_entry_folder("ImportedTypeLibraries", bytes.fromhex("00000000000000000000000005"), []),
        pack_entry_folder("Packages", bytes.fromhex("00000000000000000000000007"), []),
        pack_entry_folder("Miscellaneous", bytes.fromhex("00000000000000000000000006"), []),
    ]

    project_bytes = pack_project(root_name, entries)
    with open(output_path, "wb") as f:
        f.write(project_bytes)
    print(f"Successfully packed {output_path} ({len(project_bytes)} bytes, {len(source_entries)} source files)")

def main():
    all_studio_files = collect_all_src_files(include_studio=True)
    engine_only_files = collect_all_src_files(include_studio=False)

    # 1. Build OpenAccessStudio.twinproj (ALL files in src/ including src/studio/**)
    build_twinproj(
        root_name="OpenAccessStudio",
        output_path=OUTPUT_STUDIO_TWINPROJ,
        app_title="OpenAccess Studio",
        description="OpenAccess Studio Desktop Application - Microsoft Access Environment",
        project_id="{7B12C45E-3D89-4FA1-901B-E567A8C9D012}",
        startup_object="MainForm",
        include_forms_pkg=True,
        file_tuples=all_studio_files,
    )

    # 2. Build OpenAccess.twinproj (All non-studio files in src/)
    build_twinproj(
        root_name="OpenAccess",
        output_path=OUTPUT_ENGINE_TWINPROJ,
        app_title="OpenAccess Engine",
        description="OpenAccess Native Jet4/ACE Database Engine",
        project_id="{3A91B24C-8E12-4D50-A123-C456E789F001}",
        startup_object="Sub Main",
        include_forms_pkg=False,
        file_tuples=engine_only_files,
    )

if __name__ == "__main__":
    main()
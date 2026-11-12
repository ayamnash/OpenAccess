OPENACCESS STUDIO — TECHNICAL ARCHITECTURE, ENGINE INDEPENDENCE, PROJECT BRANCHES & ROADMAP
[🌐 github (https://github.com/ayamnash/OpenAccess)
[🌐 Short videos to introduce the project (https://reelaivideo.com/?community=openaccess)
1. PROJECT VISION & STRATEGIC GOAL
OpenAccess Studio (F:\NEW_MSACCESS) is the foundational first step toward building a standalone, modern desktop database environment and application development platform that runs parallel to Microsoft Access. Written in twinBASIC (https://twinbasic.com/), its goal is to read, create, query, and manipulate native Microsoft Access database files (.accdb and .mdb) directly at the binary page level while providing an independent desktop IDE and runtime environment.

2. INTERNAL DATABASE ENGINE: 100% STANDALONE & ZERO MICROSOFT ACCESS / ACE DEPENDENCY
Yes — the internal database engine in OpenAccess Studio is completely independent. It does NOT require Microsoft Access, Microsoft Office, the Microsoft Access Database Engine Redistributable (ACE.OLEDB / ACE DAO), or Windows Jet DLLs to be installed on the machine.

How the Native Engine Works Internally:
- Direct Binary File I/O (FormatProbe.twin, CatalogReader.twin, PageWriter.twin): Opens .accdb (ACE 12/14/16) and .mdb (Jet 4) files directly via low-level 4096-byte page reads and writes.
- Native Table & Page Decoder (CatalogReader.twin, RowDecoder.twin): Parses Page 0 database headers, RC4 page headers, Type 0x02 Table Definition (TDEF) pages, Type 0x01 Data pages, Type 0x04 B-Tree Index pages, Usage Maps (Type 0 inline and Type 1 reference bitmaps), and LVAL (Long Value) single-chunk and multi-chunk chains for Memo and LongBinary (BLOB) columns.
- Native Row Packer & Index Writer (RecordWriter.twin): Packs fixed-length columns, variable-length offset tables, null bitmasks, AutoNumber counters, and B-Tree leaf index keys (both Jet 4 Legacy 1-byte and Access 2010+ General 2-byte sort weights) directly onto 4096-byte pages with transaction rollback support.
- Native DAO Compatibility Layer (DaoEngine.twin): Implements a self-contained DAO object model (DBEngine, Workspace, Database, TableDefs, TableDef, Fields, Field, Indexes, Index, QueryDefs, QueryDef, Relations, Relation, Recordset) and an internal SQL engine supporting SELECT, INNER/LEFT/RIGHT JOIN (multi-table hash joins), WHERE, GROUP BY, ORDER BY, INSERT, UPDATE, DELETE, CREATE TABLE, and ALTER TABLE.
- Native System Catalog Interoperability: Reads and writes MSysObjects, MSysQueries, MSysRelationships, MSysACEs, and MSysAccessStorage directly so files created or modified by OpenAccess Studio can be opened in Microsoft Access and vice versa.

3. WHAT HAS BEEN ACCOMPLISHED SO FAR
- Full Binary Read/Write for Tables: Creating tables, modifying schemas (adding/dropping columns, Primary Keys, Required, AllowZeroLength, DefaultValue, ValidationRule), and editing records in Datasheet View.
- Foreign Key Relationships & Lookup Resolution (LookupCache.twin): Reading and writing MSysRelationships, enforcing referential integrity (including Cascade Update and Cascade Delete), and resolving Foreign Key Lookup displays (ComboBox bound ID to display text) without false self-lookup on Primary Keys.
- Query Engine & MSysQueries Catalog Persistence (DaoEngine.twin): Parsing SQL into MSysQueries rows (Attributes 0, 255, 1, 3, 5, 6, 7, 8, 11, 254), supporting single-table and multi-table INNER/LEFT/RIGHT JOIN queries, visual QBE grid editing, and interactive Join deletion/modification.
- Native Access Form & Report Stream Decoding (AccessStreamDecoder.twin, StudioController.twin): Reading MSysAccessStorage Form/Report DirData, TypeInfo, and Blob property streams to render existing Access forms and controls on an owner-drawn canvas.
- MS-OVBA Decompression & Inspection (VbaProjectStore.twin, VbaLexer.twin, VbaParser.twin): Decompressing MS-OVBA compressed streams (dir and module streams) from MSysAccessStorage to display native Form class modules (Form_&lt;Name&gt;) and standard VBA modules in the built-in VBE editor, plus interpreting core DoCmd actions (DoCmd.OpenForm, DoCmd.Close, DoCmd.OpenQuery, DoCmd.RunSQL, DoCmd.GoToRecord, MsgBox).

4. THE TWO PROPOSED INDEPENDENT PROJECT BRANCHES
To avoid the fragility of reverse-engineering undocumented Microsoft Access form binaries and compiled VBA p-code caches, the project is structured around two independent strategic branches:

Branch 1 — Data & Query Interoperability + Native OpenAccess Forms/Reports (Recommended Core Path):
- Scope: 100% binary compatibility with Microsoft Access strictly at the Data Engine layer (Tables, Relationships, Indexes, Queries in MSysObjects / MSysQueries / MSysRelationships, Linked Tables, and Front-End / Back-End Database Splitting).
- Forms, Reports & Code: OpenAccess Studio provides its own modern, native Form Designer, Report Designer, and Scripting/Code Engine stored in clean, documented catalog structures (or standalone project files) with zero dependency on MS Access's proprietary MSysAccessStorage Form Blob or undocumented VBA p-code streams.
- Benefit: Databases (.accdb / .mdb) can be shared, split, and queried seamlessly between Microsoft Access and OpenAccess Studio, while OpenAccess Studio gets a fast, modern UI and form/report engine unconstrained by 1990s Access binary quirks.

Branch 2 — Direct In-Place Editing of Native MS Access Forms (Events) & VBA Modules:
- Scope: Without designing new native Access forms from scratch, allow opening an existing .accdb file, inspecting its native Access Forms and Standard Modules, editing event procedures (e.g., CommandButton_Click) or VBA modules, and writing those changes back into MSysAccessStorage so Microsoft Access executes the updated code.
- Technical Reality: Requires byte-for-byte compliance with undocumented MS Access internal structures (MSysAccessStorage multi-page B-Tree indexes, MS-OVBA dir stream, _VBA_PROJECT compiled p-code cache invalidation, and Access Form Blob HasModule/Event flags).

5. CURRENT CHALLENGES & ACTIVE ISSUES
-An error sometimes occurs when creating a query consisting of two tables or a table and a query linked by a relationship, causing Microsoft Access to display "not recognized format". After repairing the database, an error table appears with the codes -1206 -3003.
- MSysAccessStorage & _VBA_PROJECT Binary Fragility in Microsoft Access:
  When OpenAccess Studio modifies a VBA module stream inside MSysAccessStorage, Microsoft Access checks the undocumented _VBA_PROJECT binary stream (which caches precompiled VBA p-code and project state) and the multi-page B-Tree indexes of MSysAccessStorage. Any mismatch between the compressed source text, the PerformanceCache p-code header, the dir stream offsets, or the MSysAccessStorage B-Tree leaf pages causes Microsoft Access to display:
  1) "The database cannot be opened because the VBA project contained in it cannot be read." (which prompts Access to delete the entire VBA project).
  2) "Cannot open database ''. It may not be a database that your application recognizes, or the file may be corrupt." (triggered when MSysAccessStorage page slots or B-Tree index pointers are altered in a way ACE rejects).
- Query Designer (QBE) Round-Trip Edge Cases:
  Editing existing complex queries in-place (rather than saving as a new query) and ensuring all column aliases and table qualifiers in MSysQueries Attribute 6 and Attribute 7 match MS Access's exact expectations without prompting for unknown parameters.
- Front-End UI Overhaul:
  The current legacy single-window toolbar and property sheet UI in MainForm.twin is cluttered and needs a clean, modern redesign separated by workflow.

6. OFFICIAL TWINBASIC ROADMAP (https://twinbasic.com/roadmap)
According to the official twinBASIC Roadmap (updated April 17, 2026 by TWINBASIC LTD, https://twinbasic.com/roadmap):
- Strategic Context: TWINBASIC LTD prioritized "Fusion" technology (enabling seamless interoperability between 32-bit and 64-bit components, including ActiveX) and completed its corporate transition and strategic investment (https://twinbasic.com/news/twinbasic-investment-july2026) to accelerate long-term development.
- 2026 Q2-Q4 (April - December 2026):
  * General bug-fixing and compatibility improvements.
  * Completion of all remaining intrinsic control properties and methods.
  * Support for external source files linked from the main .twinproj file, enabling clean Git/source-control workflows.
  * Mnemonics support (almost finished).
  * UserControl property pages support (almost finished).
  * Partial-recompilation support for much faster editing and build times in large projects (such as OpenAccess Studio).
  * Out-of-process debugging for ActiveX DLLs.
  * LLVM optimized compilation support (available to paid subscribers).
  * Completion of missing App object methods (in progress).
  * Version 1 Release Candidate (RC) builds available within this period.
- Tentative Version 1 Release Schedule:
  * Release Candidate: November 16, 2026.
  * Official v1.0 Release Date: December 14, 2026.
- 2027 Q1 (January - March 2027):
  * New IDE features including rename-refactoring and Test Explorer.
  * Start of Analysis Extension API.
  * Full vbWatchdog global error-handling support.
  * Multi-threading syntax support.
  * Start of cross-platform compilation support for x86/x64 Linux and macOS (Ultimate Edition subscribers).
- 2027 Q2 Onwards (April 2027+):
  * Cross-platform support for ARM Linux, macOS, and Android (Ultimate Edition subscribers).
  * Reimplementation of all remaining shipped VB6 controls (Winsock, MAPI, Adodc, DataGrid, MSCOMM).

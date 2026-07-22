# MAC Analyzer Pro

MAC Analyzer Pro is a web application for MAC inventory analysis, two-file
enrichment, OUI/vendor/model detection, history, comparisons, analytics,
dashboards, topology, and export.

## Primary autonomous mode

The supported user entry point is `index.html`. It works in a Chromium-based
browser without Python, EXE, CMD, administrator rights, or a backend process.
For distribution to another computer, build the single-file edition:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_html_portable.ps1
```

Open `portable/html/MAC-Analyzer-Pro.html`. This generated file contains the
frontend, styles, XLSX reader, enrichment logic, history, and local database
modules. Do not edit it directly; rebuild it from the source files.

`mac_analyzer_standalone.html` is a legacy parity artifact and is not the main
application. New functionality belongs in `index.html`, `app.js`, and
`frontend/`.

## Local data

Autonomous results and snapshots are stored in IndexedDB in chunks. Only the
current result page remains in JavaScript memory. The application can also use
a user-selected local folder for portable database, imports, exports,
settings, logs, and backups. Browser security requires the user to grant this
folder once; a plain HTML page cannot silently write an arbitrary disk path.

To move data to another browser or computer, select the same local data folder
or export and import the portable `.madb` database from the Data section.

Large XLSX files are read from `File.slice()` as a ZIP stream. The complete
workbook is not copied into browser heap, temporary enrichment rows are stored
in IndexedDB, and abandoned rows from interrupted runs are pruned on startup.

## Optional backend

`server.py` provides HTTP API and centralized SQLite storage for development or
multi-user deployments. It is optional and is not required by the autonomous
HTML application. Backend domain logic lives under `backend/services/`, and
runtime paths are managed by `backend/services/system/storage_paths.py`.

## Project checks

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1
.venv\Scripts\python.exe -m tests.test_web_api_ui_smoke
powershell -ExecutionPolicy Bypass -File scripts/build_html_portable.ps1
```

The repeated-enrichment suite includes real XLSX parsing, chunked IndexedDB
snapshots, persistence compaction, and backend SQLite regression coverage.

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md),
[README_WEB.md](README_WEB.md), and [PARITY_REGISTRY.md](PARITY_REGISTRY.md) for
architecture, API, and PyQt parity details.

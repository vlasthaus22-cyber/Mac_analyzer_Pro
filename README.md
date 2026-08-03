# MAC Analyzer Pro

MAC Analyzer Pro is a web application for MAC inventory analysis, multi-file
enrichment, OUI/vendor/model detection, history, comparisons, analytics,
dashboards, topology, and export.

An optional third DDIO export is kept outside normal enrichment. Reservation
and lease MAC columns are matched independently; when a device moves to a
different switch IP, DDIO can show an underlined candidate device IP in the
results table. The hint never overwrites devices, history, snapshots, or exports.

Analytics change tabs open the journal with an explicit active category for
all, critical, added, missing, or modified devices. Reopening the journal
clears stale category filters; the same behavior is available without backend.

## Primary autonomous mode

In a downloaded GitHub Release, launch the root `MAC-Analyzer-Pro.html`. It
works in a Chromium-based browser without Python, EXE, CMD, administrator
rights, or a backend process. `index.html` is the development source page and
should only be opened from the project tree while developing the application.
To rebuild the user-facing single-file edition:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_html_portable.ps1
```

Open `portable/html/MAC-Analyzer-Pro.html` after a local build. This generated file contains the
frontend, styles, XLSX reader, enrichment logic, history, and local database
modules. Do not edit it directly; rebuild it from the source files.

For a release archive containing the entire tracked project plus the generated
autonomous HTML, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_full_project_release.ps1
```

The full-project builder includes every Git-tracked file and verifies that no
source file is omitted. User databases, imports, exports, logs, secrets, caches,
virtual environments, and previous build output remain excluded.

To create the all-in-one Windows release containing the ready runtime, clean
initialized SQLite database, OUI reference, autonomous HTML, and the complete
source project, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_everything_release.ps1
```

To combine the current fixed program with the preserved working database,
history, snapshots, mappings, imports, and backups from v1.0.27, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_v1027_data_release.ps1
```

Release artifacts use short, stable names: `MAC-Analyzer-<version>-Browser.zip`,
`MAC-Analyzer-<version>-Source.zip`, `MAC-Analyzer-<version>-Windows.zip`, and
the complete data package `MAC-Analyzer-<version>-Full.zip`. The directory at
the root of each ZIP uses the same short name.

The migration works on an archive copy and removes saved API keys, passwords,
webhooks, tokens, and engineering sessions before release packaging.

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

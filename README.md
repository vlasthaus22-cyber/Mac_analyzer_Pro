# MAC Analyzer Pro

MAC Analyzer Pro is a web application for MAC inventory analysis, multi-file
enrichment, OUI/vendor/model detection, history, comparisons, analytics,
dashboards, topology, and export.

An optional third DDIO export is kept outside normal enrichment. Reservation
and lease MAC/IP pairs are mapped independently, including columns after H;
the DDIO selectors always display Excel letters such as I, J, and AA. When a
device moves to a different switch IP, DDIO can show an underlined candidate
device IP in the results table. The hint never overwrites devices, history,
snapshots, or exports. A `❗` warning beside the MAC in change history preserves
the display-only DDIO candidate IP and explains that it appeared after a switch
IP change; no device field is replaced. Legacy DDIO mappings with one shared IP
column remain compatible.

Analytics change tabs open the journal with an explicit active category for
all, critical, added, missing, or modified devices. Reopening the journal
clears stale category filters; the same behavior is available without backend.

Repeated enrichment restores the newest non-empty manufacturer, model, IP,
physical address, room, SmartRoom identifier, switch IP, and switch port for
the exact MAC from earlier exports. A known physical address is also reused for
other devices on the same switch IP. Values present in the current export are
never overwritten by historical values. The backend uses indexed SQLite
lookups; autonomous mode keeps the exact device history in IndexedDB and
processes it in bounded chunks.

Version v1.0.40 also learns persistent Smartroom ID-to-room and switch
IP-to-physical-address relationships during normal analysis. DDIO switch moves
are recorded from the compared exports even when SQLite has no earlier row, so
the candidate IP warning remains visible in results and change history. The
analytics and movement-history searches update while typing and include MAC,
model, address, Smartroom and DDIO candidate fields. Theme-aware foregrounds
keep selected controls and severity badges readable in both themes.

Version v1.0.41 bundles the complete public IEEE Registration Authority
catalogue for MA-L, MA-M, MA-S, IAB, and CID: 58,361 HEX assignments at build
time. Vendor lookup uses the valid 24-, 28-, and 36-bit MAC assignment sizes;
CID remains visible in the catalogue but is not misused as a MAC manufacturer.
The update utility `tools/update_ieee_registry.py` refreshes both the compressed
backend catalogue and the offline browser module from the official IEEE CSVs.

Every observed device is now retained in a cumulative inventory in SQLite and
IndexedDB. The **All devices XLSX** export streams the entire inventory instead
of exporting only the newest upload. The portable MADB carries the inventory,
learned vendor/model mappings, switch-IP/address mappings, Smartroom mappings,
snapshots, and movements to another computer. When the project is launched by
`START_MAC_ANALYZER.cmd`, the browser automatically connects to the database
from the program folder; a directly opened autonomous HTML remains backend-free.
DDIO also compares a new upload with the stored device history, so a switch-IP
change is detected even when the previous export is not loaded in the current
workspace. IndexedDB version alignment and short-lived analytics/history render
caches improve tab opening and repeated navigation.

Version v1.0.42 keeps numbered rooms such as `Переговорная 1` and
`Переговорная 2` separate, while stored identifiers continue to resolve to
their exact room names. Automatic vendor, model, physical-address, and room enrichment
continues to reuse exact-MAC history and switch-IP mappings. Enrichment and
mapping files no longer replace the primary filename on resulting devices;
Analytics, History, and comparison selectors show only completed final
enrichments and select the previous/latest pair by default.

Version v1.0.43 applies switch-IP/address and vendor/model rules directly to
the current final result. Its snapshot identifier, source filename, timestamp,
and position in Analytics remain unchanged, so applying a mapping no longer
creates a separate analytical upload. Autonomous IndexedDB uses a temporary
chunked copy and an atomic key swap to keep large results bounded and
recoverable; SQLite updates the same snapshot ID. Enrichment continues to fill
only missing address, vendor, and model values and preserves explicit data from
the current file. Learned 3–5-byte model prefixes can now be downloaded as CSV.
Analytics expand/collapse controls and selected-card labels use theme-aware
foreground colors on hover and in both themes.

Version v1.0.44 preserves `Smartroom ID` and the room name as independent
columns. Smartroom ID is used as the stable identity only when counting rooms,
so two rooms with the same display name and different IDs remain distinct.
The full JSON report is valid, human-readable, streamed across lines, and now
contains the cumulative all-device inventory, including MAC addresses absent
from the latest upload. MAC chronology merges browser and SQLite evidence
without allowing a sparse duplicate to erase values present in an older final
export; matching history rows repair legacy snapshot persistence gaps.

Version v1.0.45 makes every ordinary table header interactive: click once for
ascending order and again for descending order. The main result table sorts
the complete backend snapshot; autonomous IndexedDB scans chunks and retains a
fixed 100,000-row sort window instead of copying the full database into memory.
Search input is debounced, obsolete requests are cancelled, recent result
pages and analytics are cached, and heavy view rendering begins after the new
screen is visible. Device dialogs show the current row immediately and cache
the completed chronology for fast reopening. Empty values are placed last and
numbers, IP-like values, and dates use natural ordering.

The Smartroom monitoring stage adds lazy tab mounting through
`DocumentFragment`, Web Worker aggregation, and a 20-row virtual window for
tables over 100 rows. `Smartroom ID` is the room identity, while its display
name remains a separate field. The **Rooms**, **IP history**, and **Room
chronology** views show missing equipment, switch-IP changes with DDIO
`Possible_IPs`, and the full replacement chain. Three locally bundled Chart.js
4.5.1 charts update from snapshot history. A configurable DDIO URL is fetched
on startup; the newest IndexedDB `DDIO_Snapshot` is used when the URL is not
available. The browser database also exposes the requested `Equipment`,
`History`, and `DDIO_Snapshot` object stores.

Version v1.0.47 completes the full frontend/backend audit in the original
`vlasthaus22-cyber/Mac_analyzer_Pro` release line. Null or blank Smartroom IDs are
skipped safely, while added and removed devices are counted by
the composite `smartroom_id + mac` identity. The selected room survives tab
switches through `sessionStorage`. IP warnings are emitted only when a trimmed
switch IP differs from the preceding persisted snapshot. MAC history is merged
into a complete first-to-current chain, and the separate `RoomTimeline` module
renders both a horizontally scrollable chronology and an Added/Removed table.
The ARP cache resolves a physical MAC with the explicit `MAC не найден`
fallback; unknown models can be entered from the chronology and are reused by
future enrichments through the IndexedDB `KnownModels` store. IndexedDB v8
adds `by_smartroom`, `by_mac`, `by_switch`, and `by_timestamp` without deleting
existing browser data. DDIO now indexes possible IPs by MAC and Device ID and
shows them in an accessible dropdown on `.critical-change` rows. Chart instances are destroyed before refresh, legends and
value labels are enabled, and the total comparison shows the percentage
relative to the previous snapshot. Chart failures and empty datasets now show
an explicit UI state instead of a blank canvas. All chronology timestamps are
normalized to UTC, dynamic intervals are calculated from milliseconds, and
missing dates never break rendering. Room views include an instant city filter.
IPv4/IPv6 values from DDIO are validated before warning badges are rendered.
Virtual tables use a fixed 44-pixel row contract and ignore their own DOM
mutations, eliminating scroll jumps. Navigation is grouped into collapsible
Processing, Monitoring, and Management sections. A 10,000-row worker regression
verifies bounded aggregation below 500 ms.

In backend mode, the Data screen can upload a `.db`, `.sqlite`, or `.sqlite3`
file. The server verifies the SQLite header and integrity, stores the uploaded
copy under `data/imports`, and additively merges supported MAC Analyzer tables;
it never replaces or truncates the active user database.

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

## Local development with Live Server

Open the repository in Visual Studio Code, run **Live Server** for `index.html`,
and use the generated `http://127.0.0.1:.../index.html` address. Opening the
source page through HTTP avoids browser restrictions applied to `file://`.
Alternatively, run `python server.py` and open `http://127.0.0.1:8080`.

Minimal DDIO JSON accepted by the Smartroom loader:

```json
[
  {
    "Smartroom_ID": "SR-001",
    "room": "Переговорная 1",
    "mac": "00:11:22:33:44:55",
    "ip_switch": "10.10.0.12",
    "switch_port": "Gi1/0/7",
    "reservation_mac": "00:11:22:33:44:55",
    "reservation_ip": "192.168.10.21",
    "lease_mac": "00:11:22:33:44:55",
    "lease_ip": "192.168.10.22",
    "Possible_IPs": ["192.168.10.21", "192.168.10.22"]
  }
]
```

The autonomous HTML requires no environment variables. The DDIO endpoint is
saved in the **Ссылка на выгрузку DDIO** field, or can be supplied before app
startup as `window.MAC_ANALYZER_API_URL`. Backend deployments may set
`MAC_ANALYZER_HOST`, `MAC_ANALYZER_PORT`, `MAC_ANALYZER_DATA_DIR`,
`MAC_ANALYZER_DATABASE_PATH`, and `MAC_ANALYZER_ENGINEERING_PASSWORD`.

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

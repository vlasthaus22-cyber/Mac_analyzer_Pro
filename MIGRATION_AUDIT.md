# MAC Analyzer Pro: PyQt -> Web parity audit

Status: complete.

This audit reflects the current web system with frontend, backend REST APIs and
SQLite persistence. The machine-checkable source of truth is
`GET /api/parity/status`; the downloadable detailed report is
`GET /api/parity/report`.

## Current Coverage

- PyQt blocks covered by web equivalents: 31/31.
- PARITY_REGISTRY.md requirements: 74/74.
- Missing web equivalents: 0.
- Unchecked items in `PARITY_REGISTRY.md`: 0.
- Legacy SQLite import: available through `GET /api/legacy/import/status` and
  protected `POST /api/legacy/import`.
- UI visibility: Settings contains the PyQt -> Web parity status block with a
  detailed list and JSON export.

## v1.0.46 Smartroom audit

- Null/blank Smartroom IDs are skipped safely and reported without throwing.
- Snapshot math and additions/removals use the composite `smartroom_id + mac`
  identity; percentage change is based on the previous snapshot count.
- MAC and room chronology preserve every ordered appearance and replacement.
- The primary final export is authoritative; enrichment can only fill blanks.
- DDIO switch-IP warnings compare the current trimmed value strictly against
  persisted history, never against a secondary file in the same analysis.
- Lazy tabs, cached in-flight requests, Web Worker aggregation and twenty-row
  virtual windows keep large UI updates bounded and responsive.

## Covered PyQt Areas

- Database management and legacy SQLite migration.
- MAC history, movements and extended history search/statistics.
- Vendor/model learning history, uploads and mapping learning.
- IP address mapping import, autodetection, apply and export.
- Column detection, conflict visibility, mapping summary and saved preferences.
- OUI formatting and vendor/model detection settings.
- Single-file analysis with backend import, preview, manual mapping and SQLite
  snapshot/history support.
- Multi-file enrichment with jobs, progress and cancellation.
- Two-file and multi-file comparison with exports.
- Time statistics, charts, dashboard, topology and clustering.
- Data quality analysis and saved reports.
- Notifications, scheduler, queued files and API enrichment.
- Export to CSV, TXT, HTML, JSON, YAML, XLSX and PDF.
- Single-device and model/prefix analytics.
- Theme selection, engineering mode, settings, autosave and logging.
- Role-aware in-app guide and read-only system diagnostics for frontend files,
  storage directories, SQLite integrity/tables, API routes, parity and XLSX
  Out of Memory guards.

## Verification Commands

```powershell
.venv\Scripts\python.exe -m tests.test_parity_status
.venv\Scripts\python.exe -m tests.test_web_api_ui_smoke
.venv\Scripts\python.exe -m tests.test_legacy_migration_service
```

## Architecture Audit

- `app.js` is the browser UI coordinator. The complete Excel report schema,
  history partitioning and row mapping are isolated in
  `frontend/full-xlsx-report.js`; ZIP/XML writing remains in
  `frontend/xlsx-exporter.js`.
- `frontend/mac-chronology.js` owns point lookup, merging and presentation of a
  single MAC timeline across browser and backend history.
- Complete snapshots and per-MAC history are streamed through
  `frontend/browser-snapshot-store.js`. Neither report module hydrates all
  saved snapshots into a second device collection.
- Frontend source modules are embedded by `scripts/build_html_portable.ps1`;
  generated files under `portable/` are never hand-edited.
- Backend domain behavior is grouped under `backend/services/analytics`,
  `comparison`, `detection`, `exporting`, `integrations`, `system`, and
  `workspace`. Root service files remain compatibility wrappers.
- The PyQt source remains an immutable parity reference. Current machine
  parity has no missing equivalent and no unchecked registry item.

## Latest Verification

- Full automated suite: 95/95 Python test files, 299/299 test functions, plus
  all frontend Node regression and syntax checks.
- Smartroom worker performance: 10,000 composite `smartroom_id + mac` rows were
  aggregated in 81.7 ms in the release run, below the 500 ms requirement.
- The complete browser Excel report is verified as a real ten-sheet XLSX with
  current devices, analytics, snapshots, every available MAC appearance,
  changes, invalid rows, source-file metadata, references, and settings.
  History is partitioned by the Excel row limit and the complete workbook has
  a 512 MB bounded-memory guard.
- System diagnostics: healthy, readiness 100%, 8/8 checks, SQLite
  `PRAGMA quick_check: ok`, 14/14 required tables.
- Browser XLSX stress test: 100,000 rows and 800,000 cells parsed by the
  browser-only streaming reader in 527 ms with 5 progress updates and no tab
  crash, console error or Out of Memory error.
- Two-file enrichment stress test: 100,000 primary plus 100,000 enrichment
  rows merged in 2.63 seconds; the detection context stayed at 222.1 MB and
  avoided a duplicate similarity index when vendor/model values were already
  present.
- Repeated browser enrichment now persists full local snapshots in a separate
  IndexedDB store, retains only a 500-row preview in workspace state and uses a
  compact previous-result index. The standalone HTML applies the same bounded
  snapshot/DOM policy. Room occupancy analytics is available in local and REST
  reports with assigned, unassigned, percentage, average and per-room counts.
- Cross-browser folder restore now discovers `database/mac-analyzer-data.madb`
  from a selected directory even without the File System Access API. Snapshot
  rows stream directly into chunked IndexedDB while only a 250-row preview is
  retained in the live workspace, so restoring a large shared database does not
  create a second full JavaScript copy.
- Repeated two-file stress verification: four consecutive enrichments of
  50,000 primary plus 50,000 enrichment rows completed in 3.08-3.13 seconds
  per round; traced live allocations returned to 0.0 MB after every round and
  the peak stayed flat at 67.3 MB. Browser UI opened on `#analytics`, all three
  memory/persistence modules reported `ready`, and the console had no errors.
- Autosave on interval, manual save and page close now always sends compact
  metadata rather than serializing the live dataset. Standalone queue rows are
  shared without cloning and released after completion. External API enrichment
  resolves server datasets by snapshot ID and returns a bounded result page.
- Snapshot creation, IP mapping, analysis notifications and scheduler queueing
  now resolve compact `snapshotId`/`fileToken` references. Applying IP mappings
  writes a new full SQLite snapshot and returns only a bounded page. Browser-only
  export stops with a controlled memory-limit message before building an unsafe
  in-memory table.
- Browser-only enrichment now validates the combined rows and cells of the
  primary and all enrichment files before allocating its MAC index. The portable
  standalone HTML additionally rejects unsafe compressed, expanded XML and
  shared-string XLSX sizes before decompression.
- Modular browser import now rejects unsafe source/batch sizes, ZIP entry counts,
  expanded workbook sizes and low-heap reads before allocating XLSX buffers.
  Backend single-file analysis uses binary upload plus `fileToken`, stores the
  full SQLite snapshot and returns a bounded page without Base64 or full row copies.
- The complete standalone inline JavaScript is compiled during every project
  test run; this also corrected the Raspberry Pi `DCA632` vendor-prefix key and
  the help screen's engineering-session function binding.
- IEEE OUI reference: 39,749 manufacturer assignments are stored under
  `data/reference`; analysis loads only prefixes required by the current batch.
- REST/UI smoke covers import, two-file enrichment, OUI 3/4/5 detection,
  vendor/model history, dashboard, snapshots, history, exports, engineering
  access and diagnostics.
- Portable Windows backend is assembled as a self-contained PyInstaller folder.
  Its launcher resolves a relocated path with spaces and Cyrillic characters,
  waits for `/api/health`, and keeps SQLite/history outside the executable in
  the package's structured `data` directory.
- Browser-only enrichment now checks text volume and live JS heap headroom
  before allocating result indexes. Local results are persisted once in the
  dedicated snapshot store, while repeated standalone runs release the prior
  result and clear their temporary MAC index.

Last verified state:

```text
status=complete
pyqtBlocks=31
webComplete=31
missingEquivalents=0
registryUnchecked=0
registryChecked=53
registryTotal=53
```

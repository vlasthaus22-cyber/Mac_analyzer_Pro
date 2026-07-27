# Frontend modules

- `file-readers.js` reads CSV, TSV, JSON and XLSX directly in the browser.
- `workspace-file-lifecycle.js` replaces enrichment inputs after a completed run while snapshots and movement history remain persisted.
- `memory-guard.js` bounds autonomous datasets and provides copy-free paging, signatures and cooperative processing.
- `state-persistence.js` prevents large server-backed XLSX rows and result pages from being cloned into browser storage.
- `browser-snapshot-store.js` keeps complete browser-only snapshots in a dedicated IndexedDB store; the live workspace keeps only metadata and a 500-row preview.
- `mac-chronology.js` loads one requested MAC from compact snapshot metadata and IndexedDB chunks, merges browser and backend appearances, history and movements, and renders the device timeline without hydrating full snapshots.
- `xlsx-exporter.js` creates styled single- or multi-sheet XLSX workbooks in the browser with frozen headers, filters, column widths and bounded-memory streaming. The full report streams devices and every saved MAC appearance from IndexedDB into one workbook with analytics, snapshots, changes, errors, source-file metadata, references, and settings without hydrating the full device collection.
- `full-xlsx-report.js` owns the report schema, history-sheet partitioning and row mapping. `app.js` only supplies state/streams and coordinates progress plus download.
- Repeated browser enrichment streams worksheets and shared strings, releases transient dashboard/result references, and removes consumed input files from the next workspace.
- Backend imports send the original binary file, retain only a bounded 100-row preview in browser memory, and stream full rows from `data/imports/workspace-cache/workspace_cache.db` during enrichment.
- Autonomous enrichment stores complete results in chunked IndexedDB snapshots and keeps only the current result page in live JavaScript state.
- Autonomous row merging uses the temporary IndexedDB `enrichmentRows` store instead of a full in-memory device `Map`.
- Reopening, filtering and paging an autonomous snapshot stream its 1,000-row chunks instead of hydrating the complete result array.
- `app.js` remains the application controller while modules are extracted from it.
- `index.html` loads modules with classic scripts so local `file://` startup keeps working.

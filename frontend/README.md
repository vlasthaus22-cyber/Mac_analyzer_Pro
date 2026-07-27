# Frontend modules

- `file-readers.js` reads CSV, TSV, JSON and XLSX directly in the browser.
- `workspace-file-lifecycle.js` replaces enrichment inputs after a completed run while snapshots and movement history remain persisted.
- `memory-guard.js` bounds autonomous datasets and provides copy-free paging, signatures and cooperative processing.
- `state-persistence.js` prevents large server-backed XLSX rows and result pages from being cloned into browser storage.
- `browser-snapshot-store.js` keeps complete browser-only snapshots in a dedicated IndexedDB store; the live workspace keeps only metadata and a 500-row preview.
- `xlsx-exporter.js` creates real XLSX workbooks in the browser and streams every chunk of the active IndexedDB snapshot without hydrating the full device collection.
- Repeated browser enrichment streams worksheets and shared strings, releases transient dashboard/result references, and removes consumed input files from the next workspace.
- Backend imports send the original binary file, retain only a bounded 100-row preview in browser memory, and stream full rows from `data/imports/workspace-cache/workspace_cache.db` during enrichment.
- Autonomous enrichment stores complete results in chunked IndexedDB snapshots and keeps only the current result page in live JavaScript state.
- Autonomous row merging uses the temporary IndexedDB `enrichmentRows` store instead of a full in-memory device `Map`.
- Reopening, filtering and paging an autonomous snapshot stream its 1,000-row chunks instead of hydrating the complete result array.
- `app.js` remains the application controller while modules are extracted from it.
- `index.html` loads modules with classic scripts so local `file://` startup keeps working.

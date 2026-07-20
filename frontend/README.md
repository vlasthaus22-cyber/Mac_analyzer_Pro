# Frontend modules

- `file-readers.js` reads CSV, TSV, JSON and XLSX directly in the browser.
- `memory-guard.js` bounds autonomous datasets and provides copy-free paging, signatures and cooperative processing.
- `state-persistence.js` prevents large server-backed XLSX rows and result pages from being cloned into browser storage.
- `browser-snapshot-store.js` keeps complete browser-only snapshots in a dedicated IndexedDB store; the live workspace keeps only metadata and a 500-row preview.
- Repeated browser enrichment releases the previous full result after building a compact comparison index, preventing each run from multiplying heap use.
- Backend imports send the original binary file and retain only a bounded 100-row preview in browser memory.
- `app.js` remains the application controller while modules are extracted from it.
- `index.html` loads modules with classic scripts so local `file://` startup keeps working.

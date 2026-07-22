# MAC Analyzer Pro engineering guide

## Product architecture

- `index.html`, `styles.css`, `app.js`, and `frontend/*.js` are the web frontend.
- `scripts/build_html_portable.ps1` produces the autonomous one-file HTML build.
- Generated files under `portable/` must never be edited manually.
- `server.py` is the optional HTTP and SQLite backend.
- Domain logic belongs under `backend/services/`.
- `MAC_ANALYZER финальная.py` is the original PyQt parity reference.
- Do not modify or delete the PyQt reference until parity is complete.

## Browser-only requirements

- XLSX import, analysis, enrichment, history, and export must work without backend.
- Do not require EXE, CMD, administrator privileges, or installed Python.
- Large datasets must use bounded-memory processing.
- Do not create multiple full copies of worksheets or device collections.
- Persistent browser data belongs in IndexedDB, not localStorage.
- Test repeated enrichment to prevent browser Out of Memory failures.

## Backend and storage

- Use `backend/services/system/storage_paths.py` for storage locations.
- Databases belong in `data/databases/`.
- Backups, imports, exports, logs, settings, and reference data stay in their
  designated `data/`, `config/`, or `logs/` directories.
- Never delete, truncate, migrate, or rewrite a user database during tests.
- Backend routes should delegate domain behavior to `backend/services/`.

## Generated and legacy files

- Do not commit `.venv`, caches, databases, build output, release archives,
  imported workbooks, logs, or generated portable packages.
- Root-level service modules are compatibility wrappers only.
- New code must import services through `backend.services`.
- Do not extend `mac_analyzer_standalone.html`; migrate behavior to the primary
  frontend and autonomous HTML build.

## Verification

- Run all checks with:
  `powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1`
- Run API/UI smoke coverage with:
  `.venv\Scripts\python.exe -m tests.test_web_api_ui_smoke`
- Tests belong under `tests/`; maintenance utilities belong under `tools/`.
- After parity changes, update `PARITY_REGISTRY.md` and run:
  `.venv\Scripts\python.exe tools/generate_parity_status.py`
- Verify the autonomous build with:
  `powershell -ExecutionPolicy Bypass -File scripts/build_html_portable.ps1`

## Change discipline

- Keep changes focused and preserve existing user data.
- Do not hand-edit generated release files.
- Add regression coverage for every repaired user-facing failure.
- Do not mark a parity item complete until frontend, backend where applicable,
  autonomous HTML, and tests implement the behavior.

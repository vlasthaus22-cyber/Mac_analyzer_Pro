# MAC Analyzer Pro engineering guide

## Runtime boundaries

- `index.html`, `app.js`, and `styles.css` are the web frontend.
- `server.py` owns HTTP routing, SQLite integration, and static file serving.
- Domain behavior belongs in focused modules under `backend/services/`; the
  detection family lives in `backend/services/detection/`.
- `MAC_ANALYZER финальная.py` is the original PyQt parity reference; do not
  modify it while transferring behavior to the web application.
- Browser-only XLSX and enrichment behavior must continue to work when
  `index.html` is opened without a backend.

## Data safety

- Use `storage_paths.py`; do not place databases, backups, imports, exports,
  logs, or settings back in the source root.
- Do not delete or rewrite legacy databases during tests.
- Keep generated runtime files ignored by Git.

## Verification

- Run all project checks with `powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1`.
- Regression tests live in `tests/`; do not add new `test_*.py` files to the root.
- Maintenance and migration entry points live in `tools/`.
- Run API/UI integration coverage with `.venv\Scripts\python.exe -m tests.test_web_api_ui_smoke`.
- Update `PARITY_REGISTRY.md` and run `tools/generate_parity_status.py` after a parity change.

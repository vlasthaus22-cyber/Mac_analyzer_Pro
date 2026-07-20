# Maintenance tools

- `generate_parity_status.py` rebuilds `PARITY_STATUS.json`.
- `benchmark_workspace_payload.py` measures compact workspace payloads.
- `migrate_legacy.py` runs all legacy SQLite import utilities.
- `migrate_legacy_*.py` can run one legacy import category.

Run tools from the project root, for example:

```powershell
.venv\Scripts\python.exe -m tools.generate_parity_status
```

Legacy migration commands write to the active SQLite database. Back up `data/`
before running them manually.

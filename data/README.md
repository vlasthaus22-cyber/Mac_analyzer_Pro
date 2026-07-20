# MAC Analyzer data

- `databases/` contains the active web SQLite database and its WAL/SHM files.
- `legacy/` contains source databases imported from the PyQt application.
- `backups/` contains timestamped application backups.
- `exports/` is reserved for server-side exports.
- `imports/workspace-cache/` stores bounded, expiring full tables for token-based enrichment and backend restart recovery.
- `reference/` contains portable OUI TXT/CSV registries used for automatic vendor detection. A root `oui.txt`/`oui.csv` is migrated here without overwriting an existing registry.
- `runtime/` contains disposable process state.

These paths are managed by `storage_paths.py`. Do not move an active SQLite file
while the backend is running.

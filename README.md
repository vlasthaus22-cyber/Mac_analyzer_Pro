# MAC Analyzer Pro

Web-version of MAC Analyzer Pro with an HTML/JavaScript frontend, Python
backend, SQLite storage, XLSX import and export, enrichment, history,
analytics, dashboards, OUI detection, and a portable Windows build.

## Full workspace download

The complete workspace snapshot is published in the private GitHub Release:

- [MAC Analyzer Pro v1.0.0](https://github.com/vlasthaus22-cyber/Mac_analyzer_Pro/releases/tag/v1.0.0)
- The `full-workspace` ZIP asset contains the complete local workspace,
  including `.venv`, databases, backups, imported XLSX files, settings, logs,
  OUI data, caches, build files, and the portable package.
- GitHub displays the verified SHA-256 digest and exact size beside the Release
  asset.

The local `.git` directory is repository metadata. Git recreates it when the
repository is cloned, so it is not stored inside its own file tree or archive.

## Portable Windows build

Download `MAC-Analyzer-Pro-windows-x64-3558b6c.zip` from the same Release,
extract it, and run `START_MAC_ANALYZER.cmd`. This package includes the backend
executable, frontend, Python runtime, XLSX/PDF dependencies, and OUI reference
data.

For development, setup, API routes, and operating instructions, see
[README_WEB.md](README_WEB.md).

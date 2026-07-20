# Project agent context

This directory is not used by MAC Analyzer at runtime. It stores concise
maintenance context for coding agents and automated project work.

- The executable web entry point is `index.html` served by `server.py`.
- Browser-only fallback logic remains embedded in `index.html`.
- Backend domain services are being grouped under `backend/services/`.
- Persistent data belongs under `data/`, logs under `logs/`, and local settings
  under `config/`.
- The source of truth for PyQt/Web parity is `PARITY_REGISTRY.md`.
- Standalone regression checks live under `tests/`.
- Maintenance entry points live under `tools/`.
- Run `scripts/run_tests.ps1` after changes.

Repository-wide engineering instructions are in the root `AGENTS.md` file.

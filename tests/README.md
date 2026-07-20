# Regression tests

All standalone regression and parity checks live in this directory. They do
not require pytest: use the project runner from the repository root.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1
```

Use `-Filter` to run a subset, for example `-Filter test_history_*.py`.
The runner executes every file as a `tests.*` module. An individual check can be
started portably with `python -m tests.test_name` from the project root.

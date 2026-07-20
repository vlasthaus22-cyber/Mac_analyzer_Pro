from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8-sig")


def test_frozen_backend_uses_the_executable_directory():
    server = _read("server.py")
    assert 'getattr(sys, "frozen", False)' in server
    assert "Path(sys.executable).resolve().parent" in server


def test_portable_build_is_self_contained_and_excludes_working_data():
    builder = _read("scripts/build_portable.ps1")
    assert '"--onedir"' in builder
    assert '"--contents-directory", "."' in builder
    assert '"--name", "MACAnalyzerBackend"' in builder
    assert '@("frontend", "frontend")' in builder
    assert '@("backend", "backend")' in builder
    assert 'data\\reference' in builder
    assert "data\\databases" not in builder
    assert "data\\backups" not in builder


def test_portable_launcher_resolves_a_relocated_cyrillic_path():
    powershell = shutil.which("powershell")
    assert powershell, "Windows PowerShell is required for the portable launcher"

    runtime = ROOT / "data" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="MAC Analyzer перенос ", dir=runtime) as temporary:
        relocated = Path(temporary) / "Новый компьютер" / "MAC Analyzer Pro"
        scripts = relocated / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts" / "portable_start.ps1", scripts / "portable_start.ps1")
        for name in ("server.py", "index.html", "requirements-web.txt"):
            shutil.copy2(ROOT / name, relocated / name)

        completed = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(scripts / "portable_start.ps1"),
                "-ValidateOnly",
            ],
            cwd=Path(temporary),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=20,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        report = json.loads(completed.stdout.strip())
        assert Path(report["root"]).resolve() == relocated.resolve()
        assert report["server"] is True
        assert report["index"] is True
        assert report["requirements"] is True
        assert report["portableExecutable"] is False


def test_root_launchers_delegate_to_portable_scripts():
    start = _read("START_MAC_ANALYZER.cmd")
    stop = _read("STOP_MAC_ANALYZER.cmd")
    launcher = _read("scripts/portable_start.ps1")
    assert "portable_start.ps1" in start
    assert "portable_stop.ps1" in stop
    assert 'Join-Path $root "MACAnalyzerBackend.exe"' in launcher
    assert 'Join-Path $root ".venv-portable\\Scripts\\python.exe"' in launcher
    assert "Test-MacAnalyzerHealth" in launcher
    assert 'WindowStyle = "Hidden"' in launcher
    assert "if ($argumentList.Count)" in launcher
    assert "$process = Start-Process @startParameters" in launcher
    assert "$pathKeys.Count -gt 1" in launcher
    assert 'SetEnvironmentVariable("Path", $pathValue, "Process")' in launcher


if __name__ == "__main__":
    for name, value in sorted(globals().items()):
        if name.startswith("test_") and callable(value):
            value()
    print("portable backend tests passed")

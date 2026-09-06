from __future__ import annotations

import json
import shutil
import subprocess
import sys
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
    assert '@("scripts\\portable_launcher.py", "scripts")' in builder
    assert '@("mac_analyzer_standalone.html", ".")' not in builder
    assert 'data\\reference' in builder
    assert "data\\databases" not in builder
    assert "data\\backups" not in builder
    assert "Portable frontend contains obsolete memoryGuard code" in builder
    assert "Portable frontend is stale" in builder
    assert "BUILD_INFO.json" in builder
    assert "PACKAGE_INFO.json" in builder
    assert 'administratorRightsRequired = $false' in builder
    assert '"--manifest", $manifestPath' in builder
    assert "build_source_portable.ps1" not in builder
    assert 'Join-Path $outputRoot "source"' in builder


def test_windows_fallback_never_requests_elevation():
    builder = _read("scripts/build_portable.ps1")
    manifest = _read("config/windows-as-invoker.manifest")
    launcher = _read("scripts/portable_start.ps1")
    assert 'requestedExecutionLevel level="asInvoker" uiAccess="false"' in manifest
    assert "--uac-admin" not in builder
    assert "-Verb RunAs" not in launcher
    verifier = _read("tools/verify_portable_backend.py")
    assert 'b"requestedExecutionLevel" not in manifest' in verifier
    assert 'b"asInvoker" not in manifest' in verifier
    assert 'package / "mac_analyzer_standalone.html"' in verifier
    assert "--use-package-database" in verifier
    assert '"restartPersistence": restart_persistence' in verifier


def test_source_only_portable_package_has_no_backend_executable():
    builder = _read("scripts/build_source_portable.ps1")
    assert 'source\\MACAnalyzerWebSource' in builder
    assert 'entryPoint = "server.py"' in builder
    assert 'executableBackend = $false' in builder
    assert 'Filter "*.exe"' in builder
    assert 'Filter "__pycache__"' in builder
    assert '"data\\databases"' in builder
    assert '"data\\imports"' in builder
    assert '"data\\backups"' in builder


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
    python_launcher = _read("scripts/portable_launcher.py")
    assert "portable_launcher.py" in start
    assert "portable_start.ps1" in start, "PowerShell remains only as a no-Python compatibility fallback"
    assert "portable_stop.ps1" in stop
    assert "runas" not in start.lower()
    assert "CREATE_NEW_CONSOLE" in python_launcher
    assert "administratorRightsRequired" in python_launcher
    assert "webbrowser.open" in python_launcher
    assert "/api/health" in python_launcher
    assert 'Join-Path $root "MACAnalyzerBackend.exe"' in launcher
    assert 'Join-Path $root ".venv-portable\\Scripts\\python.exe"' in launcher
    assert launcher.index("if ($python) {") < launcher.index("elseif (Test-Path -LiteralPath $portableExecutable)")
    assert 'Starting MAC Analyzer without elevation: $backendMode' in launcher
    assert "Test-MacAnalyzerHealth" in launcher
    assert 'WindowStyle = "Hidden"' in launcher
    assert "if ($argumentList.Count)" in launcher
    assert "$process = Start-Process @startParameters" in launcher
    assert "$pathKeys.Count -gt 1" in launcher
    assert 'SetEnvironmentVariable("Path", $pathValue, "Process")' in launcher


def test_python_launcher_validates_a_relocated_cyrillic_path():
    runtime = ROOT / "data" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="MAC Python launcher ", dir=runtime) as temporary:
        relocated = Path(temporary) / "Другой компьютер" / "MAC Analyzer Pro"
        scripts = relocated / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts" / "portable_launcher.py", scripts / "portable_launcher.py")
        for name in ("server.py", "index.html", "START_MAC_ANALYZER.cmd"):
            shutil.copy2(ROOT / name, relocated / name)

        completed = subprocess.run(
            [
                sys.executable,
                str(scripts / "portable_launcher.py"),
                "--root",
                str(relocated),
                "--validate-only",
            ],
            cwd=Path(temporary),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        report = json.loads(completed.stdout.strip())
        assert Path(report["root"]).resolve() == relocated.resolve()
        assert report["server"] is True
        assert report["index"] is True
        assert report["launcher"] is True
        assert report["administratorRightsRequired"] is False


if __name__ == "__main__":
    for name, value in sorted(globals().items()):
        if name.startswith("test_") and callable(value):
            value()
    print("portable backend tests passed")

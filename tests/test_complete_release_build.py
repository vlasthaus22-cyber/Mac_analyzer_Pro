from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_complete_release_contains_program_layers_without_executables():
    powershell = shutil.which("powershell")
    assert powershell
    runtime = ROOT / "data" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="complete-release-", dir=runtime) as temporary:
        completed = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts" / "build_complete_release.ps1"),
                "-OutputDirectory",
                temporary,
                "-Version",
                "test",
                "-ExcludeRuntimeData",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=90,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        report = json.loads(completed.stdout.strip())
        archive = Path(report["file"])
        assert archive.is_file()
        assert report["executableFiles"] == 0
        assert report["commandFiles"] == 0
        with zipfile.ZipFile(archive) as package:
            raw_names = package.namelist()
            assert all("\\" not in name for name in raw_names)
            names = set(raw_names)
            suffixes = {Path(name).suffix.lower() for name in names}
            required = (
                "MAC-Analyzer-Pro.html",
                "index.html",
                "app.js",
                "server.py",
                "MAC_ANALYZER финальная.py",
                "frontend/portable-database.js",
                "backend/services/workspace/enrichment_service.py",
                "backend/services/detection/vendor_detector_service.py",
                "tests/test_web_api_ui_smoke.py",
                "tools/generate_parity_status.py",
                "scripts/run_tests.ps1",
                "FILE_MANIFEST.sha256",
                "PACKAGE_INFO.json",
            )
            for expected in required:
                assert any(name.endswith("/" + expected) for name in names), expected
            assert not suffixes.intersection({".exe", ".dll", ".cmd", ".bat", ".com", ".msi"})


if __name__ == "__main__":
    test_complete_release_contains_program_layers_without_executables()
    print("complete release build test passed")

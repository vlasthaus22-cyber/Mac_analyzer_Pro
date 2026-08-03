from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")


def _tracked_files() -> set[str]:
    assert GIT
    output = subprocess.check_output(
        [GIT, "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=ROOT,
    )
    return {item.decode("utf-8") for item in output.split(b"\0") if item}


def test_everything_release_combines_runtime_autonomous_html_and_all_sources():
    powershell = shutil.which("powershell")
    assert powershell
    runtime = ROOT / "data" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="everything-release-", dir=runtime) as temporary:
        temporary_path = Path(temporary)
        fake_runtime = temporary_path / "fake-runtime"
        fake_runtime.mkdir()
        (fake_runtime / "MACAnalyzerBackend.exe").write_bytes(b"test-runtime")
        (fake_runtime / "START_MAC_ANALYZER.cmd").write_text("@echo off\r\n", encoding="utf-8")
        (fake_runtime / "PACKAGE_INFO.json").write_text("{}", encoding="utf-8")

        completed = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts" / "build_everything_release.ps1"),
                "-OutputDirectory",
                str(temporary_path / "output"),
                "-Version",
                "test",
                "-PortablePackage",
                str(fake_runtime),
                "-SkipCleanDatabase",
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
        assert archive.name == "MAC-Analyzer-test-Windows.zip"
        assert len(archive.stem) <= 32
        assert report["autonomousHtmlIncluded"] is True
        assert report["fullSourceIncluded"] is True
        assert report["windowsRuntimeIncluded"] is True
        assert report["cleanDatabaseIncluded"] is False
        assert report["userRuntimeDataIncluded"] is False

        with zipfile.ZipFile(archive) as package:
            prefix = package.namelist()[0].split("/", 1)[0] + "/"
            assert prefix == "MAC-Analyzer-test-Windows/"
            names = {name.removeprefix(prefix) for name in package.namelist()}
            assert "MAC-Analyzer-Pro.html" in names
            assert "Windows-Portable/MACAnalyzerBackend.exe" in names
            assert "Windows-Portable/START_MAC_ANALYZER.cmd" in names
            assert "README_FIRST.txt" in names
            assert "FILE_MANIFEST.sha256" in names
            tracked = _tracked_files()
            missing_sources = {
                relative for relative in tracked if f"Source/{relative}" not in names
            }
            assert not missing_sources, f"Missing source files: {sorted(missing_sources)}"


if __name__ == "__main__":
    test_everything_release_combines_runtime_autonomous_html_and_all_sources()
    print("everything release build test passed")

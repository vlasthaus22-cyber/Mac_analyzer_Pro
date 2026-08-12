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


def test_full_project_release_contains_every_tracked_file_and_no_user_data():
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    assert powershell
    runtime = ROOT / "data" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="full-project-release-", dir=runtime) as temporary:
        completed = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts" / "build_full_project_release.ps1"),
                "-OutputDirectory",
                temporary,
                "-Version",
                "test",
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
        assert report["fullTrackedProject"] is True
        assert report["runtimeDataIncluded"] is False
        archive = Path(report["file"])
        assert archive.is_file()
        assert archive.name == "MAC-Analyzer-test-Source.zip"
        assert len(archive.stem) <= 32

        with zipfile.ZipFile(archive) as package:
            raw_names = package.namelist()
            assert all("\\" not in name for name in raw_names)
            prefix = raw_names[0].split("/", 1)[0] + "/"
            assert prefix == "MAC-Analyzer-test-Source/"
            names = {name.removeprefix(prefix) for name in raw_names}
            tracked = _tracked_files()
            assert not tracked - names, f"Missing tracked files: {sorted(tracked - names)}"
            for relative in tracked:
                assert package.read(prefix + relative) == (ROOT / relative).read_bytes()

            required = {
                "START_MAC_ANALYZER.cmd",
                "STOP_MAC_ANALYZER.cmd",
                "config/windows-as-invoker.manifest",
                "mac_analyzer_standalone.html",
                "portable/.gitkeep",
                "MAC-Analyzer-Pro.html",
                "FILE_MANIFEST.sha256",
                "PACKAGE_INFO.json",
            }
            assert not required - names, f"Missing full-project files: {sorted(required - names)}"
            forbidden_runtime_suffixes = {".db", ".db-shm", ".db-wal", ".log", ".pyc", ".pyo"}
            assert not {
                name
                for name in names
                if Path(name).suffix.lower() in forbidden_runtime_suffixes
            }


if __name__ == "__main__":
    test_full_project_release_contains_every_tracked_file_and_no_user_data()
    print("full project release build test passed")

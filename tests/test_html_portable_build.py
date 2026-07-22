from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_html_portable_builder_outputs_one_self_contained_html_file():
    powershell = shutil.which("powershell")
    assert powershell
    runtime = ROOT / "data" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="html-portable-", dir=runtime) as temporary:
        completed = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts" / "build_html_portable.ps1"),
                "-OutputDirectory",
                temporary,
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        report = json.loads(completed.stdout.strip())
        files = list(Path(temporary).iterdir())
        assert len(files) == 1
        assert files[0].name == "MAC-Analyzer-Pro.html"
        assert report["executableFiles"] == 0
        assert report["commandFiles"] == 0
        assert report["backendFiles"] == 0
        html = files[0].read_text(encoding="utf-8-sig")
        assert '<script src=' not in html
        assert '<link rel="stylesheet"' not in html
        assert "window.MacAnalyzerPortableDatabase" in html
        assert "window.MacAnalyzerLocalFolderStore" in html
        assert "window.MacAnalyzerAppBootstrapped = true;" in html
        assert "window.MacAnalyzerFallbackReady = true;" not in html
        assert "xlsxWorksheetRows" in html
        assert "assertEnrichmentCapacity" in html
        assert 'const autonomousHtmlMode = browserOnlyMode || location.protocol === "file:";' in html
        assert "const backendCandidates = [];" in html


if __name__ == "__main__":
    test_html_portable_builder_outputs_one_self_contained_html_file()
    print("autonomous single HTML build test passed")

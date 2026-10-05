from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_unified_release_contains_program_runtime_source_and_sanitized_history():
    script = (ROOT / "scripts" / "build_unified_release.ps1").read_text(encoding="utf-8-sig")
    assert "build_split_data_release.ps1" in script
    assert 'packageName = "MAC-Analyzer-$Version-Full"' in script
    assert "mac_analyzer_history.db" in script
    assert "historicalDatabaseIncluded" in script
    assert "fullProgramIncluded = $true" in script
    assert "fullSourceIncluded = $true" in script
    assert "windowsRuntimeIncluded = $true" in script
    assert "autonomousHtmlIncluded = $true" in script
    assert "secretsRedacted = $true" in script
    assert "FILE_MANIFEST.sha256" in script


if __name__ == "__main__":
    test_unified_release_contains_program_runtime_source_and_sanitized_history()
    print("unified release build test passed")

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_split_release_keeps_program_complete_and_database_optional():
    script = (ROOT / "scripts" / "build_split_data_release.ps1").read_text(
        encoding="utf-8-sig"
    )
    assert "build_everything_release.ps1" in script
    assert "Full-Program.zip" in script
    assert "History-Database.zip" in script
    assert 'databaseName = "mac_analyzer_history.db"' in script
    assert 'programContainsHistoricalDatabase = $false' in script
    assert 'databaseIsSeparateAsset = $true' in script
    assert "Load SQLite database" in script
    assert "The import is additive" in script
    assert "Copy-Item -LiteralPath $preparedDatabase" in script


if __name__ == "__main__":
    test_split_release_keeps_program_complete_and_database_optional()
    print("split data release build test passed")

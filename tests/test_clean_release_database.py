from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
PYTHON = LOCAL_PYTHON if LOCAL_PYTHON.is_file() else Path(sys.executable)


def test_clean_release_database_has_complete_schema_and_no_user_rows():
    with tempfile.TemporaryDirectory(prefix="clean-release-database-") as temporary:
        data_root = Path(temporary) / "data"
        (data_root / "reference").mkdir(parents=True)
        (data_root / "reference" / ".gitkeep").write_text("", encoding="utf-8")
        completed = subprocess.run(
            [
                str(PYTHON),
                str(ROOT / "tools" / "create_clean_release_database.py"),
                "--application-root",
                str(ROOT),
                "--data-root",
                str(data_root),
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
        assert report["integrity"] == "ok"
        assert report["tables"] >= report["requiredTables"] == 20
        assert report["userDataRows"] == 0
        assert report["vendorMappings"] > 1_000
        assert report["modelMappings"] == 0
        assert report["ouiReferenceIncluded"] is True
        assert report["ieeeRegistryIncluded"] is True
        assert report["workspaceCacheIncluded"] is False

        database = data_root / "databases" / "mac_analyzer_web.db"
        assert database.is_file()
        assert database.stat().st_size == report["bytes"]
        assert not database.with_name(database.name + "-wal").exists()
        assert not database.with_name(database.name + "-shm").exists()
        assert not (data_root / "imports" / "workspace-cache").exists()
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert connection.execute("SELECT COUNT(*) FROM mac_history").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0
        finally:
            connection.close()


if __name__ == "__main__":
    test_clean_release_database_has_complete_schema_and_no_user_rows()
    print("clean release database test passed")

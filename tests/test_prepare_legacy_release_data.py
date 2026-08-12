from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
PYTHON = LOCAL_PYTHON if LOCAL_PYTHON.is_file() else Path(sys.executable)


def test_legacy_release_data_preserves_history_and_redacts_secrets():
    with tempfile.TemporaryDirectory(prefix="legacy-release-data-") as temporary:
        workspace = Path(temporary)
        legacy_root = workspace / "legacy" / "data"
        created = subprocess.run(
            [
                str(PYTHON),
                str(ROOT / "tools" / "create_clean_release_database.py"),
                "--application-root",
                str(ROOT),
                "--data-root",
                str(legacy_root),
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=90,
            check=False,
        )
        assert created.returncode == 0, created.stderr
        database = legacy_root / "databases" / "mac_analyzer_web.db"
        connection = sqlite3.connect(database)
        try:
            connection.execute(
                "INSERT INTO mac_history "
                "(mac, mac_formatted, vendor, model, source, recorded_at) "
                "VALUES ('AABBCC000001', 'AA:BB:CC:00:00:01', 'Legacy Vendor', "
                "'Legacy Model', 'v1.0.27', '2026-01-01T00:00:00Z')"
            )
            connection.execute(
                "INSERT INTO vendor_model_history "
                "(mac, vendor, model, source, observed_at) "
                "VALUES ('AABBCC000001', 'Legacy Vendor', 'Legacy Model', "
                "'v1.0.27', '2026-01-01T00:00:00Z')"
            )
            connection.execute(
                "INSERT INTO engineering_sessions "
                "(token_hash, role, permissions_json, created_at, expires_at) "
                "VALUES ('secret-hash', 'engineer', '[]', '2026-01-01', '2099-01-01')"
            )
            connection.commit()
        finally:
            connection.close()

        config = workspace / "legacy" / "config" / "mac_analyzer_settings.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps({"api_settings": {"api_key": "must-not-ship"}, "theme": "dark"}),
            encoding="utf-8",
        )
        archive = workspace / "legacy.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
            for path in (workspace / "legacy").rglob("*"):
                if path.is_file():
                    package.write(path, "MAC-Analyzer-v1.0.27/" + path.relative_to(workspace / "legacy").as_posix())

        package_root = workspace / "package"
        package_root.mkdir()
        shutil.copy2(ROOT / "server.py", package_root / "server.py")
        shutil.copytree(
            ROOT / "backend",
            package_root / "backend",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        prepared = subprocess.run(
            [
                str(PYTHON),
                str(ROOT / "tools" / "prepare_legacy_release_data.py"),
                "--legacy-archive",
                str(archive),
                "--package-root",
                str(package_root),
                "--minimum-history-records",
                "1",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=90,
            check=False,
        )
        assert prepared.returncode == 0, prepared.stderr
        report = json.loads(prepared.stdout.strip())
        assert report["databaseIntegrity"] == "ok"
        assert report["mac_history"] == 1
        assert report["vendor_model_history"] == 1
        assert report["configSecretsRedacted"] == 1
        assert report["engineeringSessionsRemoved"] == 1

        sanitized = json.loads(
            (package_root / "config" / "mac_analyzer_settings.json").read_text(
                encoding="utf-8-sig"
            )
        )
        assert sanitized["api_settings"]["api_key"] == ""
        connection = sqlite3.connect(
            f"file:{package_root / 'data/databases/mac_analyzer_web.db'}?mode=ro",
            uri=True,
        )
        try:
            assert connection.execute("SELECT COUNT(*) FROM mac_history").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM engineering_sessions").fetchone()[0] == 0
        finally:
            connection.close()


if __name__ == "__main__":
    test_legacy_release_data_preserves_history_and_redacts_secrets()
    print("legacy release data preparation test passed")

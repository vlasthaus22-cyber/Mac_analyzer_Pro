import os
import tempfile
from datetime import datetime
from pathlib import Path

from backend.services.workspace.batch_folder_service import (
    BatchFolderRegistry,
    date_from_filename,
    observation_date,
    scan_batch_folders,
)


def test_csv_dates_are_resolved_from_separated_and_compact_filenames():
    assert date_from_filename("main_2026-09-20.csv") == "2026-09-20T00:00:00Z"
    assert date_from_filename("smartroom_20092026_153000.csv") == "2026-09-20T15:30:00Z"
    assert date_from_filename("DDIO_20260921.csv") == "2026-09-21T00:00:00Z"
    assert date_from_filename("bad_20260231.csv") == ""


def test_csv_without_filename_date_uses_filesystem_timestamp():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "main.csv"
        path.write_text("MAC,IP\n001122334455,10.0.0.1\n", encoding="utf-8")
        timestamp = datetime(2025, 5, 6, 7, 8, 9).timestamp()
        os.utime(path, (timestamp, timestamp))
        info = observation_date(path)
        assert info["source"] in {"filesystem.created", "filesystem.modified"}
        assert info["date"]


def test_three_folders_are_scanned_without_reading_file_contents():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        folders = {role: root / role for role in ("primary", "smartroom", "ddio")}
        for path in folders.values():
            path.mkdir()
        (folders["primary"] / "main_20260920.csv").write_text("MAC\n001122334455\n", encoding="utf-8")
        (folders["smartroom"] / "sr_20260920.xlsx").write_bytes(b"not-read-during-scan")
        (folders["ddio"] / "ddio_20260920.json").write_text("[]", encoding="utf-8")
        (folders["ddio"] / "ignore.exe").write_bytes(b"ignored")
        registry = BatchFolderRegistry()
        result = scan_batch_folders({role: str(path) for role, path in folders.items()}, registry)
        assert len(result["files"]) == 3
        assert {item["role"] for item in result["files"]} == {"primary", "smartroom", "ddio"}
        assert registry.resolve(result["files"][0]["backendToken"]).is_file()

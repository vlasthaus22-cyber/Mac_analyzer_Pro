from pathlib import Path

from storage_paths import build_storage_layout, initialize_storage, resolve_legacy_database


def test_storage_layout_creates_separate_directories_and_moves_known_files(tmp_path=None):
    import tempfile

    context = tempfile.TemporaryDirectory() if tmp_path is None else None
    root = Path(context.name) if context else Path(tmp_path)
    try:
        fixtures = {
            "mac_analyzer_web.db": b"database",
            "mac_analyzer_web.db-wal": b"wal",
            "mac_analyzer_web.db-shm": b"shm",
            "mac_history.db": b"history",
            "vendor_model_history.db": b"models",
            "mac_analyzer_stats.db": b"statistics",
            "mac_analyzer.log": b"log",
            "mac_analyzer_settings.json": b"{}",
            "server.stdout.log": b"stdout",
        }
        for name, content in fixtures.items():
            (root / name).write_bytes(content)

        layout, report = initialize_storage(root)

        for directory in layout.directories():
            assert directory.is_dir()
        assert layout.database.read_bytes() == b"database"
        assert layout.database.with_name(layout.database.name + "-wal").read_bytes() == b"wal"
        assert layout.database.with_name(layout.database.name + "-shm").read_bytes() == b"shm"
        assert (layout.legacy / "mac_history.db").read_bytes() == b"history"
        assert (layout.legacy / "vendor_model_history.db").read_bytes() == b"models"
        assert (layout.legacy / "mac_analyzer_stats.db").read_bytes() == b"statistics"
        assert (layout.logs / "mac_analyzer.log").read_bytes() == b"log"
        assert (layout.logs / "server.stdout.log").read_bytes() == b"stdout"
        assert (layout.config / "mac_analyzer_settings.json").read_bytes() == b"{}"
        assert len(report["moved"]) == len(fixtures)
        assert resolve_legacy_database(layout, "mac_history.db") == layout.legacy / "mac_history.db"
        assert not any((root / name).exists() for name in fixtures)
    finally:
        if context:
            context.cleanup()


def test_storage_layout_does_not_overwrite_existing_destination(tmp_path=None):
    import tempfile

    context = tempfile.TemporaryDirectory() if tmp_path is None else None
    root = Path(context.name) if context else Path(tmp_path)
    try:
        layout = build_storage_layout(root)
        layout.databases.mkdir(parents=True, exist_ok=True)
        layout.database.write_bytes(b"existing")
        (root / "mac_analyzer_web.db").write_bytes(b"source")

        _, report = initialize_storage(root)

        assert layout.database.read_bytes() == b"existing"
        assert (root / "mac_analyzer_web.db").read_bytes() == b"source"
        assert report["skipped"][0]["reason"] == "destination exists"
    finally:
        if context:
            context.cleanup()

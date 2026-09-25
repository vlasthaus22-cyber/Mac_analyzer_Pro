"""Overlay v1.0.27 runtime data onto a current portable package safely."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sqlite3
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


# The full-history release needs the historical SQLite knowledge base, not
# imported workbooks, logs, workspace caches, exports, or old backup copies.
# Keeping this allow-list exact prevents unrelated user files from entering a
# public release while preserving MAC/model/history records in the database.
ALLOWED_RUNTIME_FILES = {
    "data/databases/mac_analyzer_web.db",
    "config/mac_analyzer_settings.json",
}
SENSITIVE_PARTS = ("api_key", "apikey", "password", "secret", "token", "webhook")


def is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().lower()
    return any(part in normalized for part in SENSITIVE_PARTS)


def redact_sensitive_values(value: Any) -> tuple[Any, int]:
    redacted = 0
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if is_sensitive_key(key) and str(item or "").strip():
                cleaned[str(key)] = ""
                redacted += 1
            else:
                cleaned[str(key)], nested = redact_sensitive_values(item)
                redacted += nested
        return cleaned, redacted
    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            cleaned, nested = redact_sensitive_values(item)
            cleaned_list.append(cleaned)
            redacted += nested
        return cleaned_list, redacted
    return value, 0


def extract_runtime_data(legacy_archive: Path, package_root: Path) -> int:
    copied = 0
    with zipfile.ZipFile(legacy_archive) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        if not files:
            raise RuntimeError("Legacy archive is empty")
        root_prefix = files[0].filename.split("/", 1)[0] + "/"
        for item in files:
            if not item.filename.startswith(root_prefix):
                raise RuntimeError(f"Unexpected archive root: {item.filename}")
            relative = item.filename[len(root_prefix) :]
            if relative not in ALLOWED_RUNTIME_FILES:
                continue
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"Unsafe archive path: {item.filename}")
            destination = package_root.joinpath(*path.parts).resolve()
            if package_root.resolve() not in destination.parents:
                raise RuntimeError(f"Archive path escapes package root: {item.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
            copied += 1
    return copied


def sanitize_json_file(path: Path) -> int:
    if not path.is_file():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    cleaned, redacted = redact_sensitive_values(payload)
    path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return redacted


def sanitize_database(database: Path) -> dict[str, int]:
    redacted = 0
    sessions_removed = 0
    notifications_sanitized = 0
    settings_sanitized = 0
    connection = sqlite3.connect(database)
    try:
        sessions_removed = int(
            connection.execute("SELECT COUNT(*) FROM engineering_sessions").fetchone()[0]
        )
        connection.execute("DELETE FROM engineering_sessions")

        for channel, config_json in connection.execute(
            "SELECT channel, config_json FROM notification_settings"
        ).fetchall():
            try:
                payload = json.loads(config_json)
            except (TypeError, ValueError):
                payload = {}
            cleaned, count = redact_sensitive_values(payload)
            if count:
                connection.execute(
                    "UPDATE notification_settings SET config_json = ?, enabled = 0 WHERE channel = ?",
                    (json.dumps(cleaned, ensure_ascii=False), channel),
                )
                redacted += count
                notifications_sanitized += 1

        for key, raw_value in connection.execute(
            "SELECT key, value FROM app_settings"
        ).fetchall():
            try:
                payload = json.loads(raw_value)
            except (TypeError, ValueError):
                continue
            cleaned, count = redact_sensitive_values(payload)
            if count:
                connection.execute(
                    "UPDATE app_settings SET value = ? WHERE key = ?",
                    (json.dumps(cleaned, ensure_ascii=False), key),
                )
                redacted += count
                settings_sanitized += 1
        connection.commit()
    finally:
        connection.close()
    return {
        "databaseSecretsRedacted": redacted,
        "engineeringSessionsRemoved": sessions_removed,
        "notificationsSanitized": notifications_sanitized,
        "settingsSanitized": settings_sanitized,
    }


def database_counts(database: Path) -> tuple[str, int, dict[str, int]]:
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        tables = int(
            connection.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0]
        )
        available = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        counts = {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            if table in available else 0
            for table in (
                "mac_history",
                "vendor_model_history",
                "snapshots",
                "vendor_mappings",
                "model_mappings",
                "app_autosaves",
            )
        }
        return integrity, tables, counts
    finally:
        connection.close()


def prepare(
    legacy_archive: Path,
    package_root: Path,
    minimum_history_records: int = 500_000,
) -> dict[str, Any]:
    legacy_archive = legacy_archive.resolve()
    package_root = package_root.resolve()
    if not legacy_archive.is_file():
        raise FileNotFoundError(legacy_archive)
    if not (package_root / "server.py").is_file():
        raise FileNotFoundError(package_root / "server.py")

    copied_files = extract_runtime_data(legacy_archive, package_root)
    database = package_root / "data" / "databases" / "mac_analyzer_web.db"
    if not database.is_file():
        raise FileNotFoundError(database)

    config_redacted = sanitize_json_file(
        package_root / "config" / "mac_analyzer_settings.json"
    )
    database_security = sanitize_database(database)
    legacy_integrity, legacy_tables, legacy_counts = database_counts(database)
    if legacy_integrity != "ok":
        raise RuntimeError(f"Legacy database integrity check failed: {legacy_integrity}")
    if (
        legacy_counts["mac_history"] < minimum_history_records
        or legacy_counts["vendor_model_history"] < minimum_history_records
    ):
        raise RuntimeError(f"Legacy history was not preserved: {legacy_counts}")

    # A legacy database may contain stale frontend autosaves whose snapshot
    # metadata points at rows that no longer exist.  Starting the shipped app
    # with that database makes the UI appear to contain data and then fail to
    # load it.  Preserve the sanitized database byte-for-byte as an explicit
    # import/backup source, while creating a coherent active database for the
    # current schema.
    legacy_backup = (
        package_root
        / "data"
        / "backups"
        / "legacy-v1.0.27"
        / "mac_analyzer_web.db"
    )
    legacy_backup.parent.mkdir(parents=True, exist_ok=True)
    if legacy_backup.exists():
        legacy_backup.unlink()
    shutil.move(str(database), str(legacy_backup))

    os.environ["MAC_ANALYZER_DATA_DIR"] = str(package_root / "data")
    os.environ["MAC_ANALYZER_DATABASE_PATH"] = str(database)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(package_root))
    try:
        server = importlib.import_module("server")
        server.init_database()
    finally:
        try:
            sys.path.remove(str(package_root))
        except ValueError:
            pass

    # Importing the backend may initialize empty runtime caches and log files.
    # They are machine-local state, not part of the historical database.
    for generated_directory in (
        package_root / "data" / "imports" / "workspace-cache",
        package_root / "data" / "runtime",
        package_root / "logs",
    ):
        if generated_directory.exists():
            shutil.rmtree(generated_directory)

    integrity, tables, active_counts = database_counts(database)

    caches = [
        path
        for path in package_root.rglob("*")
        if path.name == "__pycache__" or path.suffix.lower() in {".pyc", ".pyo"}
    ]
    if caches:
        raise RuntimeError(f"Prepared package contains Python caches: {caches}")
    if integrity != "ok":
        raise RuntimeError(f"Active database integrity check failed: {integrity}")
    if active_counts["app_autosaves"]:
        raise RuntimeError("Fresh active database unexpectedly contains an autosave")

    return {
        "legacyArchive": legacy_archive.name,
        "runtimeFilesCopied": copied_files,
        "database": str(database),
        "databaseBytes": database.stat().st_size,
        "databaseIntegrity": integrity,
        "databaseTables": tables,
        "legacyDatabase": str(legacy_backup),
        "legacyDatabaseBytes": legacy_backup.stat().st_size,
        "legacyDatabaseIntegrity": legacy_integrity,
        "legacyDatabaseTables": legacy_tables,
        **legacy_counts,
        "activeSnapshots": active_counts["snapshots"],
        "activeAutosaves": active_counts["app_autosaves"],
        "configSecretsRedacted": config_redacted,
        **database_security,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-archive", type=Path, required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--minimum-history-records", type=int, default=500_000)
    arguments = parser.parse_args()
    print(
        json.dumps(
            prepare(
                arguments.legacy_archive,
                arguments.package_root,
                arguments.minimum_history_records,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

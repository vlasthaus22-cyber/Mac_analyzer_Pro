"""Create and validate a clean SQLite database for a release package."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path


REQUIRED_TABLES = {
    "api_cache",
    "app_autosaves",
    "app_logs",
    "app_settings",
    "column_preferences",
    "data_quality_reports",
    "engineering_sessions",
    "ip_address_mappings",
    "mac_history",
    "mac_movements",
    "model_mappings",
    "notification_settings",
    "performance_metrics",
    "scheduled_tasks",
    "snapshots",
    "task_file_queue",
    "vendor_mappings",
    "vendor_model_history",
}

USER_DATA_TABLES = {
    "api_cache",
    "app_autosaves",
    "column_preferences",
    "data_quality_reports",
    "engineering_sessions",
    "ip_address_mappings",
    "mac_history",
    "mac_movements",
    "notification_settings",
    "performance_metrics",
    "scheduled_tasks",
    "snapshots",
    "task_file_queue",
    "vendor_model_history",
}


def create_clean_database(application_root: Path, data_root: Path) -> dict[str, object]:
    application_root = application_root.resolve()
    data_root = data_root.resolve()
    server_path = application_root / "server.py"
    if not server_path.is_file():
        raise FileNotFoundError(server_path)

    reference_directory = data_root / "reference"
    reference_directory.mkdir(parents=True, exist_ok=True)
    packaged_reference = reference_directory / "oui.csv"
    source_reference = application_root / "data" / "reference" / "oui.csv"
    if not packaged_reference.is_file() and source_reference.is_file():
        shutil.copy2(source_reference, packaged_reference)

    database = data_root / "databases" / "mac_analyzer_web.db"
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists():
        raise FileExistsError(f"Refusing to overwrite an existing database: {database}")
    unexpected_files = [
        path
        for path in data_root.rglob("*")
        if path.is_file() and path.resolve() != packaged_reference.resolve()
    ]
    if unexpected_files:
        raise RuntimeError(
            f"Refusing to initialize a non-empty release data directory: {unexpected_files}"
        )

    os.environ["MAC_ANALYZER_DATA_DIR"] = str(data_root)
    os.environ["MAC_ANALYZER_DATABASE_PATH"] = str(database)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(application_root))
    try:
        server = importlib.import_module("server")
        server.init_database()
    finally:
        try:
            sys.path.remove(str(application_root))
        except ValueError:
            pass
    workspace_cache = data_root / "imports" / "workspace-cache"
    if workspace_cache.exists():
        shutil.rmtree(workspace_cache)

    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        missing_tables = sorted(REQUIRED_TABLES - tables)
        if missing_tables:
            raise RuntimeError(f"Clean database is missing tables: {missing_tables}")
        user_counts = {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in sorted(USER_DATA_TABLES)
        }
        populated_user_tables = {
            table: count for table, count in user_counts.items() if count
        }
        if populated_user_tables:
            raise RuntimeError(
                f"Clean database contains user data: {populated_user_tables}"
            )
        vendor_mappings = int(
            connection.execute("SELECT COUNT(*) FROM vendor_mappings").fetchone()[0]
        )
        model_mappings = int(
            connection.execute("SELECT COUNT(*) FROM model_mappings").fetchone()[0]
        )
        connection.execute("VACUUM")
    finally:
        connection.close()

    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    return {
        "database": str(database),
        "bytes": database.stat().st_size,
        "integrity": integrity,
        "tables": len(tables),
        "requiredTables": len(REQUIRED_TABLES),
        "userDataRows": sum(user_counts.values()),
        "vendorMappings": vendor_mappings,
        "modelMappings": model_mappings,
        "ouiReferenceIncluded": packaged_reference.is_file(),
        "workspaceCacheIncluded": workspace_cache.exists(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--application-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    arguments = parser.parse_args()
    report = create_clean_database(arguments.application_root, arguments.data_root)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

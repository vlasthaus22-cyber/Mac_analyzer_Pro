"""Validated, additive import of a MAC Analyzer SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


IMPORTABLE_TABLES = (
    "device_inventory",
    "mac_history",
    "mac_movements",
    "vendor_model_history",
    "snapshots",
    "vendor_mappings",
    "model_mappings",
    "ip_address_mappings",
    "smartroom_room_mappings",
    "column_preferences",
    "notification_settings",
    "api_cache",
    "data_quality_reports",
    "scheduled_tasks",
    "task_file_queue",
    "app_settings",
    "app_autosaves",
)


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_info(connection: sqlite3.Connection, schema: str, table: str) -> list[dict[str, Any]]:
    rows = connection.execute(f"PRAGMA {_quote(schema)}.table_info({_quote(table)})").fetchall()
    return [
        {"name": str(row[1]), "type": str(row[2] or ""), "notnull": bool(row[3]), "default": row[4], "pk": int(row[5] or 0)}
        for row in rows
    ]


def inspect_and_merge_database(source_path: Path, target_path: Path) -> dict[str, Any]:
    """Check *source_path* and merge supported tables into *target_path*.

    The target is never replaced. Existing rows are retained and exact logical
    duplicates are ignored, including rows whose source integer IDs differ.
    """

    source_path = Path(source_path).resolve()
    target_path = Path(target_path).resolve()
    if source_path == target_path:
        raise ValueError("Нельзя импортировать активную базу саму в себя")
    if not source_path.is_file() or source_path.stat().st_size < 100:
        raise ValueError("Файл SQLite отсутствует или пуст")
    with source_path.open("rb") as source:
        if source.read(16) != b"SQLite format 3\x00":
            raise ValueError("Выбранный файл не является базой SQLite")

    source_uri = source_path.as_uri() + "?mode=ro"
    source_connection = sqlite3.connect(source_uri, uri=True, timeout=30)
    try:
        integrity = str(source_connection.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity.lower() != "ok":
            raise ValueError("Проверка целостности загружаемой SQLite не пройдена: " + integrity)
        source_tables = {
            str(row[0]) for row in source_connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
    finally:
        source_connection.close()
    supported = [table for table in IMPORTABLE_TABLES if table in source_tables]
    if not supported:
        raise ValueError("В базе не найдены поддерживаемые таблицы MAC Analyzer")

    imported: dict[str, int] = {}
    skipped: dict[str, str] = {}
    connection = sqlite3.connect(target_path, timeout=60)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("ATTACH DATABASE ? AS imported", (str(source_path),))
        connection.execute("BEGIN IMMEDIATE")
        for table in supported:
            target_info = _table_info(connection, "main", table)
            source_info = _table_info(connection, "imported", table)
            if not target_info or not source_info:
                skipped[table] = "таблица отсутствует в текущей схеме"
                continue
            source_names = {column["name"] for column in source_info}
            columns = [column for column in target_info if column["name"] in source_names]
            # A generated integer primary key must not collide with target IDs.
            columns = [
                column for column in columns
                if not (column["pk"] and column["name"].lower() == "id" and "INT" in column["type"].upper())
            ]
            missing_required = [
                column["name"] for column in target_info
                if column["name"] not in {item["name"] for item in columns}
                and column["notnull"] and column["default"] is None and not column["pk"]
            ]
            if not columns or missing_required:
                skipped[table] = "несовместимая схема" + (": " + ", ".join(missing_required) if missing_required else "")
                continue
            names = [column["name"] for column in columns]
            column_sql = ", ".join(_quote(name) for name in names)
            select_sql = ", ".join("src." + _quote(name) for name in names)
            equality_sql = " AND ".join(
                f"dst.{_quote(name)} IS src.{_quote(name)}" for name in names
            )
            before = int(connection.execute(f"SELECT COUNT(*) FROM main.{_quote(table)}").fetchone()[0])
            connection.execute(
                f"INSERT OR IGNORE INTO main.{_quote(table)} ({column_sql}) "
                f"SELECT {select_sql} FROM imported.{_quote(table)} AS src "
                f"WHERE NOT EXISTS (SELECT 1 FROM main.{_quote(table)} AS dst WHERE {equality_sql})"
            )
            after = int(connection.execute(f"SELECT COUNT(*) FROM main.{_quote(table)}").fetchone()[0])
            imported[table] = max(0, after - before)
        connection.commit()
        connection.execute("DETACH DATABASE imported")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return {
        "ok": True,
        "integrity": integrity,
        "sourceBytes": source_path.stat().st_size,
        "tables": imported,
        "imported": sum(imported.values()),
        "skipped": skipped,
    }

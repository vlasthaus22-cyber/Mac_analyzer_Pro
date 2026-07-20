"""Legacy PyQt SQLite migration helpers for the web backend."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


LEGACY_DATABASES = {
    "history": "mac_history.db",
    "vendorModel": "vendor_model_history.db",
    "statistics": "mac_analyzer_stats.db",
}


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return bool(row)


def _count(conn: sqlite3.Connection, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _result(source: str, path: Path) -> dict[str, Any]:
    return {
        "source": source,
        "path": str(path),
        "exists": path.exists(),
        "available": 0,
        "imported": 0,
        "skipped": 0,
        "errors": [],
    }


def _insert_count(cursor: sqlite3.Cursor) -> int:
    return max(0, int(cursor.rowcount or 0))


def migrate_history(old: sqlite3.Connection, new: sqlite3.Connection, dry_run: bool) -> dict[str, Any]:
    result = {"tables": {}, "available": 0, "imported": 0, "skipped": 0}
    history_rows = old.execute(
        "SELECT mac, mac_formatted, oui_3byte, vendor, model, ip, address, room, switch_ip, switch_port, source_file, timestamp FROM mac_history"
    ).fetchall() if _table_exists(old, "mac_history") else []
    result["tables"]["mac_history"] = len(history_rows)
    result["available"] += len(history_rows)
    if not dry_run:
        for row in history_rows:
            cursor = new.execute(
                "INSERT INTO mac_history (mac, mac_formatted, oui, vendor, model, ip, address, room, switch_ip, switch_port, source, recorded_at) "
                "SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS "
                "(SELECT 1 FROM mac_history WHERE mac = ? AND recorded_at = ? AND source = ?)",
                (
                    row["mac"], row["mac_formatted"] or row["mac"], row["oui_3byte"], row["vendor"],
                    row["model"], row["ip"], row["address"], row["room"], row["switch_ip"],
                    row["switch_port"], row["source_file"], row["timestamp"],
                    row["mac"], row["timestamp"], row["source_file"],
                ),
            )
            result["imported"] += _insert_count(cursor)

    movement_rows = old.execute(
        "SELECT mac, field_name, from_value, to_value, source_file, timestamp FROM mac_movements"
    ).fetchall() if _table_exists(old, "mac_movements") else []
    result["tables"]["mac_movements"] = len(movement_rows)
    result["available"] += len(movement_rows)
    if not dry_run:
        for row in movement_rows:
            cursor = new.execute(
                "INSERT INTO mac_movements (mac, field_name, from_value, to_value, source, changed_at) "
                "SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS "
                "(SELECT 1 FROM mac_movements WHERE mac = ? AND field_name = ? AND changed_at = ? AND source = ?)",
                (
                    row["mac"], row["field_name"], row["from_value"], row["to_value"],
                    row["source_file"], row["timestamp"], row["mac"], row["field_name"],
                    row["timestamp"], row["source_file"],
                ),
            )
            result["imported"] += _insert_count(cursor)
    result["skipped"] = result["available"] - result["imported"] if not dry_run else 0
    return result


def migrate_vendor_model(old: sqlite3.Connection, new: sqlite3.Connection, now: str, dry_run: bool) -> dict[str, Any]:
    result = {"tables": {}, "available": 0, "imported": 0, "skipped": 0}
    mapping_specs = (
        ("oui_vendor_history", "oui_3byte", "vendor", "vendor_mappings", "oui", "vendor"),
        ("mac5_model_history", "mac_5byte", "model", "model_mappings", "prefix", "model"),
    )
    for table, key, value, target, target_key, target_value in mapping_specs:
        rows = old.execute(f"SELECT {key}, {value} FROM {table}").fetchall() if _table_exists(old, table) else []
        result["tables"][table] = len(rows)
        result["available"] += len(rows)
        if dry_run:
            continue
        for row in rows:
            if not row[key] or not row[value]:
                continue
            cursor = new.execute(
                f"INSERT INTO {target} ({target_key}, {target_value}, source, updated_at) VALUES (?, ?, 'legacy', ?) "
                f"ON CONFLICT({target_key}) DO UPDATE SET {target_value}=excluded.{target_value}, source='legacy', updated_at=excluded.updated_at",
                (str(row[key]).upper(), row[value], now),
            )
            result["imported"] += _insert_count(cursor)

    load_rows = old.execute(
        "SELECT filename, load_date, devices_count, new_vendors_added, new_models_added, enriched_from_history FROM history_loads"
    ).fetchall() if _table_exists(old, "history_loads") else []
    result["tables"]["history_loads"] = len(load_rows)
    result["available"] += len(load_rows)
    if not dry_run:
        for row in load_rows:
            snapshot_id = "legacy-load-" + str(row["filename"] or "load") + "-" + str(row["load_date"] or now)
            cursor = new.execute(
                "INSERT OR IGNORE INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    snapshot_id,
                    str(row["filename"] or "Legacy vendor/model load"),
                    "legacy:vendor_model_history",
                    int(row["devices_count"] or 0),
                    "[]",
                    str(row["load_date"] or now),
                ),
            )
            result["imported"] += _insert_count(cursor)
    result["skipped"] = result["available"] - result["imported"] if not dry_run else 0
    return result


def migrate_statistics(old: sqlite3.Connection, new: sqlite3.Connection, dry_run: bool) -> dict[str, Any]:
    result = {"tables": {}, "available": 0, "imported": 0, "skipped": 0}
    analysis_rows = old.execute("SELECT * FROM analysis_history").fetchall() if _table_exists(old, "analysis_history") else []
    result["tables"]["analysis_history"] = len(analysis_rows)
    result["available"] += len(analysis_rows)
    if not dry_run:
        for row in analysis_rows:
            data = dict(row)
            name = str(data.get("filename") or "Legacy analysis")
            created_at = str(data.get("timestamp") or data.get("date") or "1970-01-01T00:00:00Z")
            cursor = new.execute(
                "INSERT OR IGNORE INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "legacy-analysis-" + str(data.get("id") or created_at),
                    name,
                    name,
                    int(data.get("devices_count") or data.get("total_devices") or 0),
                    "[]",
                    created_at,
                ),
            )
            result["imported"] += _insert_count(cursor)

    metric_rows = old.execute("SELECT operation, timestamp, duration_seconds, details FROM performance_metrics").fetchall() if _table_exists(old, "performance_metrics") else []
    result["tables"]["performance_metrics"] = len(metric_rows)
    result["available"] += len(metric_rows)
    if not dry_run:
        for row in metric_rows:
            cursor = new.execute(
                "INSERT INTO performance_metrics (operation, duration_ms, details, created_at) "
                "SELECT ?, ?, ?, ? WHERE NOT EXISTS "
                "(SELECT 1 FROM performance_metrics WHERE operation = ? AND created_at = ? AND details = ?)",
                (
                    row["operation"],
                    float(row["duration_seconds"] or 0) * 1000,
                    row["details"],
                    row["timestamp"],
                    row["operation"],
                    row["timestamp"],
                    row["details"],
                ),
            )
            result["imported"] += _insert_count(cursor)
    result["skipped"] = result["available"] - result["imported"] if not dry_run else 0
    return result


def migrate_legacy_sqlite(root: Path, web_database: Path, now: str, dry_run: bool = False) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    total = {"available": 0, "imported": 0, "skipped": 0, "errors": 0}
    for source, filename in LEGACY_DATABASES.items():
        path = root / filename
        item = _result(source, path)
        if not path.exists():
            item["errors"].append("file not found")
            total["errors"] += 1
            results.append(item)
            continue
        try:
            with _connect(path) as old, _connect(web_database) as new:
                if source == "history":
                    details = migrate_history(old, new, dry_run)
                elif source == "vendorModel":
                    details = migrate_vendor_model(old, new, now, dry_run)
                else:
                    details = migrate_statistics(old, new, dry_run)
                if dry_run:
                    new.rollback()
                else:
                    new.commit()
                item.update(details)
        except sqlite3.Error as error:
            item["errors"].append(str(error))
            total["errors"] += 1
        total["available"] += int(item.get("available", 0))
        total["imported"] += int(item.get("imported", 0))
        total["skipped"] += int(item.get("skipped", 0))
        results.append(item)
    return {"dryRun": dry_run, "sources": results, "summary": total}

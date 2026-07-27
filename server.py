#!/usr/bin/env python3
"""Local web backend for MAC Analyzer Pro Web.

Run: python server.py
Open: http://127.0.0.1:8080
"""

from __future__ import annotations

import json
import csv
import binascii
import hashlib
import hmac
import html as html_lib
import io
import ipaddress
import mimetypes
import os
import re
import secrets
import signal
import smtplib
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import base64
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse

from backend.services.workspace.xlsx_service import read_xlsx
from backend.services.workspace.file_import_service import read_table
from backend.services.detection.column_detector_service import detect as detect_columns
from backend.services.exporting.export_manager_service import export_managed, supported_export_formats
from backend.services.workspace.enrichment_service import enrich_files, enrich_workspace_files
from backend.services.detection.oui_service import format_oui_for_devices
from backend.services.workspace.single_file_service import analyze_single_file, analyze_single_file_table, summarize_single_file
from backend.services.comparison.comparison_service import compare_devices, compare_many_devices, compare_many_snapshots, compare_snapshots, export_comparison
from backend.services.analytics.chart_service import build_chart_payload, export_charts_json, export_charts_svg
from backend.services.analytics.dashboard_service import build_dashboard_metrics_payload, build_dashboard_payload, export_dashboard_html, export_dashboard_png, normalize_dashboard_settings
from backend.services.analytics.topology_service import build_topology, export_topology_html
from backend.services.analytics.cluster_service import build_clusters, export_clusters_csv
from backend.services.analytics.device_analytics_service import build_device_analytics, build_model_analytics, export_device_analytics_html
from backend.services.integrations.external_api_service import external_api_provider_options, external_enrich_devices, normalize_external_api_settings, test_mac_vendor_api
from backend.services.integrations.notification_service import build_analysis_event, dispatch_notification_event
from backend.services.integrations.scheduler_service import prepare_queue_files, queue_summary, run_file_queue
from backend.services.analytics.data_quality_service import analyze_data_quality
from backend.services.analytics.analytics_report_service import build_analytics_report, export_analytics_report_txt
from backend.services.detection.vendor_detector_service import detect_model, detect_vendor, normalize_detector_settings
from backend.services.detection.detection_index_service import (
    build_similarity_index,
    build_vendor_model_history_index,
    compile_rule_index,
    indexed_history_suggestion,
    similarity_detection,
)
from backend.services.detection.reference_data_service import import_oui_reference, reference_status
from backend.services.system.legacy_migration_service import migrate_legacy_sqlite
from backend.services.system.parity_service import build_parity_report, build_parity_status
from backend.services.system.diagnostics_service import build_system_diagnostics
from backend.services.system.storage_paths import initialize_storage
from backend.services.workspace.workspace_cache_service import WorkspaceCacheMiss, WorkspaceFileCache, prepare_workspace_files, resolve_workspace_files

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
STORAGE, STORAGE_MIGRATION_REPORT = initialize_storage(ROOT)
DATABASE_PATH = STORAGE.database
HOST = os.environ.get("MAC_ANALYZER_HOST", "127.0.0.1")
PORT = int(os.environ.get("MAC_ANALYZER_PORT", "8080"))
DEFAULT_RESULT_COLUMNS = ["macFormatted", "oui", "vendor", "model", "ip", "address", "room", "switchIp", "switchPort", "source"]
DEFAULT_RESULT_COLUMN_WIDTHS = {
    "macFormatted": 180,
    "oui": 110,
    "vendor": 150,
    "model": 150,
    "ip": 130,
    "address": 200,
    "room": 120,
    "switchIp": 150,
    "switchPort": 100,
    "source": 150,
}
ENHANCED_HISTORY_COLUMNS = ["mac", "count", "dates", "vendor", "model", "address", "room", "field", "before", "after", "source"]
ENHANCED_HISTORY_COLUMN_LABELS = {
    "mac": "MAC-адрес", "count": "Изменений", "dates": "Дата/время",
    "vendor": "Производитель", "model": "Модель", "address": "Адрес помещения", "room": "Помещение",
    "field": "Поле", "before": "Было", "after": "Стало", "source": "Файл",
}
ENHANCED_HISTORY_COLUMN_WIDTHS = {
    "mac": 180, "count": 100, "dates": 170, "vendor": 160, "model": 160,
    "address": 220, "room": 120, "field": 120, "before": 240, "after": 240, "source": 160,
}
DEFAULT_RESULT_LABELS = {
    "mac": "MAC-адрес",
    "macFormatted": "MAC",
    "oui": "OUI",
    "vendor": "Производитель",
    "model": "Модель",
    "ip": "IP",
    "address": "Адрес",
    "room": "Помещение",
    "switchIp": "IP коммутатора",
    "switchPort": "Порт",
    "source": "Источник",
    "vendorSource": "Источник вендора",
    "vendorConfidence": "Уверенность вендора",
    "vendorMatchedPrefix": "Префикс вендора",
    "modelSource": "Источник модели",
    "modelConfidence": "Уверенность модели",
    "modelMatchedPrefix": "Префикс модели",
}
ENGINEERING_PERMISSIONS = ["delete:history", "delete:snapshots", "delete:mappings", "delete:tasks", "delete:ip-mappings", "delete:api-cache", "write:settings", "write:migration"]

BUILTIN_VENDORS = {
    "00037F": "Apple Inc.", "001A11": "Apple Inc.", "18FE34": "Apple Inc.",
    "001B44": "Intel Corporation", "00A0C9": "Intel Corporation",
    "ACDE48": "Samsung Electronics", "002590": "Samsung Electronics",
    "001122": "Cisco Systems", "00055D": "Cisco Systems", "0050B6": "Dell Inc.",
    "00155F": "Hewlett Packard", "0050C2": "Microsoft Corp.", "005A39": "Google LLC",
    "0025D3": "Huawei Technologies", "002128": "Xiaomi Corporation",
    "0022B0": "TP-Link Technologies", "001E52": "Netgear Inc.",
    "F832E4": "ASUSTeK Computer", "B827EB": "Raspberry Pi Foundation",
    "002314": "Lenovo Group", "0022BD": "Acer Inc.",
    "0024B2": "LG Electronics", "001E58": "Sony Corporation",
    "000E58": "Cisco-Linksys", "001E13": "Nintendo", "000C29": "VMware",
    "0050F2": "Microsoft", "00107B": "Dell", "001EC9": "Huawei",
    "0017C8": "Apple", "00236C": "Xiaomi", "001AA9": "Samsung",
}
BUILTIN_MODELS = {
    "00112233": "Cisco Catalyst 2960", "00112244": "Cisco Catalyst 3560",
    "00112255": "Cisco Catalyst 3750", "00112266": "Cisco Catalyst 4500",
    "00112277": "Cisco Catalyst 6500", "00112288": "Cisco ASR 1000",
    "00112299": "Cisco ISR 4000", "005055AA": "Cisco Nexus 3000",
    "005055BB": "Cisco Nexus 5000", "005055CC": "Cisco Nexus 7000",
    "0010B5AA": "Dell PowerEdge R740", "0010B5BB": "Dell PowerEdge R640",
    "0010B5CC": "Dell PowerEdge T340", "0010B5DD": "Dell OptiPlex 7070",
    "0010B5EE": "Dell Latitude 5400", "0010B5FF": "Dell XPS 15",
    "00215AAB": "HP ProLiant DL380", "00215ACC": "HP ProLiant DL360",
    "00215ADD": "HP EliteBook 840", "00215AEE": "HP ZBook 15",
    "00215AFF": "HP LaserJet Pro", "00215A11": "HP OfficeJet Pro",
    "001A1101": "iPhone 13", "001A1102": "iPhone 14", "001A1103": "iPhone 15",
    "001A1120": "iPad Pro", "001A1121": "iPad Air", "001A1130": "MacBook Pro",
    "001A1131": "MacBook Air", "001A1140": "iMac 24\"", "001A1150": "Mac Studio",
    "00259001": "Samsung Galaxy S23", "00259002": "Samsung Galaxy S22",
    "00259010": "Samsung Galaxy Tab", "00259020": "Samsung SSD 980 Pro",
    "00259030": "Samsung Smart Monitor", "00259040": "Samsung M7",
    "001EC901": "Huawei Mate 50", "001EC902": "Huawei P60",
    "001EC910": "Huawei MateBook X", "001EC920": "Huawei Watch GT",
    "00236C01": "Xiaomi Mi 11", "00236C02": "Xiaomi 12T",
    "00236C10": "Xiaomi Mi Band", "00236C20": "Xiaomi Robot Vacuum",
    "0022B001": "TP-Link Archer AX73", "0022B002": "TP-Link Deco X60",
    "0022B010": "TP-Link Tapo C200", "0022B020": "TP-Link Kasa KP115",
    "001E5201": "Netgear Nighthawk RAX200", "001E5202": "Netgear Orbi RBK852",
    "001E5210": "Netgear GS308", "001E5220": "Netgear ReadyNAS",
    "F832E401": "ASUS ROG Zephyrus", "F832E402": "ASUS TUF Gaming",
    "F832E410": "ASUS RT-AX88U", "F832E420": "ASUS ZenBook",
    "00231401": "Lenovo ThinkPad X1", "00231402": "Lenovo ThinkPad T14",
    "00231410": "Lenovo Legion 5", "00231420": "Lenovo Yoga 9i",
}
DEVICE_FIELDS = ("vendor", "model", "ip", "address", "room", "switchIp", "switchPort")
SIGNAL_STATE: dict[str, Any] = {"lastSignal": None, "lastSignalAt": None, "shutdownRequested": False}
ENRICHMENT_JOBS: dict[str, dict[str, Any]] = {}
WORKSPACE_FILE_CACHE = WorkspaceFileCache(
    ttl_seconds=int(os.environ.get("MAC_ANALYZER_WORKSPACE_CACHE_TTL", "2592000")),
    max_entries=int(os.environ.get("MAC_ANALYZER_WORKSPACE_CACHE_FILES", "100")),
    max_rows=int(os.environ.get("MAC_ANALYZER_WORKSPACE_CACHE_ROWS", "2000000")),
    storage_directory=STORAGE.imports / "workspace-cache",
)


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def log_action(action: str, details: str = "") -> None:
    action_text = str(action or "event").strip() or "event"
    details_text = str(details or "")
    timestamp = utc_now()
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO app_logs (action, details, created_at) VALUES (?, ?, ?)",
            (action_text, details_text, timestamp),
        )
    return {"action": action_text, "details": details_text, "createdAt": timestamp}


def app_log_records(action: str = "", query_text: str = "", limit: int = 200) -> dict[str, Any]:
    try:
        requested_limit = int(limit or 200)
    except (TypeError, ValueError):
        requested_limit = 200
    bounded_limit = max(1, min(requested_limit, 1000))
    action_filter = as_text(action)
    query_filter = as_text(query_text).lower()
    where: list[str] = []
    params: list[Any] = []
    if action_filter:
        where.append("action = ?")
        params.append(action_filter)
    if query_filter:
        where.append("(lower(action) LIKE ? OR lower(details) LIKE ?)")
        like = f"%{query_filter}%"
        params.extend([like, like])
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    with db_connection() as conn:
        rows = conn.execute(
            f"SELECT id, action, details, created_at FROM app_logs{where_sql} ORDER BY id DESC LIMIT ?",
            [*params, bounded_limit],
        ).fetchall()
    logs = [dict(row) for row in rows]
    counts: dict[str, int] = {}
    for row in logs:
        counts[row["action"]] = counts.get(row["action"], 0) + 1
    return {
        "logs": logs,
        "summary": {
            "count": len(logs),
            "actions": [{"action": name, "count": count} for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))],
        },
    }


def load_app_settings(keys: Optional[list[str]] = None) -> dict[str, Any]:
    wanted = [as_text(key) for key in (keys or []) if as_text(key)]
    with db_connection() as conn:
        if wanted:
            placeholders = ",".join("?" for _ in wanted)
            rows = conn.execute(f"SELECT key, value, updated_at FROM app_settings WHERE key IN ({placeholders}) ORDER BY key", wanted).fetchall()
        else:
            rows = conn.execute("SELECT key, value, updated_at FROM app_settings ORDER BY key").fetchall()
    settings: dict[str, Any] = {}
    metadata: dict[str, str] = {}
    for row in rows:
        try:
            settings[row["key"]] = json.loads(row["value"])
        except (TypeError, ValueError, json.JSONDecodeError):
            settings[row["key"]] = row["value"]
        metadata[row["key"]] = row["updated_at"]
    return {"settings": settings, "updatedAt": metadata}


def save_app_settings(settings: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(settings, dict):
        raise ValueError("settings must be an object")
    timestamp = utc_now()
    saved: list[str] = []
    with db_connection() as conn:
        for setting_key, value in settings.items():
            key = as_text(setting_key)
            if not key:
                continue
            conn.execute(
                "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, json.dumps(value, ensure_ascii=False), timestamp),
            )
            saved.append(key)
    if saved:
        log_action("Settings updated", ",".join(saved))
    return {"saved": saved, "updatedAt": timestamp, **load_app_settings(saved)}


def delete_app_setting(key: str) -> bool:
    setting_key = as_text(key)
    if not setting_key:
        return False
    with db_connection() as conn:
        cursor = conn.execute("DELETE FROM app_settings WHERE key = ?", (setting_key,))
    if cursor.rowcount:
        log_action("Settings deleted", setting_key)
    return bool(cursor.rowcount)


def save_autosave_state(state: dict[str, Any], slot: str = "main", reason: str = "manual") -> dict[str, Any]:
    if not isinstance(state, dict):
        raise ValueError("state must be an object")
    autosave_slot = as_text(slot) or "main"
    timestamp = utc_now()
    payload = json.dumps(state, ensure_ascii=False)
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO app_autosaves (slot, state_json, reason, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(slot) DO UPDATE SET state_json=excluded.state_json, reason=excluded.reason, updated_at=excluded.updated_at",
            (autosave_slot, payload, as_text(reason), timestamp),
        )
    log_action("Autosave", f"slot={autosave_slot}, reason={as_text(reason)}, bytes={len(payload)}")
    return {
        "slot": autosave_slot,
        "updatedAt": timestamp,
        "bytes": len(payload),
        "statusText": f"Autosaved: {format_display_datetime(timestamp)}",
    }


def load_autosave_state(slot: str = "main", hydrate: bool = True) -> Optional[dict[str, Any]]:
    autosave_slot = as_text(slot) or "main"
    with db_connection() as conn:
        row = conn.execute("SELECT slot, state_json, reason, updated_at FROM app_autosaves WHERE slot = ?", (autosave_slot,)).fetchone()
        state = json.loads(row["state_json"]) if row else None
        snapshot_id = as_text(
            state.get("resultSnapshotId") or state.get("activeSnapshotId")
        ) if isinstance(state, dict) else ""
        if snapshot_id:
            snapshot = conn.execute(
                "SELECT id, device_count, devices_json FROM snapshots WHERE id = ?",
                (snapshot_id,),
            ).fetchone()
            if snapshot and hydrate and not state.get("devices"):
                state["devices"] = json.loads(snapshot["devices_json"])
            elif snapshot and not hydrate:
                state["resultSnapshotId"] = snapshot["id"]
                state["resultDeviceCount"] = int(snapshot["device_count"] or 0)
                state["devices"] = []
                state["invalid"] = []
        if isinstance(state, dict) and not hydrate:
            state["devices"] = []
            state["invalid"] = []
    if not row:
        return None
    files = state.get("files") if isinstance(state, dict) else None
    if hydrate and isinstance(files, list) and any(item.get("fileToken") and not item.get("rows") for item in files if isinstance(item, dict)):
        try:
            state["files"] = resolve_workspace_files(files, WORKSPACE_FILE_CACHE)
        except WorkspaceCacheMiss:
            pass
    elif not hydrate and isinstance(files, list):
        state["files"] = [
            {**item, "rows": []} if isinstance(item, dict) else item
            for item in files
        ]
    return {
        "slot": row["slot"],
        "state": state,
        "reason": row["reason"],
        "updatedAt": row["updated_at"],
        "statusText": f"Autosave restored: {format_display_datetime(row['updated_at'])}",
    }


def list_autosave_states(limit: int = 50) -> dict[str, Any]:
    try:
        requested_limit = int(limit or 50)
    except (TypeError, ValueError):
        requested_limit = 50
    bounded_limit = max(1, min(requested_limit, 200))
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT slot, state_json, reason, updated_at FROM app_autosaves ORDER BY updated_at DESC LIMIT ?",
            (bounded_limit,),
        ).fetchall()
    autosaves = []
    for row in rows:
        autosaves.append({
            "slot": row["slot"],
            "reason": row["reason"],
            "updatedAt": row["updated_at"],
            "bytes": len(row["state_json"] or ""),
        })
    return {"autosaves": autosaves, "summary": {"count": len(autosaves), "slots": [item["slot"] for item in autosaves]}}


def delete_autosave_state(slot: str = "main") -> bool:
    autosave_slot = as_text(slot) or "main"
    with db_connection() as conn:
        cursor = conn.execute("DELETE FROM app_autosaves WHERE slot = ?", (autosave_slot,))
    if cursor.rowcount:
        log_action("Autosave deleted", f"slot={autosave_slot}")
    return bool(cursor.rowcount)


def autosave_delete_status_text(deleted: bool) -> str:
    return "Autosave deleted from SQLite." if deleted else "Autosave slot is already empty."


def export_app_backup(state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise ValueError("state must be an object")
    content = json.dumps({"version": 1, "createdAt": utc_now(), "state": state}, ensure_ascii=False, indent=2)
    filename = "mac-analyzer-backup.json"
    stored_name = "mac-analyzer-backup-" + datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ") + ".json"
    stored_path = STORAGE.backups / stored_name
    stored_path.write_text(content, encoding="utf-8")
    return {
        "filename": filename,
        "mimeType": "application/json",
        "content": content,
        "bytes": len(content.encode("utf-8")),
        "storedPath": str(stored_path),
    }


def restore_app_backup(content_base64: str) -> dict[str, Any]:
    try:
        raw = base64.b64decode(as_text(content_base64), validate=True).decode("utf-8-sig")
        payload = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as error:
        raise ValueError("Invalid backup JSON") from error
    if isinstance(payload, dict) and isinstance(payload.get("state"), dict):
        state = payload["state"]
        version = payload.get("version", 1)
    elif isinstance(payload, dict):
        state = payload
        version = 0
    else:
        raise ValueError("Backup must contain a state object")
    restored_name = "restored-backup-" + datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ") + ".json"
    restored_path = STORAGE.backups / restored_name
    restored_path.write_text(raw, encoding="utf-8")
    return {"state": state, "version": version, "bytes": len(raw.encode("utf-8")), "storedPath": str(restored_path)}


def handle_shutdown_signal(signum: int, server: Optional[ThreadingHTTPServer] = None) -> None:
    SIGNAL_STATE.update({"lastSignal": int(signum), "lastSignalAt": utc_now(), "shutdownRequested": server is not None})
    log_action("Backend shutdown signal", f"signal={signum}")
    if server is not None:
        threading.Thread(target=server.shutdown, daemon=True).start()


def signal_status() -> dict[str, Any]:
    return dict(SIGNAL_STATE)


def start_enrichment_job(job_id: str = "", source: str = "", strategy: str = "primary") -> dict[str, Any]:
    normalized_id = as_text(job_id) or str(uuid.uuid4())
    timestamp = utc_now()
    job = {
        "id": normalized_id,
        "source": as_text(source),
        "strategy": as_text(strategy) or "primary",
        "status": "running",
        "cancelRequested": False,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "progress": {"status": "running", "percent": 0, "rows": 0, "valid": 0, "invalid": 0},
    }
    ENRICHMENT_JOBS[normalized_id] = job
    return job


def update_enrichment_job(job_id: str, progress: dict[str, Any], status: str = "") -> dict[str, Any]:
    normalized_id = as_text(job_id)
    job = ENRICHMENT_JOBS.get(normalized_id) or start_enrichment_job(normalized_id)
    job["progress"] = {**job.get("progress", {}), **(progress or {})}
    job["status"] = as_text(status) or job["progress"].get("status") or job.get("status") or "running"
    job["updatedAt"] = utc_now()
    return job


def cancel_enrichment_job(job_id: str) -> dict[str, Any]:
    normalized_id = as_text(job_id)
    job = ENRICHMENT_JOBS.get(normalized_id) or start_enrichment_job(normalized_id)
    job["cancelRequested"] = True
    if job.get("status") != "completed":
        job["status"] = "cancelled"
    job["progress"] = {**job.get("progress", {}), "status": job["status"]}
    job["updatedAt"] = utc_now()
    log_action("Enrichment cancelled", f"job={normalized_id}")
    return job


def enrichment_job_status(job_id: str) -> Optional[dict[str, Any]]:
    job = ENRICHMENT_JOBS.get(as_text(job_id))
    return dict(job) if job else None


def install_signal_handlers(server: ThreadingHTTPServer) -> None:
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda received, _frame, srv=server: handle_shutdown_signal(received, srv))


class ManagedSQLiteConnection(sqlite3.Connection):
    """Commit or roll back and always release the SQLite handle after `with`."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=30, factory=ManagedSQLiteConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def init_database() -> None:
    with db_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS app_autosaves (
                slot TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                reason TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS engineering_sessions (
                token_hash TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                permissions_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_engineering_sessions_expires ON engineering_sessions(expires_at);
            CREATE TABLE IF NOT EXISTS vendor_mappings (
                oui TEXT PRIMARY KEY,
                vendor TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'custom',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS model_mappings (
                prefix TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'custom',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mac_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT NOT NULL,
                mac_formatted TEXT NOT NULL,
                oui TEXT,
                vendor TEXT,
                model TEXT,
                ip TEXT,
                address TEXT,
                room TEXT,
                switch_ip TEXT,
                switch_port TEXT,
                source TEXT,
                recorded_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mac_history_mac ON mac_history(mac);
            CREATE INDEX IF NOT EXISTS idx_mac_history_oui ON mac_history(oui);
            CREATE INDEX IF NOT EXISTS idx_mac_history_recorded_at ON mac_history(recorded_at);
            CREATE TABLE IF NOT EXISTS mac_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT NOT NULL,
                field_name TEXT NOT NULL,
                from_value TEXT,
                to_value TEXT,
                source TEXT,
                changed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mac_movements_mac ON mac_movements(mac);
            CREATE TABLE IF NOT EXISTS vendor_model_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT NOT NULL,
                oui TEXT,
                prefix TEXT,
                vendor TEXT,
                model TEXT,
                source TEXT,
                observed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_vendor_model_history_mac ON vendor_model_history(mac);
            CREATE INDEX IF NOT EXISTS idx_vendor_model_history_oui ON vendor_model_history(oui);
            CREATE INDEX IF NOT EXISTS idx_vendor_model_history_prefix ON vendor_model_history(prefix);
            CREATE INDEX IF NOT EXISTS idx_vendor_model_history_observed ON vendor_model_history(observed_at);
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source TEXT,
                device_count INTEGER NOT NULL,
                devices_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL DEFAULT '{}',
                last_run_at TEXT,
                next_run_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS task_file_queue (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_base64 TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                FOREIGN KEY(task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_task_file_queue_task ON task_file_queue(task_id);
            CREATE INDEX IF NOT EXISTS idx_task_file_queue_status ON task_file_queue(status);
            CREATE TABLE IF NOT EXISTS ip_address_mappings (
                switch_ip TEXT PRIMARY KEY,
                physical_address TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS column_preferences (
                view_name TEXT PRIMARY KEY,
                columns_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notification_settings (
                channel TEXT PRIMARY KEY,
                config_json TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                cached_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS app_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS data_quality_reports (
                id TEXT PRIMARY KEY,
                source TEXT,
                score REAL NOT NULL,
                grade TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_data_quality_reports_created ON data_quality_reports(created_at);
            """
        )
        for oui, vendor in BUILTIN_VENDORS.items():
            conn.execute(
                "INSERT OR IGNORE INTO vendor_mappings (oui, vendor, source, updated_at) VALUES (?, ?, 'builtin', ?)",
                (oui, vendor, utc_now()),
            )
        for prefix, model in BUILTIN_MODELS.items():
            conn.execute(
                "INSERT OR IGNORE INTO model_mappings (prefix, model, source, updated_at) VALUES (?, ?, 'builtin', ?)",
                (prefix, model, utc_now()),
            )
        for reference_path in (STORAGE.reference / "oui.csv", STORAGE.reference / "oui.txt"):
            if not reference_path.is_file():
                continue
            signature = f"{reference_path.name}:{reference_path.stat().st_size}:{reference_path.stat().st_mtime_ns}"
            saved = conn.execute("SELECT value FROM app_settings WHERE key = 'oui_reference_signature'").fetchone()
            if saved and saved["value"] == signature:
                break
            try:
                result = import_oui_reference(conn, reference_path.read_bytes(), reference_path.name)
                conn.execute(
                    "INSERT INTO app_settings (key, value, updated_at) VALUES ('oui_reference_signature', ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (signature, utc_now()),
                )
                conn.execute(
                    "INSERT INTO app_logs (action, details, created_at) VALUES (?, ?, ?)",
                    ("OUI reference synchronized", json.dumps(result, ensure_ascii=False), utc_now()),
                )
            except (OSError, ValueError, csv.Error, UnicodeError) as error:
                conn.execute(
                    "INSERT INTO app_logs (action, details, created_at) VALUES (?, ?, ?)",
                    ("OUI reference synchronization failed", str(error), utc_now()),
                )
            break


def normalize_mac(value: Any) -> Optional[str]:
    cleaned = re.sub(r"[^0-9A-F]", "", str(value or "").upper())
    if len(cleaned) == 10:
        cleaned = "00" + cleaned
    elif len(cleaned) == 11:
        cleaned = "0" + cleaned
    elif len(cleaned) == 8:
        cleaned = "0000" + cleaned
    return cleaned if len(cleaned) == 12 else None


def format_mac(mac: str) -> str:
    return ":".join(mac[index:index + 2] for index in range(0, 12, 2))


def as_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def format_display_datetime(value: Any) -> str:
    text = as_text(value)
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%d.%m.%Y, %H:%M:%S")
    except ValueError:
        return text


def normalize_result_columns(columns: Any) -> list[str]:
    normalized: list[str] = []
    for column in columns if isinstance(columns, list) else DEFAULT_RESULT_COLUMNS:
        name = as_text(column)
        if name and name not in normalized:
            normalized.append(name)
    return normalized or list(DEFAULT_RESULT_COLUMNS)


def result_cell_value(row: dict[str, Any], column: str) -> str:
    value = row.get(column)
    if column == "macFormatted" and not as_text(value):
        mac = normalize_mac(row.get("mac"))
        value = format_mac(mac) if mac else row.get("mac")
    return as_text(value) or "—"


def result_header_html(columns: list[str], labels: Any) -> str:
    label_map = {**DEFAULT_RESULT_LABELS, **(labels if isinstance(labels, dict) else {})}
    return "".join(
        f"<th>{html_lib.escape(as_text(label_map.get(column)) or column)}</th>"
        for column in columns
    )


def result_table_rows_html(rows: list[dict[str, Any]], columns: list[str]) -> str:
    colspan = max(1, len(columns))
    if not rows:
        return f'<tr><td colspan="{colspan}" class="empty-state">Нет записей по заданному фильтру.</td></tr>'
    rendered: list[str] = []
    for row in rows:
        if row.get("valid"):
            mac = html_lib.escape(as_text(row.get("mac")))
            cells = "".join(
                f"<td>{html_lib.escape(result_cell_value(row, column))}</td>"
                for column in columns
            )
            rendered.append(f'<tr data-mac="{mac}">{cells}</tr>')
        else:
            line = html_lib.escape(as_text(row.get("row")))
            source = html_lib.escape(as_text(row.get("source")))
            raw = html_lib.escape(as_text(row.get("raw")))
            rendered.append(f'<tr><td colspan="{colspan}"><strong>Ошибка:</strong> строка {line} в {source}: «{raw}» не похожа на MAC.</td></tr>')
    return "".join(rendered)


def result_vendor_options_html(vendors: list[str], selected_vendor: str = "") -> str:
    options = ['<option value="">Все вендоры</option>']
    for vendor in vendors:
        safe_vendor = html_lib.escape(vendor)
        selected = " selected" if vendor == selected_vendor else ""
        options.append(f'<option value="{safe_vendor}"{selected}>{safe_vendor}</option>')
    return "".join(options)


def filter_result_devices(
    devices: list[dict[str, Any]],
    invalid: list[dict[str, Any]],
    filters: dict[str, Any],
    columns: Any = None,
    labels: Any = None,
) -> dict[str, Any]:
    query = as_text(filters.get("query")).lower()
    vendor = as_text(filters.get("vendor"))
    validity = as_text(filters.get("validity")).lower()
    try:
        oui_length = int(filters.get("ouiLength") or 3)
    except (TypeError, ValueError):
        oui_length = 3
    oui_style = as_text(filters.get("ouiStyle")) or "plain"

    try:
        limit = max(25, min(int(filters.get("limit") or 250), 1000))
    except (TypeError, ValueError):
        limit = 250
    try:
        offset = max(0, int(filters.get("offset") or 0))
    except (TypeError, ValueError):
        offset = 0

    def matches(row: dict[str, Any]) -> bool:
        if vendor and as_text(row.get("vendor")) != vendor:
            return False
        if query:
            haystack = " ".join(as_text(value) for value in row.values()).lower()
            if query not in haystack:
                return False
        return True

    page_rows: list[dict[str, Any]] = []
    total = 0
    valid_count = 0
    invalid_count = 0
    sources: list[tuple[list[dict[str, Any]], bool]] = []
    if validity != "invalid":
        sources.append((devices, True))
    if validity != "valid":
        sources.append((invalid, False))
    for source_rows, is_valid in sources:
        for raw_row in source_rows:
            if not isinstance(raw_row, dict) or not matches(raw_row):
                continue
            if total >= offset and len(page_rows) < limit:
                page_rows.append({**raw_row, "valid": is_valid})
            total += 1
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1

    formatted_ouis = format_oui_for_devices(page_rows, oui_length, oui_style)
    enriched_rows = [
        {**row, "oui": formatted.get("oui", row.get("oui", ""))}
        for row, formatted in zip(page_rows, formatted_ouis)
    ]
    vendors = sorted({
        as_text(device.get("vendor"))
        for device in devices
        if as_text(device.get("vendor"))
    })
    normalized_columns = normalize_result_columns(columns)
    table_rows_html = result_table_rows_html(enriched_rows, normalized_columns)
    pages = max(1, (total + limit - 1) // limit)
    page = min(pages, offset // limit + 1)
    return {
        "items": enriched_rows,
        "vendors": vendors,
        "columns": normalized_columns,
        "headerHtml": result_header_html(normalized_columns, labels),
        "tableRowsHtml": table_rows_html,
        "emptyTableRowsHtml": result_table_rows_html([], normalized_columns),
        "vendorOptionsHtml": result_vendor_options_html(vendors, vendor),
        "summaryText": f"{total} записей",
        "pagination": {
            "total": total,
            "offset": offset,
            "limit": limit,
            "page": page,
            "pages": pages,
            "hasPrevious": offset > 0,
            "hasNext": offset + limit < total,
        },
        "summary": {
            "total": total,
            "valid": valid_count,
            "invalid": invalid_count,
            "vendors": len(vendors),
        },
    }


def result_dataset_summary(devices: list[dict[str, Any]], invalid: list[dict[str, Any]]) -> dict[str, Any]:
    known_vendor = [
        device for device in devices
        if as_text(device.get("vendor")) not in {"", "Unknown", "Не определено"}
    ]
    normalized_macs = [normalize_mac(device.get("mac") or device.get("macFormatted")) for device in devices]
    return {
        "devices": len(devices),
        "invalid": len(invalid),
        "vendors": len({as_text(device.get("vendor")) for device in known_vendor}),
        "models": len({as_text(device.get("model")) for device in devices if as_text(device.get("model"))}),
        "known": len(known_vendor),
        "knownPercent": round(len(known_vendor) / len(devices) * 100) if devices else 0,
        "oui3": len({mac[:6] for mac in normalized_macs if len(mac) >= 6}),
        "oui4": len({mac[:8] for mac in normalized_macs if len(mac) >= 8}),
        "oui5": len({mac[:10] for mac in normalized_macs if len(mac) >= 10}),
        "autoVendors": sum(1 for device in known_vendor if device.get("vendorMatchedPrefix") or as_text(device.get("vendorSource")) not in {"file", "history"}),
        "autoModels": sum(1 for device in devices if as_text(device.get("model")) and (device.get("modelMatchedPrefix") or as_text(device.get("modelSource")) not in {"file", "history"})),
    }


def result_header_payload(columns: Any = None, labels: Any = None) -> dict[str, Any]:
    normalized_columns = normalize_result_columns(columns)
    return {
        "columns": normalized_columns,
        "columnCount": len(normalized_columns),
        "headerHtml": result_header_html(normalized_columns, labels),
        "emptyTableRowsHtml": result_table_rows_html([], normalized_columns),
    }


def normalize_column_preferences(payload: dict[str, Any]) -> dict[str, Any]:
    raw_columns = payload.get("columns")
    raw_order = payload.get("order", raw_columns if isinstance(raw_columns, list) else DEFAULT_RESULT_COLUMNS)
    raw_visible = payload.get("visible", raw_columns if isinstance(raw_columns, list) else raw_order)
    raw_custom = payload.get("custom", payload.get("customColumns", []))
    raw_widths = payload.get("widths", payload.get("columnWidths", {}))
    explicit_visible = "visible" in payload or isinstance(raw_columns, list)

    order: list[str] = []
    for column in raw_order if isinstance(raw_order, list) else []:
        name = as_text(column)
        if name and name not in order:
            order.append(name)
    for column in DEFAULT_RESULT_COLUMNS:
        if column not in order:
            order.append(column)

    visible: list[str] = []
    for column in raw_visible if isinstance(raw_visible, list) else []:
        name = as_text(column)
        if name and name in order and name not in visible:
            visible.append(name)
    if not visible:
        visible = [column for column in order if column in DEFAULT_RESULT_COLUMNS]

    custom: list[dict[str, Any]] = []
    if isinstance(raw_custom, list):
        for item in raw_custom:
            if isinstance(item, dict):
                key = as_text(item.get("key") or item.get("field"))
                title = as_text(item.get("title") or item.get("label") or key)
                source_index = item.get("sourceIndex", item.get("source_index"))
            else:
                key = as_text(item)
                title = key
                source_index = None
            if key and key not in {entry["key"] for entry in custom}:
                if key not in order:
                    order.append(key)
                if key not in visible and payload.get("showCustomByDefault", not explicit_visible):
                    visible.append(key)
                custom.append({"key": key, "title": title, "sourceIndex": source_index})

    widths: dict[str, int] = {}
    width_values = raw_widths if isinstance(raw_widths, dict) else {}
    for column in order:
        fallback = DEFAULT_RESULT_COLUMN_WIDTHS.get(column, 150)
        try:
            width = int(width_values.get(column, fallback))
        except (TypeError, ValueError):
            width = fallback
        widths[column] = max(64, min(width, 600))

    return {"order": order, "visible": visible, "custom": custom, "widths": widths}


def save_column_preferences(view_name: str, preferences: dict[str, Any]) -> dict[str, Any]:
    name = as_text(view_name) or "results"
    normalized = normalize_column_preferences(preferences)
    timestamp = utc_now()
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO column_preferences (view_name, columns_json, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(view_name) DO UPDATE SET columns_json=excluded.columns_json, updated_at=excluded.updated_at",
            (name, json.dumps(normalized, ensure_ascii=False), timestamp),
        )
    return {**normalized, "updatedAt": timestamp}


def load_column_preferences(view_name: str) -> dict[str, Any]:
    name = as_text(view_name) or "results"
    with db_connection() as conn:
        row = conn.execute("SELECT columns_json, updated_at FROM column_preferences WHERE view_name = ?", (name,)).fetchone()
    if not row:
        normalized = normalize_column_preferences({"columns": DEFAULT_RESULT_COLUMNS})
        return {**normalized, "updatedAt": None}
    saved = json.loads(row["columns_json"])
    if isinstance(saved, list):
        normalized = normalize_column_preferences({"columns": saved})
    elif isinstance(saved, dict):
        normalized = normalize_column_preferences(saved)
    else:
        normalized = normalize_column_preferences({"columns": DEFAULT_RESULT_COLUMNS})
    return {**normalized, "updatedAt": row["updated_at"]}


def column_preferences_panel_payload(preferences: dict[str, Any], labels: Any = None) -> dict[str, Any]:
    prefs = normalize_column_preferences(preferences if isinstance(preferences, dict) else {})
    custom = prefs.get("custom") or []
    custom_keys = [as_text(item.get("key")) for item in custom if as_text(item.get("key"))]
    custom_labels = {as_text(item.get("key")): as_text(item.get("title")) or as_text(item.get("key")) for item in custom if as_text(item.get("key"))}
    label_map = {**DEFAULT_RESULT_LABELS, **custom_labels, **(labels if isinstance(labels, dict) else {})}
    base_fields = [*DEFAULT_RESULT_COLUMNS, *[key for key in custom_keys if key not in DEFAULT_RESULT_COLUMNS]]
    fields = [field for field in prefs.get("order", []) if field in base_fields]
    fields.extend(field for field in base_fields if field not in fields)
    visible = set(prefs.get("visible") or [])
    widths = prefs.get("widths") or {}
    rows = []
    for index, field in enumerate(fields):
        escaped_field = html_lib.escape(as_text(field), quote=True)
        checked = " checked" if field in visible else ""
        up_disabled = " disabled" if index == 0 else ""
        down_disabled = " disabled" if index == len(fields) - 1 else ""
        remove_button = (
            f'<button type="button" data-remove-custom-column="{escaped_field}">Удалить</button>'
            if field in custom_keys else ""
        )
        width = int(widths.get(field) or DEFAULT_RESULT_COLUMN_WIDTHS.get(field, 150))
        rows.append(
            f'<label class="check" data-column-field="{escaped_field}">'
            f'<input type="checkbox" value="{escaped_field}"{checked}> '
            f'{html_lib.escape(as_text(label_map.get(field)) or as_text(field))}'
            f'<input type="number" min="64" max="600" value="{width}" data-column-width="{escaped_field}" title="Ширина столбца в пикселях">'
            f'<button type="button" data-move-column="{escaped_field}" data-direction="up"{up_disabled}>↑</button>'
            f'<button type="button" data-move-column="{escaped_field}" data-direction="down"{down_disabled}>↓</button>'
            f'{remove_button}</label>'
        )
    return {
        "preferences": prefs,
        "columns": prefs.get("visible", []),
        "listHtml": "".join(rows) or '<p class="muted">Колонки не настроены.</p>',
        "emptyListHtml": '<p class="muted">Колонки не настроены.</p>',
    }


def normalize_enrichment_fields(fields: Any) -> dict[str, bool]:
    defaults = {field: True for field in DEVICE_FIELDS}
    defaults["history"] = True
    if not isinstance(fields, dict):
        return defaults
    for field in defaults:
        if field in fields:
            defaults[field] = bool(fields[field])
    return defaults


def enrichment_field_summary(fields: dict[str, bool]) -> dict[str, Any]:
    enabled = [field for field, value in fields.items() if value]
    disabled = [field for field, value in fields.items() if not value]
    return {"enabled": enabled, "disabled": disabled, "total": len(fields), "enabledCount": len(enabled)}


def enrichment_progress_html(progress: Any = None, status: str = "running") -> str:
    data = progress if isinstance(progress, dict) else {}
    normalized_status = as_text(status).lower()
    if normalized_status in {"starting", "start", "pending"}:
        label = as_text(data.get("label")) or "Обогащение"
        detail = as_text(data.get("detail")) or "запуск"
        percent = int(data.get("percent") or 15)
    else:
        label = f"Файлов: {int(data.get('files') or 0)}, строк: {int(data.get('rows') or 0)}"
        detail = f"OK: {int(data.get('valid') or 0)} / ошибок: {int(data.get('invalid') or 0)}"
        percent = int(data.get("percent") or 100)
    percent = max(0, min(100, percent))
    return (
        '<div class="bar-item"><div class="bar-label">'
        f'<span>{html_lib.escape(label)}</span>'
        f'<strong>{html_lib.escape(detail)}</strong>'
        '</div><div class="bar-track">'
        f'<div class="bar-fill" style="width:{percent}%"></div>'
        '</div></div>'
    )


def column_label(field: Any) -> str:
    labels = {**DEFAULT_RESULT_LABELS, "mac": "MAC-адрес"}
    return labels.get(as_text(field), as_text(field))


def mapping_summary_html(summary: dict[str, Any]) -> str:
    required = summary.get("requiredMissing") or []
    return (
        '<div class="mapping-row"><span><strong>Mapping summary</strong>'
        f'<small>{len(summary.get("mapped") or [])} mapped · missing {len(summary.get("missing") or [])} · '
        f'required {html_lib.escape(", ".join(as_text(item) for item in required) if required else "OK")}</small>'
        '</span></div>'
    )


def column_detection_html(result: dict[str, Any], headers: list[Any]) -> str:
    names = _normalize_header_names(headers)
    mapping = result.get("mapping") if isinstance(result.get("mapping"), dict) else {}
    mapped = []
    for field, index in mapping.items():
        try:
            header = names[int(index)]
        except (TypeError, ValueError, IndexError):
            header = as_text(index)
        mapped.append(
            '<div class="mapping-row"><span>'
            f'<strong>{html_lib.escape(column_label(field))}</strong>'
            f'<small>{html_lib.escape(header)}</small>'
            '</span></div>'
        )
    ai = []
    for item in ((result.get("ai") or {}).get("suggestions") or [])[:8]:
        ai.append(
            '<div class="mapping-row"><span>'
            f'<strong>AI: {html_lib.escape(column_label(item.get("field")))}</strong>'
            f'<small>{html_lib.escape(as_text(item.get("header") if item.get("header") is not None else item.get("index")))} · '
            f'{html_lib.escape(as_text(item.get("confidence")))} · {html_lib.escape(as_text(item.get("reason")))}</small>'
            '</span></div>'
        )
    conflicts = []
    for item in result.get("conflicts") or []:
        fields = ", ".join(as_text(field) for field in item.get("fields") or [])
        resolution = f' · {html_lib.escape(as_text(item.get("resolution")))}' if as_text(item.get("resolution")) else ""
        conflicts.append(
            '<div class="mapping-row"><span><strong>Conflict</strong>'
            f'<small>{html_lib.escape(as_text(item.get("header")) or "column")} -> {html_lib.escape(fields)}{resolution}</small>'
            '</span></div>'
        )
    warnings = []
    for item in (result.get("warnings") or [])[:6]:
        confidence = f' · {html_lib.escape(as_text(item.get("confidence")))}' if item.get("confidence") is not None else ""
        warnings.append(
            '<div class="mapping-row"><span>'
            f'<strong>{html_lib.escape(as_text(item.get("field")))}</strong>'
            f'<small>{html_lib.escape(as_text(item.get("message")))}{confidence}</small>'
            '</span></div>'
        )
    return (
        '<div class="mapping-row"><span><strong>Column detector</strong>'
        f'<small>{len(mapping)} fields mapped · {html_lib.escape(as_text(result.get("mode")) or "auto")}</small></span></div>'
        + "".join(mapped + ai + conflicts + warnings)
    )


def column_conflict_review_payload(headers: list[Any], rows: list[Any], result: dict[str, Any]) -> dict[str, Any]:
    names = _normalize_header_names(headers)
    scores = result.get("scores") if isinstance(result.get("scores"), dict) else {}
    selected_mapping = result.get("mapping") if isinstance(result.get("mapping"), dict) else {}
    fields = [
        ("mac", "MAC-адрес", True), ("vendor", "Производитель", False),
        ("model", "Модель", False), ("ip", "IP-адрес", False),
        ("address", "Физический адрес", False), ("room", "Помещение", False),
        ("switchIp", "IP коммутатора", False), ("switchPort", "Порт подключения", False),
    ]
    review_rows: list[dict[str, Any]] = []
    rows_html: list[str] = []
    auto_mapping: dict[str, int] = {}
    for field, label, required in fields:
        candidates = scores.get(field, []) if isinstance(scores.get(field), list) else []
        best = candidates[0] if candidates and float(candidates[0].get("confidence") or 0) > 0.15 else None
        selected_index = selected_mapping.get(field)
        if selected_index is None and best:
            selected_index = best.get("index")
        try:
            normalized_selected = int(selected_index) if selected_index is not None else None
        except (TypeError, ValueError):
            normalized_selected = None
        if best:
            auto_mapping[field] = int(best["index"])
            confidence = int(round(float(best.get("confidence") or 0) * 100))
            recommendation = f'{best.get("header") or names[int(best["index"])]} ({confidence}%)'
            reason = as_text(best.get("reason"))
            sample_index = int(best["index"])
        else:
            confidence = 0
            recommendation = "Не определено"
            reason = "Выберите колонку вручную"
            sample_index = normalized_selected if normalized_selected is not None else -1
        samples: list[str] = []
        for row in rows[:10] if isinstance(rows, list) else []:
            if isinstance(row, dict):
                value = row.get(sample_index, row.get(str(sample_index)))
            elif isinstance(row, (list, tuple)) and 0 <= sample_index < len(row):
                value = row[sample_index]
            else:
                value = None
            text = as_text(value)
            if text and text not in samples:
                samples.append(text[:60])
            if len(samples) == 2:
                break
        options = ['<option value="">Не указано</option>']
        for index, name in enumerate(names):
            selected = " selected" if normalized_selected == index else ""
            options.append(f'<option value="{index}"{selected}>{html_lib.escape(name)}</option>')
        required_class = " required-field" if required else ""
        rows_html.append(
            f'<tr data-conflict-field="{field}" data-ai-index="{auto_mapping.get(field, "")}">'
            f'<td class="{required_class.strip()}"><strong>{html_lib.escape(label)}</strong>{" *" if required else ""}</td>'
            f'<td><strong>{html_lib.escape(recommendation)}</strong><small>{html_lib.escape(reason)}</small></td>'
            f'<td><select data-conflict-column="{field}" aria-label="Колонка для {html_lib.escape(label)}">{"".join(options)}</select></td>'
            f'<td>{html_lib.escape(", ".join(samples))}</td>'
            '</tr>'
        )
        review_rows.append({
            "field": field, "label": label, "required": required, "selectedIndex": normalized_selected,
            "recommendedIndex": auto_mapping.get(field), "recommendation": recommendation,
            "confidence": confidence, "reason": reason, "samples": samples,
            "alternatives": candidates[:4],
        })
    return {
        "fields": review_rows,
        "autoMapping": auto_mapping,
        "selectedMapping": {
            field: int(index) for field, index in selected_mapping.items()
            if field in {item[0] for item in fields} and str(index).isdigit()
        },
        "conflicts": result.get("conflicts") or [],
        "warnings": result.get("warnings") or [],
        "requiresReview": bool(result.get("conflicts") or result.get("warnings")),
        "rowsHtml": "".join(rows_html),
        "emptyRowsHtml": '<tr><td colspan="4" class="empty-state">Кандидаты колонок не найдены.</td></tr>',
    }


def mapping_summary(headers: list[Any], mapping: dict[str, Any], fields: Optional[dict[str, bool]] = None) -> dict[str, Any]:
    names = _normalize_header_names(headers)
    mapped = []
    missing = []
    for field in ("mac", *DEVICE_FIELDS):
        value = mapping.get(field, "") if isinstance(mapping, dict) else ""
        if value == "" or value is None:
            missing.append(field)
            continue
        try:
            index = int(value)
        except (TypeError, ValueError):
            missing.append(field)
            continue
        mapped.append({"field": field, "index": index, "header": names[index] if 0 <= index < len(names) else str(index)})
    normalized_fields = normalize_enrichment_fields(fields or {})
    result = {
        "headers": len(names),
        "mapped": mapped,
        "missing": missing,
        "requiredMissing": [field for field in missing if field == "mac"],
        "enrichment": enrichment_field_summary(normalized_fields),
    }
    return {**result, "summaryHtml": mapping_summary_html(result)}


def _normalize_header_names(headers: list[Any]) -> list[str]:
    names = []
    for index, header in enumerate(headers if isinstance(headers, list) else []):
        if isinstance(header, dict):
            names.append(as_text(header.get("name") or header.get("title") or index))
        else:
            names.append(as_text(header) or str(index))
    return names


def oui_settings() -> dict[str, Any]:
    with db_connection() as conn:
        row = conn.execute("SELECT value, updated_at FROM app_settings WHERE key = 'oui_format'").fetchone()
    if not row:
        return {"length": 3, "style": "plain", "updatedAt": None}
    try:
        value = json.loads(row["value"])
    except (TypeError, ValueError, json.JSONDecodeError):
        value = {}
    return normalize_oui_settings(value, row["updated_at"])


def normalize_oui_settings(value: dict[str, Any], updated_at: Optional[str] = None) -> dict[str, Any]:
    try:
        length = int(value.get("length", 3) if isinstance(value, dict) else 3)
    except (TypeError, ValueError):
        length = 3
    style = as_text(value.get("style") if isinstance(value, dict) else "plain").lower() or "plain"
    if style not in {"plain", "colon", "dash", "dot", "cisco-dot"}:
        style = "plain"
    return {"length": max(3, min(length, 6)), "style": style, "updatedAt": updated_at}


def save_oui_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_oui_settings(settings)
    timestamp = utc_now()
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES ('oui_format', ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (json.dumps({"length": normalized["length"], "style": normalized["style"]}, ensure_ascii=False), timestamp),
        )
    log_action("OUI settings updated", f"length={normalized['length']}, style={normalized['style']}")
    normalized["updatedAt"] = timestamp
    return normalized


def vendor_detector_settings() -> dict[str, Any]:
    with db_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'vendor_detector'").fetchone()
    if not row:
        return normalize_detector_settings({})
    try:
        return normalize_detector_settings(json.loads(row["value"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return normalize_detector_settings({})


def save_vendor_detector_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_detector_settings(settings)
    timestamp = utc_now()
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES ('vendor_detector', ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (json.dumps(normalized, ensure_ascii=False), timestamp),
        )
    log_action("Vendor detector settings updated", json.dumps(normalized, ensure_ascii=False))
    return {**normalized, "updatedAt": timestamp}


def normalize_history_enrichment_settings(settings: dict[str, Any] | None) -> dict[str, Any]:
    source = settings if isinstance(settings, dict) else {}
    return {
        "enabled": source.get("enabled") is not False,
        "priorityHistory": source.get("priorityHistory") is not False,
        "useOuiMatch": source.get("useOuiMatch") is not False,
        "useMac5Match": source.get("useMac5Match") is not False,
    }


def history_enrichment_settings() -> dict[str, Any]:
    with db_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'history_enrichment'").fetchone()
    if not row:
        return normalize_history_enrichment_settings({})
    try:
        return normalize_history_enrichment_settings(json.loads(row["value"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return normalize_history_enrichment_settings({})


def save_history_enrichment_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_history_enrichment_settings(settings)
    timestamp = utc_now()
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES ('history_enrichment', ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (json.dumps(normalized, ensure_ascii=False), timestamp),
        )
    log_action("History enrichment settings updated", json.dumps(normalized, ensure_ascii=False))
    return {**normalized, "updatedAt": timestamp}


def list_column_preferences() -> dict[str, Any]:
    with db_connection() as conn:
        rows = conn.execute("SELECT view_name, columns_json, updated_at FROM column_preferences ORDER BY view_name").fetchall()
    views = []
    for row in rows:
        try:
            saved = json.loads(row["columns_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            saved = {}
        normalized = normalize_column_preferences(saved if isinstance(saved, dict) else {"columns": saved})
        views.append({"view": row["view_name"], "preferences": {**normalized, "updatedAt": row["updated_at"]}})
    return {"views": views, "summary": {"views": len(views), "customColumns": sum(len(item["preferences"]["custom"]) for item in views)}}


def snapshot_state_items(limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit or 100), 500))
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT rowid AS snapshot_order, * FROM snapshots ORDER BY rowid DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "source": row["source"],
            "createdAt": row["created_at"],
            "created_at": row["created_at"],
            "deviceCount": int(row["device_count"] or 0),
            "devices": [],
            "backendStored": True,
            "snapshotOrder": int(row["snapshot_order"] or 0),
            "kind": "analysis" if as_text(row["name"]).casefold().startswith("анализ:") else "snapshot",
        }
        for row in rows
    ]


def hydrate_snapshot_devices(snapshots: Any) -> list[dict[str, Any]]:
    """Load SQLite-backed snapshot bodies only for operations that need them."""
    items = [dict(item) for item in snapshots if isinstance(item, dict)] if isinstance(snapshots, list) else []
    missing_ids = [
        as_text(item.get("id"))
        for item in items
        if as_text(item.get("id")) and not item.get("devices")
    ]
    if not missing_ids:
        return items
    placeholders = ",".join("?" for _ in missing_ids)
    with db_connection() as conn:
        rows = conn.execute(
            f"SELECT id, devices_json, device_count FROM snapshots WHERE id IN ({placeholders})",
            missing_ids,
        ).fetchall()
    stored = {row["id"]: row for row in rows}
    for item in items:
        row = stored.get(as_text(item.get("id")))
        if row is None or item.get("devices"):
            continue
        try:
            item["devices"] = json.loads(row["devices_json"] or "[]")
        except json.JSONDecodeError:
            item["devices"] = []
        item["deviceCount"] = int(row["device_count"] or len(item["devices"]))
    return items


def dashboard_snapshot_context(
    snapshots: Any,
    current_snapshot_id: str = "",
    settings: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Resolve only the two final enrichment snapshots needed by Dashboard.

    Snapshot bodies remain in SQLite. The browser receives metadata, while this
    helper hydrates the immediately previous and current final results for an
    exact comparison without depending on the movement log.
    """
    client_items = [dict(item) for item in snapshots if isinstance(item, dict)] if isinstance(snapshots, list) else []
    current_id = as_text(current_snapshot_id)
    use_stored_items = bool(current_id) or any(bool(item.get("backendStored")) for item in client_items)
    stored_items = snapshot_state_items(200) if use_stored_items else []
    merged: dict[str, dict[str, Any]] = {}
    anonymous: list[dict[str, Any]] = []
    for item in client_items:
        snapshot_id = as_text(item.get("id") or item.get("snapshotId"))
        if snapshot_id:
            merged[snapshot_id] = item
        else:
            anonymous.append(item)
    for stored in stored_items:
        snapshot_id = as_text(stored.get("id"))
        if not snapshot_id:
            continue
        current = merged.get(snapshot_id, {})
        merged[snapshot_id] = {**stored, **current}

    items = [*merged.values(), *anonymous]
    final_items = [
        item for item in items
        if as_text(item.get("kind")).casefold() == "analysis"
        or as_text(item.get("name")).casefold().startswith("анализ:")
    ]
    options = final_items if len(final_items) >= 2 else items
    options.sort(key=lambda item: (
        int(item.get("snapshotOrder") or item.get("snapshot_order") or 0),
        as_text(item.get("createdAt") or item.get("created_at")),
        as_text(item.get("id")),
    ))

    normalized_settings = dict(settings or {})
    option_ids = [as_text(item.get("id") or item.get("snapshotId")) for item in options]
    option_ids = [snapshot_id for snapshot_id in option_ids if snapshot_id]
    comparison_id = as_text(normalized_settings.get("comparisonSnapshotId"))
    if comparison_id not in option_ids:
        comparison_id = current_id if current_id in option_ids else (option_ids[-1] if option_ids else "")
    baseline_id = as_text(normalized_settings.get("baselineSnapshotId"))
    if baseline_id not in option_ids or baseline_id == comparison_id:
        try:
            comparison_index = option_ids.index(comparison_id)
        except ValueError:
            comparison_index = len(option_ids)
        baseline_id = option_ids[comparison_index - 1] if comparison_index > 0 else ""

    explicit_period = bool(normalized_settings.get("changeDateFrom") or normalized_settings.get("changeDateTo"))
    if baseline_id and comparison_id and (current_id or not explicit_period):
        normalized_settings["changeMode"] = "snapshots"
        normalized_settings["baselineSnapshotId"] = baseline_id
        normalized_settings["comparisonSnapshotId"] = comparison_id

    selected_ids = {baseline_id, comparison_id} - {""}
    selected = [item for item in options if as_text(item.get("id") or item.get("snapshotId")) in selected_ids]
    hydrated = hydrate_snapshot_devices(selected)
    hydrated.sort(key=lambda item: option_ids.index(as_text(item.get("id") or item.get("snapshotId"))))
    return options, hydrated, normalized_settings


def open_snapshot_payload(snapshot_id: str, snapshots: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    target_id = as_text(snapshot_id)
    if not target_id:
        raise ValueError("snapshot id is required")
    for item in snapshots or []:
        if not isinstance(item, dict) or as_text(item.get("id")) != target_id:
            continue
        devices = item.get("devices", [])
        if not isinstance(devices, list):
            devices = []
        if not devices and item.get("backendStored"):
            break
        return {
            "snapshot": {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "source": item.get("source", ""),
                "createdAt": item.get("createdAt") or item.get("created_at", ""),
                "deviceCount": len(devices),
            },
            "devices": devices,
            "invalid": [],
            "lastAnalysis": utc_now(),
        }
    with db_connection() as conn:
        row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (target_id,)).fetchone()
    if not row:
        raise LookupError("Снимок не найден")
    try:
        devices = json.loads(row["devices_json"] or "[]")
    except json.JSONDecodeError:
        devices = []
    if not isinstance(devices, list):
        devices = []
    return {
        "snapshot": {
            "id": row["id"],
            "name": row["name"],
            "source": row["source"],
            "createdAt": row["created_at"],
            "deviceCount": len(devices),
        },
        "devices": devices,
        "invalid": [],
        "lastAnalysis": utc_now(),
    }


def open_compact_snapshot_payload(
    snapshot_id: str,
    snapshots: list[dict[str, Any]] | None = None,
    page_size: Any = 250,
) -> dict[str, Any]:
    """Open a snapshot without returning its complete device array to the browser."""
    opened = open_snapshot_payload(snapshot_id, snapshots)
    devices = opened.get("devices", [])
    invalid = opened.get("invalid", [])
    if not isinstance(devices, list):
        devices = []
    if not isinstance(invalid, list):
        invalid = []
    try:
        limit = max(25, min(int(page_size or 250), 1000))
    except (TypeError, ValueError):
        limit = 250
    page = filter_result_devices(devices, invalid, {"offset": 0, "limit": limit})
    snapshot = opened.get("snapshot", {}) if isinstance(opened.get("snapshot"), dict) else {}
    reference_id = as_text(snapshot.get("id")) or as_text(snapshot_id)
    return {
        **opened,
        "devices": page["items"],
        "invalid": [],
        "compactResult": True,
        "resultReference": {
            "snapshotId": reference_id,
            "deviceCount": len(devices),
            "invalidCount": len(invalid),
            "pageSize": limit,
        },
        "resultSummary": result_dataset_summary(devices, invalid),
        "resultPage": page,
    }


def resolve_payload_devices(payload: dict[str, Any], key: str = "devices") -> list[dict[str, Any]]:
    """Resolve a browser result reference without requiring a full device payload."""
    snapshot_id = as_text(payload.get("snapshotId") or payload.get("resultSnapshotId"))
    if snapshot_id:
        try:
            opened = open_snapshot_payload(snapshot_id)
            devices = opened.get("devices", [])
            return devices if isinstance(devices, list) else []
        except LookupError:
            # A browser may retain an expired/deleted reference across restarts.
            # Keep API routes responsive until bootstrap clears that reference.
            fallback = payload.get(key, [])
            return fallback if isinstance(fallback, list) else []
    devices = payload.get(key, [])
    return devices if isinstance(devices, list) else []


def snapshot_select_payload(snapshots: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    items = [item for item in (snapshots or []) if isinstance(item, dict)]

    def label(item: dict[str, Any]) -> str:
        created_at = as_text(item.get("createdAt") or item.get("created_at"))
        formatted = format_display_datetime(created_at)
        name = as_text(item.get("name")) or as_text(item.get("id")) or "Snapshot"
        return f"{name} · {formatted}" if formatted else name

    options_html = "".join(
        f'<option value="{html_lib.escape(as_text(item.get("id")), quote=True)}">{html_lib.escape(label(item))}</option>'
        for item in items
        if as_text(item.get("id"))
    )
    return {
        "optionsHtml": options_html,
        "emptyOptionHtml": "<option>Нет снимков</option>",
        "comparisonSelectedIndex": 1 if len(items) > 1 else 0,
        "count": len(items),
    }


def bootstrap_payload() -> dict[str, Any]:
    preferences = load_column_preferences("results")
    custom = preferences.get("custom") or []
    return {
        "snapshots": snapshot_state_items(),
        "autosave": load_autosave_state("main", hydrate=False),
        "columns": preferences,
        "customColumns": [item.get("key") for item in custom if item.get("key")],
        "customColumnMappings": {item.get("key"): item.get("sourceIndex") for item in custom if item.get("key")},
        "customLabels": {item.get("key"): item.get("title") or item.get("key") for item in custom if item.get("key")},
    }


def reset_column_preferences(view_name: str) -> dict[str, Any]:
    name = as_text(view_name) or "results"
    with db_connection() as conn:
        cursor = conn.execute("DELETE FROM column_preferences WHERE view_name = ?", (name,))
    log_action("Column preferences reset", f"view={name}, deleted={cursor.rowcount}")
    preferences = load_column_preferences(name)
    return {"deleted": bool(cursor.rowcount), "columns": preferences["visible"], "preferences": preferences}


def move_column_preference(view_name: str, column: str, direction: str) -> dict[str, Any]:
    name = as_text(view_name) or "results"
    field = as_text(column)
    normalized_direction = as_text(direction).lower()
    preferences = load_column_preferences(name)
    order = list(preferences["order"])
    if field not in order:
        raise ValueError("column not found")
    index = order.index(field)
    if normalized_direction in {"up", "left"} and index > 0:
        order[index - 1], order[index] = order[index], order[index - 1]
    elif normalized_direction in {"down", "right"} and index < len(order) - 1:
        order[index + 1], order[index] = order[index], order[index + 1]
    elif normalized_direction not in {"up", "left", "down", "right"}:
        raise ValueError("direction must be up, down, left, or right")
    saved = save_column_preferences(name, {**preferences, "order": order})
    log_action("Column moved", f"view={name}, column={field}, direction={normalized_direction}")
    return {"columns": saved["visible"], "preferences": saved}


def mappings(kind: str) -> dict[str, str]:
    table, key, value = ("vendor_mappings", "oui", "vendor") if kind == "vendors" else ("model_mappings", "prefix", "model")
    with db_connection() as conn:
        rows = conn.execute(f"SELECT {key}, {value} FROM {table} ORDER BY {key}").fetchall()
    return {row[key]: row[value] for row in rows}


def mapping_rules(kind: str) -> list[dict[str, Any]]:
    table, key, value = ("vendor_mappings", "oui", "vendor") if kind == "vendors" else ("model_mappings", "prefix", "model")
    with db_connection() as conn:
        rows = conn.execute(f"SELECT {key}, {value}, source, updated_at FROM {table} ORDER BY LENGTH({key}) DESC, {key}").fetchall()
    return [dict(row) for row in rows]


def mapping_rows_html(rules: list[dict[str, Any]], kind: str) -> str:
    rows = []
    is_model = kind == "model"
    prioritized_rules = list(rules)
    for item in prioritized_rules[:100]:
        key = as_text(item.get("prefix") if is_model else item.get("oui"))
        value = as_text(item.get("model") if is_model else item.get("vendor"))
        source = as_text(item.get("source")) or "SQLite"
        model_button = (
            f'<button data-model-prefixes="{html_lib.escape(value, quote=True)}">Префиксы</button>'
            if is_model else ""
        )
        rows.append(
            '<div class="mapping-row"><span>'
            f"<strong>{html_lib.escape(key)}</strong> · {html_lib.escape(value)}"
            f"<small>{html_lib.escape(source)}</small></span><span>"
            f'{model_button}<button data-remove-{kind}="{html_lib.escape(key, quote=True)}">Удалить</button>'
            "</span></div>"
        )
    return "".join(rows) or '<p class="muted">Правила пока не загружены.</p>'


def mappings_panel_payload() -> dict[str, Any]:
    def visible_rules(kind: str, limit: int = 250) -> tuple[list[dict[str, Any]], int]:
        table, key, value = (
            ("vendor_mappings", "oui", "vendor")
            if kind == "vendors"
            else ("model_mappings", "prefix", "model")
        )
        with db_connection() as conn:
            total = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            rows = conn.execute(
                f"""
                SELECT {key}, {value}, source, updated_at
                FROM {table}
                ORDER BY CASE WHEN source IN ('reference', 'builtin') THEN 1 ELSE 0 END,
                         updated_at DESC, LENGTH({key}) DESC, {key}
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows], total

    vendor_rules, total_vendor_rules = visible_rules("vendors")
    model_rules, total_model_rules = visible_rules("models")
    vendor_values = {item["oui"]: item["vendor"] for item in vendor_rules}
    model_values = {item["prefix"]: item["model"] for item in model_rules}
    return {
        "vendors": vendor_values,
        "models": model_values,
        "vendorRules": vendor_rules,
        "modelRules": model_rules,
        "vendorRowsHtml": mapping_rows_html(vendor_rules, "vendor"),
        "modelRowsHtml": mapping_rows_html(model_rules, "model"),
        "summary": {
            "vendorRules": len(vendor_rules),
            "modelRules": len(model_rules),
            "totalVendorRules": total_vendor_rules,
            "totalModelRules": total_model_rules,
            "customVendorRules": sum(1 for item in vendor_rules if item.get("source") == "custom"),
            "customModelRules": sum(1 for item in model_rules if item.get("source") == "custom"),
        },
    }


def similar_vendor_observations(mac: str) -> list[dict[str, Any]]:
    prefixes = [mac[:10], mac[:8], mac[:6]]
    clauses = [prefix for prefix in prefixes if prefix]
    if not clauses:
        return []
    where = " OR ".join("mac LIKE ?" for _ in clauses)
    params = [prefix + "%" for prefix in clauses]
    with db_connection() as conn:
        rows = conn.execute(
            f"SELECT mac, vendor FROM mac_history WHERE vendor IS NOT NULL AND vendor != '' AND ({where}) ORDER BY recorded_at DESC LIMIT 300",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def _chunks(values: list[str], size: int = 400):
    for offset in range(0, len(values), size):
        yield values[offset:offset + size]


def _json_setting(rows: dict[str, str], key: str) -> dict[str, Any]:
    try:
        value = json.loads(rows.get(key, "{}"))
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def build_enrichment_context(devices: list[dict[str, Any]]) -> dict[str, Any]:
    """Load every detector dependency once for an entire analysis batch."""
    normalized_devices = [item for item in devices if isinstance(item, dict)]
    macs = sorted({normalize_mac(item.get("mac") or item.get("macFormatted")) for item in normalized_devices} - {""})
    target_macs = set(macs)
    ouis = sorted({mac[:6] for mac in macs})
    switch_ips = sorted({as_text(item.get("switchIp")) for item in normalized_devices} - {""})
    vendor_rules: list[dict[str, Any]] = []
    model_rules: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    history_similarity_rows: list[dict[str, Any]] = []
    vendor_model_rows: list[dict[str, Any]] = []
    ip_mappings: dict[str, str] = {}
    settings_rows: dict[str, str] = {}
    with db_connection() as conn:
        settings_rows = {
            row["key"]: row["value"]
            for row in conn.execute(
                "SELECT key, value FROM app_settings WHERE key IN ('vendor_detector', 'history_enrichment')"
            ).fetchall()
        }
        candidate_prefixes = sorted({mac[:length] for mac in macs for length in (6, 8, 10)})
        for chunk in _chunks(candidate_prefixes):
            placeholders = ",".join("?" for _ in chunk)
            vendor_rules.extend(dict(row) for row in conn.execute(
                f"""
                SELECT oui, vendor, source, updated_at
                FROM vendor_mappings
                WHERE oui IN ({placeholders})
                ORDER BY LENGTH(oui) DESC, oui
                """,
                chunk,
            ).fetchall())
        model_rules = [dict(row) for row in conn.execute(
            "SELECT prefix, model, source, updated_at FROM model_mappings ORDER BY LENGTH(prefix) DESC, prefix"
        ).fetchall()]
        for chunk in _chunks(macs):
            placeholders = ",".join("?" for _ in chunk)
            history_rows.extend(dict(row) for row in conn.execute(
                f"""
                SELECT history.mac, history.vendor, history.model, history.ip, history.address,
                       history.room, history.switch_ip, history.switch_port, history.id
                FROM mac_history AS history
                JOIN (
                    SELECT mac, MAX(id) AS latest_id
                    FROM mac_history
                    WHERE mac IN ({placeholders})
                    GROUP BY mac
                ) AS latest ON latest.latest_id = history.id
                """,
                chunk,
            ).fetchall())
            vendor_model_rows.extend({**dict(row), "exact": True, "count": 1} for row in conn.execute(
                f"""
                SELECT history.mac, history.vendor, history.model, history.id
                FROM vendor_model_history AS history
                JOIN (
                    SELECT mac, MAX(id) AS latest_id
                    FROM vendor_model_history
                    WHERE mac IN ({placeholders})
                    GROUP BY mac
                ) AS latest ON latest.latest_id = history.id
                """,
                chunk,
            ).fetchall())
        for chunk in _chunks(ouis):
            placeholders = ",".join("?" for _ in chunk)
            history_similarity_rows.extend({**dict(row), "aggregate": True} for row in conn.execute(
                f"""
                SELECT SUBSTR(mac, 1, 10) AS mac, vendor, model, COUNT(*) AS count
                FROM mac_history
                WHERE SUBSTR(mac, 1, 6) IN ({placeholders})
                  AND (COALESCE(vendor, '') != '' OR COALESCE(model, '') != '')
                GROUP BY SUBSTR(mac, 1, 10), vendor, model
                """,
                chunk,
            ).fetchall())
            vendor_model_rows.extend({**dict(row), "aggregate": True} for row in conn.execute(
                f"""
                SELECT SUBSTR(mac, 1, 10) AS mac, vendor, model, COUNT(*) AS count
                FROM vendor_model_history
                WHERE oui IN ({placeholders}) AND (COALESCE(vendor, '') != '' OR COALESCE(model, '') != '')
                GROUP BY SUBSTR(mac, 1, 10), vendor, model
                """,
                chunk,
            ).fetchall())
        for chunk in _chunks(switch_ips):
            placeholders = ",".join("?" for _ in chunk)
            for row in conn.execute(
                f"SELECT switch_ip, physical_address FROM ip_address_mappings WHERE switch_ip IN ({placeholders})",
                chunk,
            ).fetchall():
                ip_mappings[row["switch_ip"]] = as_text(row["physical_address"])
    latest_history: dict[str, dict[str, Any]] = {}
    for row in history_rows:
        mac = normalize_mac(row.get("mac"))
        if mac in target_macs and mac not in latest_history:
            latest_history[mac] = row
    detector_settings = normalize_detector_settings(_json_setting(settings_rows, "vendor_detector"))
    history_settings = normalize_history_enrichment_settings(_json_setting(settings_rows, "history_enrichment"))
    # vendor_model_history has its own exact/MAC5/OUI index and confidence
    # rules. Feeding it into generic similarity changed source priority and
    # duplicated the same observations in memory.
    needs_similarity = detector_settings.get("enabled", True) and detector_settings.get("useInference", True) and any(
        not as_text(item.get("vendor")) or not as_text(item.get("model"))
        for item in normalized_devices
    )
    history_observations = history_similarity_rows if history_settings.get("enabled", True) and needs_similarity else []
    observations = [*history_observations, *normalized_devices] if needs_similarity else []
    return {
        "vendorRules": vendor_rules,
        "modelRules": model_rules,
        "vendorRuleIndex": compile_rule_index(vendor_rules, "oui", "vendor"),
        "modelRuleIndex": compile_rule_index(model_rules, "prefix", "model"),
        "latestHistory": latest_history,
        "vendorModelHistoryIndex": build_vendor_model_history_index(vendor_model_rows),
        "similarityIndex": build_similarity_index(observations),
        "ipMappings": ip_mappings,
        "detectorSettings": detector_settings,
        "historySettings": history_settings,
        "statistics": {
            "devices": len(normalized_devices),
            "macs": len(macs),
            "vendorRules": len(vendor_rules),
            "modelRules": len(model_rules),
            "historyRows": len(history_rows),
            "historySimilarityAggregates": len(history_similarity_rows),
            "vendorModelAggregates": len(vendor_model_rows),
            "similarityRequired": needs_similarity,
            "ipMappings": len(ip_mappings),
        },
    }


def enrich_device(device: dict[str, Any], context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    mac = normalize_mac(device.get("mac") or device.get("macFormatted"))
    if not mac:
        return {"valid": False, "raw": device.get("mac") or device.get("macFormatted") or ""}
    batch = context or build_enrichment_context([device])
    vendor_rules = batch.get("vendorRules") or []
    model_rules = batch.get("modelRules") or []
    history = dict((batch.get("latestHistory") or {}).get(mac) or {})
    value = lambda key, history_key=None: as_text(device.get(key)) or as_text(history.get(history_key or key))
    history_settings = batch.get("historySettings") or normalize_history_enrichment_settings({})
    vendor_model_suggestion = indexed_history_suggestion(mac, batch.get("vendorModelHistoryIndex"), history_settings)
    priority_history = history_settings.get("enabled") and history_settings.get("priorityHistory")
    history_vendor = as_text(history.get("vendor")) or (as_text(vendor_model_suggestion.get("vendor")) if priority_history else "")
    history_model = as_text(history.get("model")) or (as_text(vendor_model_suggestion.get("model")) if priority_history else "")
    text_values = [device.get(field) for field in ("model", "description", "name", "hostname", "device_name")]
    detector_settings = batch.get("detectorSettings") or normalize_detector_settings({})
    similar_result = similarity_detection(mac, batch.get("similarityIndex"))
    vendor_detection = detect_vendor(mac, device.get("vendor"), history_vendor, vendor_rules, [], text_values, detector_settings, batch.get("vendorRuleIndex"), similar_result)
    model_detection = detect_model(mac, device.get("model"), history_model, model_rules, detector_settings, batch.get("modelRuleIndex"), similar_result)
    if vendor_detection.get("source") == "history" and not as_text(history.get("vendor")) and history_vendor:
        vendor_detection["source"] = vendor_model_suggestion.get("source", "vendor_model_history")
        vendor_detection["confidence"] = vendor_model_suggestion.get("confidence", vendor_detection.get("confidence", 0.0))
        vendor_detection["matchedPrefix"] = vendor_model_suggestion.get("matchedPrefix", "")
    if model_detection.get("source") == "history" and not as_text(history.get("model")) and history_model:
        model_detection["source"] = vendor_model_suggestion.get("source", "vendor_model_history")
        model_detection["confidence"] = vendor_model_suggestion.get("confidence", model_detection.get("confidence", 0.0))
        model_detection["matchedPrefix"] = vendor_model_suggestion.get("matchedPrefix", "")
    if history_settings.get("enabled") and not priority_history and vendor_model_suggestion:
        if vendor_detection.get("source") in {"unknown", "disabled"} and as_text(vendor_model_suggestion.get("vendor")):
            vendor_detection = {
                "value": as_text(vendor_model_suggestion.get("vendor")),
                "source": vendor_model_suggestion.get("source", "vendor_model_history"),
                "confidence": vendor_model_suggestion.get("confidence", 0.0),
                "matchedPrefix": vendor_model_suggestion.get("matchedPrefix", ""),
            }
        if model_detection.get("source") in {"unknown", "disabled"} and as_text(vendor_model_suggestion.get("model")):
            model_detection = {
                "value": as_text(vendor_model_suggestion.get("model")),
                "source": vendor_model_suggestion.get("source", "vendor_model_history"),
                "confidence": vendor_model_suggestion.get("confidence", 0.0),
                "matchedPrefix": vendor_model_suggestion.get("matchedPrefix", ""),
            }
    switch_ip = as_text(device.get("switchIp"))
    address = as_text(device.get("address"))
    if switch_ip and not address:
        address = as_text((batch.get("ipMappings") or {}).get(switch_ip))
    if not address:
        address = as_text(history.get("address"))
    return {
        "valid": True,
        "mac": mac,
        "macFormatted": format_mac(mac),
        "oui": mac[:6],
        "vendor": vendor_detection["value"],
        "vendorSource": vendor_detection["source"],
        "vendorConfidence": vendor_detection["confidence"],
        "vendorMatchedPrefix": vendor_detection.get("matchedPrefix", ""),
        "model": model_detection["value"],
        "modelSource": model_detection["source"],
        "modelConfidence": model_detection["confidence"],
        "modelMatchedPrefix": model_detection.get("matchedPrefix", ""),
        "ip": value("ip"),
        "address": address,
        "room": value("room"),
        "switchIp": switch_ip,
        "switchPort": value("switchPort", "switch_port"),
        "source": as_text(device.get("source")),
        "row": device.get("row"),
    }


def save_history(devices: list[dict[str, Any]], source: str, recorded_at: str = "") -> None:
    timestamp = as_text(recorded_at) or utc_now()
    valid_devices = [device for device in devices if normalize_mac(device.get("mac") or device.get("macFormatted"))]
    macs = sorted({normalize_mac(device.get("mac") or device.get("macFormatted")) for device in valid_devices})
    previous_by_mac: dict[str, dict[str, Any]] = {}
    with db_connection() as conn:
        for chunk in _chunks(macs):
            placeholders = ",".join("?" for _ in chunk)
            rows = conn.execute(
                f"SELECT mac, vendor, model, ip, address, room, switch_ip, switch_port FROM mac_history WHERE mac IN ({placeholders}) ORDER BY id DESC",
                chunk,
            ).fetchall()
            for row in rows:
                previous_by_mac.setdefault(row["mac"], dict(row))
        history_rows = []
        movement_rows = []
        for device in valid_devices:
            mac = normalize_mac(device.get("mac") or device.get("macFormatted"))
            history_rows.append((
                mac, device.get("macFormatted") or format_mac(mac), device.get("oui") or mac[:6],
                as_text(device.get("vendor")), as_text(device.get("model")), as_text(device.get("ip")),
                as_text(device.get("address")), as_text(device.get("room")), as_text(device.get("switchIp")),
                as_text(device.get("switchPort")), source or as_text(device.get("source")), timestamp,
            ))
            previous = previous_by_mac.get(mac)
            if previous:
                current_values = {
                    "vendor": as_text(device.get("vendor")), "model": as_text(device.get("model")), "ip": as_text(device.get("ip")),
                    "address": as_text(device.get("address")), "room": as_text(device.get("room")), "switchIp": as_text(device.get("switchIp")),
                    "switchPort": as_text(device.get("switchPort")),
                }
                for field, new_value in current_values.items():
                    old_value = as_text(previous.get({"switchIp": "switch_ip", "switchPort": "switch_port"}.get(field, field)))
                    if new_value != old_value and (new_value or old_value):
                        movement_rows.append((mac, field, old_value, new_value, source, timestamp))
        conn.executemany(
            "INSERT INTO mac_history (mac, mac_formatted, oui, vendor, model, ip, address, room, switch_ip, switch_port, source, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            history_rows,
        )
        if movement_rows:
            conn.executemany(
                "INSERT INTO mac_movements (mac, field_name, from_value, to_value, source, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
                movement_rows,
            )
    recorded = record_vendor_model_history(valid_devices, source, timestamp)
    if recorded:
        try:
            learn_vendor_model_mappings(2, source)
        except sqlite3.Error:
            pass


def record_vendor_model_history(devices: list[dict[str, Any]], source: str, timestamp: Optional[str] = None) -> int:
    observed_at = timestamp or utc_now()
    rows: list[tuple[str, str, str, str, str, str, str]] = []
    for device in devices:
        mac = normalize_mac(device.get("mac") or device.get("macFormatted"))
        if not mac:
            continue
        vendor = as_text(device.get("vendor"))
        model = as_text(device.get("model"))
        if not vendor and not model:
            continue
        rows.append((mac, mac[:6], mac[:10], vendor, model, source or as_text(device.get("source")), observed_at))
    if not rows:
        return 0
    with db_connection() as conn:
        conn.executemany(
            """
            INSERT INTO vendor_model_history (mac, oui, prefix, vendor, model, source, observed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def vendor_model_where_clause(query_text: str = "", date_from: str = "", date_to: str = "") -> tuple[str, list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    normalized_query = normalize_mac(query_text)
    text_query = as_text(query_text)
    if text_query:
        like_value = f"%{text_query}%"
        query_parts = ["mac LIKE ?", "oui LIKE ?", "prefix LIKE ?", "vendor LIKE ?", "model LIKE ?", "source LIKE ?"]
        params.extend([like_value] * len(query_parts))
        if normalized_query:
            query_parts.append("mac LIKE ?")
            params.append(f"%{normalized_query}%")
        where.append("(" + " OR ".join(query_parts) + ")")
    if date_from:
        where.append("observed_at >= ?")
        params.append(date_from + "T00:00:00")
    if date_to:
        where.append("observed_at <= ?")
        params.append(date_to + "T23:59:59")
    return (" WHERE " + " AND ".join(where) if where else ""), params


def vendor_model_history(query_text: str = "", limit: int = 500, date_from: str = "", date_to: str = "") -> dict[str, Any]:
    where_sql, params = vendor_model_where_clause(query_text, date_from, date_to)
    try:
        requested_limit = int(limit or 500)
    except (TypeError, ValueError):
        requested_limit = 500
    bounded_limit = max(1, min(requested_limit, 2000))
    with db_connection() as conn:
        rows = [dict(row) for row in conn.execute(
            f"SELECT * FROM vendor_model_history{where_sql} ORDER BY observed_at DESC, id DESC LIMIT ?",
            (*params, bounded_limit),
        ).fetchall()]

    def grouped(field: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for row in rows:
            value = row.get(field) or "Unknown"
            counts[value] = counts.get(value, 0) + 1
        return [{"name": name, "count": count} for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]]

    return {
        "history": rows,
        "statistics": {
            "records": len(rows),
            "uniqueMacs": len({row["mac"] for row in rows}),
            "vendors": grouped("vendor"),
            "models": grouped("model"),
            "sources": grouped("source"),
        },
    }


def vendor_model_statistics(query_text: str = "", date_from: str = "", date_to: str = "", limit: int = 20) -> dict[str, Any]:
    where_sql, params = vendor_model_where_clause(query_text, date_from, date_to)
    try:
        requested_limit = int(limit or 20)
    except (TypeError, ValueError):
        requested_limit = 20
    bounded_limit = max(1, min(requested_limit, 100))

    def grouped(conn: sqlite3.Connection, field: str, alias: str = "name") -> list[dict[str, Any]]:
        rows = conn.execute(
            f"""
            SELECT COALESCE(NULLIF({field}, ''), 'Unknown') AS {alias}, COUNT(*) AS count, COUNT(DISTINCT mac) AS unique_macs
            FROM vendor_model_history{where_sql}
            GROUP BY COALESCE(NULLIF({field}, ''), 'Unknown')
            ORDER BY count DESC, {alias}
            LIMIT ?
            """,
            (*params, bounded_limit),
        ).fetchall()
        return [dict(row) for row in rows]

    with db_connection() as conn:
        totals = dict(conn.execute(
            f"""
            SELECT COUNT(*) AS records,
                   COUNT(DISTINCT mac) AS uniqueMacs,
                   COUNT(DISTINCT NULLIF(vendor, '')) AS uniqueVendors,
                   COUNT(DISTINCT NULLIF(model, '')) AS uniqueModels,
                   COUNT(DISTINCT NULLIF(source, '')) AS sources,
                   MIN(observed_at) AS firstObserved,
                   MAX(observed_at) AS lastObserved
            FROM vendor_model_history{where_sql}
            """,
            params,
        ).fetchone())
        return {
            "totals": totals,
            "vendors": grouped(conn, "vendor"),
            "models": grouped(conn, "model"),
            "sources": grouped(conn, "source"),
            "ouis": grouped(conn, "oui", "oui"),
            "prefixes": grouped(conn, "prefix", "prefix"),
        }


def vendor_model_upload_history(query_text: str = "", date_from: str = "", date_to: str = "", limit: int = 100) -> dict[str, Any]:
    where_sql, params = vendor_model_where_clause(query_text, date_from, date_to)
    try:
        requested_limit = int(limit or 100)
    except (TypeError, ValueError):
        requested_limit = 100
    bounded_limit = max(1, min(requested_limit, 500))
    with db_connection() as conn:
        uploads = [dict(row) for row in conn.execute(
            f"""
            SELECT COALESCE(NULLIF(source, ''), 'Unknown') AS source,
                   COUNT(*) AS records,
                   COUNT(DISTINCT mac) AS uniqueMacs,
                   COUNT(DISTINCT NULLIF(vendor, '')) AS vendors,
                   COUNT(DISTINCT NULLIF(model, '')) AS models,
                   MIN(observed_at) AS firstObserved,
                   MAX(observed_at) AS lastObserved
            FROM vendor_model_history{where_sql}
            GROUP BY COALESCE(NULLIF(source, ''), 'Unknown')
            ORDER BY lastObserved DESC, records DESC
            LIMIT ?
            """,
            (*params, bounded_limit),
        ).fetchall()]
        snapshot_rows = [dict(row) for row in conn.execute(
            "SELECT source, COUNT(*) AS snapshots, SUM(device_count) AS devices, MIN(created_at) AS firstSnapshot, MAX(created_at) AS lastSnapshot FROM snapshots GROUP BY source"
        ).fetchall()]
    snapshots_by_source = {as_text(row.get("source")) or "Unknown": row for row in snapshot_rows}
    for upload in uploads:
        snapshot = snapshots_by_source.get(upload["source"], {})
        upload["snapshots"] = int(snapshot.get("snapshots") or 0)
        upload["snapshotDevices"] = int(snapshot.get("devices") or 0)
        upload["firstSnapshot"] = snapshot.get("firstSnapshot")
        upload["lastSnapshot"] = snapshot.get("lastSnapshot")
    return {
        "uploads": uploads,
        "summary": {
            "uploads": len(uploads),
            "records": sum(int(item.get("records") or 0) for item in uploads),
            "uniqueMacs": sum(int(item.get("uniqueMacs") or 0) for item in uploads),
            "snapshots": sum(int(item.get("snapshots") or 0) for item in uploads),
        },
    }


def vendor_model_history_suggestion(mac: str, settings: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = normalize_mac(mac)
    if not normalized:
        return {}
    normalized_settings = normalize_history_enrichment_settings(settings if settings is not None else history_enrichment_settings())
    if not normalized_settings["enabled"]:
        return {}
    prefix_plan: list[tuple[int, float]] = []
    if normalized_settings["useMac5Match"]:
        prefix_plan.extend([(10, 0.82), (8, 0.76)])
    if normalized_settings["useOuiMatch"]:
        prefix_plan.append((6, 0.68))
    with db_connection() as conn:
        exact = conn.execute(
            """
            SELECT vendor, model, mac AS matched_prefix, 1 AS matches
            FROM vendor_model_history
            WHERE mac = ? AND (vendor IS NOT NULL OR model IS NOT NULL)
            ORDER BY observed_at DESC, id DESC
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
        if exact:
            result = dict(exact)
            return {
                "vendor": as_text(result.get("vendor")),
                "model": as_text(result.get("model")),
                "source": "vendor_model_history_exact",
                "confidence": 0.93,
                "matchedPrefix": result["matched_prefix"],
                "matches": result["matches"],
            }
        for prefix_length, confidence in prefix_plan:
            prefix = normalized[:prefix_length]
            rows = conn.execute(
                """
                SELECT vendor, model, COUNT(*) AS matches
                FROM vendor_model_history
                WHERE mac LIKE ? AND (vendor IS NOT NULL OR model IS NOT NULL)
                GROUP BY vendor, model
                ORDER BY matches DESC, vendor, model
                LIMIT 1
                """,
                (prefix + "%",),
            ).fetchone()
            if rows:
                result = dict(rows)
                return {
                    "vendor": as_text(result.get("vendor")),
                    "model": as_text(result.get("model")),
                    "source": "vendor_model_history_prefix",
                    "confidence": confidence,
                    "matchedPrefix": prefix,
                    "matches": result["matches"],
                }
    return {}


def learn_vendor_model_mappings(min_count: int = 2, source: str = "") -> dict[str, int]:
    threshold = max(1, int(min_count or 2))
    learned_at = utc_now()
    learned_vendors = 0
    learned_models = 0
    source_filter = as_text(source)
    source_where = "AND source = ?" if source_filter else ""
    source_params: tuple[Any, ...] = (source_filter,) if source_filter else ()
    with db_connection() as conn:
        for prefix_length in (6, 8, 10):
            vendor_rows = conn.execute(
                f"""
                SELECT SUBSTR(mac, 1, ?) AS oui, vendor, COUNT(*) AS total
                FROM vendor_model_history
                WHERE vendor IS NOT NULL AND vendor != '' AND vendor != 'Unknown' {source_where}
                GROUP BY SUBSTR(mac, 1, ?), vendor
                HAVING total >= ?
                ORDER BY total DESC
                """,
                (prefix_length, *source_params, prefix_length, threshold),
            ).fetchall()
            for row in vendor_rows:
                exists = conn.execute("SELECT 1 FROM vendor_mappings WHERE oui = ?", (row["oui"],)).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO vendor_mappings (oui, vendor, source, updated_at) VALUES (?, ?, 'learned', ?)",
                        (row["oui"], row["vendor"], learned_at),
                    )
                    learned_vendors += 1
        model_rows = conn.execute(
            f"""
            SELECT SUBSTR(mac, 1, 10) AS prefix, model, COUNT(*) AS total
            FROM vendor_model_history
            WHERE model IS NOT NULL AND model != '' {source_where}
            GROUP BY SUBSTR(mac, 1, 10), model
            HAVING total >= ?
            ORDER BY total DESC
            """,
            (*source_params, threshold),
        ).fetchall()
        for row in model_rows:
            exists = conn.execute("SELECT 1 FROM model_mappings WHERE prefix = ?", (row["prefix"],)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO model_mappings (prefix, model, source, updated_at) VALUES (?, ?, 'learned', ?)",
                    (row["prefix"], row["model"], learned_at),
                )
                learned_models += 1
    return {"vendors": learned_vendors, "models": learned_models}


def valid_ipv4(value: str) -> bool:
    try:
        return ipaddress.ip_address(as_text(value)).version == 4
    except ValueError:
        return False


def save_ip_mappings(pairs: list[dict[str, Any]], source: str = "manual") -> dict[str, int]:
    imported = 0
    skipped = 0
    timestamp = utc_now()
    with db_connection() as conn:
        for pair in pairs:
            switch_ip = as_text(pair.get("switchIp") or pair.get("switch_ip") or pair.get("ip"))
            address = as_text(pair.get("address") or pair.get("physicalAddress") or pair.get("physical_address") or pair.get("location"))
            if not valid_ipv4(switch_ip) or not address:
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO ip_address_mappings (switch_ip, physical_address, source, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(switch_ip) DO UPDATE SET physical_address=excluded.physical_address, source=excluded.source, updated_at=excluded.updated_at",
                (switch_ip, address, source, timestamp),
            )
            imported += 1
    return {"imported": imported, "skipped": skipped}


def parse_ip_mapping_import(filename: str, content: str) -> list[dict[str, str]]:
    text = content.lstrip("\ufeff")
    if filename.lower().endswith(".json") or text.strip().startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("JSON import must contain an array")
        return [
            {
                "switchIp": as_text(item.get("switchIp") or item.get("switch_ip") or item.get("ip")),
                "address": as_text(item.get("address") or item.get("physicalAddress") or item.get("physical_address") or item.get("location")),
            }
            for item in data
            if isinstance(item, dict)
        ]
    lines = text.splitlines()
    first_line = lines[0] if lines else ""
    delimiter = "\t" if "\t" in first_line or filename.lower().endswith(".tsv") else (";" if ";" in first_line else ",")
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    if not rows:
        return []
    header = [cell.strip().lower() for cell in rows[0]]
    has_header = any(name in {"ip", "switchip", "switch_ip", "switch ip", "address", "physicaladdress", "physical_address", "location"} for name in header)
    data_rows = rows[1:] if has_header else rows
    ip_index = 0
    address_index = 1
    if has_header:
        for index, name in enumerate(header):
            normalized = re.sub(r"[^a-z0-9]", "", name)
            if normalized in {"ip", "switchip"}:
                ip_index = index
            if normalized in {"address", "physicaladdress", "location"}:
                address_index = index
    return [
        {
            "switchIp": as_text(row[ip_index]) if len(row) > ip_index else "",
            "address": as_text(row[address_index]) if len(row) > address_index else "",
        }
        for row in data_rows
    ]


def import_ip_mappings(filename: str, content: str) -> dict[str, int]:
    return save_ip_mappings(parse_ip_mapping_import(filename, content), "import")


def export_ip_mappings_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["switch_ip", "physical_address", "source", "updated_at"])
    with db_connection() as conn:
        rows = conn.execute("SELECT switch_ip, physical_address, source, updated_at FROM ip_address_mappings ORDER BY switch_ip").fetchall()
    for row in rows:
        writer.writerow([row["switch_ip"], row["physical_address"], row["source"], row["updated_at"]])
    return output.getvalue()


def ip_mapping_statistics(devices: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    devices = devices if isinstance(devices, list) else []
    with db_connection() as conn:
        rows = [dict(row) for row in conn.execute(
            "SELECT switch_ip, physical_address, source, updated_at FROM ip_address_mappings ORDER BY switch_ip"
        ).fetchall()]
    mapped = {row["switch_ip"]: row for row in rows}
    switches = [as_text(device.get("switchIp") or device.get("switch_ip")) for device in devices if isinstance(device, dict)]
    switches = [switch for switch in switches if switch]
    unique_switches = sorted(set(switches))
    matched = [switch for switch in unique_switches if switch in mapped]
    missing = [switch for switch in unique_switches if switch not in mapped]
    source_counts: dict[str, int] = {}
    for row in rows:
        source = row.get("source") or "unknown"
        source_counts[source] = source_counts.get(source, 0) + 1
    return {
        "totalMappings": len(rows),
        "sources": [{"name": name, "count": count} for name, count in sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))],
        "deviceSwitches": len(unique_switches),
        "matchedSwitches": len(matched),
        "missingSwitches": len(missing),
        "coverage": round(len(matched) / max(1, len(unique_switches)) * 100, 2) if unique_switches else 0,
        "missing": missing[:100],
    }


def apply_ip_mappings_to_devices(devices: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(devices, list):
        raise ValueError("devices must be an array")
    with db_connection() as conn:
        rows = conn.execute("SELECT switch_ip, physical_address FROM ip_address_mappings").fetchall()
    mapping = {row["switch_ip"]: row["physical_address"] for row in rows}
    updated_devices: list[dict[str, Any]] = []
    matched = 0
    filled = 0
    missing: set[str] = set()
    for device in devices:
        current = dict(device) if isinstance(device, dict) else {}
        switch_ip = as_text(current.get("switchIp") or current.get("switch_ip"))
        if switch_ip and switch_ip in mapping:
            matched += 1
            if not as_text(current.get("address")):
                filled += 1
            current["address"] = mapping[switch_ip]
            current["addressSource"] = "ip_mapping"
        elif switch_ip:
            missing.add(switch_ip)
        updated_devices.append(current)
    return {
        "devices": updated_devices,
        "summary": {
            "devices": len(updated_devices),
            "matched": matched,
            "filled": filled,
            "missingSwitches": sorted(missing),
            "coverage": round(matched / max(1, len([device for device in updated_devices if as_text(device.get("switchIp") or device.get("switch_ip"))])) * 100, 2),
        },
    }


def autodetect_ip_mappings(devices: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: dict[str, dict[str, int]] = {}
    for device in devices:
        switch_ip = as_text(device.get("switchIp") or device.get("switch_ip"))
        address = as_text(device.get("address") or device.get("physicalAddress") or device.get("physical_address"))
        if valid_ipv4(switch_ip) and address:
            candidates.setdefault(switch_ip, {})
            candidates[switch_ip][address] = candidates[switch_ip].get(address, 0) + 1
    mappings_to_save = [
        {
            "switchIp": switch_ip,
            "address": sorted(addresses.items(), key=lambda item: (-item[1], item[0]))[0][0],
        }
        for switch_ip, addresses in candidates.items()
    ]
    result = save_ip_mappings(mappings_to_save, "auto")
    return {**result, "mappings": mappings_to_save}


def delete_history_records(mac: Optional[str] = None) -> int:
    normalized_mac = normalize_mac(mac) if mac else ""
    with db_connection() as conn:
        if normalized_mac:
            history_count = conn.execute("SELECT COUNT(*) FROM mac_history WHERE mac = ?", (normalized_mac,)).fetchone()[0]
            movement_count = conn.execute("SELECT COUNT(*) FROM mac_movements WHERE mac = ?", (normalized_mac,)).fetchone()[0]
            conn.execute("DELETE FROM mac_movements WHERE mac = ?", (normalized_mac,))
            conn.execute("DELETE FROM mac_history WHERE mac = ?", (normalized_mac,))
            return int(history_count or 0) + int(movement_count or 0)
        history_count = conn.execute("SELECT COUNT(*) FROM mac_history").fetchone()[0]
        movement_count = conn.execute("SELECT COUNT(*) FROM mac_movements").fetchone()[0]
        conn.execute("DELETE FROM mac_movements")
        conn.execute("DELETE FROM mac_history")
        return int(history_count or 0) + int(movement_count or 0)


def history_deleted_html(deleted: int, mac: str = "") -> str:
    label = "История удалена."
    if deleted:
        label = f"История удалена: {deleted} записей."
    elif normalize_mac(mac):
        label = "История этого MAC уже была пуста."
    return f'<tr><td colspan="5" class="empty-state">{html_lib.escape(label)}</td></tr>'


def history_where_clause(query_text: str = "", date_from: str = "", date_to: str = "") -> tuple[str, list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    normalized_query = normalize_mac(query_text)
    text_query = as_text(query_text)
    if text_query:
        like_value = f"%{text_query}%"
        query_parts = [
            "mac LIKE ?",
            "mac_formatted LIKE ?",
            "oui LIKE ?",
            "vendor LIKE ?",
            "model LIKE ?",
            "ip LIKE ?",
            "address LIKE ?",
            "room LIKE ?",
            "switch_ip LIKE ?",
            "switch_port LIKE ?",
            "source LIKE ?",
        ]
        params.extend([like_value] * len(query_parts))
        if normalized_query:
            query_parts.append("mac LIKE ?")
            params.append(f"%{normalized_query}%")
        where.append("(" + " OR ".join(query_parts) + ")")
    if date_from:
        where.append("recorded_at >= ?")
        params.append(date_from + "T00:00:00")
    if date_to:
        where.append("recorded_at <= ?")
        params.append(date_to + "T23:59:59")
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    return where_sql, params


def movement_where_clause(query_text: str = "", date_from: str = "", date_to: str = "") -> tuple[str, list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    normalized_query = normalize_mac(query_text)
    text_query = as_text(query_text)
    if text_query:
        like_value = f"%{text_query}%"
        query_parts = ["mac LIKE ?", "field_name LIKE ?", "from_value LIKE ?", "to_value LIKE ?", "source LIKE ?"]
        params.extend([like_value] * len(query_parts))
        if normalized_query:
            query_parts.append("mac LIKE ?")
            params.append(f"%{normalized_query}%")
        where.append("(" + " OR ".join(query_parts) + ")")
    if date_from:
        where.append("changed_at >= ?")
        params.append(date_from + "T00:00:00")
    if date_to:
        where.append("changed_at <= ?")
        params.append(date_to + "T23:59:59")
    return (" WHERE " + " AND ".join(where) if where else ""), params


def movement_change_type(row: dict[str, Any]) -> str:
    before = as_text(row.get("from_value"))
    after = as_text(row.get("to_value"))
    if not before and after:
        return "added"
    if before and not after:
        return "removed"
    return "modified"


def enhanced_movement_where_clause(filters: Optional[dict[str, Any]] = None) -> tuple[str, list[Any]]:
    filters = filters if isinstance(filters, dict) else {}
    where: list[str] = []
    params: list[Any] = []
    query_text = as_text(filters.get("query"))
    normalized_mac = normalize_mac(query_text)
    if query_text:
        like_value = f"%{query_text}%"
        parts = [
            "m.mac LIKE ?", "m.field_name LIKE ?", "m.from_value LIKE ?", "m.to_value LIKE ?", "m.source LIKE ?",
            "h.mac_formatted LIKE ?", "h.vendor LIKE ?", "h.model LIKE ?", "h.room LIKE ?", "h.address LIKE ?",
            "h.switch_ip LIKE ?", "h.switch_port LIKE ?",
        ]
        params.extend([like_value] * len(parts))
        if normalized_mac:
            parts.append("m.mac LIKE ?")
            params.append(f"%{normalized_mac}%")
        where.append("(" + " OR ".join(parts) + ")")

    field_name = as_text(filters.get("field"))
    if field_name:
        where.append("m.field_name = ?")
        params.append(field_name)

    change_type = as_text(filters.get("changeType") or filters.get("type")).lower()
    if change_type == "added":
        where.append("COALESCE(m.from_value, '') = '' AND COALESCE(m.to_value, '') <> ''")
    elif change_type == "removed":
        where.append("COALESCE(m.from_value, '') <> '' AND COALESCE(m.to_value, '') = ''")
    elif change_type == "modified":
        where.append("NOT (COALESCE(m.from_value, '') = '' AND COALESCE(m.to_value, '') <> '')")
        where.append("NOT (COALESCE(m.from_value, '') <> '' AND COALESCE(m.to_value, '') = '')")

    date_from = as_text(filters.get("dateFrom") or filters.get("from"))
    date_to = as_text(filters.get("dateTo") or filters.get("to"))
    if date_from:
        where.append("m.changed_at >= ?")
        params.append(date_from + ("T00:00:00" if "T" not in date_from else ""))
    if date_to:
        where.append("m.changed_at <= ?")
        params.append(date_to + ("T23:59:59" if "T" not in date_to else ""))
    return (" WHERE " + " AND ".join(where) if where else ""), params


def enhanced_history_column_settings() -> dict[str, Any]:
    with db_connection() as conn:
        row = conn.execute("SELECT value, updated_at FROM app_settings WHERE key = ?", ("enhanced_history_columns",)).fetchone()
    raw: dict[str, Any] = {}
    if row:
        try:
            parsed = json.loads(row["value"])
            raw = parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            raw = {}
    visible = [column for column in raw.get("visible", []) if column in ENHANCED_HISTORY_COLUMNS]
    if not visible:
        visible = list(ENHANCED_HISTORY_COLUMNS)
    elif int(raw.get("version") or 1) < 2 and "address" not in visible:
        visible.insert(visible.index("room") if "room" in visible else len(visible), "address")
    widths: dict[str, int] = {}
    raw_widths = raw.get("widths", {}) if isinstance(raw.get("widths"), dict) else {}
    for column in ENHANCED_HISTORY_COLUMNS:
        try:
            width = int(raw_widths.get(column, ENHANCED_HISTORY_COLUMN_WIDTHS[column]))
        except (TypeError, ValueError):
            width = ENHANCED_HISTORY_COLUMN_WIDTHS[column]
        widths[column] = max(64, min(width, 600))
    controls_html = "".join(
        '<label class="movement-column-control">'
        f'<input type="checkbox" data-movement-column-toggle="{column}"{" checked" if column in visible else ""}>'
        f'<span>{html_lib.escape(ENHANCED_HISTORY_COLUMN_LABELS[column])}</span>'
        f'<input type="number" min="64" max="600" value="{widths[column]}" data-movement-column-width="{column}" aria-label="Ширина {html_lib.escape(ENHANCED_HISTORY_COLUMN_LABELS[column])}">'
        '</label>'
        for column in ENHANCED_HISTORY_COLUMNS
    )
    return {
        "visible": visible,
        "widths": widths,
        "columns": list(ENHANCED_HISTORY_COLUMNS),
        "labels": dict(ENHANCED_HISTORY_COLUMN_LABELS),
        "controlsHtml": controls_html,
        "updatedAt": row["updated_at"] if row else None,
    }


def save_enhanced_history_column_settings(settings: dict[str, Any]) -> dict[str, Any]:
    visible = [column for column in settings.get("visible", []) if column in ENHANCED_HISTORY_COLUMNS]
    if not visible:
        raise ValueError("At least one enhanced history column must remain visible")
    raw_widths = settings.get("widths", {}) if isinstance(settings.get("widths"), dict) else {}
    widths: dict[str, int] = {}
    for column in ENHANCED_HISTORY_COLUMNS:
        try:
            width = int(raw_widths.get(column, ENHANCED_HISTORY_COLUMN_WIDTHS[column]))
        except (TypeError, ValueError):
            width = ENHANCED_HISTORY_COLUMN_WIDTHS[column]
        widths[column] = max(64, min(width, 600))
    timestamp = utc_now()
    value = json.dumps({"version": 2, "visible": visible, "widths": widths}, ensure_ascii=False)
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            ("enhanced_history_columns", value, timestamp),
        )
    return enhanced_history_column_settings()


def enhanced_movement_history(filters: Optional[dict[str, Any]] = None, limit: int = 5000) -> dict[str, Any]:
    where_sql, params = enhanced_movement_where_clause(filters)
    try:
        requested_limit = int(limit or 5000)
    except (TypeError, ValueError):
        requested_limit = 5000
    bounded_limit = max(1, min(requested_limit, 5000))
    with db_connection() as conn:
        total = int(conn.execute(
            "SELECT COUNT(*) FROM mac_movements m LEFT JOIN mac_history h ON h.id = "
            "(SELECT id FROM mac_history WHERE mac = m.mac AND recorded_at <= m.changed_at ORDER BY recorded_at DESC, id DESC LIMIT 1)" + where_sql,
            params,
        ).fetchone()[0] or 0)
        records = [dict(row) for row in conn.execute(
            """
            SELECT m.*, h.mac_formatted, h.vendor, h.model, h.room, h.address, h.switch_ip, h.switch_port
            FROM mac_movements m
            LEFT JOIN mac_history h ON h.id = (
                SELECT id FROM mac_history WHERE mac = m.mac AND recorded_at <= m.changed_at ORDER BY recorded_at DESC, id DESC LIMIT 1
            )
            """ + where_sql + " ORDER BY m.changed_at DESC, m.id DESC LIMIT ?",
            (*params, bounded_limit),
        ).fetchall()]

    for record in records:
        record["change_type"] = movement_change_type(record)
        record["mac_formatted"] = as_text(record.get("mac_formatted")) or format_mac(record["mac"])

    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["mac"], []).append(record)
    ordered_groups = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    rows: list[str] = []
    type_counts = {"added": 0, "removed": 0, "modified": 0}
    for mac, movements in ordered_groups:
        for movement in movements:
            type_counts[movement["change_type"]] += 1
        first = movements[0]
        dates = sorted(as_text(item.get("changed_at")) for item in movements if as_text(item.get("changed_at")))
        date_range = dates[0] if len(dates) == 1 else f"{dates[0]} — {dates[-1]}"
        group_counts = {kind: sum(1 for item in movements if item["change_type"] == kind) for kind in type_counts}
        safe_mac = html_lib.escape(mac, quote=True)
        parent_values = {
            "mac": f'<button class="movement-group-toggle" data-toggle-movement-group="{safe_mac}" aria-expanded="true" title="Свернуть группу">▾</button> {html_lib.escape(first["mac_formatted"])}',
            "count": str(len(movements)), "dates": html_lib.escape(date_range),
            "vendor": html_lib.escape(as_text(first.get("vendor")) or "Unknown"),
            "model": html_lib.escape(as_text(first.get("model"))), "address": html_lib.escape(as_text(first.get("address"))),
            "room": html_lib.escape(as_text(first.get("room"))),
            "field": f'+{group_counts["added"]} −{group_counts["removed"]} Δ{group_counts["modified"]}',
            "before": "", "after": "", "source": "",
        }
        rows.append('<tr class="movement-group-row" data-movement-group="{mac}">{cells}</tr>'.format(
            mac=safe_mac,
            cells="".join(f'<td data-movement-column="{column}">{parent_values[column]}</td>' for column in ENHANCED_HISTORY_COLUMNS),
        ))
        for movement in movements:
            child_values = {
                "mac": "", "count": "", "dates": html_lib.escape(format_display_datetime(movement.get("changed_at"))),
                "vendor": html_lib.escape(as_text(movement.get("vendor"))), "model": html_lib.escape(as_text(movement.get("model"))),
                "address": html_lib.escape(as_text(movement.get("address"))), "room": html_lib.escape(as_text(movement.get("room"))),
                "field": html_lib.escape(as_text(movement.get("field_name"))),
                "before": html_lib.escape(as_text(movement.get("from_value"))), "after": html_lib.escape(as_text(movement.get("to_value"))),
                "source": html_lib.escape(as_text(movement.get("source"))),
            }
            rows.append(
                f'<tr class="movement-child-row movement-{movement["change_type"]}" data-movement-child="{safe_mac}" data-movement-id="{int(movement["id"])}" data-mac="{safe_mac}">'
                + "".join(f'<td data-movement-column="{column}">{child_values[column]}</td>' for column in ENHANCED_HISTORY_COLUMNS)
                + "</tr>"
            )

    summary_html = "".join(
        f'<div class="bar-label"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in (
            ("Всего изменений", total), ("Показано", len(records)), ("Добавлено", type_counts["added"]),
            ("Удалено", type_counts["removed"]), ("Изменено", type_counts["modified"]), ("Уникальных MAC", len(grouped)),
        )
    )
    return {
        "records": records, "groups": len(grouped), "total": total, "count": len(records),
        "ids": [int(record["id"]) for record in records], "statistics": {**type_counts, "uniqueMacs": len(grouped)},
        "summaryHtml": summary_html, "rowsHtml": "".join(rows),
        "emptyRowsHtml": '<tr><td colspan="10" class="empty-state">Нет изменений за выбранный период.</td></tr>',
        "columnSettings": enhanced_history_column_settings(),
    }


def delete_enhanced_movement_history(ids: list[Any]) -> int:
    clean_ids: list[int] = []
    for value in ids if isinstance(ids, list) else []:
        try:
            row_id = int(value)
        except (TypeError, ValueError):
            continue
        if row_id > 0 and row_id not in clean_ids:
            clean_ids.append(row_id)
    clean_ids = clean_ids[:5000]
    if not clean_ids:
        raise ValueError("No shown movement records were selected for deletion")
    placeholders = ",".join("?" for _ in clean_ids)
    with db_connection() as conn:
        deleted = int(conn.execute(f"SELECT COUNT(*) FROM mac_movements WHERE id IN ({placeholders})", clean_ids).fetchone()[0] or 0)
        conn.execute(f"DELETE FROM mac_movements WHERE id IN ({placeholders})", clean_ids)
    log_action("Delete filtered movements", f"deleted={deleted}")
    return deleted


def export_enhanced_movement_history(filters: Optional[dict[str, Any]] = None, export_format: str = "xlsx") -> dict[str, Any]:
    result = enhanced_movement_history(filters, 5000)
    export_rows = [{
        "macFormatted": record["mac_formatted"], "vendor": record.get("vendor") or "", "model": record.get("model") or "",
        "room": record.get("room") or "", "changedAt": record.get("changed_at") or "", "changeType": record["change_type"],
        "field": record.get("field_name") or "", "before": record.get("from_value") or "", "after": record.get("to_value") or "",
        "source": record.get("source") or "",
    } for record in result["records"]]
    if not export_rows:
        raise ValueError("No movement history records to export")
    columns = [
        {"key": "macFormatted", "title": "MAC-адрес"}, {"key": "vendor", "title": "Производитель"},
        {"key": "model", "title": "Модель"}, {"key": "room", "title": "Помещение"},
        {"key": "changedAt", "title": "Дата/время"}, {"key": "changeType", "title": "Тип изменения"},
        {"key": "field", "title": "Поле"}, {"key": "before", "title": "Было"},
        {"key": "after", "title": "Стало"}, {"key": "source", "title": "Файл"},
    ]
    return export_managed(export_rows, columns, export_format, "filtered-history")


def search_history_records(
    query_text: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 500,
) -> dict[str, Any]:
    where_sql, params = history_where_clause(query_text, date_from, date_to)
    movement_where_sql, movement_params = movement_where_clause(query_text, date_from, date_to)
    try:
        requested_limit = int(limit or 500)
    except (TypeError, ValueError):
        requested_limit = 500
    bounded_limit = max(1, min(requested_limit, 2000))
    with db_connection() as conn:
        records = [dict(row) for row in conn.execute(
            f"SELECT * FROM mac_history{where_sql} ORDER BY recorded_at DESC, id DESC LIMIT ?",
            (*params, bounded_limit),
        ).fetchall()]
        movements = [dict(row) for row in conn.execute(
            f"SELECT * FROM mac_movements{movement_where_sql} ORDER BY changed_at DESC, id DESC LIMIT ?",
            (*movement_params, bounded_limit),
        ).fetchall()]
    unique_macs = len({row["mac"] for row in records})

    def grouped(field: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for row in records:
            name = row.get(field) or "Unknown"
            counts[name] = counts.get(name, 0) + 1
        return [{"name": name, "count": count} for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]]

    return {
        "history": records,
        "movements": movements,
        "statistics": {
            "records": len(records),
            "uniqueMacs": unique_macs,
            "movements": len(movements),
            "vendors": grouped("vendor"),
            "models": grouped("model"),
            "sources": grouped("source"),
        },
    }


def history_timeline(mac_value: Any, limit: int = 500) -> dict[str, Any]:
    mac = normalize_mac(mac_value)
    if not mac:
        raise ValueError("valid mac is required")
    try:
        requested_limit = int(limit or 500)
    except (TypeError, ValueError):
        requested_limit = 500
    bounded_limit = max(1, min(requested_limit, 1000))
    with db_connection() as conn:
        records = [dict(row) for row in conn.execute(
            "SELECT * FROM mac_history WHERE mac = ? ORDER BY recorded_at DESC, id DESC LIMIT ?",
            (mac, bounded_limit),
        ).fetchall()]
        movements = [dict(row) for row in conn.execute(
            "SELECT * FROM mac_movements WHERE mac = ? ORDER BY changed_at DESC, id DESC LIMIT ?",
            (mac, bounded_limit),
        ).fetchall()]

    timeline = []
    for record in records:
        timeline.append({
            "type": "record",
            "mac": record["mac"],
            "date": record["recorded_at"],
            "field": "snapshot",
            "before": "",
            "after": " / ".join(filter(None, [record.get("vendor"), record.get("model"), record.get("ip"), record.get("address")])),
            "source": record.get("source") or "",
            "record": record,
        })
    for movement in movements:
        timeline.append({
            "type": "movement",
            "mac": movement["mac"],
            "date": movement["changed_at"],
            "field": movement["field_name"],
            "before": movement.get("from_value") or "",
            "after": movement.get("to_value") or "",
            "source": movement.get("source") or "",
            "record": movement,
        })
    timeline.sort(key=lambda item: (item.get("date") or "", item.get("type") or ""), reverse=True)

    field_counts: dict[str, int] = {}
    sources: dict[str, int] = {}
    for movement in movements:
        field = movement.get("field_name") or "unknown"
        field_counts[field] = field_counts.get(field, 0) + 1
    for record in records:
        source = record.get("source") or "unknown"
        sources[source] = sources.get(source, 0) + 1
    return {
        "history": records,
        "movements": movements,
        "timeline": timeline[:bounded_limit],
        "summary": {
            "mac": mac,
            "records": len(records),
            "movements": len(movements),
            "timeline": min(len(timeline), bounded_limit),
            "fields": [{"field": field, "count": count} for field, count in sorted(field_counts.items(), key=lambda item: (-item[1], item[0]))],
            "sources": [{"source": source, "count": count} for source, count in sorted(sources.items(), key=lambda item: (-item[1], item[0]))],
        },
    }


def history_statistics(query_text: str = "", date_from: str = "", date_to: str = "", limit: int = 20) -> dict[str, Any]:
    where_sql, params = history_where_clause(query_text, date_from, date_to)
    movement_where_sql, movement_params = movement_where_clause(query_text, date_from, date_to)
    try:
        requested_limit = int(limit or 20)
    except (TypeError, ValueError):
        requested_limit = 20
    bounded_limit = max(1, min(requested_limit, 100))

    def grouped(conn: sqlite3.Connection, field: str, alias: str = "name") -> list[dict[str, Any]]:
        rows = conn.execute(
            f"""
            SELECT COALESCE(NULLIF({field}, ''), 'Unknown') AS {alias}, COUNT(*) AS count, COUNT(DISTINCT mac) AS unique_macs
            FROM mac_history{where_sql}
            GROUP BY COALESCE(NULLIF({field}, ''), 'Unknown')
            ORDER BY count DESC, {alias}
            LIMIT ?
            """,
            (*params, bounded_limit),
        ).fetchall()
        return [dict(row) for row in rows]

    with db_connection() as conn:
        totals = dict(conn.execute(
            f"""
            SELECT COUNT(*) AS records,
                   COUNT(DISTINCT mac) AS uniqueMacs,
                   MIN(recorded_at) AS firstSeen,
                   MAX(recorded_at) AS lastSeen
            FROM mac_history{where_sql}
            """,
            params,
        ).fetchone())
        movement_totals = dict(conn.execute(
            f"""
            SELECT COUNT(*) AS movements,
                   COUNT(DISTINCT mac) AS movementMacs,
                   MIN(changed_at) AS firstMovement,
                   MAX(changed_at) AS lastMovement
            FROM mac_movements{movement_where_sql}
            """,
            movement_params,
        ).fetchone())
        movement_fields = [dict(row) for row in conn.execute(
            f"""
            SELECT field_name AS field, COUNT(*) AS count
            FROM mac_movements{movement_where_sql}
            GROUP BY field_name
            ORDER BY count DESC, field_name
            LIMIT ?
            """,
            (*movement_params, bounded_limit),
        ).fetchall()]
        recent_movements = [dict(row) for row in conn.execute(
            f"SELECT * FROM mac_movements{movement_where_sql} ORDER BY changed_at DESC, id DESC LIMIT ?",
            (*movement_params, min(50, bounded_limit)),
        ).fetchall()]
        recent_records = [dict(row) for row in conn.execute(
            f"SELECT * FROM mac_history{where_sql} ORDER BY recorded_at DESC, id DESC LIMIT ?",
            (*params, min(50, bounded_limit)),
        ).fetchall()]
        return {
            "totals": {**totals, **movement_totals},
            "vendors": grouped(conn, "vendor"),
            "models": grouped(conn, "model"),
            "sources": grouped(conn, "source"),
            "rooms": grouped(conn, "room"),
            "switches": grouped(conn, "switch_ip", "switchIp"),
            "movementFields": movement_fields,
            "recentMovements": recent_movements,
            "recentRecords": recent_records,
        }


def history_panel_payload(query_text: str = "", date_from: str = "", date_to: str = "", limit: int = 500) -> dict[str, Any]:
    try:
        requested_limit = int(limit or 500)
    except (TypeError, ValueError):
        requested_limit = 500
    bounded_limit = max(1, min(requested_limit, 2000))
    summary_limit = min(100, max(20, bounded_limit))
    history_search = search_history_records(query_text, date_from, date_to, bounded_limit)
    history_stats = history_statistics(query_text, date_from, date_to, summary_limit)
    vendor_history = vendor_model_history(query_text, bounded_limit, date_from, date_to)
    vendor_stats = vendor_model_statistics(query_text, date_from, date_to, summary_limit)
    upload_history = vendor_model_upload_history(query_text, date_from, date_to, min(500, summary_limit))
    history_rows_html = "".join(
        "<tr "
        f'data-mac="{html_lib.escape(as_text(item.get("mac")), quote=True)}">'
        f"<td>{html_lib.escape(as_text(item.get('mac_formatted')) or format_mac(as_text(item.get('mac'))))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('vendor')))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('model')))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('ip')))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('address')))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('source')))}</td>"
        f"<td>{html_lib.escape(format_display_datetime(item.get('recorded_at')))}</td>"
        "</tr>"
        for item in history_search.get("history", [])
    )
    def stat_summary_html(cards: list[tuple[str, Any]]) -> str:
        return "".join(
            '<div class="bar-label">'
            f'<span>{html_lib.escape(label)}</span>'
            f'<strong>{html_lib.escape(as_text(value if value not in (None, "") else "-"))}</strong>'
            '</div>'
            for label, value in cards
        )

    history_totals = history_stats.get("totals") or {}
    history_top_vendor = (history_stats.get("vendors") or [{}])[0] if isinstance(history_stats.get("vendors"), list) else {}
    history_search_stats = history_search.get("statistics") or {}
    history_summary_html = stat_summary_html([
        ("Records", history_totals.get("records", history_search_stats.get("records", 0))),
        ("Unique MAC", history_totals.get("uniqueMacs", history_search_stats.get("uniqueMacs", 0))),
        ("Movements", history_totals.get("movements", history_search_stats.get("movements", 0))),
        ("Top vendor", history_top_vendor.get("name") or "-"),
    ])
    history_search = {
        **history_search,
        "summaryHtml": history_summary_html,
        "tableRowsHtml": history_rows_html,
        "emptyTableRowsHtml": '<tr><td colspan="7" class="empty-state">SQLite history is empty.</td></tr>',
    }
    vendor_model_rows_html = "".join(
        "<tr>"
        f"<td>{html_lib.escape(format_mac(as_text(item.get('mac'))))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('oui')))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('prefix')))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('vendor')))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('model')))}</td>"
        f"<td>{html_lib.escape(as_text(item.get('source')))}</td>"
        f"<td>{html_lib.escape(format_display_datetime(item.get('observed_at')))}</td>"
        "</tr>"
        for item in vendor_history.get("history", [])
    )
    vendor_totals = vendor_stats.get("totals") or {}
    vendor_history_stats = vendor_history.get("statistics") or {}
    vendor_top_vendor = (vendor_stats.get("vendors") or [{}])[0] if isinstance(vendor_stats.get("vendors"), list) else {}
    vendor_top_model = (vendor_stats.get("models") or [{}])[0] if isinstance(vendor_stats.get("models"), list) else {}
    upload_summary = upload_history.get("summary") or {}
    vendor_summary_html = stat_summary_html([
        ("Records", vendor_totals.get("records", vendor_history_stats.get("records", 0))),
        ("Unique MAC", vendor_totals.get("uniqueMacs", vendor_history_stats.get("uniqueMacs", 0))),
        ("Uploads", upload_summary.get("uploads", 0)),
        ("Snapshots", upload_summary.get("snapshots", 0)),
        ("Top vendor", vendor_top_vendor.get("name") or "-"),
        ("Top model", vendor_top_model.get("name") or "-"),
    ])
    vendor_history = {
        **vendor_history,
        "summaryHtml": vendor_summary_html,
        "tableRowsHtml": vendor_model_rows_html,
        "emptyTableRowsHtml": '<tr><td colspan="7" class="empty-state">Vendor/model history is empty.</td></tr>',
    }
    vendors = history_stats.get("vendors") or vendor_stats.get("vendors") or []
    models = vendor_stats.get("models") or history_stats.get("models") or []
    def summary_rows_html(items: list[dict[str, Any]]) -> str:
        return "".join(
            "<tr>"
            f"<td>{html_lib.escape(as_text(item.get('name') or item.get('vendor') or item.get('model') or 'Unknown'))}</td>"
            f"<td>{int(item.get('count') or 0)}</td>"
            f"<td>{int(item.get('unique_macs') or item.get('uniqueMacs') or 0)}</td>"
            "</tr>"
            for item in items
        )

    summary_empty_html = '<tr><td colspan="3" class="empty-state">Backend history is empty.</td></tr>'
    return {
        "query": as_text(query_text),
        "from": as_text(date_from),
        "to": as_text(date_to),
        "limit": bounded_limit,
        "summaryTables": {
            "vendors": vendors,
            "models": models,
            "vendorRowsHtml": summary_rows_html(vendors),
            "modelRowsHtml": summary_rows_html(models),
            "emptyRowsHtml": summary_empty_html,
        },
        "historySearch": history_search,
        "historyStats": history_stats,
        "vendorModelHistory": vendor_history,
        "vendorModelStats": vendor_stats,
        "vendorModelUploads": upload_history,
    }


def database_search(query_text: str = "", limit: int = 100) -> dict[str, Any]:
    text_query = as_text(query_text)
    normalized_mac = normalize_mac(text_query)
    try:
        requested_limit = int(limit or 100)
    except (TypeError, ValueError):
        requested_limit = 100
    bounded_limit = max(1, min(requested_limit, 500))
    like_value = f"%{text_query}%"
    mac_like = f"%{normalized_mac}%"
    results: list[dict[str, Any]] = []
    with db_connection() as conn:
        if text_query:
            history_rows = conn.execute(
                """
                SELECT mac, mac_formatted, vendor, model, ip, address, room, switch_ip, switch_port, source, recorded_at
                FROM mac_history
                WHERE mac LIKE ? OR mac_formatted LIKE ? OR vendor LIKE ? OR model LIKE ? OR ip LIKE ?
                   OR address LIKE ? OR room LIKE ? OR switch_ip LIKE ? OR switch_port LIKE ? OR source LIKE ?
                ORDER BY recorded_at DESC, id DESC
                LIMIT ?
                """,
                (mac_like, like_value, like_value, like_value, like_value, like_value, like_value, like_value, like_value, like_value, bounded_limit),
            ).fetchall()
            vendor_rows = conn.execute(
                """
                SELECT mac, oui, prefix, vendor, model, source, observed_at
                FROM vendor_model_history
                WHERE mac LIKE ? OR oui LIKE ? OR prefix LIKE ? OR vendor LIKE ? OR model LIKE ? OR source LIKE ?
                ORDER BY observed_at DESC, id DESC
                LIMIT ?
                """,
                (mac_like, like_value, like_value, like_value, like_value, like_value, bounded_limit),
            ).fetchall()
            ip_rows = conn.execute(
                """
                SELECT switch_ip, physical_address, source, updated_at
                FROM ip_address_mappings
                WHERE switch_ip LIKE ? OR physical_address LIKE ? OR source LIKE ?
                ORDER BY switch_ip
                LIMIT ?
                """,
                (like_value, like_value, like_value, bounded_limit),
            ).fetchall()
        else:
            history_rows = conn.execute(
                """
                SELECT mac, mac_formatted, vendor, model, ip, address, room, switch_ip, switch_port, source, recorded_at
                FROM mac_history
                ORDER BY recorded_at DESC, id DESC
                LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
            vendor_rows = []
            ip_rows = []
    for row in history_rows:
        results.append({
            "type": "device",
            "mac": row["mac"],
            "title": row["mac_formatted"] or format_mac(row["mac"]),
            "subtitle": " · ".join(filter(None, [row["vendor"], row["model"], row["ip"], row["address"]])),
            "source": row["source"],
            "updatedAt": row["recorded_at"],
        })
    for row in vendor_rows:
        results.append({
            "type": "vendorModel",
            "mac": row["mac"],
            "title": row["vendor"] or row["model"] or row["mac"],
            "subtitle": " · ".join(filter(None, [row["model"], row["oui"], row["prefix"]])),
            "source": row["source"],
            "updatedAt": row["observed_at"],
        })
    for row in ip_rows:
        results.append({
            "type": "ipMapping",
            "mac": "",
            "title": row["switch_ip"],
            "subtitle": row["physical_address"],
            "source": row["source"],
            "updatedAt": row["updated_at"],
        })
    results.sort(key=lambda item: (item.get("updatedAt") or "", item.get("title") or ""), reverse=True)
    limited_results = results[:bounded_limit]
    results_html = "".join(
        '<div class="mapping-row" '
        f'data-db-type="{html_lib.escape(as_text(item.get("type")), quote=True)}" '
        f'data-db-mac="{html_lib.escape(as_text(item.get("mac")), quote=True)}">'
        "<span>"
        f"<strong>{html_lib.escape(as_text(item.get('title')))}</strong>"
        f"<small>{html_lib.escape(as_text(item.get('type')))} · {html_lib.escape(as_text(item.get('subtitle')))}</small>"
        "</span>"
        f'<span class="muted">{html_lib.escape(as_text(item.get("source")))}</span>'
        "</div>"
        for item in limited_results
    )
    return {
        "results": limited_results,
        "count": len(limited_results),
        "resultsHtml": results_html,
        "emptyResultsHtml": '<p class="muted">Ничего не найдено.</p>',
    }


def database_history_where_clause(filters: Optional[dict[str, Any]] = None) -> tuple[str, list[Any]]:
    filters = filters if isinstance(filters, dict) else {}
    where: list[str] = []
    params: list[Any] = []

    mac_text = as_text(filters.get("mac"))
    if mac_text:
        normalized_mac = normalize_mac(mac_text)
        parts = ["mac_formatted LIKE ?"]
        params.append(f"%{mac_text}%")
        if normalized_mac:
            parts.append("mac LIKE ?")
            params.append(f"%{normalized_mac}%")
        where.append("(" + " OR ".join(parts) + ")")

    for key, column in (("source", "source"), ("vendor", "vendor"), ("model", "model"), ("room", "room")):
        value = as_text(filters.get(key))
        if value:
            where.append(f"{column} LIKE ?")
            params.append(f"%{value}%")

    date_from = as_text(filters.get("dateFrom") or filters.get("from"))
    date_to = as_text(filters.get("dateTo") or filters.get("to"))
    if date_from:
        where.append("recorded_at >= ?")
        params.append(date_from + ("T00:00:00" if "T" not in date_from else ""))
    if date_to:
        where.append("recorded_at <= ?")
        params.append(date_to + ("T23:59:59" if "T" not in date_to else ""))
    return (" WHERE " + " AND ".join(where) if where else ""), params


def database_history_records(filters: Optional[dict[str, Any]] = None, limit: int = 1000) -> dict[str, Any]:
    where_sql, params = database_history_where_clause(filters)
    try:
        requested_limit = int(limit or 1000)
    except (TypeError, ValueError):
        requested_limit = 1000
    bounded_limit = max(1, min(requested_limit, 5000))
    with db_connection() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM mac_history{where_sql}", params).fetchone()[0] or 0)
        summary = dict(conn.execute(
            f"""
            SELECT COUNT(DISTINCT mac) AS unique_macs,
                   COUNT(DISTINCT NULLIF(vendor, '')) AS vendors,
                   COUNT(DISTINCT NULLIF(model, '')) AS models,
                   COUNT(DISTINCT NULLIF(room, '')) AS rooms,
                   COUNT(DISTINCT NULLIF(source, '')) AS sources
            FROM mac_history{where_sql}
            """,
            params,
        ).fetchone())
        records = [dict(row) for row in conn.execute(
            f"SELECT * FROM mac_history{where_sql} ORDER BY recorded_at DESC, id DESC LIMIT ?",
            (*params, bounded_limit),
        ).fetchall()]

    rows_html = "".join(
        '<tr data-db-history-id="{id}" data-db-history-mac="{mac}">'
        '<td><input type="checkbox" data-db-history-select value="{id}" aria-label="Выбрать запись {id}"></td>'
        '<td>{id}</td><td>{mac_formatted}</td><td>{vendor}</td><td>{model}</td><td>{ip}</td>'
        '<td>{address}</td><td>{room}</td><td>{switch_ip}</td><td>{switch_port}</td>'
        '<td>{source}</td><td>{recorded_at}</td>'
        '<td><button class="icon-button database-history-delete" data-delete-db-history-id="{id}" title="Удалить запись" aria-label="Удалить запись {id}">×</button></td>'
        '</tr>'.format(
            id=int(row["id"]),
            mac=html_lib.escape(as_text(row.get("mac")), quote=True),
            mac_formatted=html_lib.escape(as_text(row.get("mac_formatted")) or format_mac(row.get("mac"))),
            vendor=html_lib.escape(as_text(row.get("vendor"))),
            model=html_lib.escape(as_text(row.get("model"))),
            ip=html_lib.escape(as_text(row.get("ip"))),
            address=html_lib.escape(as_text(row.get("address"))),
            room=html_lib.escape(as_text(row.get("room"))),
            switch_ip=html_lib.escape(as_text(row.get("switch_ip"))),
            switch_port=html_lib.escape(as_text(row.get("switch_port"))),
            source=html_lib.escape(as_text(row.get("source"))),
            recorded_at=html_lib.escape(as_text(row.get("recorded_at"))),
        )
        for row in records
    )
    empty_rows_html = '<tr><td colspan="13" class="empty-state">Записи истории не найдены.</td></tr>'
    summary_html = "".join(
        f'<div class="bar-label"><span>{label}</span><strong>{int(value or 0)}</strong></div>'
        for label, value in (
            ("Записей", total),
            ("Показано", len(records)),
            ("Уникальных MAC", summary.get("unique_macs")),
            ("Производителей", summary.get("vendors")),
            ("Моделей", summary.get("models")),
            ("Помещений", summary.get("rooms")),
            ("Источников", summary.get("sources")),
        )
    )
    return {
        "records": records,
        "count": len(records),
        "total": total,
        "limit": bounded_limit,
        "summary": {**summary, "records": total, "shown": len(records)},
        "summaryHtml": summary_html,
        "rowsHtml": rows_html,
        "emptyRowsHtml": empty_rows_html,
    }


def delete_database_history_records(
    ids: Optional[list[Any]] = None,
    filters: Optional[dict[str, Any]] = None,
) -> int:
    clean_ids: list[int] = []
    for value in ids if isinstance(ids, list) else []:
        try:
            row_id = int(value)
        except (TypeError, ValueError):
            continue
        if row_id > 0 and row_id not in clean_ids:
            clean_ids.append(row_id)
    clean_ids = clean_ids[:5000]

    if clean_ids:
        placeholders = ",".join("?" for _ in clean_ids)
        where_sql = f" WHERE id IN ({placeholders})"
        params: list[Any] = clean_ids
        mode = "selected"
    else:
        active_filters = {
            key: value for key, value in (filters.items() if isinstance(filters, dict) else [])
            if key in {"mac", "source", "vendor", "model", "room", "dateFrom", "dateTo", "from", "to"} and as_text(value)
        }
        if not active_filters:
            raise ValueError("Select records or set at least one filter before deleting history")
        where_sql, params = database_history_where_clause(active_filters)
        mode = "filtered"

    with db_connection() as conn:
        deleted = int(conn.execute(f"SELECT COUNT(*) FROM mac_history{where_sql}", params).fetchone()[0] or 0)
        conn.execute(f"DELETE FROM mac_history{where_sql}", params)
    log_action("Delete database history", f"mode={mode}; deleted={deleted}")
    return deleted


def database_device_lookup(mac_value: Any) -> Optional[dict[str, Any]]:
    mac = normalize_mac(mac_value)
    if not mac:
        return None
    with db_connection() as conn:
        history = conn.execute(
            """
            SELECT mac, mac_formatted, oui, vendor, model, ip, address, room, switch_ip, switch_port, source, recorded_at
            FROM mac_history
            WHERE mac = ?
            ORDER BY recorded_at DESC, id DESC
            LIMIT 1
            """,
            (mac,),
        ).fetchone()
        vendor_model = conn.execute(
            """
            SELECT oui, prefix, vendor, model, source, observed_at
            FROM vendor_model_history
            WHERE mac = ?
            ORDER BY observed_at DESC, id DESC
            LIMIT 1
            """,
            (mac,),
        ).fetchone()
        movement_count = conn.execute("SELECT COUNT(*) FROM mac_movements WHERE mac = ?", (mac,)).fetchone()[0]
        appearances = conn.execute("SELECT COUNT(*) FROM mac_history WHERE mac = ?", (mac,)).fetchone()[0]

    if not history and not vendor_model:
        return None

    base = enrich_device({"mac": mac})
    if history:
        base.update({
            "mac": history["mac"],
            "macFormatted": history["mac_formatted"] or format_mac(history["mac"]),
            "oui": history["oui"] or base.get("oui"),
            "vendor": history["vendor"] or base.get("vendor"),
            "model": history["model"] or base.get("model"),
            "ip": history["ip"] or "",
            "address": history["address"] or "",
            "room": history["room"] or "",
            "switchIp": history["switch_ip"] or "",
            "switchPort": history["switch_port"] or "",
            "source": history["source"] or "",
            "recordedAt": history["recorded_at"],
            "lookupSource": "mac_history",
        })
    if vendor_model:
        if not base.get("vendor") or base.get("vendor") == "Unknown":
            base["vendor"] = vendor_model["vendor"] or base.get("vendor")
        if not base.get("model"):
            base["model"] = vendor_model["model"] or base.get("model")
        base["vendorModelSource"] = vendor_model["source"]
        base["vendorModelObservedAt"] = vendor_model["observed_at"]
        base["vendorModelPrefix"] = vendor_model["prefix"]
    base["database"] = {
        "historyRecords": int(appearances or 0),
        "movements": int(movement_count or 0),
        "found": True,
    }
    return base


def database_device_or_lookup(mac_value: Any) -> dict[str, Any]:
    mac = normalize_mac(mac_value)
    if not mac:
        raise ValueError("mac is required")
    device = database_device_lookup(mac)
    if device:
        return {"device": device, "source": device.get("lookupSource") or "database", "found": True}
    device = enrich_device({"mac": mac})
    if device["vendor"] == "Unknown":
        external = external_vendor_lookup(mac)
        if external:
            device["vendor"] = external
            device["vendorSource"] = "external_api"
    device["database"] = {"historyRecords": 0, "movements": 0, "found": False}
    device["lookupSource"] = device.get("vendorSource") or "enrichment"
    return {"device": device, "source": device["lookupSource"], "found": False}


def delete_snapshots(source: str = "", before: str = "", ids: Optional[list[Any]] = None) -> int:
    where: list[str] = []
    params: list[Any] = []
    source_filter = as_text(source)
    before_filter = as_text(before)
    selected_ids = [as_text(value) for value in (ids or []) if as_text(value)]
    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        where.append(f"id IN ({placeholders})")
        params.extend(selected_ids)
    if source_filter:
        where.append("source = ?")
        params.append(source_filter)
    if before_filter:
        where.append("created_at < ?")
        params.append(before_filter)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    with db_connection() as conn:
        count = conn.execute(f"SELECT COUNT(*) FROM snapshots{where_sql}", params).fetchone()[0]
        conn.execute(f"DELETE FROM snapshots{where_sql}", params)
    log_action("Delete snapshots", f"ids={len(selected_ids)}, source={source_filter or '*'}, before={before_filter or '*'}, deleted={count}")
    return int(count or 0)


def database_summary() -> dict[str, Any]:
    table_queries = {
        "history": "SELECT COUNT(*) FROM mac_history",
        "movements": "SELECT COUNT(*) FROM mac_movements",
        "vendorModelHistory": "SELECT COUNT(*) FROM vendor_model_history",
        "autosaves": "SELECT COUNT(*) FROM app_autosaves",
        "snapshots": "SELECT COUNT(*) FROM snapshots",
        "vendors": "SELECT COUNT(*) FROM vendor_mappings",
        "models": "SELECT COUNT(*) FROM model_mappings",
        "ipMappings": "SELECT COUNT(*) FROM ip_address_mappings",
        "logs": "SELECT COUNT(*) FROM app_logs",
        "metrics": "SELECT COUNT(*) FROM performance_metrics",
    }
    with db_connection() as conn:
        summary = {name: conn.execute(sql).fetchone()[0] for name, sql in table_queries.items()}
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        freelist_count = conn.execute("PRAGMA freelist_count").fetchone()[0]
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        table_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    db_size = DATABASE_PATH.stat().st_size if DATABASE_PATH.exists() else 0
    wal_path = DATABASE_PATH.with_name(DATABASE_PATH.name + "-wal")
    shm_path = DATABASE_PATH.with_name(DATABASE_PATH.name + "-shm")
    return {
        "summary": summary,
        "storage": STORAGE.as_dict(),
        "migration": STORAGE_MIGRATION_REPORT,
        "database": {
            "path": str(DATABASE_PATH),
            "sizeBytes": db_size,
            "walBytes": wal_path.stat().st_size if wal_path.exists() else 0,
            "shmBytes": shm_path.stat().st_size if shm_path.exists() else 0,
            "pageCount": page_count,
            "pageSize": page_size,
            "estimatedBytes": page_count * page_size,
            "freePages": freelist_count,
            "journalMode": journal_mode,
            "tables": [row["name"] for row in table_rows],
        },
    }


def database_maintenance(vacuum: bool = False, optimize: bool = True, integrity: bool = True) -> dict[str, Any]:
    before = database_summary()["database"]
    integrity_result = "skipped"
    with db_connection() as conn:
        if integrity:
            integrity_result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if optimize:
            conn.execute("PRAGMA optimize")
    if vacuum:
        with db_connection() as conn:
            conn.execute("VACUUM")
    after = database_summary()["database"]
    log_action("Database maintenance", f"vacuum={vacuum}, optimize={optimize}, integrity={integrity_result}")
    return {
        "ok": integrity_result in {"ok", "skipped"},
        "integrity": integrity_result,
        "before": before,
        "after": after,
        "reclaimedBytes": max(0, int(before.get("sizeBytes", 0)) - int(after.get("sizeBytes", 0))),
    }


def legacy_migration_status(dry_run: bool = True) -> dict[str, Any]:
    init_database()
    result = migrate_legacy_sqlite(STORAGE.legacy, DATABASE_PATH, utc_now(), dry_run=dry_run)
    if not dry_run:
        log_action(
            "Legacy SQLite migration",
            f"available={result['summary']['available']}, imported={result['summary']['imported']}, skipped={result['summary']['skipped']}, errors={result['summary']['errors']}",
        )
    return result


def save_statistics_snapshot(
    devices: list[dict[str, Any]],
    name: str = "",
    source: str = "",
    snapshot_id: str = "",
    created_at: str = "",
) -> dict[str, Any]:
    if not isinstance(devices, list):
        raise ValueError("devices must be a list")
    normalized_id = as_text(snapshot_id) or str(uuid.uuid4())
    normalized_name = as_text(name) or "Snapshot"
    normalized_source = as_text(source)
    timestamp = as_text(created_at) or utc_now()
    saved_at = utc_now()
    payload = json.dumps(devices, ensure_ascii=False)
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, source=excluded.source, device_count=excluded.device_count, "
            "devices_json=excluded.devices_json, created_at=excluded.created_at",
            (normalized_id, normalized_name, normalized_source, len(devices), payload, timestamp),
        )
        snapshot_order = int(conn.execute(
            "SELECT rowid FROM snapshots WHERE id = ?", (normalized_id,)
        ).fetchone()[0])
    log_action("Save statistics snapshot", f"id={normalized_id}, source={normalized_source or '*'}, devices={len(devices)}")
    return {
        "id": normalized_id,
        "name": normalized_name,
        "source": normalized_source,
        "deviceCount": len(devices),
        "createdAt": timestamp,
        "savedAt": saved_at,
        "snapshotOrder": snapshot_order,
        "kind": "analysis" if normalized_name.casefold().startswith("анализ:") else "snapshot",
    }


def save_performance_metric(operation: str, duration_ms: Any, details: str = "", created_at: str = "") -> dict[str, Any]:
    normalized_operation = as_text(operation) or "unknown"
    try:
        duration = round(float(duration_ms or 0), 2)
    except (TypeError, ValueError):
        duration = 0.0
    timestamp = as_text(created_at) or utc_now()
    with db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO performance_metrics (operation, duration_ms, details, created_at) VALUES (?, ?, ?, ?)",
            (normalized_operation, duration, as_text(details), timestamp),
        )
        metric_id = cursor.lastrowid
    return {
        "id": metric_id,
        "operation": normalized_operation,
        "durationMs": duration,
        "details": as_text(details),
        "createdAt": timestamp,
    }


def statistics_snapshot_history(
    query_text: str = "",
    source: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    try:
        requested_limit = int(limit or 100)
    except (TypeError, ValueError):
        requested_limit = 100
    bounded_limit = max(1, min(requested_limit, 1000))
    query_filter = as_text(query_text).lower()
    source_filter = as_text(source)
    from_filter = as_text(date_from)
    to_filter = as_text(date_to)
    where: list[str] = []
    params: list[Any] = []
    if source_filter:
        where.append("source = ?")
        params.append(source_filter)
    if from_filter:
        where.append("created_at >= ?")
        params.append(from_filter)
    if to_filter:
        where.append("created_at <= ?")
        params.append(to_filter)
    if query_filter:
        where.append("(lower(name) LIKE ? OR lower(source) LIKE ? OR lower(devices_json) LIKE ?)")
        like = f"%{query_filter}%"
        params.extend([like, like, like])
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    with db_connection() as conn:
        rows = conn.execute(
            f"SELECT id, name, source, device_count, devices_json, created_at FROM snapshots{where_sql} ORDER BY created_at DESC LIMIT ?",
            [*params, bounded_limit],
        ).fetchall()

    snapshots = []
    unique_macs: set[str] = set()
    sources: set[str] = set()
    for row in rows:
        try:
            devices = json.loads(row["devices_json"] or "[]")
        except json.JSONDecodeError:
            devices = []
        macs = {as_text(device.get("mac") or device.get("macFormatted")) for device in devices if as_text(device.get("mac") or device.get("macFormatted"))}
        unique_macs.update(macs)
        if as_text(row["source"]):
            sources.add(as_text(row["source"]))
        snapshots.append({
            "id": row["id"],
            "name": row["name"],
            "source": row["source"],
            "deviceCount": int(row["device_count"] or len(devices)),
            "uniqueMacs": len(macs),
            "createdAt": row["created_at"],
        })
    table_rows_html = "".join(
        "<tr>"
        f'<td><input type="checkbox" data-snapshot-select value="{html_lib.escape(as_text(snapshot.get("id")), quote=True)}" aria-label="Выбрать выгрузку"></td>'
        f"<td>{html_lib.escape(format_display_datetime(snapshot.get('createdAt')))}</td>"
        f"<td>{html_lib.escape(as_text(snapshot.get('name')))}</td>"
        f"<td>{int(snapshot.get('deviceCount') or 0)}</td>"
        f"<td>{html_lib.escape(as_text(snapshot.get('source')))}</td>"
        f'<td><button class="button secondary" data-load-snapshot="{html_lib.escape(as_text(snapshot.get("id")), quote=True)}">Открыть</button></td>'
        "</tr>"
        for snapshot in snapshots
    )
    return {
        "snapshots": snapshots,
        "tableRowsHtml": table_rows_html,
        "emptyTableRowsHtml": '<tr><td colspan="6" class="empty-state">Backend snapshot history is empty.</td></tr>',
        "summary": {
            "snapshots": len(snapshots),
            "devices": sum(item["deviceCount"] for item in snapshots),
            "uniqueMacs": len(unique_macs),
            "sources": len(sources),
        },
    }


def export_snapshot_history(
    query_text: str = "",
    source: str = "",
    date_from: str = "",
    date_to: str = "",
    export_format: str = "html",
    limit: int = 1000,
) -> dict[str, Any]:
    data = statistics_snapshot_history(query_text, source, date_from, date_to, limit)
    snapshots = data["snapshots"]
    summary = data["summary"]
    fmt = as_text(export_format).lower() or "html"
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    if fmt == "json":
        content = json.dumps({**data, "createdAt": created_at}, ensure_ascii=False, indent=2)
        return {
            "filename": "mac-history.json",
            "mimeType": "application/json",
            "content": content,
            "format": "json",
            "encoding": "utf-8",
            "size": len(content.encode("utf-8")),
        }

    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "createdAt", "name", "source", "deviceCount", "uniqueMacs"])
        for snapshot in snapshots:
            writer.writerow([
                snapshot["id"],
                snapshot["createdAt"],
                snapshot["name"],
                snapshot["source"],
                snapshot["deviceCount"],
                snapshot["uniqueMacs"],
            ])
        content = buffer.getvalue()
        return {
            "filename": "mac-history.csv",
            "mimeType": "text/csv",
            "content": content,
            "format": "csv",
            "encoding": "utf-8",
            "size": len(content.encode("utf-8")),
        }

    if fmt != "html":
        raise ValueError("Unsupported snapshot history export format")

    rows = "".join(
        "<tr>"
        f"<td>{html_lib.escape(as_text(snapshot['id']))}</td>"
        f"<td>{html_lib.escape(as_text(snapshot['createdAt']))}</td>"
        f"<td>{html_lib.escape(as_text(snapshot['name']))}</td>"
        f"<td>{html_lib.escape(as_text(snapshot['source']))}</td>"
        f"<td>{int(snapshot['deviceCount'])}</td>"
        f"<td>{int(snapshot['uniqueMacs'])}</td>"
        "</tr>"
        for snapshot in snapshots
    )
    content = (
        '<!doctype html><meta charset="utf-8"><title>MAC history</title>'
        "<style>body{font:14px Arial;margin:32px}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #bbb;padding:7px;text-align:left}th{background:#eee}</style>"
        "<h1>MAC Analyzer history</h1>"
        f"<p>Created: {html_lib.escape(created_at)}</p>"
        "<ul>"
        f"<li>Snapshots: {int(summary['snapshots'])}</li>"
        f"<li>Devices: {int(summary['devices'])}</li>"
        f"<li>Unique MAC: {int(summary['uniqueMacs'])}</li>"
        f"<li>Sources: {int(summary['sources'])}</li>"
        "</ul>"
        "<table><thead><tr><th>ID</th><th>Date</th><th>Snapshot</th><th>Source</th><th>Devices</th><th>Unique MAC</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
    return {
        "filename": "mac-history.html",
        "mimeType": "text/html",
        "content": content,
        "format": "html",
        "encoding": "utf-8",
        "size": len(content.encode("utf-8")),
    }


def performance_statistics(operation: str = "", limit: int = 200) -> dict[str, Any]:
    try:
        requested_limit = int(limit or 200)
    except (TypeError, ValueError):
        requested_limit = 200
    bounded_limit = max(1, min(requested_limit, 1000))
    operation_filter = as_text(operation)
    where_sql = " WHERE operation = ?" if operation_filter else ""
    params: list[Any] = [operation_filter] if operation_filter else []
    with db_connection() as conn:
        rows = conn.execute(
            f"SELECT id, operation, duration_ms, details, created_at FROM performance_metrics{where_sql} ORDER BY id DESC LIMIT ?",
            [*params, bounded_limit],
        ).fetchall()

    metrics = [dict(row) for row in rows]
    grouped: dict[str, dict[str, Any]] = {}
    for row in metrics:
        operation_name = row["operation"]
        duration = float(row["duration_ms"] or 0)
        entry = grouped.setdefault(operation_name, {
            "operation": operation_name,
            "count": 0,
            "totalMs": 0.0,
            "minMs": duration,
            "maxMs": duration,
            "lastAt": row["created_at"],
        })
        entry["count"] += 1
        entry["totalMs"] += duration
        entry["minMs"] = min(entry["minMs"], duration)
        entry["maxMs"] = max(entry["maxMs"], duration)
        entry["lastAt"] = max(entry["lastAt"], row["created_at"])

    operations = []
    for entry in grouped.values():
        operations.append({
            "operation": entry["operation"],
            "count": entry["count"],
            "avgMs": round(entry["totalMs"] / entry["count"], 2) if entry["count"] else 0,
            "minMs": round(entry["minMs"], 2),
            "maxMs": round(entry["maxMs"], 2),
            "lastAt": entry["lastAt"],
        })
    operations.sort(key=lambda item: (-item["count"], item["operation"]))
    return {
        "metrics": metrics,
        "operations": operations,
        "summary": {
            "metrics": len(metrics),
            "operations": len(operations),
            "avgMs": round(sum(float(row["duration_ms"] or 0) for row in metrics) / len(metrics), 2) if metrics else 0,
            "maxMs": round(max((float(row["duration_ms"] or 0) for row in metrics), default=0), 2),
        },
    }


def statistics_summary(limit: int = 100, source: str = "") -> dict[str, Any]:
    try:
        requested_limit = int(limit or 100)
    except (TypeError, ValueError):
        requested_limit = 100
    bounded_limit = max(1, min(requested_limit, 500))
    source_filter = as_text(source)
    snapshot_sql = "SELECT id, name, source, device_count, devices_json, created_at FROM snapshots"
    snapshot_params: list[Any] = []
    if source_filter:
        snapshot_sql += " WHERE source = ?"
        snapshot_params.append(source_filter)
    snapshot_sql += " ORDER BY created_at ASC LIMIT ?"
    snapshot_params.append(bounded_limit)
    with db_connection() as conn:
        snapshot_rows = conn.execute(snapshot_sql, snapshot_params).fetchall()
        if source_filter:
            metric_rows = conn.execute(
                "SELECT operation, duration_ms, details, created_at FROM performance_metrics WHERE details LIKE ? ORDER BY created_at DESC LIMIT 200",
                (source_filter + "%",),
            ).fetchall()
        else:
            metric_rows = conn.execute(
                "SELECT operation, duration_ms, details, created_at FROM performance_metrics ORDER BY created_at DESC LIMIT 200"
            ).fetchall()

    trends = []
    previous_macs: set[str] = set()
    all_devices: list[dict[str, Any]] = []
    for row in snapshot_rows:
        devices = json.loads(row["devices_json"] or "[]")
        macs = {as_text(device.get("mac")) for device in devices if as_text(device.get("mac"))}
        all_devices.extend(devices)
        trends.append({
            "id": row["id"],
            "name": row["name"],
            "source": row["source"],
            "createdAt": row["created_at"],
            "deviceCount": row["device_count"],
            "uniqueMacs": len(macs),
            "added": len(macs - previous_macs) if previous_macs else len(macs),
            "removed": len(previous_macs - macs) if previous_macs else 0,
            "vendors": len({as_text(device.get("vendor")) for device in devices if as_text(device.get("vendor"))}),
            "rooms": len({as_text(device.get("room")) for device in devices if as_text(device.get("room"))}),
            "switches": len({as_text(device.get("switchIp") or device.get("switch_ip")) for device in devices if as_text(device.get("switchIp") or device.get("switch_ip"))}),
        })
        previous_macs = macs

    def grouped(field: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for device in all_devices:
            value = as_text(device.get(field)) or "Unknown"
            counts[value] = counts.get(value, 0) + 1
        return [{"name": name, "count": count} for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]]

    operation_totals: dict[str, dict[str, Any]] = {}
    for row in metric_rows:
        entry = operation_totals.setdefault(row["operation"], {"operation": row["operation"], "count": 0, "totalMs": 0.0, "maxMs": 0.0})
        duration = float(row["duration_ms"] or 0)
        entry["count"] += 1
        entry["totalMs"] += duration
        entry["maxMs"] = max(entry["maxMs"], duration)
    operations = []
    for entry in operation_totals.values():
        operations.append({
            "operation": entry["operation"],
            "count": entry["count"],
            "avgMs": round(entry["totalMs"] / entry["count"], 2) if entry["count"] else 0,
            "maxMs": round(entry["maxMs"], 2),
        })
    operations.sort(key=lambda item: (-item["count"], item["operation"]))

    return {
        "summary": {
            "snapshots": len(snapshot_rows),
            "devices": sum(row["device_count"] for row in snapshot_rows),
            "uniqueMacs": len({as_text(device.get("mac")) for device in all_devices if as_text(device.get("mac"))}),
            "metrics": len(metric_rows),
        },
        "trends": trends,
        "distributions": {
            "vendors": grouped("vendor"),
            "models": grouped("model"),
            "rooms": grouped("room"),
        },
        "performance": operations,
    }


def temporal_statistics(period: str = "day", source: str = "", limit: int = 365) -> dict[str, Any]:
    normalized_period = as_text(period).lower() or "day"
    if normalized_period not in {"day", "week", "month"}:
        raise ValueError("period must be day, week, or month")
    try:
        requested_limit = int(limit or 365)
    except (TypeError, ValueError):
        requested_limit = 365
    bounded_limit = max(1, min(requested_limit, 1000))
    source_filter = as_text(source)

    sql = "SELECT id, name, source, device_count, devices_json, created_at FROM snapshots"
    params: list[Any] = []
    if source_filter:
        sql += " WHERE source = ?"
        params.append(source_filter)
    sql += " ORDER BY created_at ASC LIMIT ?"
    params.append(bounded_limit)
    with db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    def parse_created_at(value: str) -> datetime:
        text = as_text(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return datetime.utcnow()

    def period_key(created_at: datetime) -> str:
        if normalized_period == "month":
            return created_at.strftime("%Y-%m")
        if normalized_period == "week":
            year, week, _ = created_at.isocalendar()
            return f"{year}-W{week:02d}"
        return created_at.strftime("%Y-%m-%d")

    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        created_at = parse_created_at(row["created_at"])
        key = period_key(created_at)
        bucket = buckets.setdefault(key, {
            "period": key,
            "periodType": normalized_period,
            "snapshotCount": 0,
            "deviceTotal": 0,
            "maxDevices": 0,
            "macs": set(),
            "vendors": set(),
            "rooms": set(),
            "sources": set(),
            "snapshots": [],
        })
        try:
            devices = json.loads(row["devices_json"] or "[]")
        except json.JSONDecodeError:
            devices = []
        macs = {as_text(device.get("mac") or device.get("macFormatted")) for device in devices if as_text(device.get("mac") or device.get("macFormatted"))}
        bucket["snapshotCount"] += 1
        bucket["deviceTotal"] += int(row["device_count"] or len(devices))
        bucket["maxDevices"] = max(bucket["maxDevices"], int(row["device_count"] or len(devices)))
        bucket["macs"].update(macs)
        bucket["vendors"].update(as_text(device.get("vendor")) for device in devices if as_text(device.get("vendor")))
        bucket["rooms"].update(as_text(device.get("room")) for device in devices if as_text(device.get("room")))
        if as_text(row["source"]):
            bucket["sources"].add(as_text(row["source"]))
        bucket["snapshots"].append({"id": row["id"], "name": row["name"], "createdAt": row["created_at"], "deviceCount": row["device_count"]})

    periods = []
    previous_macs: set[str] = set()
    for key in sorted(buckets):
        bucket = buckets[key]
        macs = bucket["macs"]
        periods.append({
            "period": key,
            "periodType": normalized_period,
            "snapshotCount": bucket["snapshotCount"],
            "deviceTotal": bucket["deviceTotal"],
            "maxDevices": bucket["maxDevices"],
            "uniqueMacs": len(macs),
            "added": len(macs - previous_macs) if previous_macs else len(macs),
            "removed": len(previous_macs - macs) if previous_macs else 0,
            "vendors": len(bucket["vendors"]),
            "rooms": len(bucket["rooms"]),
            "sources": sorted(bucket["sources"]),
            "snapshots": bucket["snapshots"],
        })
        previous_macs = set(macs)

    return {
        "period": normalized_period,
        "summary": {
            "periods": len(periods),
            "snapshots": sum(item["snapshotCount"] for item in periods),
            "uniqueMacs": len(set().union(*(buckets[key]["macs"] for key in buckets))) if buckets else 0,
            "deviceTotal": sum(item["deviceTotal"] for item in periods),
        },
        "periods": periods,
    }


def statistics_panel_html(summary: dict[str, Any], statistics_detail: str, trend_rows: list[dict[str, Any]], performance_rows: list[dict[str, Any]]) -> str:
    header = (
        '<div class="mapping-row"><span><strong>SQLite snapshots</strong>'
        f"<small>{int(summary.get('snapshots') or 0)} snapshots · {int(summary.get('uniqueMacs') or 0)} unique MAC · {int(summary.get('metrics') or 0)} metrics</small></span></div>"
        '<div class="mapping-row"><span><strong>StatisticsDatabase API</strong>'
        f"<small>{html_lib.escape(as_text(statistics_detail))}</small></span></div>"
    )
    trends = "".join(
        '<div class="bar-item"><div class="bar-label">'
        f"<span>{html_lib.escape(format_display_datetime(item.get('label')))}</span>"
        f"<strong>{int(item.get('deviceCount') or 0)} · +{int(item.get('added') or 0)} / -{int(item.get('removed') or 0)}</strong>"
        '</div><div class="bar-track">'
        f'<div class="bar-fill" style="width:{max(4, int(item.get("percent") or 0))}%"></div>'
        '</div></div>'
        for item in trend_rows
    )
    metrics = "".join(
        '<div class="mapping-row"><span>'
        f"<strong>{html_lib.escape(as_text(item.get('operation')))}</strong>"
        f"<small>{html_lib.escape(as_text(item.get('detail')))}</small>"
        '</span></div>'
        for item in performance_rows
    )
    return header + trends + metrics


def temporal_statistics_html(temporal_rows: list[dict[str, Any]]) -> str:
    if not temporal_rows:
        return '<p class="muted">Нет SQLite-снимков для временной статистики.</p>'
    return "".join(
        '<div class="bar-item"><div class="bar-label">'
        f"<span>{html_lib.escape(as_text(item.get('period')))}</span>"
        f"<strong>{int(item.get('uniqueMacs') or 0)} MAC · +{int(item.get('added') or 0)} / -{int(item.get('removed') or 0)}</strong>"
        '</div><div class="bar-track">'
        f'<div class="bar-fill" style="width:{int(item.get("percent") or 0)}%"></div>'
        '</div></div>'
        for item in temporal_rows
    )


def backend_charts_html(charts: list[dict[str, Any]]) -> str:
    if not charts:
        return '<p class="muted">Backend не вернул диаграммы.</p>'
    rows = []
    for chart in charts:
        preview = " · ".join(
            f"{html_lib.escape(as_text(item.get('label')))}: {html_lib.escape(as_text(item.get('value')))}"
            for item in (chart.get("preview") or [])
        )
        rows.append(
            '<div class="mapping-row"><span>'
            f"<strong>{html_lib.escape(as_text(chart.get('title')))}</strong>"
            f"<small>{html_lib.escape(as_text(chart.get('type')))} · {preview}</small>"
            '</span></div>'
        )
    return "".join(rows)


def chart_bar_items_html(items: list[dict[str, Any]], empty_message: str = "Недостаточно данных.") -> str:
    safe_items = [item for item in items if isinstance(item, dict)]
    if not safe_items:
        return f'<p class="muted">{html_lib.escape(empty_message)}</p>'
    max_value = max((float(item.get("value") or 0) for item in safe_items), default=1)
    max_value = max(1, max_value)
    return "".join(
        '<div class="bar-item"><div class="bar-label">'
        f'<span>{html_lib.escape(as_text(item.get("label")) or "-")}</span>'
        f'<strong>{html_lib.escape(as_text(item.get("value") or 0))}</strong>'
        '</div><div class="bar-track">'
        f'<div class="bar-fill" style="width:{round(float(item.get("value") or 0) / max_value * 100)}%"></div>'
        '</div></div>'
        for item in safe_items[:8]
    )


def cluster_rows_html(cluster_rows: list[dict[str, Any]]) -> str:
    if not cluster_rows:
        return '<p class="muted">Backend не нашёл кластеров.</p>'
    return "".join(
        '<div class="bar-item"><div class="bar-label">'
        f"<span>{html_lib.escape(as_text(cluster.get('label')))}</span>"
        f"<strong>{int(cluster.get('count') or 0)} · MAC {int(cluster.get('uniqueMacs') or 0)}</strong>"
        '</div><div class="bar-track">'
        f'<div class="bar-fill" style="width:{int(cluster.get("percent") or 0)}%"></div>'
        '</div></div>'
        for cluster in cluster_rows
    )


def topology_nodes_html(nodes: list[dict[str, Any]]) -> str:
    if not nodes:
        return '<p class="muted">Backend не нашёл связей топологии.</p>'
    node_rows = []
    for node in nodes:
        ports = "".join(
            f'<span class="topology-port">Порт {html_lib.escape(as_text(port.get("port")))} · {int(port.get("deviceCount") or 0)}</span>'
            for port in (node.get("ports") or [])
        )
        rooms = ", ".join(as_text(room) for room in (node.get("rooms") or []) if as_text(room)) or "Помещение не указано"
        node_rows.append(
            '<article class="topology-node"><header>'
            f"<span>{html_lib.escape(as_text(node.get('switchIp')))}</span>"
            f"<span>{int(node.get('deviceCount') or 0)} устройств · {int(node.get('portCount') or 0)} портов</span>"
            f"</header><small>{html_lib.escape(rooms)}</small><div class=\"topology-ports\">{ports}</div></article>"
        )
    return "".join(node_rows)


def statistics_panel_payload(source: str = "") -> dict[str, Any]:
    summary_data = statistics_summary(limit=100, source=source)
    snapshot_history = statistics_snapshot_history(source=source, limit=25)
    performance_data = performance_statistics(limit=200)
    temporal_data = temporal_statistics(period="day", source=source, limit=365)

    trends = summary_data.get("trends", [])[-5:]
    trend_max = max((int(item.get("deviceCount") or 0) for item in trends), default=1)
    trend_rows = []
    for item in trends:
        devices = int(item.get("deviceCount") or 0)
        trend_rows.append({
            "id": item.get("id"),
            "label": item.get("createdAt") or item.get("name") or "",
            "deviceCount": devices,
            "added": int(item.get("added") or 0),
            "removed": int(item.get("removed") or 0),
            "percent": round(devices / max(1, trend_max) * 100),
        })

    performance_rows = []
    for item in (summary_data.get("performance") or [])[:4]:
        performance_rows.append({
            "operation": item.get("operation") or "",
            "count": int(item.get("count") or 0),
            "avgMs": item.get("avgMs") or 0,
            "maxMs": item.get("maxMs") or 0,
            "detail": f"{int(item.get('count') or 0)} runs · avg {item.get('avgMs') or 0} ms · max {item.get('maxMs') or 0} ms",
        })

    periods = (temporal_data.get("periods") or [])[-8:]
    period_max = max((int(item.get("maxDevices") or item.get("deviceTotal") or 0) for item in periods), default=1)
    temporal_rows = []
    for item in periods:
        devices = int(item.get("maxDevices") or item.get("deviceTotal") or 0)
        temporal_rows.append({
            "period": item.get("period") or "",
            "uniqueMacs": int(item.get("uniqueMacs") or 0),
            "added": int(item.get("added") or 0),
            "removed": int(item.get("removed") or 0),
            "percent": round(devices / max(1, period_max) * 100),
        })

    history_summary = snapshot_history.get("summary", {})
    performance_summary = performance_data.get("summary", {})
    statistics_detail = (
        f"{history_summary.get('snapshots', 0)} recent snapshots В· "
        f"{history_summary.get('sources', 0)} sources В· avg {performance_summary.get('avgMs', 0)} ms"
    )
    return {
        "summary": summary_data.get("summary", {}),
        "historySummary": history_summary,
        "performanceSummary": performance_summary,
        "statisticsApiDetail": (
            f"{history_summary.get('snapshots', 0)} recent snapshots · "
            f"{history_summary.get('sources', 0)} sources · avg {performance_summary.get('avgMs', 0)} ms"
        ),
        "trendRows": trend_rows,
        "performanceRows": performance_rows,
        "temporalSummary": temporal_data.get("summary", {}),
        "temporalRows": temporal_rows,
        "statisticsHtml": statistics_panel_html(summary_data.get("summary", {}), statistics_detail, trend_rows, performance_rows),
        "temporalHtml": temporal_statistics_html(temporal_rows),
    }


def analytics_panel_payload(devices: list[dict[str, Any]], snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(devices, list) or not isinstance(snapshots, list):
        raise ValueError("devices and snapshots must be arrays")
    chart_payload = build_chart_payload(devices, snapshots)
    chart_map = {chart["id"]: chart for chart in chart_payload.get("charts", [])}
    backend_charts = []
    for chart_id in ("vendors", "models", "rooms", "quality"):
        chart = chart_map.get(chart_id)
        if not chart:
            continue
        backend_charts.append({
            "id": chart_id,
            "title": chart.get("title") or chart_id,
            "type": chart.get("type") or "",
            "preview": [
                {"label": item.get("label"), "value": item.get("value")}
                for item in (chart.get("items") or [])[:3]
            ],
        })
    clusters = build_clusters(devices, ["vendor", "room", "switchIp"], 1)
    cluster_items = clusters.get("clusters", [])
    cluster_max = max((int(cluster.get("count") or 0) for cluster in cluster_items), default=1)
    cluster_rows = []
    for cluster in cluster_items[:10]:
        count = int(cluster.get("count") or 0)
        cluster_rows.append({
            "label": cluster.get("label") or "",
            "count": count,
            "uniqueMacs": int(cluster.get("uniqueMacs") or 0),
            "percent": round(count / max(1, cluster_max) * 100),
        })
    primary_charts = {
        key: (chart_map.get(key, {}).get("items") or [])
        for key in ("vendors", "models", "quality", "timeline")
    }
    return {
        "charts": chart_payload.get("charts", []),
        "primaryCharts": primary_charts,
        "primaryChartsHtml": {
            key: chart_bar_items_html(items)
            for key, items in primary_charts.items()
        },
        "backendCharts": backend_charts,
        "backendChartsHtml": backend_charts_html(backend_charts),
        "clusterRows": cluster_rows,
        "clusterRowsHtml": cluster_rows_html(cluster_rows),
        "emptyClusterRowsHtml": cluster_rows_html([]),
        "clusterSummary": clusters.get("summary", {}),
    }


def dashboard_settings() -> dict[str, Any]:
    with db_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'dashboard'").fetchone()
    if not row:
        return normalize_dashboard_settings({})
    try:
        return normalize_dashboard_settings(json.loads(row["value"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return normalize_dashboard_settings({})


def save_dashboard_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_dashboard_settings(settings)
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES ('dashboard', ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (json.dumps(normalized, ensure_ascii=False), utc_now()),
        )
    return normalized


def dashboard_history_context() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load the same 30-day change context used by the PyQt DashboardWidget."""
    with db_connection() as conn:
        movements = [dict(row) for row in conn.execute(
            "SELECT * FROM mac_movements "
            "WHERE datetime(changed_at) >= datetime('now', '-30 days') "
            "ORDER BY changed_at DESC, id DESC LIMIT 5000"
        ).fetchall()]
        recent_history = [dict(row) for row in conn.execute(
            "SELECT * FROM mac_history ORDER BY id DESC LIMIT 20000"
        ).fetchall()]
    history_devices = []
    seen_macs: set[str] = set()
    for row in recent_history:
        mac = as_text(row.get("mac"))
        if not mac or mac in seen_macs:
            continue
        seen_macs.add(mac)
        history_devices.append(row)
        if len(history_devices) >= 5000:
            break
    return movements, history_devices


def external_api_settings() -> dict[str, Any]:
    with db_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'external_api'").fetchone()
    if not row:
        return normalize_external_api_settings({})
    try:
        return normalize_external_api_settings(json.loads(row["value"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return normalize_external_api_settings({})


def save_external_api_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_external_api_settings(settings)
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES ('external_api', ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (json.dumps(normalized, ensure_ascii=False), utc_now()),
        )
    return normalized


THEME_OPTIONS = [
    {"key": "dark", "name": "Темная", "background": "#1e1e1e", "surface": "#2d2d2d", "accent": "#4a90d9", "text": "#e0e0e0"},
    {"key": "light", "name": "Светлая", "background": "#f5f5f5", "surface": "#ffffff", "accent": "#2c6b9e", "text": "#333333"},
]


def normalize_theme(value: Any) -> str:
    theme = as_text(value).lower()
    return theme if theme in {"light", "dark"} else "light"


def theme_payload(theme: Any) -> dict[str, Any]:
    normalized = normalize_theme(theme)
    return {"theme": normalized, "active": next(item for item in THEME_OPTIONS if item["key"] == normalized), "themes": THEME_OPTIONS}


def theme_settings() -> dict[str, Any]:
    with db_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'theme'").fetchone()
    if not row:
        return theme_payload("light")
    try:
        return theme_payload(json.loads(row["value"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return theme_payload("light")


def save_theme_settings(theme: Any) -> dict[str, Any]:
    normalized = normalize_theme(theme)
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES ('theme', ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (json.dumps(normalized, ensure_ascii=False), utc_now()),
        )
    log_action("Theme changed", normalized)
    return theme_payload(normalized)


def engineering_token_hash(token: str) -> str:
    return hashlib.sha256(as_text(token).encode("utf-8")).hexdigest()


def normalize_engineering_ttl(ttl_minutes: Any = 480) -> int:
    try:
        normalized = int(ttl_minutes or 480)
    except (TypeError, ValueError):
        normalized = 480
    return min(1440, max(1, normalized))


def issue_engineering_session(ttl_minutes: int = 480) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    created_at = utc_now()
    expires_at = (datetime.utcnow() + timedelta(minutes=normalize_engineering_ttl(ttl_minutes))).replace(microsecond=0).isoformat() + "Z"
    session = {
        "token": token,
        "role": "engineer",
        "permissions": ENGINEERING_PERMISSIONS,
        "expiresAt": expires_at,
        "createdAt": created_at,
    }
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO engineering_sessions (token_hash, role, permissions_json, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (engineering_token_hash(token), session["role"], json.dumps(session["permissions"]), created_at, expires_at),
        )
    return session


def validate_engineering_session(token: str, permission: str = "") -> Optional[dict[str, Any]]:
    if not as_text(token):
        return None
    token_hash = engineering_token_hash(token)
    with db_connection() as conn:
        row = conn.execute(
            "SELECT role, permissions_json, created_at, expires_at, revoked_at FROM engineering_sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
    if not row or row["revoked_at"]:
        return None
    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", ""))
    if expires_at <= datetime.utcnow():
        return None
    permissions = json.loads(row["permissions_json"])
    if permission and permission not in permissions:
        return None
    return {
        "role": row["role"],
        "permissions": permissions,
        "createdAt": row["created_at"],
        "expiresAt": row["expires_at"],
    }


def revoke_engineering_session(token: str) -> bool:
    token_hash = engineering_token_hash(token)
    with db_connection() as conn:
        cursor = conn.execute(
            "UPDATE engineering_sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (utc_now(), token_hash),
        )
    return cursor.rowcount > 0


def api_cache_get(key: str) -> Optional[dict[str, str]]:
    with db_connection() as conn:
        row = conn.execute("SELECT value, cached_at FROM api_cache WHERE cache_key = ?", (key,)).fetchone()
    return dict(row) if row else None


def api_cache_set(key: str, value: str) -> None:
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO api_cache (cache_key, value, cached_at) VALUES (?, ?, ?) "
            "ON CONFLICT(cache_key) DO UPDATE SET value=excluded.value, cached_at=excluded.cached_at",
            (key, value, utc_now()),
        )


def api_cache_summary(limit: int = 50) -> dict[str, Any]:
    safe_limit = max(1, min(200, int(limit or 50)))
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT cache_key, value, cached_at FROM api_cache ORDER BY cached_at DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM api_cache").fetchone()[0]
        providers = conn.execute(
            """
            SELECT substr(cache_key, 17, instr(substr(cache_key, 17), ':') - 1) AS provider, COUNT(*) AS count
            FROM api_cache
            WHERE cache_key LIKE 'external_vendor:%'
            GROUP BY provider
            """
        ).fetchall()
    return {
        "total": int(total or 0),
        "providers": {row["provider"] or "legacy": row["count"] for row in providers},
        "items": [dict(row) for row in rows],
    }


def clear_api_cache(prefix: str = "") -> int:
    cache_prefix = as_text(prefix)
    with db_connection() as conn:
        if cache_prefix:
            cursor = conn.execute("DELETE FROM api_cache WHERE cache_key LIKE ?", (cache_prefix + "%",))
        else:
            cursor = conn.execute("DELETE FROM api_cache")
    log_action("API cache cleared", f"prefix={cache_prefix or '*'}, deleted={cursor.rowcount}")
    return int(cursor.rowcount or 0)


def external_lookup_client(mac: str, settings: dict[str, Any]) -> Optional[str]:
    provider = settings.get("provider")
    if provider == "custom" and settings.get("endpoint"):
        url = str(settings["endpoint"]).replace("{mac}", mac)
    elif provider == "maclookup":
        url = "https://api.maclookup.app/v2/macs/" + mac + "/"
    elif provider == "mac2vendor":
        url = "https://mac2vendor.com/api/v1/lookup/" + mac
    else:
        url = "https://api.macvendors.com/" + mac
    request = urllib.request.Request(url, headers={"User-Agent": "MAC-Analyzer-Pro-Web/1.0"})
    if settings.get("apiKey"):
        request.add_header("Authorization", "Bearer " + str(settings["apiKey"]))
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status != 200:
                return None
            text = response.read().decode("utf-8", errors="replace").strip()
            if provider in {"maclookup", "mac2vendor"}:
                try:
                    payload = json.loads(text)
                    return as_text(payload.get("company") or payload.get("vendor") or payload.get("name")) or None
                except json.JSONDecodeError:
                    return None
            return text or None
    except (urllib.error.URLError, TimeoutError):
        return None


def notification_channels() -> list[dict[str, Any]]:
    with db_connection() as conn:
        rows = conn.execute("SELECT channel, config_json, enabled, updated_at FROM notification_settings ORDER BY channel").fetchall()
    channels = []
    for row in rows:
        try:
            config = json.loads(row["config_json"] or "{}")
        except json.JSONDecodeError:
            config = {}
        channels.append({"channel": row["channel"], "config": config, "enabled": bool(row["enabled"]), "updatedAt": row["updated_at"]})
    return channels


def notification_config_from_payload(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    channel = as_text(payload.get("channel")).strip().lower() or "email"
    if channel not in {"email", "telegram", "slack"}:
        raise ValueError("Поддерживаются каналы email, telegram и slack")
    if isinstance(payload.get("config"), dict):
        return channel, payload["config"]
    if "configText" in payload:
        config_text = as_text(payload.get("configText")).strip()
        if not config_text:
            return channel, {}
        try:
            config = json.loads(config_text)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid notification config JSON: {error.msg}") from error
        if not isinstance(config, dict):
            raise ValueError("notification config must be a JSON object")
        return channel, config
    return channel, {key: value for key, value in payload.items() if key not in {"channel", "enabled"}}


def send_notification_message(channel: str, config: dict[str, Any], event: dict[str, Any]) -> None:
    subject = as_text(event.get("subject")) or "MAC Analyzer notification"
    text = as_text(event.get("text")) or subject
    if channel == "email":
        host, sender, password, recipient = (as_text(config.get(name)) for name in ("smtpHost", "from", "password", "to"))
        port = int(config.get("smtpPort", 587))
        message = MIMEMultipart()
        message["From"], message["To"], message["Subject"] = sender, recipient, subject
        message.attach(MIMEText(text, "plain", "utf-8"))
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.send_message(message)
        return
    if channel == "telegram":
        body = json.dumps({"chat_id": as_text(config.get("chatId")), "text": text}).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{as_text(config.get('botToken'))}/sendMessage",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=15):
            return
    if channel == "slack":
        body = json.dumps({"text": text}).encode("utf-8")
        request = urllib.request.Request(
            as_text(config.get("webhookUrl")),
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=15):
            return
    raise ValueError("Unsupported notification channel")


def notify_analysis_completed(devices: list[dict[str, Any]], invalid: list[Any], source: str) -> dict[str, Any]:
    event = build_analysis_event(devices, invalid, source)
    result = dispatch_notification_event(event, notification_channels(), send_notification_message)
    log_action("Analysis notification event", json.dumps({"sent": result["sent"], "errors": result["errors"], "skipped": result["skipped"]}, ensure_ascii=False))
    return result


def task_queue(task_id: str = "") -> list[dict[str, Any]]:
    sql = "SELECT * FROM task_file_queue"
    params: list[Any] = []
    if task_id:
        sql += " WHERE task_id = ?"
        params.append(task_id)
    sql += " ORDER BY created_at DESC"
    with db_connection() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def scheduled_tasks_payload() -> dict[str, Any]:
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM scheduled_tasks ORDER BY created_at DESC").fetchall()
    tasks = []
    for row in rows:
        task = {**dict(row), "payload": json.loads(row["payload_json"])}
        task["queue"] = queue_summary(task_queue(task["id"]))
        tasks.append(task)
    return {"tasks": tasks}


def services_panel_html(
    ip_payload: dict[str, Any],
    task_payload: dict[str, Any],
    log_payload: dict[str, Any],
    metric_payload: dict[str, Any],
    database_payload: dict[str, Any],
    autosave_payload: dict[str, Any],
    signal_payload: dict[str, Any],
    legacy_payload: dict[str, Any],
) -> dict[str, str]:
    ip_stats = ip_payload.get("statistics") or {}
    ip_mappings = ip_payload.get("mappings") or []
    ip_rows = (
        '<div class="mapping-row"><span><strong>Coverage</strong>'
        f"<small>{int(ip_stats.get('coverage') or 0)}% · mappings {int(ip_stats.get('totalMappings') or 0)}"
        f" · matched switches {int(ip_stats.get('matchedSwitches') or 0)}/{int(ip_stats.get('deviceSwitches') or 0)}</small>"
        "</span></div>"
    )
    ip_rows += "".join(
        '<div class="mapping-row"><span>'
        f"<strong>{html_lib.escape(as_text(item.get('switch_ip')))}</strong> · {html_lib.escape(as_text(item.get('physical_address')))}"
        f'</span><button data-remove-ip="{html_lib.escape(as_text(item.get("switch_ip")), quote=True)}">Удалить</button></div>'
        for item in ip_mappings
    ) or '<p class="muted">Соответствия пока не добавлены.</p>'

    task_rows = "".join(
        '<div class="mapping-row"><span>'
        f"<strong>{html_lib.escape(as_text(item.get('name')))}</strong>"
        f"<small>Каждые {int(item.get('interval_minutes') or 0)} мин. · последний запуск: "
        f"{html_lib.escape(format_display_datetime(item.get('last_run_at')) or 'ещё не было')} · очередь: "
        f"{int((item.get('queue') or {}).get('pending') or 0)} ждёт / {int((item.get('queue') or {}).get('done') or 0)} готово / "
        f"{int((item.get('queue') or {}).get('error') or 0)} ошибок</small></span>"
        f'<button data-remove-task="{html_lib.escape(as_text(item.get("id")), quote=True)}">Удалить</button></div>'
        for item in task_payload.get("tasks", [])
    ) or '<p class="muted">Задачи пока не созданы.</p>'

    signal = signal_payload.get("signal") or {}
    log_summary = log_payload.get("summary") or {}
    log_rows = (
        '<div class="mapping-row"><span><strong>AppLogger</strong>'
        f"<small>{int(log_summary.get('count') or 0)} records · last signal {html_lib.escape(as_text(signal.get('lastSignal')) or 'none')}</small>"
        "</span></div>"
    )
    log_rows += "".join(
        '<div class="mapping-row"><span>'
        f"<strong>{html_lib.escape(as_text(item.get('action')))}</strong><small>{html_lib.escape(as_text(item.get('details')))}</small>"
        f"</span><span class=\"muted\">{html_lib.escape(format_display_datetime(item.get('created_at')))}</span></div>"
        for item in (log_payload.get("logs") or [])[:20]
    ) or '<p class="muted">Журнал пока пуст.</p>'

    metric_rows = "".join(
        '<div class="mapping-row"><span>'
        f"<strong>{html_lib.escape(as_text(item.get('operation')))}</strong><small>{html_lib.escape(as_text(item.get('details')))}</small>"
        f"</span><span>{html_lib.escape(as_text(item.get('duration_ms')))} мс</span></div>"
        for item in (metric_payload.get("metrics") or [])[:20]
    ) or '<p class="muted">Метрики пока пусты.</p>'

    metric_summary = metric_payload.get("summary") or {}
    time_summary_rows = (
        f'<div class="bar-label"><span>Operations</span><strong>{int(metric_summary.get("operations") or 0)}</strong></div>'
        f'<div class="bar-label"><span>Records</span><strong>{int(metric_summary.get("metrics") or 0)}</strong></div>'
        f'<div class="bar-label"><span>Average</span><strong>{html_lib.escape(as_text(metric_summary.get("avgMs") or 0))} ms</strong></div>'
        f'<div class="bar-label"><span>Max</span><strong>{html_lib.escape(as_text(metric_summary.get("maxMs") or 0))} ms</strong></div>'
    )

    def metric_detail_value(details: Any, key: str) -> str:
        for part in as_text(details).split(","):
            name, _, value = part.strip().partition("=")
            if name.strip() == key:
                return value.strip()
        return ""

    time_history_rows = "".join(
        "<tr>"
        f"<td>{html_lib.escape((as_text(item.get('created_at')) or '')[:10])}</td>"
        f"<td>{html_lib.escape((as_text(item.get('created_at')) or '')[11:19])}</td>"
        f"<td>{html_lib.escape(as_text(item.get('operation')))}</td>"
        f"<td>{html_lib.escape(metric_detail_value(item.get('details'), 'source') or '-')}</td>"
        f"<td>{html_lib.escape(metric_detail_value(item.get('details'), 'devices') or '-')}</td>"
        f"<td>{html_lib.escape(as_text(item.get('duration_ms')))} ms</td>"
        "</tr>"
        for item in (metric_payload.get("metrics") or [])[:50]
    ) or '<tr><td colspan="6" class="empty-state">Time statistics are empty.</td></tr>'

    summary_labels = {
        "history": "История MAC",
        "movements": "Перемещения",
        "vendorModelHistory": "История vendor/model",
        "snapshots": "Снимки",
        "vendors": "Вендоры",
        "models": "Модели",
        "ipMappings": "IP-правила",
    }
    db_info = database_payload.get("database") or {}
    db_summary = database_payload.get("summary") or {}
    db_size = round((int(db_info.get("sizeBytes") or 0)) / 1024)
    database_rows = (
        f'<div class="bar-label"><span>SQLite file</span><strong>{db_size} KB</strong></div>'
        f'<div class="bar-label"><span>Data folder</span><strong title="{html_lib.escape(as_text(STORAGE.data))}">{html_lib.escape(STORAGE.data.name)}</strong></div>'
        f'<div class="bar-label"><span>Database folder</span><strong title="{html_lib.escape(as_text(STORAGE.databases))}">{html_lib.escape(STORAGE.databases.name)}</strong></div>'
        f'<div class="bar-label"><span>Tables</span><strong>{len(db_info.get("tables") or [])}</strong></div>'
        f'<div class="bar-label"><span>Free pages</span><strong>{int(db_info.get("freePages") or 0)}</strong></div>'
    )
    database_rows += "".join(
        f'<div class="bar-label"><span>{html_lib.escape(summary_labels.get(name, as_text(name)))}</span><strong>{html_lib.escape(as_text(value))}</strong></div>'
        for name, value in db_summary.items()
    )

    legacy_summary = legacy_payload.get("summary") or {}
    legacy_sources = legacy_payload.get("sources") or []
    legacy_rows = (
        f'<div class="bar-label"><span>Legacy rows</span><strong>{int(legacy_summary.get("available") or 0)}</strong></div>'
        f'<div class="bar-label"><span>Ready sources</span><strong>{sum(1 for item in legacy_sources if item.get("exists"))}/{len(legacy_sources)}</strong></div>'
    )
    legacy_rows += "".join(
        f'<div class="bar-label"><span>{html_lib.escape(as_text(item.get("source")))} · {"found" if item.get("exists") else "missing"}</span>'
        f'<strong>{int(item.get("available") or 0)}</strong></div>'
        for item in legacy_sources
    )

    autosaves = autosave_payload.get("autosaves") or []
    autosave_status = "Autosaves: " + "; ".join(
        f"{as_text(item.get('slot'))} · {format_display_datetime(item.get('updatedAt'))}"
        for item in autosaves
    ) if autosaves else "Autosave slots are empty."

    return {
        "ipRowsHtml": ip_rows,
        "taskRowsHtml": task_rows,
        "logRowsHtml": log_rows,
        "metricRowsHtml": metric_rows,
        "timeStatsSummaryHtml": time_summary_rows,
        "timeStatsRowsHtml": time_history_rows,
        "databaseSummaryHtml": database_rows,
        "legacySummaryHtml": legacy_rows,
        "autosaveStatusText": autosave_status,
    }


def services_panel_payload() -> dict[str, Any]:
    with db_connection() as conn:
        ip_rows = conn.execute("SELECT * FROM ip_address_mappings ORDER BY switch_ip").fetchall()
    ip_payload = {"mappings": [dict(row) for row in ip_rows], "statistics": ip_mapping_statistics()}
    task_payload = scheduled_tasks_payload()
    log_payload = app_log_records(limit=20)
    metric_payload = performance_statistics(limit=20)
    database_payload = database_summary()
    autosave_payload = list_autosave_states(50)
    signal_payload = {"signal": signal_status()}
    legacy_payload = legacy_migration_status(dry_run=True)
    return {
        "ip": ip_payload,
        "tasks": task_payload,
        "notifications": {"channels": notification_channels()},
        "logs": log_payload,
        "metrics": metric_payload,
        "database": database_payload,
        "autosaves": autosave_payload,
        "signals": signal_payload,
        "legacy": legacy_payload,
        "html": services_panel_html(ip_payload, task_payload, log_payload, metric_payload, database_payload, autosave_payload, signal_payload, legacy_payload),
    }


def add_task_files(task_id: str, files: list[dict[str, Any]]) -> dict[str, Any]:
    queued = 0
    with db_connection() as conn:
        exists = conn.execute("SELECT 1 FROM scheduled_tasks WHERE id = ?", (task_id,)).fetchone()
        if not exists:
            raise ValueError("Task not found")
        for file_item in prepare_queue_files(files):
            filename = as_text(file_item.get("filename") or file_item.get("name"))
            content = as_text(file_item.get("content") or file_item.get("contentBase64"))
            if not filename or not content:
                continue
            conn.execute(
                "INSERT INTO task_file_queue (id, task_id, filename, content_base64, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
                (str(uuid.uuid4()), task_id, filename, content, utc_now()),
            )
            queued += 1
    return {"queued": queued, "summary": queue_summary(task_queue(task_id))}


def run_task_now(task_id: str) -> dict[str, Any]:
    with db_connection() as conn:
        task = conn.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            raise ValueError("Task not found")
        rows = [dict(row) for row in conn.execute(
            "SELECT * FROM task_file_queue WHERE task_id = ? AND status IN ('pending', 'error') ORDER BY created_at ASC",
            (task_id,),
        ).fetchall()]
        for row in rows:
            conn.execute("UPDATE task_file_queue SET status = 'running', started_at = ?, error = NULL WHERE id = ?", (utc_now(), row["id"]))

    def analyzer(filename: str, content: bytes) -> dict[str, Any]:
        result = analyze_single_file(filename, content)
        raw_devices = result.get("devices", [])
        context = build_enrichment_context(raw_devices)
        devices = [enrich_device(device, context) for device in raw_devices]
        devices = [device for device in devices if device.get("valid")]
        result["devices"] = devices
        if devices:
            save_history(devices, filename)
        return result

    result = run_file_queue(rows, analyzer)
    with db_connection() as conn:
        for item in result["results"]:
            if item["status"] == "done":
                conn.execute(
                    "UPDATE task_file_queue SET status = 'done', result_json = ?, error = NULL, finished_at = ? WHERE id = ?",
                    (json.dumps(item["result"], ensure_ascii=False), utc_now(), item["id"]),
                )
            else:
                conn.execute(
                    "UPDATE task_file_queue SET status = 'error', error = ?, finished_at = ? WHERE id = ?",
                    (item.get("error", ""), utc_now(), item["id"]),
                )
        now = datetime.utcnow()
        next_run = now + timedelta(minutes=max(1, int(task["interval_minutes"] or 1)))
        conn.execute(
            "UPDATE scheduled_tasks SET last_run_at = ?, next_run_at = ? WHERE id = ?",
            (utc_now(), next_run.replace(microsecond=0).isoformat() + "Z", task_id),
        )
    log_action("Scheduled task run", f"id={task_id}, processed={result['processed']}, done={result['done']}, errors={result['errors']}")
    return {**result, "queue": queue_summary(task_queue(task_id))}


def save_quality_report(report: dict[str, Any], source: str = "") -> dict[str, Any]:
    report_id = str(uuid.uuid4())
    created_at = utc_now()
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO data_quality_reports (id, source, score, grade, report_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                report_id,
                as_text(source),
                float(report.get("score", 0) or 0),
                as_text(report.get("grade")) or "D",
                json.dumps(report, ensure_ascii=False),
                created_at,
            ),
        )
    log_action("Data quality report", f"id={report_id}, score={report.get('score')}, grade={report.get('grade')}")
    return {**report, "id": report_id, "createdAt": created_at, "source": as_text(source)}


def quality_reports(limit: int = 20) -> list[dict[str, Any]]:
    safe_limit = max(1, min(100, int(limit or 20)))
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, source, score, grade, report_json, created_at FROM data_quality_reports ORDER BY created_at DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    reports = []
    for row in rows:
        report = json.loads(row["report_json"])
        reports.append({
            **report,
            "id": row["id"],
            "source": row["source"],
            "score": row["score"],
            "grade": row["grade"],
            "createdAt": row["created_at"],
        })
    return reports


def quality_insights_html(panel: dict[str, Any]) -> str:
    issues = panel.get("issueRows") or []
    recommendations = panel.get("recommendationRows") or []
    issue_rows = "".join(
        '<div class="bar-item">'
        f'<div class="bar-label"><span>{html_lib.escape(as_text(issue.get("title")))}</span>'
        f'<strong>{int(issue.get("count") or 0)} · {html_lib.escape(as_text(issue.get("severity")))}</strong></div>'
        '<div class="bar-track">'
        f'<div class="bar-fill" style="width:{int(issue.get("percent") or 0)}%"></div>'
        '</div>'
        f'<small>{html_lib.escape(as_text(issue.get("recommendation")))}</small>'
        '</div>'
        for issue in issues
    ) or '<p class="muted">Backend не нашёл проблем качества.</p>'
    recommendation_rows = (
        '<div class="mapping-row"><span><strong>AI recommendations</strong>'
        f'<small>{" · ".join(html_lib.escape(item) for item in recommendations)}</small></span></div>'
        if recommendations else ""
    )
    return (
        '<div class="mapping-row"><span>'
        f'<strong>{html_lib.escape(as_text(panel.get("headline")) or "Quality score 0 / 100 · D")}</strong>'
        f'<small>{html_lib.escape(as_text(panel.get("summaryText")) or "0 devices · 0 unique MAC · completeness 0%")}</small>'
        '</span></div>'
        f'{issue_rows}{recommendation_rows}'
    )


def quality_reports_html(reports: list[dict[str, Any]]) -> str:
    if not reports:
        return '<p class="muted">Saved quality reports are empty.</p>'
    rows = "".join(
        '<div class="mapping-row"><span>'
        f'<strong>{html_lib.escape(as_text(report.get("grade")) or "D")} · {html_lib.escape(as_text(report.get("score") or 0))}/100</strong>'
        f'<small>{html_lib.escape(as_text(report.get("source")) or "unknown")} · {html_lib.escape(format_display_datetime(report.get("createdAt")))} · issues {len(report.get("issues") or [])}</small>'
        '</span></div>'
        for report in reports
    )
    return (
        '<div class="mapping-row"><span><strong>Saved quality reports</strong>'
        f'<small>{len(reports)} recent SQLite reports</small></span></div>'
        f'{rows}'
    )


def quality_report_panel(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    devices = max(1, int(summary.get("devices") or 0))
    issue_rows = []
    for issue in report.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        count = int(issue.get("count") or 0)
        issue_rows.append({
            "id": issue.get("id") or "",
            "title": issue.get("title") or "",
            "count": count,
            "severity": issue.get("severity") or "",
            "recommendation": issue.get("recommendation") or "",
            "percent": min(100, max(5, round(count / devices * 100))) if count else 0,
        })
    recommendations = [as_text(item) for item in report.get("recommendations") or [] if as_text(item)]
    panel = {
        "report": report,
        "headline": f"Quality score {report.get('score', 0)} / 100 · {report.get('grade') or 'D'}",
        "summaryText": (
            f"{summary.get('devices', 0)} devices · "
            f"{summary.get('uniqueMacs', 0)} unique MAC · "
            f"completeness {summary.get('completeness', 0)}%"
        ),
        "issueRows": issue_rows,
        "recommendationRows": recommendations,
    }
    return {**panel, "insightsHtml": quality_insights_html(panel)}


def quality_panel_payload(devices: list[dict[str, Any]], invalid: list[Any] | None = None, source: str = "", save: bool = True) -> dict[str, Any]:
    if not isinstance(devices, list):
        raise ValueError("devices must be an array")
    invalid_rows = invalid if isinstance(invalid, list) else []
    report = analyze_data_quality(devices, invalid_rows)
    if save:
        report = save_quality_report(report, as_text(source))
    reports = quality_reports(5)
    return {
        **quality_report_panel(report),
        "reports": reports,
        "reportsHtml": quality_reports_html(reports),
        "emptyReportsHtml": quality_reports_html([]),
        "reportsSummary": {"recent": len(reports)},
    }


def single_file_summary_html(summary: dict[str, Any]) -> str:
    cards = [
        ("Строк", summary.get("rows")),
        ("Устройств", summary.get("valid")),
        ("Ошибок", summary.get("invalid")),
        ("Уникальных MAC", summary.get("uniqueMacs")),
        ("С адресом", summary.get("withAddress")),
        ("С помещением", summary.get("withRoom")),
        ("С моделью", summary.get("withModel")),
        ("Коммутаторов", summary.get("withSwitch")),
    ]
    return '<div class="single-metrics">' + "".join(
        f'<div class="metric"><span>{html_lib.escape(label)}</span><strong>{int(value or 0)}</strong></div>'
        for label, value in cards
    ) + "</div>"


def single_file_detected_columns_html(summary: dict[str, Any]) -> str:
    columns = summary.get("detectedColumns") or []
    if not columns:
        return '<p class="muted">Колонки не определены.</p>'
    return "".join(
        '<div class="mapping-row"><span>'
        f'<strong>{html_lib.escape(column_label(item.get("field")))}</strong>'
        f'<small>{html_lib.escape(as_text(item.get("header")))} · {round(float(item.get("confidence") or 0) * 100)}%</small>'
        '</span></div>'
        for item in columns
    )


def single_file_preview_html(headers: list[Any], rows: list[list[Any]], invalid: list[dict[str, Any]]) -> dict[str, str]:
    safe_headers = [as_text(header) for header in headers if as_text(header)] or ["Строка", "Ошибка", "Значение", "Источник"]
    visible_headers = safe_headers[:12]
    head_html = "<tr>" + "".join(f"<th>{html_lib.escape(header)}</th>" for header in visible_headers) + "</tr>"
    preview_rows = rows[:10] if isinstance(rows, list) else []
    invalid_rows = [
        ["Ошибка MAC", f"строка {as_text(item.get('row'))}", item.get("raw") or "", item.get("source") or ""]
        for item in (invalid[:10] if isinstance(invalid, list) else [])
    ]
    all_rows = [*preview_rows, *invalid_rows]
    if all_rows:
        body_html = "".join(
            "<tr>" + "".join(
                f"<td>{html_lib.escape(as_text((row or [])[index] if index < len(row or []) else ''))}</td>"
                for index, _header in enumerate(visible_headers)
            ) + "</tr>"
            for row in all_rows
        )
    else:
        body_html = f'<tr><td class="empty-state" colspan="{len(visible_headers)}">Нет данных.</td></tr>'
    return {
        "previewHeadHtml": head_html,
        "previewBodyHtml": body_html,
        "previewCountText": f"{len(preview_rows)} строк · ошибок {len(invalid) if isinstance(invalid, list) else 0}",
    }


def decorate_single_file_payload(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    preview = result.get("preview") if isinstance(result.get("preview"), dict) else {}
    return {
        **result,
        "summaryHtml": single_file_summary_html(summary),
        "detectedColumnsHtml": single_file_detected_columns_html(summary),
        **single_file_preview_html(
            preview.get("headers") or result.get("headers") or [],
            preview.get("rows") or result.get("rows") or [],
            result.get("invalid") or [],
        ),
    }


def workspace_files_panel_payload(files: list[Any]) -> dict[str, Any]:
    safe_files = [item for item in files if isinstance(item, dict)] if isinstance(files, list) else []
    primary_index = next((index for index, item in enumerate(safe_files) if as_text(item.get("role")) == "primary"), 0)
    normalized_rows: dict[str, list[str]] = {"primary": [], "enrichment": []}
    for index, file_item in enumerate(safe_files):
        role = "primary" if index == primary_index else "enrichment"
        file_item["role"] = role
        file_date = as_text(file_item.get("createdAt")) or as_text(file_item.get("fileDate"))
        date_label = format_display_datetime(file_date) if file_date else "-"
        row_count = file_item.get("rowCount")
        if not isinstance(row_count, int):
            row_count = max(0, len(file_item.get("rows") or []) - 1)
        normalized_rows[role].append(
            f'<div class="file-row" data-file-id="{html_lib.escape(as_text(file_item.get("id")), quote=True)}" data-file-role="{role}"><span>'
            f'<strong>{html_lib.escape(as_text(file_item.get("name")) or "file")}</strong>'
            f'<small>{max(0, row_count)} rows'
            f' · {role}'
            f' · file date: {html_lib.escape(date_label)}</small></span>'
            f'<button data-remove-file="{html_lib.escape(as_text(file_item.get("id")), quote=True)}">Remove</button></div>'
        )

    def group_html(role: str, title: str, empty_text: str) -> str:
        rows = normalized_rows[role]
        return (
            f'<section class="file-group" data-file-group="{role}">'
            f'<div class="file-group-head"><strong>{title}</strong><span>{len(rows)}</span></div>'
            + ("".join(rows) if rows else f'<span class="muted">{empty_text}</span>')
            + "</section>"
        )

    rows_html = group_html("primary", "Основной файл", "Основной файл не выбран") + group_html(
        "enrichment", "Файлы обогащения", "Файлы обогащения не добавлены"
    )
    return {
        "files": safe_files,
        "count": len(safe_files),
        "primaryCount": len(normalized_rows["primary"]),
        "enrichmentCount": len(normalized_rows["enrichment"]),
        "fileRowsHtml": rows_html,
        "emptyFilesHtml": '<span class="muted">Файлы пока не добавлены</span>',
    }


def workspace_mapping_grid_payload(file_item: Any) -> dict[str, Any]:
    if not isinstance(file_item, dict):
        return {
            "mappingGridHtml": '<p class="muted">Добавьте основной файл, чтобы настроить колонки.</p>',
            "customColumnOptionsHtml": '<option value="">Колонка файла</option>',
            "empty": True,
        }
    headers = file_item.get("headers") if isinstance(file_item.get("headers"), list) else []
    mapping = file_item.get("mapping") if isinstance(file_item.get("mapping"), dict) else {}
    display_mode = as_text(file_item.get("mappingDisplayMode")) or "name"

    def header_name(header: Any, index: int) -> str:
        if isinstance(header, dict):
            return as_text(header.get("name") or header.get("title") or index)
        return as_text(header) or f"Колонка {index + 1}"

    def column_letter(index: int) -> str:
        position = int(index) + 1
        letters = ""
        while position > 0:
            position, remainder = divmod(position - 1, 26)
            letters = chr(65 + remainder) + letters
        return letters or str(index + 1)

    def option_label(name: str, index: int) -> str:
        letter = column_letter(index)
        return f"{letter} · {name}" if display_mode == "letter" else name

    header_options = []
    for index, header in enumerate(headers):
        raw_index = header.get("index") if isinstance(header, dict) else index
        try:
            value = int(raw_index)
        except (TypeError, ValueError):
            value = index
        name = header_name(header, index)
        header_options.append({"index": value, "name": name, "label": option_label(name, value)})

    def options_html(selected: Any = "") -> str:
        selected_text = as_text(selected)
        options = ['<option value="">Не использовать</option>']
        for header in header_options:
            value = str(header["index"])
            selected_attr = " selected" if value == selected_text else ""
            options.append(
                f'<option value="{html_lib.escape(value, quote=True)}"{selected_attr}>{html_lib.escape(header["label"])}</option>'
            )
        return "".join(options)

    fields = ("mac", *DEVICE_FIELDS)
    grid_html = "".join(
        f'<label>{html_lib.escape(column_label(field))}<select data-map="{html_lib.escape(field, quote=True)}">'
        f'{options_html(mapping.get(field, ""))}</select></label>'
        for field in fields
    )
    custom_options = '<option value="">Колонка файла</option>' + "".join(
        f'<option value="{html_lib.escape(str(header["index"]), quote=True)}">{html_lib.escape(header["label"])}</option>'
        for header in header_options
    )
    return {
        "mappingGridHtml": grid_html,
        "customColumnOptionsHtml": custom_options,
        "empty": False,
        "headers": header_options,
    }


def workspace_single_mapping_grid_payload(headers: Any) -> dict[str, Any]:
    header_values = headers if isinstance(headers, list) else []
    if not header_values:
        return {
            "singleMappingGridHtml": '<p class="muted">Колонки появятся после выбора файла.</p>',
            "empty": True,
        }

    normalized_headers = []
    for index, header in enumerate(header_values):
        if isinstance(header, dict):
            name = as_text(header.get("name") or header.get("title") or index)
        else:
            name = as_text(header) or f"Колонка {index + 1}"
        normalized_headers.append({"index": index, "name": name})

    options = ['<option value="">Не использовать</option>'] + [
        f'<option value="{item["index"]}">{html_lib.escape(item["name"])}</option>'
        for item in normalized_headers
    ]
    option_html = "".join(options)
    fields = ("mac", *DEVICE_FIELDS)
    grid_html = "".join(
        f'<label>{html_lib.escape(column_label(field))}<select data-single-map="{html_lib.escape(field, quote=True)}">{option_html}</select></label>'
        for field in fields
    )
    return {
        "singleMappingGridHtml": grid_html,
        "headers": normalized_headers,
        "empty": False,
    }


def process_single_file_analysis(
    filename: str,
    content: bytes | None,
    sheet: str = "",
    mapping: dict[str, Any] | None = None,
    created_at: str = "",
    save_history_enabled: bool = True,
    save_snapshot_enabled: bool = True,
    notify: bool = True,
    table: dict[str, Any] | None = None,
    compact_result: bool = False,
    result_page_size: int = 250,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    mapping_override = mapping if isinstance(mapping, dict) else None
    if table is not None:
        result = analyze_single_file_table(filename, table, mapping_override)
    else:
        result = analyze_single_file(
            filename,
            content or b"",
            sheet=as_text(sheet) or None,
            mapping_override=mapping_override,
        )
    valid, invalid = [], list(result["invalid"])
    context = build_enrichment_context(result["devices"])
    for raw in result["devices"]:
        item = enrich_device(raw, context)
        (valid if item["valid"] else invalid).append(item)
    result["devices"] = valid
    result["invalid"] = invalid
    result["summary"] = summarize_single_file(
        filename,
        result.get("headers", []),
        result.get("rows", []),
        result.get("mapping", {}),
        valid,
        invalid,
        result.get("detection", {}),
    )
    if save_history_enabled:
        save_history(valid, filename, created_at)
    if save_snapshot_enabled or compact_result:
        result["snapshot"] = save_statistics_snapshot(
            valid,
            name=f"Single file: {filename}",
            source=filename,
            created_at=created_at,
        )
    if notify:
        try:
            notify_analysis_completed(valid, invalid, filename)
        except Exception as error:  # noqa: BLE001
            log_action("Analysis notification failed", str(error))
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    save_performance_metric("single_file_analyze", duration_ms, f"source={filename}, devices={len(valid)}, invalid={len(invalid)}")
    log_action("Single file analysis", f"source={filename}, devices={len(valid)}, invalid={len(invalid)}, duration_ms={duration_ms}")
    if compact_result:
        page_size = max(25, min(int(result_page_size or 250), 1000))
        raw_rows = result.get("rows") or []
        snapshot = result.get("snapshot") or {}
        result["rowCount"] = len(raw_rows)
        result["rows"] = raw_rows[:100]
        result["rowsComplete"] = False
        result["resultReference"] = {
            "snapshotId": snapshot.get("id", ""),
            "deviceCount": len(valid),
            "invalidCount": len(invalid),
            "pageSize": page_size,
        }
        result["resultSummary"] = result_dataset_summary(valid, invalid)
        result["resultPage"] = filter_result_devices(valid, invalid, {"offset": 0, "limit": page_size})
        result["devices"] = valid[:page_size]
        result["invalid"] = invalid[:page_size]
        result["compactResult"] = True
    result["processedAt"] = utc_now()
    return decorate_single_file_payload(result)


def external_vendor_lookup(mac: str) -> Optional[str]:
    if os.environ.get("MAC_ANALYZER_ENABLE_EXTERNAL_LOOKUP", "").lower() not in {"1", "true", "yes"}:
        return None
    with db_connection() as conn:
        cached = conn.execute("SELECT value, cached_at FROM api_cache WHERE cache_key = ?", ("vendor:" + mac,)).fetchone()
        if cached:
            cached_at = datetime.fromisoformat(cached["cached_at"].replace("Z", ""))
            if cached_at > datetime.utcnow() - timedelta(days=30):
                return cached["value"]
    request = urllib.request.Request(
        "https://api.macvendors.com/" + mac,
        headers={"User-Agent": "MAC-Analyzer-Pro-Web/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status == 200:
                vendor = response.read().decode("utf-8", errors="replace").strip()
                if vendor:
                    with db_connection() as conn:
                        conn.execute(
                            "INSERT INTO api_cache (cache_key, value, cached_at) VALUES (?, ?, ?) "
                            "ON CONFLICT(cache_key) DO UPDATE SET value=excluded.value, cached_at=excluded.cached_at",
                            ("vendor:" + mac, vendor, utc_now()),
                        )
                    return vendor
    except (urllib.error.URLError, TimeoutError):
        return None
    return None


class Scheduler(threading.Thread):
    daemon = True

    def run(self) -> None:
        while True:
            now = datetime.utcnow()
            with db_connection() as conn:
                tasks = conn.execute("SELECT * FROM scheduled_tasks WHERE enabled = 1").fetchall()
            due_tasks = []
            for task in tasks:
                due_at = task["next_run_at"]
                due = not due_at or datetime.fromisoformat(due_at.replace("Z", "")) <= now
                if due:
                    due_tasks.append(dict(task))
            for task in due_tasks:
                try:
                    run_task_now(task["id"])
                except Exception as error:  # noqa: BLE001
                    log_action("Scheduler task failed", f"id={task['id']}, name={task['name']}, error={error}")
            threading.Event().wait(30)


class AppHandler(BaseHTTPRequestHandler):
    server_version = "MACAnalyzerWeb/1.0"

    def end_headers(self) -> None:
        origin = as_text(self.headers.get("Origin"))
        allowed_origins = {
            "null",
            f"http://127.0.0.1:{PORT}",
            f"http://localhost:{PORT}",
        }
        if origin in allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, Authorization, X-Engineering-Token, X-File-Name, X-Sheet-Name, X-Preview-Rows",
            )
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), format % args))

    def json_response(self, data: Any, status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def binary_response(self, payload: bytes, filename: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def error_response(self, message: str, status: int = HTTPStatus.BAD_REQUEST) -> None:
        self.json_response({"error": message}, status)

    def engineering_token(self) -> str:
        authorization = as_text(self.headers.get("Authorization"))
        if authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
        return as_text(self.headers.get("X-Engineering-Token"))

    def require_engineering(self, permission: str) -> bool:
        if validate_engineering_session(self.engineering_token(), permission):
            return True
        self.error_response("Engineering mode is required for this operation", HTTPStatus.FORBIDDEN)
        return False

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 50 * 1024 * 1024:
            raise ValueError("Запрос слишком большой")
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8")) if body else {}

    def import_workspace_table(
        self,
        filename: str,
        content: bytes,
        sheet: str = "",
        compact_result: bool = False,
        preview_rows: int = 100,
    ) -> None:
        table = read_table(filename, content, sheet or None)
        file_token = WORKSPACE_FILE_CACHE.put(filename, table)
        all_rows = table.get("rows") or []
        preview_size = max(25, min(500, int(preview_rows or 100)))
        response_rows = all_rows[:preview_size] if compact_result else all_rows
        row_count = len(all_rows)
        if compact_result:
            table["rows"] = response_rows
            del all_rows
        self.json_response({
            **table,
            "rows": response_rows,
            "fileToken": file_token,
            "rowCount": row_count,
            "previewRowCount": len(response_rows),
            "compactResult": compact_result,
        })

    def serve_static(self, path: str) -> None:
        safe_name = "index.html" if path in {"/", "/index.html"} else path.lstrip("/")
        target = (ROOT / safe_name).resolve()
        if ROOT not in target.parents and target != ROOT:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type + "; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self.serve_static(parsed.path)
            return
        query = parse_qs(parsed.query)
        if parsed.path == "/api/health":
            self.json_response({"status": "ok", "database": str(DATABASE_PATH.name), "databasePath": str(DATABASE_PATH), "dataDirectory": str(STORAGE.data), "time": utc_now()})
        elif parsed.path == "/api/workspace/cache":
            self.json_response({"cache": WORKSPACE_FILE_CACHE.stats()})
        elif parsed.path == "/api/storage/structure":
            self.json_response({"layout": STORAGE.as_dict(), "migration": STORAGE_MIGRATION_REPORT})
        elif parsed.path == "/api/system/diagnostics":
            self.json_response(build_system_diagnostics(ROOT, STORAGE, db_connection))
        elif parsed.path == "/api/logs":
            self.json_response(app_log_records(
                query.get("action", [""])[0],
                query.get("query", [""])[0],
                query.get("limit", ["200"])[0],
            ))
        elif parsed.path == "/api/metrics":
            self.json_response(performance_statistics(query.get("operation", [""])[0], query.get("limit", ["200"])[0]))
        elif parsed.path == "/api/statistics/panel":
            self.json_response(statistics_panel_payload(query.get("source", [""])[0]))
        elif parsed.path == "/api/statistics":
            self.json_response(statistics_summary(query.get("limit", ["100"])[0], query.get("source", [""])[0]))
        elif parsed.path == "/api/statistics/snapshots/export":
            try:
                self.json_response(export_snapshot_history(
                    query.get("query", [""])[0],
                    query.get("source", [""])[0],
                    query.get("from", [""])[0],
                    query.get("to", [""])[0],
                    query.get("format", ["html"])[0],
                    query.get("limit", ["1000"])[0],
                ))
            except ValueError as error:
                self.error_response(str(error))
        elif parsed.path == "/api/statistics/snapshots":
            self.json_response(statistics_snapshot_history(
                query.get("query", [""])[0],
                query.get("source", [""])[0],
                query.get("from", [""])[0],
                query.get("to", [""])[0],
                query.get("limit", ["100"])[0],
            ))
        elif parsed.path == "/api/statistics/performance":
            self.json_response(performance_statistics(query.get("operation", [""])[0], query.get("limit", ["200"])[0]))
        elif parsed.path == "/api/statistics/temporal":
            self.json_response(temporal_statistics(
                query.get("period", ["day"])[0],
                query.get("source", [""])[0],
                query.get("limit", ["365"])[0],
            ))
        elif parsed.path == "/api/dashboard/settings":
            self.json_response({"settings": dashboard_settings()})
        elif parsed.path == "/api/external-enrichment/settings":
            self.json_response({"settings": external_api_settings(), "providers": external_api_provider_options()})
        elif parsed.path == "/api/reference/oui/status":
            with db_connection() as conn:
                self.json_response(reference_status(conn, STORAGE.reference))
        elif parsed.path == "/api/oui/settings":
            self.json_response({"settings": oui_settings()})
        elif parsed.path == "/api/vendor-detector/settings":
            self.json_response({"settings": vendor_detector_settings()})
        elif parsed.path == "/api/history-enrichment/settings":
            self.json_response({"settings": history_enrichment_settings()})
        elif parsed.path == "/api/database/summary":
            self.json_response(database_summary())
        elif parsed.path == "/api/legacy/import/status":
            self.json_response(legacy_migration_status(dry_run=True))
        elif parsed.path == "/api/parity/status":
            self.json_response(build_parity_status(ROOT))
        elif parsed.path == "/api/parity/report":
            self.json_response(build_parity_report(ROOT))
        elif parsed.path == "/api/database/search":
            self.json_response(database_search(query.get("query", [""])[0], query.get("limit", ["100"])[0]))
        elif parsed.path == "/api/database/history/records":
            self.json_response(database_history_records({
                "mac": query.get("mac", [""])[0],
                "source": query.get("source", [""])[0],
                "vendor": query.get("vendor", [""])[0],
                "model": query.get("model", [""])[0],
                "room": query.get("room", [""])[0],
                "dateFrom": query.get("from", [""])[0],
                "dateTo": query.get("to", [""])[0],
            }, query.get("limit", ["1000"])[0]))
        elif parsed.path == "/api/database/device":
            try:
                self.json_response(database_device_or_lookup(query.get("mac", [""])[0]))
            except ValueError as error:
                self.error_response(str(error))
                return
        elif parsed.path == "/api/bootstrap":
            self.json_response(bootstrap_payload())
        elif parsed.path == "/api/mappings/panel":
            self.json_response(mappings_panel_payload())
        elif parsed.path == "/api/mappings/vendors":
            self.json_response({"vendors": mappings("vendors"), "rules": mapping_rules("vendors")})
        elif parsed.path == "/api/mappings/models":
            self.json_response({"models": mappings("models"), "rules": mapping_rules("models")})
        elif parsed.path == "/api/snapshots":
            self.json_response({"snapshots": snapshot_state_items()})
        elif parsed.path.startswith("/api/snapshots/"):
            snapshot_id = parsed.path.rsplit("/", 1)[-1]
            with db_connection() as conn:
                row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
            if not row:
                self.error_response("Снимок не найден", HTTPStatus.NOT_FOUND)
            else:
                self.json_response({**dict(row), "devices": json.loads(row["devices_json"])})
        elif parsed.path == "/api/history/movements/export":
            try:
                self.json_response(export_enhanced_movement_history({
                    "query": query.get("query", [""])[0],
                    "changeType": query.get("type", [""])[0],
                    "field": query.get("field", [""])[0],
                    "dateFrom": query.get("from", [""])[0],
                    "dateTo": query.get("to", [""])[0],
                }, query.get("format", ["xlsx"])[0]))
            except ValueError as error:
                self.error_response(str(error))
        elif parsed.path == "/api/history/movements/columns":
            self.json_response({"settings": enhanced_history_column_settings()})
        elif parsed.path == "/api/history/movements":
            self.json_response(enhanced_movement_history({
                "query": query.get("query", [""])[0],
                "changeType": query.get("type", [""])[0],
                "field": query.get("field", [""])[0],
                "dateFrom": query.get("from", [""])[0],
                "dateTo": query.get("to", [""])[0],
            }, query.get("limit", ["5000"])[0]))
        elif parsed.path == "/api/history":
            mac = normalize_mac(query.get("mac", [""])[0])
            if not mac:
                self.error_response("Передайте корректный параметр mac")
                return
            self.json_response(history_timeline(mac, query.get("limit", ["500"])[0]))
        elif parsed.path == "/api/history/panel":
            self.json_response(history_panel_payload(
                query_text=query.get("query", [""])[0],
                date_from=query.get("from", [""])[0],
                date_to=query.get("to", [""])[0],
                limit=query.get("limit", ["500"])[0],
            ))
        elif parsed.path == "/api/history/search":
            self.json_response(search_history_records(
                query_text=query.get("query", [""])[0],
                date_from=query.get("from", [""])[0],
                date_to=query.get("to", [""])[0],
                limit=query.get("limit", ["500"])[0],
            ))
        elif parsed.path == "/api/history/statistics":
            self.json_response(history_statistics(
                query_text=query.get("query", [""])[0],
                date_from=query.get("from", [""])[0],
                date_to=query.get("to", [""])[0],
                limit=query.get("limit", ["20"])[0],
            ))
        elif parsed.path == "/api/vendor-model-history":
            self.json_response(vendor_model_history(
                query_text=query.get("query", [""])[0],
                limit=query.get("limit", ["500"])[0],
                date_from=query.get("from", [""])[0],
                date_to=query.get("to", [""])[0],
            ))
        elif parsed.path == "/api/vendor-model-history/statistics":
            self.json_response(vendor_model_statistics(
                query_text=query.get("query", [""])[0],
                date_from=query.get("from", [""])[0],
                date_to=query.get("to", [""])[0],
                limit=query.get("limit", ["20"])[0],
            ))
        elif parsed.path == "/api/vendor-model-history/uploads":
            self.json_response(vendor_model_upload_history(
                query_text=query.get("query", [""])[0],
                date_from=query.get("from", [""])[0],
                date_to=query.get("to", [""])[0],
                limit=query.get("limit", ["100"])[0],
            ))
        elif parsed.path == "/api/services/panel":
            self.json_response(services_panel_payload())
        elif parsed.path == "/api/tasks":
            self.json_response(scheduled_tasks_payload())
        elif parsed.path == "/api/tasks/queue":
            self.json_response({"queue": task_queue(query.get("taskId", [""])[0])})
        elif parsed.path == "/api/quality/reports":
            reports = quality_reports(int(query.get("limit", ["20"])[0] or 20))
            self.json_response({"reports": reports, "reportsHtml": quality_reports_html(reports), "emptyReportsHtml": quality_reports_html([])})
        elif parsed.path == "/api/api-cache":
            self.json_response({"cache": api_cache_summary(int(query.get("limit", ["50"])[0] or 50))})
        elif parsed.path == "/api/ip-mappings":
            with db_connection() as conn:
                rows = conn.execute("SELECT * FROM ip_address_mappings ORDER BY switch_ip").fetchall()
            self.json_response({"mappings": [dict(row) for row in rows], "statistics": ip_mapping_statistics()})
        elif parsed.path == "/api/ip-mappings/statistics":
            self.json_response(ip_mapping_statistics())
        elif parsed.path == "/api/ip-mappings/export":
            self.json_response({"filename": "ip-address-mappings.csv", "content": export_ip_mappings_csv()})
        elif parsed.path == "/api/export/formats":
            self.json_response(supported_export_formats())
        elif parsed.path == "/api/enrichment/jobs":
            jobs = sorted(ENRICHMENT_JOBS.values(), key=lambda item: item.get("updatedAt", ""), reverse=True)
            self.json_response({"jobs": jobs[:50], "summary": {"jobs": len(jobs), "running": sum(1 for item in jobs if item.get("status") == "running")}})
        elif parsed.path.startswith("/api/enrichment/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = enrichment_job_status(job_id)
            if not job:
                self.error_response("enrichment job not found", HTTPStatus.NOT_FOUND)
                return
            self.json_response({"job": job})
        elif parsed.path == "/api/columns/preferences":
            self.json_response(list_column_preferences())
        elif parsed.path == "/api/columns/preferences/results/render":
            preferences = load_column_preferences("results")
            self.json_response(column_preferences_panel_payload(preferences))
        elif parsed.path.startswith("/api/columns/preferences/"):
            view_name = parsed.path.rsplit("/", 1)[-1]
            preferences = load_column_preferences(view_name)
            self.json_response(column_preferences_panel_payload(preferences))
        elif parsed.path.startswith("/api/columns/"):
            view_name = parsed.path.rsplit("/", 1)[-1]
            preferences = load_column_preferences(view_name)
            self.json_response({"columns": preferences["visible"], "preferences": preferences})
        elif parsed.path == "/api/notifications":
            self.json_response({"channels": notification_channels()})
        elif parsed.path == "/api/settings":
            keys = []
            for raw_value in query.get("key", []):
                keys.extend([item.strip() for item in raw_value.split(",") if item.strip()])
            self.json_response(load_app_settings(keys or None))
        elif parsed.path == "/api/theme":
            self.json_response(theme_settings())
        elif parsed.path == "/api/signals/status":
            self.json_response({"signal": signal_status()})
        elif parsed.path == "/api/engineering/session":
            session = validate_engineering_session(self.engineering_token())
            self.json_response({"active": bool(session), "session": session})
        elif parsed.path == "/api/autosaves":
            self.json_response(list_autosave_states(query.get("limit", ["50"])[0]))
        elif parsed.path == "/api/autosave":
            compact = as_text(query.get("compact", [""])[0]).lower() in {"1", "true", "yes"}
            state = load_autosave_state(query.get("slot", ["main"])[0], hydrate=not compact)
            self.json_response({"autosave": state})
        elif parsed.path == "/api/lookup":
            mac = normalize_mac(query.get("mac", [""])[0])
            if not mac:
                self.error_response("Передайте корректный параметр mac")
                return
            device = database_device_lookup(mac) or enrich_device({"mac": mac})
            if device["vendor"] == "Unknown":
                external = external_vendor_lookup(mac)
                if external:
                    device["vendor"] = external
                    device["vendorSource"] = "external_api"
            self.json_response({"device": device})
        else:
            self.error_response("Неизвестный API-метод", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/reference/oui/import":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0:
                    raise ValueError("Файл справочника пуст")
                if length > 64 * 1024 * 1024:
                    self.error_response("Справочник превышает ограничение 64 МБ", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                    return
                filename = Path(unquote(as_text(self.headers.get("X-File-Name"))) or "oui.txt").name
                extension = Path(filename).suffix.lower()
                if extension not in {".txt", ".csv"}:
                    raise ValueError("Поддерживаются справочники OUI в формате TXT или CSV")
                content = self.rfile.read(length)
                with db_connection() as conn:
                    result = import_oui_reference(conn, content, filename)
                    signature = f"{filename}:{len(content)}:{result['sha256']}"
                    conn.execute(
                        "INSERT INTO app_settings (key, value, updated_at) VALUES ('oui_reference_signature', ?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                        (signature, utc_now()),
                    )
                destination = STORAGE.reference / ("oui.csv" if extension == ".csv" else "oui.txt")
                temporary = destination.with_suffix(destination.suffix + ".tmp")
                temporary.write_bytes(content)
                temporary.replace(destination)
                with db_connection() as conn:
                    status = reference_status(conn, STORAGE.reference)
                self.json_response({"ok": True, "imported": result, "status": status})
            except (OSError, ValueError, UnicodeError, csv.Error) as error:
                self.error_response("Не удалось импортировать OUI-справочник: " + str(error))
            return
        if parsed.path == "/api/files/import-binary":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0:
                    raise ValueError("Файл пуст")
                if length > 512 * 1024 * 1024:
                    self.error_response("Файл превышает ограничение 512 МБ", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                    return
                filename = unquote(as_text(self.headers.get("X-File-Name"))) or "import.xlsx"
                sheet = unquote(as_text(self.headers.get("X-Sheet-Name")))
                preview_rows = int(self.headers.get("X-Preview-Rows", "100") or 100)
                self.import_workspace_table(filename, self.rfile.read(length), sheet, True, preview_rows)
            except (ValueError, UnicodeError, csv.Error, json.JSONDecodeError, TypeError, binascii.Error) as error:
                self.error_response("Не удалось прочитать файл: " + str(error))
            return
        try:
            payload = self.read_json()
        except (ValueError, json.JSONDecodeError) as error:
            self.error_response("Некорректный JSON: " + str(error))
            return
        try:
            if parsed.path == "/api/enrichment/progress":
                self.json_response({
                    "progressHtml": enrichment_progress_html(payload.get("progress"), as_text(payload.get("status")) or "running")
                })
            elif parsed.path == "/api/workspace/cache/discard":
                tokens = payload.get("tokens", [])
                if not isinstance(tokens, list) or len(tokens) > 20:
                    self.error_response("tokens must be an array up to 20 items")
                    return
                discarded = 0
                for token in tokens:
                    normalized_token = as_text(token)
                    if not normalized_token:
                        continue
                    WORKSPACE_FILE_CACHE.discard(normalized_token)
                    discarded += 1
                self.json_response({"ok": True, "discarded": discarded, "cache": WORKSPACE_FILE_CACHE.stats()})
            elif parsed.path == "/api/enrichment/run":
                started_at = time.perf_counter()
                files = payload.get("files", [])
                if not isinstance(files, list) or len(files) > 10:
                    self.error_response("files must be an array up to 10 items")
                    return
                try:
                    files = prepare_workspace_files(files, WORKSPACE_FILE_CACHE)
                except WorkspaceCacheMiss:
                    self.json_response(
                        {
                            "error": "Imported file cache expired; retry with file rows",
                            "code": "WORKSPACE_CACHE_MISS",
                        },
                        HTTPStatus.CONFLICT,
                    )
                    return
                refreshed_file_tokens: list[dict[str, str]] = []
                if payload.get("refreshFileCache"):
                    for file_info in files:
                        rows = file_info.get("rows") or []
                        if not rows or not isinstance(rows[0], list):
                            continue
                        token = WORKSPACE_FILE_CACHE.put(
                            as_text(file_info.get("name")),
                            {"headers": rows[0], "rows": rows[1:], "sheet": file_info.get("sheet", "")},
                        )
                        file_info["fileToken"] = token
                        refreshed_file_tokens.append({"id": as_text(file_info.get("id")), "fileToken": token})
                strategy = as_text(payload.get("strategy")) or "primary"
                fields = normalize_enrichment_fields(payload.get("fields", {}))
                source = as_text(payload.get("source")) or (as_text(files[0].get("name")) if files else "")
                source_created_at = as_text(payload.get("createdAt")) or as_text(files[0].get("createdAt") if files and isinstance(files[0], dict) else "")
                job = start_enrichment_job(as_text(payload.get("jobId")), source, strategy)
                merged = enrich_workspace_files(
                    files,
                    WORKSPACE_FILE_CACHE,
                    strategy,
                    progress_callback=lambda progress: update_enrichment_job(job["id"], progress),
                    is_cancelled=lambda: bool(ENRICHMENT_JOBS.get(job["id"], {}).get("cancelRequested")),
                )
                valid, invalid = [], list(merged["invalid"])
                if merged["progress"].get("status") == "cancelled":
                    update_enrichment_job(job["id"], merged["progress"], "cancelled")
                    self.json_response({
                        "jobId": job["id"],
                        "status": "cancelled",
                        "devices": [],
                        "invalid": invalid,
                        "progress": merged["progress"],
                        "progressHtml": enrichment_progress_html(merged["progress"], "cancelled"),
                        "processedAt": utc_now(),
                    })
                    return
                context = build_enrichment_context(merged["devices"])
                for raw in merged["devices"]:
                    item = enrich_device(raw, context)
                    (valid if item["valid"] else invalid).append(item)
                for field in ["vendor", "model", "ip", "address", "room", "switchIp", "switchPort"]:
                    if fields.get(field, True) is False:
                        for item in valid:
                            item[field] = "Не определено" if field == "vendor" else ""
                if payload.get("saveHistory", True):
                    save_history(valid, source, source_created_at)
                if payload.get("notify", True):
                    try:
                        notify_analysis_completed(valid, invalid, source)
                    except Exception as error:  # noqa: BLE001
                        log_action("Analysis notification failed", str(error))
                snapshot = None
                if payload.get("saveSnapshot", True):
                    snapshot = save_statistics_snapshot(
                        valid,
                        as_text(payload.get("snapshotName")) or f"Анализ: {source}",
                        source,
                        created_at=source_created_at,
                    )
                compact_result = payload.get("compactResult") is True
                if compact_result and snapshot is None:
                    snapshot = save_statistics_snapshot(
                        valid,
                        as_text(payload.get("snapshotName")) or f"Анализ: {source}",
                        source,
                        created_at=source_created_at,
                    )
                update_enrichment_job(job["id"], merged["progress"], "completed")
                progress_payload = {**merged["progress"], "fields": enrichment_field_summary(fields)}
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                save_performance_metric("enrichment", duration_ms, f"source={source}, devices={len(valid)}, invalid={len(invalid)}")
                try:
                    result_page_size = max(25, min(int(payload.get("resultPageSize") or 250), 1000))
                except (TypeError, ValueError):
                    result_page_size = 250
                result_page = filter_result_devices(
                    valid,
                    invalid,
                    {"offset": 0, "limit": result_page_size},
                    payload.get("columns"),
                    payload.get("labels"),
                ) if compact_result else None
                self.json_response({
                    "jobId": job["id"],
                    "status": "completed",
                    "devices": valid if not compact_result else valid[:result_page_size],
                    "invalid": invalid if not compact_result else invalid[:result_page_size],
                    "compactResult": compact_result,
                    "resultReference": {
                        "snapshotId": snapshot.get("id") if snapshot else "",
                        "deviceCount": len(valid),
                        "invalidCount": len(invalid),
                        "pageSize": result_page_size,
                    } if compact_result else None,
                    "resultSummary": result_dataset_summary(valid, invalid) if compact_result else None,
                    "resultPage": result_page,
                    "progress": progress_payload,
                    "progressHtml": enrichment_progress_html(progress_payload, "completed"),
                    "performance": {"durationMs": duration_ms, "context": context.get("statistics", {})},
                    "snapshot": snapshot,
                    "fileTokens": refreshed_file_tokens,
                    "processedAt": utc_now(),
                })
            elif parsed.path == "/api/analyze":
                started_at = time.perf_counter()
                raw_devices = payload.get("devices", [])
                if not isinstance(raw_devices, list) or len(raw_devices) > 100000:
                    self.error_response("devices должен быть массивом до 100000 записей")
                    return
                valid, invalid = [], []
                context = build_enrichment_context([raw for raw in raw_devices if isinstance(raw, dict)])
                for raw in raw_devices:
                    item = enrich_device(raw if isinstance(raw, dict) else {}, context)
                    (valid if item["valid"] else invalid).append(item)
                source = as_text(payload.get("source"))
                source_created_at = as_text(payload.get("createdAt"))
                if payload.get("saveHistory", True):
                    save_history(valid, source, source_created_at)
                if payload.get("notify", True):
                    try:
                        notify_analysis_completed(valid, invalid, source)
                    except Exception as error:  # noqa: BLE001
                        log_action("Analysis notification failed", str(error))
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                save_performance_metric("analyze", duration_ms, f"source={source}, devices={len(valid)}, invalid={len(invalid)}")
                log_action("Анализ завершён", f"source={source}, devices={len(valid)}, duration_ms={duration_ms}")
                self.json_response({"devices": valid, "invalid": invalid, "processedAt": utc_now()})
            elif parsed.path == "/api/workspace/files":
                self.json_response(workspace_files_panel_payload(payload.get("files", [])))
            elif parsed.path == "/api/workspace/mapping-grid":
                self.json_response(workspace_mapping_grid_payload(payload.get("file")))
            elif parsed.path == "/api/workspace/single-mapping-grid":
                self.json_response(workspace_single_mapping_grid_payload(payload.get("headers", [])))
            elif parsed.path == "/api/single-file/preview":
                self.json_response(single_file_preview_html(
                    payload.get("headers", []),
                    payload.get("rows", []),
                    payload.get("invalid", []),
                ))
            elif parsed.path == "/api/xlsx/import":
                try:
                    content = base64.b64decode(payload.get("content", ""), validate=True)
                    self.json_response(read_xlsx(content, payload.get("sheet")))
                except (ValueError, TypeError, binascii.Error) as error:
                    self.error_response("Не удалось прочитать XLSX: " + str(error))
            elif parsed.path == "/api/files/import":
                try:
                    content = base64.b64decode(payload.get("content", ""), validate=True)
                    filename = as_text(payload.get("filename"))
                    self.import_workspace_table(
                        filename,
                        content,
                        as_text(payload.get("sheet")),
                        payload.get("compactResult") is True,
                        int(payload.get("previewRows") or 100),
                    )
                except (ValueError, UnicodeError, csv.Error, json.JSONDecodeError, TypeError, binascii.Error) as error:
                    self.error_response("Не удалось прочитать файл: " + str(error))
            elif parsed.path == "/api/single-file/analyze":
                filename = as_text(payload.get("filename")) or "single-file"
                file_token = as_text(payload.get("fileToken"))
                cached_table = WORKSPACE_FILE_CACHE.get(file_token) if file_token else None
                content = None if cached_table is not None else base64.b64decode(payload.get("content", ""), validate=True)
                self.json_response(process_single_file_analysis(
                    filename,
                    content,
                    sheet=as_text(payload.get("sheet")) or None,
                    mapping=payload.get("mapping") if isinstance(payload.get("mapping"), dict) else None,
                    created_at=as_text(payload.get("createdAt")),
                    save_history_enabled=payload.get("saveHistory", True),
                    save_snapshot_enabled=payload.get("saveSnapshot", True),
                    notify=payload.get("notify", True),
                    table=cached_table,
                    compact_result=payload.get("compactResult") is True,
                    result_page_size=int(payload.get("resultPageSize") or 250),
                ))
            elif parsed.path == "/api/export":
                devices = resolve_payload_devices(payload)
                columns = payload.get("columns", [])
                export_format = as_text(payload.get("format"))
                if not isinstance(devices, list) or not isinstance(columns, list):
                    self.error_response("devices and columns must be arrays")
                    return
                try:
                    oui_settings = payload.get("ouiSettings") if isinstance(payload.get("ouiSettings"), dict) else {}
                    self.json_response(export_managed(devices, columns, export_format, as_text(payload.get("filenamePrefix")) or "mac-analysis", oui_settings))
                except ValueError as error:
                    self.error_response(str(error))
            elif parsed.path == "/api/xlsx/export":
                devices = payload.get("devices", [])
                columns = payload.get("columns", [])
                if not isinstance(devices, list) or not isinstance(columns, list):
                    self.error_response("Некорректные данные XLSX")
                    return
                result = export_managed(devices, columns, "xlsx")
                self.binary_response(base64.b64decode(result["content"]), result["filename"])
            elif parsed.path == "/api/pdf/export":
                devices = payload.get("devices", [])
                columns = payload.get("columns", [])
                result = export_managed(devices, columns, "pdf")
                pdf = base64.b64decode(result["content"])
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f'attachment; filename="{result["filename"]}"')
                self.send_header("Content-Length", str(len(pdf)))
                self.end_headers()
                self.wfile.write(pdf)
            elif parsed.path == "/api/snapshots/options":
                snapshots = payload.get("snapshots", [])
                if not isinstance(snapshots, list):
                    snapshots = []
                self.json_response(snapshot_select_payload(snapshots))
            elif parsed.path == "/api/snapshots/open":
                snapshots = payload.get("snapshots", [])
                if not isinstance(snapshots, list):
                    snapshots = []
                try:
                    if payload.get("compactResult") is True:
                        self.json_response(open_compact_snapshot_payload(
                            as_text(payload.get("id")),
                            snapshots,
                            payload.get("resultPageSize"),
                        ))
                    else:
                        self.json_response(open_snapshot_payload(as_text(payload.get("id")), snapshots))
                except LookupError as error:
                    self.error_response(str(error), HTTPStatus.NOT_FOUND)
                    return
                except ValueError as error:
                    self.error_response(str(error))
                    return
            elif parsed.path == "/api/snapshots":
                devices = resolve_payload_devices(payload)
                if not isinstance(devices, list):
                    self.error_response("devices должен быть массивом")
                    return
                snapshot = save_statistics_snapshot(
                    devices,
                    as_text(payload.get("name")) or "Snapshot",
                    as_text(payload.get("source")),
                    as_text(payload.get("id")),
                    as_text(payload.get("createdAt")),
                )
                self.json_response(snapshot, HTTPStatus.CREATED)
            elif parsed.path == "/api/database/snapshots/delete":
                if not self.require_engineering("delete:snapshots"):
                    return
                ids = payload.get("ids", [])
                if not isinstance(ids, list):
                    self.error_response("ids must be an array")
                    return
                deleted = delete_snapshots(as_text(payload.get("source")), as_text(payload.get("before")), ids)
                self.json_response({"ok": True, "deleted": deleted})
            elif parsed.path == "/api/database/history/delete":
                if not self.require_engineering("delete:history"):
                    return
                ids = payload.get("ids", [])
                filters = payload.get("filters", {})
                if not isinstance(ids, list) or not isinstance(filters, dict):
                    self.error_response("ids must be an array and filters must be an object")
                    return
                deleted = delete_database_history_records(ids, filters)
                self.json_response({"ok": True, "deleted": deleted})
            elif parsed.path == "/api/history/movements/delete":
                if not self.require_engineering("delete:history"):
                    return
                ids = payload.get("ids", [])
                if not isinstance(ids, list):
                    self.error_response("ids must be an array")
                    return
                self.json_response({"ok": True, "deleted": delete_enhanced_movement_history(ids)})
            elif parsed.path == "/api/history/movements/columns":
                settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else payload
                self.json_response({"ok": True, "settings": save_enhanced_history_column_settings(settings)})
            elif parsed.path == "/api/database/maintenance":
                if not self.require_engineering("delete:snapshots"):
                    return
                self.json_response(database_maintenance(
                    vacuum=bool(payload.get("vacuum")),
                    optimize=payload.get("optimize", True) is not False,
                    integrity=payload.get("integrity", True) is not False,
                ))
            elif parsed.path == "/api/legacy/import":
                if not self.require_engineering("write:migration"):
                    return
                self.json_response(legacy_migration_status(dry_run=bool(payload.get("dryRun"))))
            elif parsed.path in {"/api/mappings/vendors", "/api/mappings/models"}:
                is_vendor = parsed.path.endswith("vendors")
                mapping_key = re.sub(r"[^0-9A-F]", "", as_text(payload.get("key")).upper())
                value = as_text(payload.get("value"))
                minimum = 6
                if len(mapping_key) < minimum or not value:
                    self.error_response("Укажите корректный префикс и значение")
                    return
                table, field, value_field = ("vendor_mappings", "oui", "vendor") if is_vendor else ("model_mappings", "prefix", "model")
                with db_connection() as conn:
                    conn.execute(
                        f"INSERT INTO {table} ({field}, {value_field}, source, updated_at) VALUES (?, ?, 'custom', ?) "
                        f"ON CONFLICT({field}) DO UPDATE SET {value_field}=excluded.{value_field}, source='custom', updated_at=excluded.updated_at",
                        (mapping_key, value, utc_now()),
                    )
                self.json_response({"ok": True})
            elif parsed.path == "/api/vendor-model-history/learn":
                result = learn_vendor_model_mappings(int(payload.get("minCount", 2) or 2), as_text(payload.get("source")))
                self.json_response({"ok": True, "learned": result})
            elif parsed.path == "/api/tasks":
                name = as_text(payload.get("name"))
                interval = int(payload.get("intervalMinutes", 0))
                if not name or interval < 1:
                    self.error_response("Укажите имя и интервал не менее минуты")
                    return
                task_id = str(uuid.uuid4())
                with db_connection() as conn:
                    conn.execute(
                        "INSERT INTO scheduled_tasks (id, name, interval_minutes, enabled, payload_json, next_run_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (task_id, name, interval, int(bool(payload.get("enabled"))), json.dumps(payload.get("payload", {})), utc_now(), utc_now()),
                    )
                self.json_response({"id": task_id}, HTTPStatus.CREATED)
            elif parsed.path == "/api/tasks/queue":
                task_id = as_text(payload.get("taskId"))
                files = payload.get("files", [])
                if not task_id or not isinstance(files, list):
                    self.error_response("taskId and files array are required")
                    return
                try:
                    files = resolve_workspace_files(files, WORKSPACE_FILE_CACHE)
                except WorkspaceCacheMiss:
                    self.json_response({"error": "Imported file cache expired; select the files again", "code": "WORKSPACE_CACHE_MISS"}, HTTPStatus.CONFLICT)
                    return
                self.json_response({"ok": True, **add_task_files(task_id, files)})
            elif parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/run"):
                task_id = parsed.path.split("/")[-2]
                self.json_response({"ok": True, **run_task_now(task_id)})
            elif parsed.path == "/api/ip-mappings/import":
                if as_text(payload.get("contentBase64")):
                    content = base64.b64decode(payload.get("contentBase64", ""), validate=True).decode("utf-8-sig")
                else:
                    content = as_text(payload.get("content"))
                result = import_ip_mappings(as_text(payload.get("filename")), content)
                self.json_response({"ok": True, **result})
            elif parsed.path == "/api/ip-mappings/autodetect":
                devices = resolve_payload_devices(payload)
                if not isinstance(devices, list):
                    self.error_response("devices РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РјР°СЃСЃРёРІРѕРј")
                    return
                self.json_response({"ok": True, **autodetect_ip_mappings(devices)})
            elif parsed.path == "/api/ip-mappings/apply":
                devices = resolve_payload_devices(payload)
                if not isinstance(devices, list):
                    self.error_response("devices must be an array")
                    return
                result = apply_ip_mappings_to_devices(devices)
                if payload.get("compactResult") is True:
                    full_devices = result["devices"]
                    result_summary = result_dataset_summary(full_devices, [])
                    snapshot = save_statistics_snapshot(
                        full_devices,
                        "IP-маппинг",
                        "ip-mapping-apply",
                        created_at=as_text(payload.get("createdAt")) or utc_now(),
                    )
                    try:
                        page_size = max(25, min(int(payload.get("resultPageSize") or 250), 1000))
                    except (TypeError, ValueError):
                        page_size = 250
                    result["devices"] = full_devices[:page_size]
                    result["snapshot"] = snapshot
                    result["compactResult"] = True
                    result["resultReference"] = {
                        "snapshotId": snapshot["id"],
                        "deviceCount": snapshot["deviceCount"],
                        "invalidCount": 0,
                        "pageSize": page_size,
                    }
                    result["resultSummary"] = result_summary
                self.json_response({"ok": True, **result})
            elif parsed.path == "/api/ip-mappings":
                switch_ip, address = as_text(payload.get("switchIp")), as_text(payload.get("address"))
                if not switch_ip or not address:
                    self.error_response("Укажите IP коммутатора и физический адрес")
                    return
                with db_connection() as conn:
                    conn.execute(
                        "INSERT INTO ip_address_mappings (switch_ip, physical_address, source, updated_at) VALUES (?, ?, 'manual', ?) "
                        "ON CONFLICT(switch_ip) DO UPDATE SET physical_address=excluded.physical_address, source='manual', updated_at=excluded.updated_at",
                        (switch_ip, address, utc_now()),
                    )
                self.json_response({"ok": True})
            elif parsed.path == "/api/columns/detect":
                headers = payload.get("headers", [])
                rows = payload.get("rows", [])
                if not isinstance(headers, list) or not isinstance(rows, list):
                    self.error_response("headers and rows must be arrays")
                    return
                ai = bool(payload.get("ai") or payload.get("mode") == "ai")
                result = detect_columns(headers, rows, ai=ai)
                self.json_response({
                    **result,
                    "detectorHtml": column_detection_html(result, headers),
                    "review": column_conflict_review_payload(headers, rows, result),
                })
            elif parsed.path == "/api/mapping/summary":
                headers = payload.get("headers", [])
                mapping = payload.get("mapping", {})
                if not isinstance(headers, list) or not isinstance(mapping, dict):
                    self.error_response("headers must be an array and mapping must be an object")
                    return
                self.json_response(mapping_summary(headers, mapping, payload.get("fields", {})))
            elif parsed.path == "/api/results/header":
                self.json_response(result_header_payload(payload.get("columns"), payload.get("labels")))
            elif parsed.path == "/api/results/filter":
                devices = resolve_payload_devices(payload)
                invalid = payload.get("invalid", [])
                filters = payload.get("filters", {})
                if not isinstance(devices, list):
                    self.error_response("devices must be an array")
                    return
                if not isinstance(invalid, list):
                    invalid = []
                if not isinstance(filters, dict):
                    filters = {}
                self.json_response(filter_result_devices(devices, invalid, filters, payload.get("columns"), payload.get("labels")))
            elif parsed.path == "/api/oui/settings":
                self.json_response({"ok": True, "settings": save_oui_settings(payload.get("settings", payload))})
            elif parsed.path == "/api/vendor-detector/settings":
                self.json_response({"ok": True, "settings": save_vendor_detector_settings(payload.get("settings", payload))})
            elif parsed.path == "/api/history-enrichment/settings":
                self.json_response({"ok": True, "settings": save_history_enrichment_settings(payload.get("settings", payload))})
            elif parsed.path == "/api/oui/format":
                devices = payload.get("devices", [])
                if not isinstance(devices, list):
                    self.error_response("devices must be an array")
                    return
                self.json_response({
                    "items": format_oui_for_devices(
                        devices,
                        int(payload.get("length", 3) or 3),
                        as_text(payload.get("style")) or "plain",
                    )
                })
            elif parsed.path == "/api/compare/snapshots":
                snapshots = hydrate_snapshot_devices(payload.get("snapshots", []))
                fields = payload.get("fields", [])
                if not isinstance(fields, list):
                    fields = []
                try:
                    self.json_response(compare_snapshots(
                        snapshots,
                        payload.get("baselineId"),
                        payload.get("currentId"),
                        [as_text(field) for field in fields],
                        as_text(payload.get("exportFormat")),
                    ))
                except ValueError as error:
                    self.error_response(str(error))
                    return
            elif parsed.path == "/api/compare/snapshots/many":
                snapshots = hydrate_snapshot_devices(payload.get("snapshots", []))
                comparison_ids = payload.get("comparisonIds", [])
                fields = payload.get("fields", [])
                if not isinstance(fields, list):
                    fields = []
                try:
                    self.json_response(compare_many_snapshots(
                        snapshots,
                        payload.get("baselineId"),
                        comparison_ids,
                        [as_text(field) for field in fields],
                        as_text(payload.get("exportFormat")),
                    ))
                except ValueError as error:
                    self.error_response(str(error))
                    return
            elif parsed.path == "/api/compare":
                baseline_devices = payload.get("baselineDevices", [])
                current_devices = payload.get("currentDevices", [])
                fields = payload.get("fields", [])
                if not isinstance(baseline_devices, list) or not isinstance(current_devices, list):
                    self.error_response("baselineDevices and currentDevices must be arrays")
                    return
                if not isinstance(fields, list):
                    fields = []
                result = compare_devices(baseline_devices, current_devices, [as_text(field) for field in fields])
                export_format = as_text(payload.get("exportFormat"))
                if export_format:
                    result["export"] = export_comparison(result["changes"], export_format)
                self.json_response(result)
            elif parsed.path == "/api/compare/many":
                baseline_devices = payload.get("baselineDevices", [])
                comparisons = payload.get("comparisons", [])
                fields = payload.get("fields", [])
                if not isinstance(baseline_devices, list) or not isinstance(comparisons, list):
                    self.error_response("baselineDevices and comparisons must be arrays")
                    return
                if not isinstance(fields, list):
                    fields = []
                result = compare_many_devices(baseline_devices, comparisons, [as_text(field) for field in fields])
                export_format = as_text(payload.get("exportFormat"))
                if export_format:
                    result["export"] = export_comparison(result["changes"], export_format)
                self.json_response(result)
            elif parsed.path == "/api/analytics/panel":
                try:
                    self.json_response(analytics_panel_payload(resolve_payload_devices(payload), payload.get("snapshots", [])))
                except ValueError as error:
                    self.error_response(str(error))
            elif parsed.path == "/api/analytics/report":
                try:
                    report = build_analytics_report(resolve_payload_devices(payload))
                except ValueError as error:
                    self.error_response(str(error))
                    return
                export_format = as_text(payload.get("exportFormat")).lower()
                if export_format == "txt":
                    report["export"] = export_analytics_report_txt(report)
                elif export_format:
                    self.error_response("Unsupported analytics report export format")
                    return
                self.json_response(report)
            elif parsed.path == "/api/charts":
                devices = resolve_payload_devices(payload)
                snapshots = payload.get("snapshots", [])
                if not isinstance(devices, list) or not isinstance(snapshots, list):
                    self.error_response("devices and snapshots must be arrays")
                    return
                result = build_chart_payload(devices, snapshots)
                export_format = as_text(payload.get("exportFormat")).lower()
                if export_format == "svg":
                    result["export"] = export_charts_svg(result)
                elif export_format == "json":
                    result["export"] = export_charts_json(result)
                elif export_format:
                    self.error_response("Unsupported chart export format")
                    return
                self.json_response(result)
            elif parsed.path == "/api/quality/panel":
                try:
                    self.json_response(quality_panel_payload(
                        resolve_payload_devices(payload),
                        payload.get("invalid", []),
                        as_text(payload.get("source")),
                        bool(payload.get("save", True)),
                    ))
                except ValueError as error:
                    self.error_response(str(error))
            elif parsed.path == "/api/quality/analyze":
                devices = resolve_payload_devices(payload)
                invalid = payload.get("invalid", [])
                if not isinstance(devices, list):
                    self.error_response("devices must be an array")
                    return
                if not isinstance(invalid, list):
                    invalid = []
                report = analyze_data_quality(devices, invalid)
                if payload.get("save", True):
                    report = save_quality_report(report, as_text(payload.get("source")))
                self.json_response({"report": report})
            elif parsed.path == "/api/dashboard/metrics":
                devices = resolve_payload_devices(payload)
                invalid = payload.get("invalid", [])
                snapshots = payload.get("snapshots", [])
                settings = payload.get("settings", {})
                if not isinstance(devices, list) or not isinstance(snapshots, list) or not isinstance(settings, dict):
                    self.error_response("devices, snapshots and settings are required")
                    return
                if not isinstance(invalid, list):
                    invalid = []
                self.json_response(build_dashboard_metrics_payload(devices, invalid, snapshots, settings))
            elif parsed.path == "/api/dashboard":
                devices = resolve_payload_devices(payload)
                snapshots = payload.get("snapshots", [])
                settings = payload.get("settings", {})
                if not isinstance(devices, list) or not isinstance(snapshots, list) or not isinstance(settings, dict):
                    self.error_response("devices, snapshots and settings are required")
                    return
                client_movements = payload.get("movements", [])
                if not isinstance(client_movements, list):
                    self.error_response("movements must be an array")
                    return
                snapshot_options, change_snapshots, settings = dashboard_snapshot_context(
                    snapshots,
                    as_text(payload.get("snapshotId") or payload.get("resultSnapshotId")),
                    settings,
                )
                database_movements, history_devices = dashboard_history_context()
                result = build_dashboard_payload(
                    devices,
                    snapshot_options,
                    settings,
                    client_movements or database_movements,
                    [] if snapshot_options else history_devices,
                    change_snapshots=change_snapshots,
                    snapshot_options=snapshot_options,
                )
                if payload.get("compactResult") is True:
                    try:
                        dashboard_page_size = max(25, min(int(payload.get("resultPageSize") or 500), 1000))
                    except (TypeError, ValueError):
                        dashboard_page_size = 500
                    filtered_devices = result.get("devices", [])
                    result["filteredDeviceCount"] = len(filtered_devices) if isinstance(filtered_devices, list) else 0
                    result["devices"] = filtered_devices[:dashboard_page_size] if isinstance(filtered_devices, list) else []
                    result["compactResult"] = True
                if payload.get("saveSettings"):
                    result["settings"] = save_dashboard_settings(settings)
                export_format = as_text(payload.get("exportFormat")).lower()
                if export_format == "html":
                    result["export"] = export_dashboard_html(result)
                elif export_format == "png":
                    result["export"] = export_dashboard_png(result)
                elif export_format:
                    self.error_response("Unsupported dashboard export format")
                    return
                self.json_response(result)
            elif parsed.path == "/api/topology":
                devices = resolve_payload_devices(payload)
                if not isinstance(devices, list):
                    self.error_response("devices must be an array")
                    return
                result = build_topology(devices)
                result["topologyHtml"] = topology_nodes_html(result.get("nodes", []))
                result["emptyTopologyHtml"] = topology_nodes_html([])
                export_format = as_text(payload.get("exportFormat")).lower()
                if export_format == "html":
                    result["export"] = export_topology_html(result)
                elif export_format:
                    self.error_response("Unsupported topology export format")
                    return
                self.json_response(result)
            elif parsed.path == "/api/clusters":
                devices = resolve_payload_devices(payload)
                fields = payload.get("fields", [])
                if not isinstance(devices, list):
                    self.error_response("devices must be an array")
                    return
                if not isinstance(fields, list):
                    fields = []
                result = build_clusters(devices, [as_text(field) for field in fields], int(payload.get("minSize") or 1))
                export_format = as_text(payload.get("exportFormat")).lower()
                if export_format == "csv":
                    result["export"] = export_clusters_csv(result)
                elif export_format:
                    self.error_response("Unsupported cluster export format")
                    return
                self.json_response(result)
            elif parsed.path == "/api/device/analytics":
                mac = normalize_mac(payload.get("mac"))
                devices = resolve_payload_devices(payload)
                snapshots = hydrate_snapshot_devices(payload.get("snapshots", []))
                if not mac or not isinstance(devices, list) or not isinstance(snapshots, list):
                    self.error_response("mac, devices and snapshots are required")
                    return
                with db_connection() as conn:
                    history = [dict(row) for row in conn.execute("SELECT * FROM mac_history WHERE mac = ? ORDER BY id DESC LIMIT 500", (mac,)).fetchall()]
                    movements = [dict(row) for row in conn.execute("SELECT * FROM mac_movements WHERE mac = ? ORDER BY id DESC LIMIT 500", (mac,)).fetchall()]
                result = build_device_analytics(mac, devices, snapshots, history, movements, mappings("models"))
                export_format = as_text(payload.get("exportFormat")).lower()
                if export_format == "html":
                    result["export"] = export_device_analytics_html(result)
                elif export_format:
                    self.error_response("Unsupported device analytics export format")
                    return
                self.json_response(result)
            elif parsed.path == "/api/model/analytics":
                model = as_text(payload.get("model"))
                devices = resolve_payload_devices(payload)
                if not model:
                    self.error_response("model is required")
                    return
                if not isinstance(devices, list):
                    devices = []
                model_rules = mapping_rules("models")
                model_mappings = {as_text(item.get("prefix")): as_text(item.get("model")) for item in model_rules}
                model_sources = {as_text(item.get("prefix")): as_text(item.get("source")) for item in model_rules}
                self.json_response(build_model_analytics(model, model_mappings, devices, model_sources))
            elif parsed.path == "/api/external-enrichment/settings":
                settings = payload.get("settings", {})
                if not isinstance(settings, dict):
                    self.error_response("settings must be an object")
                    return
                self.json_response({"settings": save_external_api_settings(settings), "providers": external_api_provider_options()})
            elif parsed.path == "/api/external-enrichment/run":
                devices = resolve_payload_devices(payload)
                selected_macs = payload.get("macs", [])
                settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else external_api_settings()
                if not isinstance(devices, list):
                    self.error_response("devices must be an array")
                    return
                if not isinstance(selected_macs, list):
                    selected_macs = []
                result = external_enrich_devices(devices, settings, api_cache_get, api_cache_set, external_lookup_client, [as_text(mac) for mac in selected_macs])
                if payload.get("saveHistory"):
                    save_history([item for item in result["devices"] if item.get("valid", True)], "external-api-enrichment", as_text(payload.get("createdAt")))
                if payload.get("notify"):
                    try:
                        notify_analysis_completed([item for item in result["devices"] if item.get("valid", True)], [], "external-api-enrichment")
                    except Exception as error:  # noqa: BLE001
                        log_action("Analysis notification failed", str(error))
                if payload.get("compactResult") is True:
                    source_created_at = as_text(payload.get("createdAt")) or utc_now()
                    snapshot = save_statistics_snapshot(
                        result["devices"],
                        "API-обогащение",
                        "external-api-enrichment",
                        created_at=source_created_at,
                    )
                    try:
                        page_size = max(25, min(int(payload.get("resultPageSize") or 250), 1000))
                    except (TypeError, ValueError):
                        page_size = 250
                    result["devices"] = result["devices"][:page_size]
                    result["snapshot"] = snapshot
                    result["compactResult"] = True
                    result["resultReference"] = {
                        "snapshotId": snapshot["id"],
                        "deviceCount": snapshot["deviceCount"],
                        "invalidCount": 0,
                        "pageSize": page_size,
                    }
                self.json_response(result)
            elif parsed.path == "/api/external-enrichment/test":
                settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else external_api_settings()
                result = test_mac_vendor_api(
                    as_text(payload.get("mac")),
                    settings,
                    api_cache_get,
                    api_cache_set,
                    external_lookup_client,
                    bool(payload.get("forceLive")),
                )
                self.json_response(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_GATEWAY)
            elif parsed.path == "/api/api-cache/clear":
                if not self.require_engineering("delete:api-cache"):
                    return
                self.json_response({"ok": True, "deleted": clear_api_cache(as_text(payload.get("prefix")))})
            elif parsed.path == "/api/columns/preferences/results/render":
                preferences = payload.get("preferences") if isinstance(payload.get("preferences"), dict) else payload
                labels = payload.get("labels") if isinstance(payload.get("labels"), dict) else {}
                self.json_response(column_preferences_panel_payload(preferences, labels))
            elif parsed.path.startswith("/api/columns/preferences/"):
                view_name = parsed.path.rsplit("/", 1)[-1]
                if as_text(payload.get("action")).lower() == "move":
                    try:
                        result = move_column_preference(view_name, payload.get("column"), payload.get("direction"))
                    except ValueError as error:
                        self.error_response(str(error))
                        return
                    self.json_response({"ok": True, **result})
                    return
                preferences = save_column_preferences(view_name, payload)
                self.json_response({"ok": True, "columns": preferences["visible"], "preferences": preferences})
            elif parsed.path.startswith("/api/columns/"):
                view_name = parsed.path.rsplit("/", 1)[-1]
                columns = payload.get("columns", [])
                if not isinstance(columns, list):
                    self.error_response("columns должен быть массивом")
                    return
                with db_connection() as conn:
                    conn.execute(
                        "INSERT INTO column_preferences (view_name, columns_json, updated_at) VALUES (?, ?, ?) "
                        "ON CONFLICT(view_name) DO UPDATE SET columns_json=excluded.columns_json, updated_at=excluded.updated_at",
                        (view_name, json.dumps(columns, ensure_ascii=False), utc_now()),
                    )
                self.json_response({"ok": True})
            elif parsed.path == "/api/notifications":
                if not self.require_engineering("write:settings"):
                    return
                channel = as_text(payload.get("channel")).strip().lower()
                if channel not in {"email", "telegram", "slack"}:
                    self.error_response("Поддерживаются каналы email, telegram и slack")
                    return
                if "configText" in payload and not isinstance(payload.get("config"), dict):
                    config_text = as_text(payload.get("configText")).strip()
                    try:
                        config = json.loads(config_text or "{}")
                    except json.JSONDecodeError as error:
                        self.error_response(f"Invalid notification config JSON: {error.msg}")
                        return
                else:
                    config = payload.get("config", {})
                if not isinstance(config, dict):
                    self.error_response("config должен быть объектом")
                    return
                with db_connection() as conn:
                    conn.execute(
                        "INSERT INTO notification_settings (channel, config_json, enabled, updated_at) VALUES (?, ?, ?, ?) "
                        "ON CONFLICT(channel) DO UPDATE SET config_json=excluded.config_json, enabled=excluded.enabled, updated_at=excluded.updated_at",
                        (channel, json.dumps(config), int(bool(payload.get("enabled"))), utc_now()),
                    )
                self.json_response({"ok": True, "channel": channel, "config": config, "enabled": bool(payload.get("enabled"))})
            elif parsed.path == "/api/settings":
                if not self.require_engineering("write:settings"):
                    return
                settings = payload.get("settings", {})
                if not isinstance(settings, dict):
                    self.error_response("settings должен быть объектом")
                    return
                self.json_response({"ok": True, **save_app_settings(settings)})
            elif parsed.path == "/api/theme":
                self.json_response({"ok": True, **save_theme_settings(payload.get("theme"))})
            elif parsed.path == "/api/autosave":
                result = save_autosave_state(
                    payload.get("state", {}),
                    slot=as_text(payload.get("slot")) or "main",
                    reason=as_text(payload.get("reason")) or "manual",
                )
                self.json_response({"ok": True, **result})
            elif parsed.path == "/api/backup/export":
                try:
                    self.json_response(export_app_backup(payload.get("state", {})))
                except ValueError as error:
                    self.error_response(str(error))
            elif parsed.path == "/api/backup/restore":
                try:
                    self.json_response({"ok": True, **restore_app_backup(as_text(payload.get("contentBase64")))})
                except ValueError as error:
                    self.error_response(str(error))
            elif parsed.path == "/api/engineering/login":
                expected = os.environ.get("MAC_ANALYZER_ENGINEERING_PASSWORD", "admin123")
                if not hmac.compare_digest(as_text(payload.get("password")), expected):
                    self.error_response("Invalid engineering password", HTTPStatus.UNAUTHORIZED)
                    return
                session = issue_engineering_session(normalize_engineering_ttl(payload.get("ttlMinutes", 480)))
                log_action("Engineering login", "success")
                self.json_response({"ok": True, **session})
            elif parsed.path == "/api/engineering/verify":
                expected = os.environ.get("MAC_ANALYZER_ENGINEERING_PASSWORD", "admin123")
                if not hmac.compare_digest(as_text(payload.get("password")), expected):
                    self.error_response("Неверный пароль", HTTPStatus.UNAUTHORIZED)
                    return
                log_action("Вход в инженерный режим", "Успешно")
                self.json_response({"ok": True})
            elif parsed.path == "/api/engineering/logout":
                revoked = revoke_engineering_session(self.engineering_token())
                self.json_response({"ok": True, "revoked": revoked})
            elif parsed.path == "/api/notifications/test":
                try:
                    channel, config = notification_config_from_payload(payload)
                except ValueError as error:
                    self.error_response(str(error))
                    return
                event = {"type": "test", "subject": "MAC Analyzer Pro Web: test", "text": "MAC Analyzer Pro Web: test notification"}
                result = dispatch_notification_event(event, [{"channel": channel, "config": config, "enabled": True}], send_notification_message)
                if result["errors"]:
                    self.error_response("; ".join("; ".join(item.get("errors", [])) for item in result["results"] if item["status"] == "error"), HTTPStatus.BAD_GATEWAY)
                    return
                self.json_response({"ok": True, **result})
            elif parsed.path == "/api/notifications/event":
                event_type = as_text(payload.get("type")) or "analysis_completed"
                if event_type != "analysis_completed":
                    self.error_response("Unsupported notification event type")
                    return
                devices = resolve_payload_devices(payload)
                invalid = payload.get("invalid", [])
                if not isinstance(devices, list):
                    devices = []
                if not isinstance(invalid, list):
                    invalid = []
                self.json_response(notify_analysis_completed(devices, invalid, as_text(payload.get("source"))))
            else:
                self.error_response("Неизвестный API-метод", HTTPStatus.NOT_FOUND)
        except (sqlite3.Error, ValueError) as error:
            self.error_response(str(error), HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        permission = ""
        if parsed.path == "/api/history":
            permission = "delete:history"
        elif parsed.path.startswith("/api/snapshots/"):
            permission = "delete:snapshots"
        elif parsed.path.startswith("/api/mappings/vendors/") or parsed.path.startswith("/api/mappings/models/"):
            permission = "delete:mappings"
        elif parsed.path.startswith("/api/tasks/"):
            permission = "delete:tasks"
        elif parsed.path.startswith("/api/ip-mappings/"):
            permission = "delete:ip-mappings"
        elif parsed.path.startswith("/api/settings/") or parsed.path.startswith("/api/autosaves/") or parsed.path == "/api/autosave":
            permission = "write:settings"
        elif parsed.path.startswith("/api/columns/preferences/"):
            permission = "write:settings"
        if permission and not self.require_engineering(permission):
            return
        if parsed.path == "/api/history":
            mac = parse_qs(parsed.query).get("mac", [""])[0]
            deleted = delete_history_records(mac)
            self.json_response({"ok": True, "deleted": deleted, "historyRowsHtml": history_deleted_html(deleted, mac)})
        elif parsed.path.startswith("/api/snapshots/"):
            snapshot_id = parsed.path.rsplit("/", 1)[-1]
            with db_connection() as conn:
                conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
            self.json_response({"ok": True})
        elif parsed.path.startswith("/api/mappings/vendors/") or parsed.path.startswith("/api/mappings/models/"):
            is_vendor = "/vendors/" in parsed.path
            mapping_key = re.sub(r"[^0-9A-F]", "", parsed.path.rsplit("/", 1)[-1].upper())
            table, field = ("vendor_mappings", "oui") if is_vendor else ("model_mappings", "prefix")
            with db_connection() as conn:
                conn.execute(f"DELETE FROM {table} WHERE {field} = ? AND source = 'custom'", (mapping_key,))
            self.json_response({"ok": True})
        elif parsed.path.startswith("/api/tasks/"):
            task_id = parsed.path.rsplit("/", 1)[-1]
            with db_connection() as conn:
                conn.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
            self.json_response({"ok": True})
        elif parsed.path.startswith("/api/ip-mappings/"):
            switch_ip = parsed.path.rsplit("/", 1)[-1]
            with db_connection() as conn:
                conn.execute("DELETE FROM ip_address_mappings WHERE switch_ip = ?", (switch_ip,))
            self.json_response({"ok": True})
        elif parsed.path.startswith("/api/settings/"):
            setting_key = parsed.path.rsplit("/", 1)[-1]
            self.json_response({"ok": True, "deleted": delete_app_setting(setting_key)})
        elif parsed.path.startswith("/api/autosaves/") or parsed.path == "/api/autosave":
            query = parse_qs(parsed.query)
            autosave_slot = parsed.path.rsplit("/", 1)[-1] if parsed.path.startswith("/api/autosaves/") else query.get("slot", ["main"])[0]
            deleted = delete_autosave_state(autosave_slot)
            self.json_response({"ok": True, "deleted": deleted, "slot": autosave_slot, "statusText": autosave_delete_status_text(deleted)})
        elif parsed.path.startswith("/api/columns/preferences/"):
            view_name = parsed.path.rsplit("/", 1)[-1]
            self.json_response({"ok": True, **reset_column_preferences(view_name)})
        elif parsed.path.startswith("/api/enrichment/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            self.json_response({"ok": True, "job": cancel_enrichment_job(job_id)})
        else:
            self.error_response("Неизвестный API-метод", HTTPStatus.NOT_FOUND)

    def send_test_notification(self, payload: dict[str, Any]) -> None:
        channel = as_text(payload.get("channel", "email"))
        if channel == "telegram":
            self.send_test_telegram(payload)
            return
        if channel == "slack":
            self.send_test_slack(payload)
            return
        self.send_test_email(payload)

    def send_test_email(self, payload: dict[str, Any]) -> None:
        host, sender, password, recipient = (as_text(payload.get(name)) for name in ("smtpHost", "from", "password", "to"))
        port = int(payload.get("smtpPort", 587))
        if not all((host, sender, password, recipient)):
            self.error_response("Для теста SMTP укажите сервер, отправителя, пароль и получателя")
            return
        message = MIMEMultipart()
        message["From"], message["To"], message["Subject"] = sender, recipient, "MAC Analyzer Pro Web: тест"
        message.attach(MIMEText("SMTP-служба MAC Analyzer Pro Web успешно настроена.", "plain", "utf-8"))
        try:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(sender, password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            self.error_response("Не удалось отправить письмо: " + str(error), HTTPStatus.BAD_GATEWAY)
            return
        self.json_response({"ok": True})

    def send_test_telegram(self, payload: dict[str, Any]) -> None:
        token, chat_id = as_text(payload.get("botToken")), as_text(payload.get("chatId"))
        if not token or not chat_id:
            self.error_response("Для Telegram укажите botToken и chatId")
            return
        body = json.dumps({"chat_id": chat_id, "text": "MAC Analyzer Pro Web: тестовое сообщение"}).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status != 200:
                    raise urllib.error.URLError(f"HTTP {response.status}")
        except (urllib.error.URLError, TimeoutError) as error:
            self.error_response("Не удалось отправить Telegram: " + str(error), HTTPStatus.BAD_GATEWAY)
            return
        self.json_response({"ok": True})

    def send_test_slack(self, payload: dict[str, Any]) -> None:
        webhook_url = as_text(payload.get("webhookUrl"))
        if not webhook_url.startswith("https://hooks.slack.com/"):
            self.error_response("Укажите корректный Slack webhookUrl")
            return
        request = urllib.request.Request(
            webhook_url,
            data=json.dumps({"text": "MAC Analyzer Pro Web: тестовое сообщение"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status not in {200, 204}:
                    raise urllib.error.URLError(f"HTTP {response.status}")
        except (urllib.error.URLError, TimeoutError) as error:
            self.error_response("Не удалось отправить Slack: " + str(error), HTTPStatus.BAD_GATEWAY)
            return
        self.json_response({"ok": True})


def main() -> None:
    init_database()
    Scheduler().start()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    install_signal_handlers(server)
    print(f"MAC Analyzer Pro Web: http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

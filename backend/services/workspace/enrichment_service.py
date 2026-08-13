import re
from typing import Any, Callable, Iterable

from backend.services.identity.device_identity_service import (
    add_identity_to_index,
    identity_candidates,
    merge_device_records,
    resolve_identity,
    stable_device_id,
)

from .workspace_cache_service import WorkspaceFileCache, workspace_row_iterator


ENRICH_FIELDS = [
    "vendor", "model", "ip", "address", "room", "smartroomId", "switchIp",
    "switchPort", "hostname", "serialNumber", "deviceId", "deviceName",
]


def normalize_source_role(value: Any, fallback: str = "primary") -> str:
    """Use the product's three unambiguous source roles.

    ``enrichment`` remains an accepted input alias for workspaces saved before
    v1.0.49, but is normalized to ``smartroom`` before domain processing.
    """
    role = str(value or fallback).strip().casefold()
    if role in {"smartroom", "smart-room", "sr", "enrichment", "secondary"}:
        return "smartroom"
    if role == "ddio":
        return "ddio"
    return "primary"


def normalize_mac(value: Any) -> str:
    normalized = re.sub(r"[^0-9A-Fa-f]", "", str(value or "")).upper()
    if len(normalized) == 10:
        normalized = "00" + normalized
    if len(normalized) == 11:
        normalized = "0" + normalized
    if len(normalized) == 8:
        normalized = "0000" + normalized
    return normalized if len(normalized) == 12 else ""


def format_mac(mac: str) -> str:
    return ":".join(mac[index:index + 2] for index in range(0, len(mac), 2))


def read_mapped(row: list[Any], mapping: dict[str, Any], field: str) -> str:
    index = mapping.get(field, "")
    if index == "" or index is None:
        return ""
    try:
        position = int(index)
    except (TypeError, ValueError):
        return ""
    if position < 0 or position >= len(row):
        return ""
    return str(row[position] or "").strip()


def compile_mapping(mapping: dict[str, Any] | None) -> dict[str, int]:
    compiled: dict[str, int] = {}
    for field, value in (mapping or {}).items():
        if value in ("", None):
            continue
        try:
            position = int(value)
        except (TypeError, ValueError):
            continue
        if position >= 0:
            compiled[field] = position
    return compiled


def row_to_device(row: list[Any], file_info: dict[str, Any], row_index: int, compiled_mapping: dict[str, int] | None = None) -> dict[str, Any]:
    mapping = compiled_mapping if compiled_mapping is not None else compile_mapping(file_info.get("mapping") or {})
    raw_mac = read_mapped(row, mapping, "mac")
    mac = normalize_mac(raw_mac)
    role = normalize_source_role(file_info.get("role"))
    device = {
        "mac": mac,
        "macFormatted": format_mac(mac) if mac else "",
        "oui": mac[:6] if mac else "",
        "source": file_info.get("name", ""),
        "sourceRole": role,
        "row": row_index + 2,
    }
    for field in ENRICH_FIELDS:
        device[field] = read_mapped(row, mapping, field)
    if not [candidate for candidate in identity_candidates(device) if not candidate.startswith("internal-id:")]:
        return {
            "invalid": True,
            "row": row_index + 2,
            "source": file_info.get("name", ""),
            "sourceRole": role,
            "raw": raw_mac,
            "error": "Нет корректного MAC, серийного номера или Device ID",
        }
    device["internalDeviceId"] = stable_device_id(device)
    return device


def merge_device(
    previous: dict[str, Any], current: dict[str, Any], *, prefer_existing: bool = False
) -> dict[str, Any]:
    return merge_device_records(
        previous,
        current,
        source=str(current.get("source") or ""),
        role=str(current.get("sourceRole") or ""),
        prefer_existing=prefer_existing,
    )


def _inline_rows(file_info: dict[str, Any]) -> Iterable[list[Any]]:
    rows = file_info.get("rows") or []
    return rows[1:] if rows and isinstance(rows[0], list) else rows


def _row_count(file_info: dict[str, Any]) -> int:
    declared = file_info.get("rowCount")
    if declared not in (None, ""):
        try:
            return max(0, int(declared))
        except (TypeError, ValueError):
            pass
    rows = file_info.get("rows") or []
    return len(rows[1:] if rows and isinstance(rows[0], list) else rows)


def _enrich_row_streams(
    files: list[dict[str, Any]],
    strategy: str,
    row_provider: Callable[[dict[str, Any]], Iterable[list[Any]]],
    progress_callback=None,
    is_cancelled=None,
) -> dict[str, Any]:
    if not files:
        return {"devices": [], "invalid": [], "progress": {"files": 0, "rows": 0, "valid": 0, "invalid": 0, "status": "completed", "percent": 100}}
    # File 1 is primary. File 2 is SmartRoom: it enriches matching devices and
    # contributes its own identifiable devices. DDIO is processed separately
    # and therefore can never create an independent final device here.
    resolved_devices: list[dict[str, Any]] = []
    identity_index: dict[str, dict[str, Any]] = {}
    invalid: list[dict[str, Any]] = []
    rows_processed = 0
    total_rows = 0
    for file_info in files:
        total_rows += _row_count(file_info)
    if progress_callback:
        progress_callback({"status": "running", "files": len(files), "rows": 0, "totalRows": total_rows, "valid": 0, "invalid": 0, "percent": 0, "strategy": strategy})
    for file_index, file_info in enumerate(files):
        compiled_mapping = compile_mapping(file_info.get("mapping") or {})
        progress_interval = max(1, min(250, total_rows // 100 or 1))
        for row_index, row in enumerate(row_provider(file_info)):
            if is_cancelled and is_cancelled():
                progress = {
                    "files": len(files),
                    "rows": rows_processed,
                    "totalRows": total_rows,
                    "valid": len(resolved_devices),
                    "invalid": len(invalid),
                    "strategy": strategy,
                    "status": "cancelled",
                    "percent": round(rows_processed / total_rows * 100) if total_rows else 100,
                }
                if progress_callback:
                    progress_callback(progress)
                return {"devices": sorted(resolved_devices, key=lambda item: (item.get("mac") or "", item.get("internalDeviceId") or "")), "invalid": invalid, "progress": progress}
            if not isinstance(row, list):
                continue
            rows_processed += 1
            current = row_to_device(row, file_info, row_index, compiled_mapping)
            if current.get("invalid"):
                # Data-quality accounting covers both authoritative inputs.
                # The source role tells the user whether the bad record came
                # from File 1 or SmartRoom.
                invalid.append(current)
                continue
            resolution = resolve_identity(current, identity_index)
            existing = resolution.get("match")
            if resolution.get("status") == "conflict":
                current = merge_device_records({}, current, source=str(current.get("source") or ""), role=str(current.get("sourceRole") or ""))
                current.setdefault("conflicts", []).append({
                    "field": "identity",
                    "selected": current.get("internalDeviceId"),
                    "selectedSource": current.get("source"),
                    "alternative": "Несколько устройств соответствуют сильным идентификаторам",
                    "alternativeSource": "identity-resolver",
                    "confidence": "Conflict",
                    "evidence": resolution.get("evidence") or [],
                })
                current["hasConflict"] = True
                current["matchConfidence"] = "Conflict"
                resolved_devices.append(current)
                add_identity_to_index(identity_index, current)
            elif existing:
                existing_internal_id = existing.get("internalDeviceId")
                merged_device = merge_device(existing, current, prefer_existing=True)
                merged_device["internalDeviceId"] = existing_internal_id or stable_device_id(merged_device)
                merged_device["matchConfidence"] = resolution.get("confidence") or "High"
                existing.clear()
                existing.update(merged_device)
                add_identity_to_index(identity_index, existing)
            else:
                current = merge_device({}, current, prefer_existing=False)
                current["internalDeviceId"] = stable_device_id(current)
                current["matchConfidence"] = "Exact" if current.get("mac") else "High"
                resolved_devices.append(current)
                add_identity_to_index(identity_index, current)
            if progress_callback and (rows_processed % progress_interval == 0 or rows_processed == total_rows):
                progress_callback({
                    "files": len(files),
                    "currentFile": file_index + 1,
                    "rows": rows_processed,
                    "totalRows": total_rows,
                    "valid": len(resolved_devices),
                    "invalid": len(invalid),
                    "strategy": strategy,
                    "status": "running",
                    "percent": round(rows_processed / total_rows * 100) if total_rows else 100,
                })
    devices = sorted(resolved_devices, key=lambda item: (item.get("mac") or "", item.get("internalDeviceId") or ""))
    switch_ip_changes: list[dict[str, str]] = []
    return {
        "devices": devices,
        "invalid": invalid,
        "switchIpChanges": switch_ip_changes,
        "progress": {
            "files": len(files),
            "rows": rows_processed,
            "totalRows": total_rows,
            "valid": len(devices),
            "invalid": len(invalid),
            "strategy": strategy,
            "status": "completed",
            "percent": 100,
        },
    }


def enrich_files(files: list[dict[str, Any]], strategy: str = "primary", progress_callback=None, is_cancelled=None) -> dict[str, Any]:
    return _enrich_row_streams(files, strategy, _inline_rows, progress_callback, is_cancelled)


def enrich_workspace_files(
    files: list[dict[str, Any]],
    cache: WorkspaceFileCache,
    strategy: str = "primary",
    progress_callback=None,
    is_cancelled=None,
) -> dict[str, Any]:
    """Merge cached imports by streaming rows from the local SQLite cache."""
    return _enrich_row_streams(
        files,
        strategy,
        lambda file_info: workspace_row_iterator(file_info, cache),
        progress_callback,
        is_cancelled,
    )

import re
from typing import Any, Callable, Iterable

from .workspace_cache_service import WorkspaceFileCache, workspace_row_iterator


ENRICH_FIELDS = ["vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort"]


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
    if not mac:
        return {
            "invalid": True,
            "row": row_index + 2,
            "source": file_info.get("name", ""),
            "raw": raw_mac,
        }
    device = {
        "mac": mac,
        "macFormatted": format_mac(mac),
        "oui": mac[:6],
        "source": file_info.get("name", ""),
        "row": row_index + 2,
    }
    for field in ENRICH_FIELDS:
        device[field] = read_mapped(row, mapping, field)
    return device


def merge_device(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    merged = dict(previous)
    for key, value in current.items():
        if key == "source" and previous:
            continue
        if value not in ("", None):
            merged[key] = value
    return merged


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
    allow_new_from_secondary = strategy == "merge"
    by_mac: dict[str, dict[str, Any]] = {}
    switch_state: dict[str, dict[str, str]] = {}
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
                    "valid": len(by_mac),
                    "invalid": len(invalid),
                    "strategy": strategy,
                    "status": "cancelled",
                    "percent": round(rows_processed / total_rows * 100) if total_rows else 100,
                }
                if progress_callback:
                    progress_callback(progress)
                return {"devices": sorted(by_mac.values(), key=lambda item: item["mac"]), "invalid": invalid, "progress": progress}
            if not isinstance(row, list):
                continue
            rows_processed += 1
            current = row_to_device(row, file_info, row_index, compiled_mapping)
            if current.get("invalid"):
                if file_index == 0:
                    invalid.append(current)
                continue
            existing = by_mac.get(current["mac"])
            if file_index == 0 or allow_new_from_secondary or existing:
                by_mac[current["mac"]] = merge_device(existing or {}, current)
                switch_ip = str(current.get("switchIp") or "").strip()
                if switch_ip:
                    if file_index == 0:
                        switch_state[current["mac"]] = {"before": switch_ip, "after": switch_ip}
                    elif existing and current["mac"] in switch_state:
                        switch_state[current["mac"]]["after"] = switch_ip
            if progress_callback and (rows_processed % progress_interval == 0 or rows_processed == total_rows):
                progress_callback({
                    "files": len(files),
                    "currentFile": file_index + 1,
                    "rows": rows_processed,
                    "totalRows": total_rows,
                    "valid": len(by_mac),
                    "invalid": len(invalid),
                    "strategy": strategy,
                    "status": "running",
                    "percent": round(rows_processed / total_rows * 100) if total_rows else 100,
                })
    devices = sorted(by_mac.values(), key=lambda item: item["mac"])
    final_source = str(files[0].get("name") or "")
    for device in devices:
        device["source"] = final_source
    switch_ip_changes = [
        {"mac": mac, "before": values["before"], "after": values["after"]}
        for mac, values in switch_state.items()
        if values.get("before") and values.get("after") and values["before"] != values["after"]
    ]
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

import re
from typing import Any, Callable, Iterable

from backend.services.identity.device_identity_service import (
    add_identity_to_index,
    identity_candidates,
    merge_device_records,
    resolve_identity,
    stable_device_id,
)
from backend.services.validation.record_validation_service import (
    invalid_identity_record,
    is_empty_row,
)

from .workspace_cache_service import WorkspaceFileCache, workspace_row_iterator


ENRICH_FIELDS = [
    "vendor", "model", "ip", "address", "room", "smartroomId", "switchIp",
    "switchPort", "hostname", "serialNumber", "deviceId", "deviceName",
]

NO_EXPANSION = "NO_EXPANSION"
ALLOW_EXPANSION = "ALLOW_EXPANSION"
_ALLOW_EXPANSION_ALIASES = {
    "allow_expansion", "allow-expansion", "expand", "union", "merge", "primary",
}


def normalize_enrichment_strategy(value: Any) -> str:
    """Normalize the only two supported Final row-count strategies."""
    normalized = str(value or "").strip().casefold()
    return ALLOW_EXPANSION if normalized in _ALLOW_EXPANSION_ALIASES else NO_EXPANSION


def strategy_allows_creation(source_role: Any, strategy: Any) -> bool:
    role = normalize_source_role(source_role)
    if role == "primary":
        return True
    return role == "smartroom" and normalize_enrichment_strategy(strategy) == ALLOW_EXPANSION


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
    if is_empty_row(row):
        return {"skipped": True, "reason": "EMPTY_ROW", "row": row_index + 2}
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
        return invalid_identity_record(
            row=row,
            row_number=row_index + 2,
            source=str(file_info.get("name") or ""),
            source_role=role,
            raw_mac=raw_mac,
            mac_column=mapping.get("mac"),
        )
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
    strategy = normalize_enrichment_strategy(strategy)
    if not files:
        return {
            "devices": [], "invalid": [], "creationDecisions": [],
            "diagnostics": {"strategy": strategy, "counts": {"finalUniqueDevices": 0}},
            "progress": {"files": 0, "rows": 0, "valid": 0, "invalid": 0, "status": "completed", "percent": 100, "stage": "completed"},
        }
    prepared_files = [dict(item) for item in files if isinstance(item, dict)]
    primary_index = next(
        (index for index, item in enumerate(prepared_files) if str(item.get("role") or "").strip().casefold() == "primary"),
        0,
    )
    for index, item in enumerate(prepared_files):
        item["role"] = "primary" if index == primary_index else normalize_source_role(item.get("role"), "smartroom")
    files = [prepared_files[primary_index], *[item for index, item in enumerate(prepared_files) if index != primary_index]]
    # File 1 is primary. File 2 is SmartRoom: it enriches matching devices and
    # contributes its own identifiable devices. DDIO is processed separately
    # and therefore can never create an independent final device here.
    resolved_devices: list[dict[str, Any]] = []
    identity_index: dict[str, dict[str, Any]] = {}
    invalid: list[dict[str, Any]] = []
    creation_decisions: list[dict[str, Any]] = []
    decision_limit = 5000
    counts = {
        "mainRawRows": 0, "mainNormalizedRows": 0, "mainUniqueDevices": 0,
        "smartroomRawRows": 0, "smartroomMatched": 0, "smartroomUnmatched": 0,
        "smartroomCreated": 0, "smartroomConflicts": 0,
        "ddioRawRows": 0, "ddioMatched": 0, "ddioUnmatched": 0, "ddioCreated": 0,
        "previousFinalMatched": 0, "finalUniqueDevices": 0, "inventoryTotal": 0,
        "emptyRowsSkipped": 0,
    }

    def record_decision(code: str, current: dict[str, Any], resolution: dict[str, Any], reason: str) -> None:
        if len(creation_decisions) >= decision_limit:
            return
        creation_decisions.append({
            "code": code, "source": str(current.get("source") or ""),
            "sourceRole": str(current.get("sourceRole") or ""), "row": current.get("row"),
            "internalDeviceId": str(current.get("internalDeviceId") or ""), "strategy": strategy,
            "reason": reason, "strongIdentifiers": identity_candidates(current),
            "evidence": list(resolution.get("evidence") or []),
        })

    def create_device(current: dict[str, Any], *, conflict: bool = False) -> dict[str, Any]:
        created = merge_device({}, current, prefer_existing=False)
        if current.get("conflicts"):
            created["conflicts"] = list(current.get("conflicts") or [])
            created["hasConflict"] = True
        if conflict:
            created.pop("internalDeviceId", None)
            created["internalDeviceId"] = stable_device_id(
                created, namespace=f"primary-conflict:{created.get('source')}:{created.get('row')}"
            )
        else:
            created["internalDeviceId"] = stable_device_id(created)
        resolved_devices.append(created)
        add_identity_to_index(identity_index, created)
        return created
    rows_processed = 0
    total_rows = 0
    for file_info in files:
        total_rows += _row_count(file_info)
    if progress_callback:
        progress_callback({"status": "running", "stage": "validation", "files": len(files), "rows": 0, "totalRows": total_rows, "valid": 0, "invalid": 0, "percent": 0, "strategy": strategy})
    for file_index, file_info in enumerate(files):
        role = normalize_source_role(file_info.get("role"), "primary" if file_index == 0 else "smartroom")
        file_info["role"] = role
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
            if role == "primary":
                counts["mainRawRows"] += 1
            elif role == "smartroom":
                counts["smartroomRawRows"] += 1
            current = row_to_device(row, file_info, row_index, compiled_mapping)
            if current.get("skipped"):
                counts["emptyRowsSkipped"] += 1
                continue
            if current.get("invalid"):
                # Data-quality accounting covers both authoritative inputs.
                # The source role tells the user whether the bad record came
                # from File 1 or SmartRoom.
                invalid.append(current)
                continue
            if role == "primary":
                counts["mainNormalizedRows"] += 1
            resolution = resolve_identity(current, identity_index)
            existing = resolution.get("match")
            if resolution.get("status") == "conflict":
                if role != "primary":
                    counts["smartroomConflicts"] += 1
                    counts["smartroomUnmatched"] += 1
                    record_decision(
                        "NOT_CREATED_FROM_SMARTROOM_CONFLICT", current, resolution,
                        "ambiguous strong identifiers",
                    )
                    continue
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
                create_device(current, conflict=True)
                record_decision(
                    "CREATED_FROM_MAIN_CONFLICT", current, resolution,
                    "main rows cannot be dropped on ambiguous identity",
                )
            elif existing:
                existing_internal_id = existing.get("internalDeviceId")
                merged_device = merge_device(existing, current, prefer_existing=True)
                merged_device["internalDeviceId"] = existing_internal_id or stable_device_id(merged_device)
                merged_device["matchConfidence"] = resolution.get("confidence") or "High"
                existing.clear()
                existing.update(merged_device)
                add_identity_to_index(identity_index, existing)
                if role == "smartroom":
                    counts["smartroomMatched"] += 1
            else:
                if not strategy_allows_creation(role, strategy):
                    if role == "smartroom":
                        counts["smartroomUnmatched"] += 1
                        record_decision(
                            "NOT_CREATED_FROM_SMARTROOM", current, resolution,
                            "strategy=NO_EXPANSION",
                        )
                    continue
                current["matchConfidence"] = "Exact" if current.get("mac") else "High"
                create_device(current)
                if role == "smartroom":
                    counts["smartroomUnmatched"] += 1
                    counts["smartroomCreated"] += 1
                    record_decision(
                        "CREATED_FROM_SMARTROOM", current, resolution,
                        "unmatched strong identity and strategy=ALLOW_EXPANSION",
                    )
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
                    "stage": "main-device-creation" if role == "primary" else "smartroom-matching",
                    "percent": round(rows_processed / total_rows * 100) if total_rows else 100,
                })
    devices = sorted(resolved_devices, key=lambda item: (item.get("mac") or "", item.get("internalDeviceId") or ""))
    counts["mainUniqueDevices"] = sum(1 for item in devices if "primary" in (item.get("sourceRoles") or []))
    counts["finalUniqueDevices"] = len(devices)
    switch_ip_changes: list[dict[str, str]] = []
    return {
        "devices": devices,
        "invalid": invalid,
        "creationDecisions": creation_decisions,
        "diagnostics": {
            "strategy": strategy,
            "counts": counts,
            "decisionLimit": decision_limit,
            "decisionsTruncated": len(creation_decisions) >= decision_limit,
        },
        "switchIpChanges": switch_ip_changes,
        "progress": {
            "files": len(files),
            "rows": rows_processed,
            "totalRows": total_rows,
            "valid": len(devices),
            "invalid": len(invalid),
            "strategy": strategy,
            "status": "completed",
            "stage": "source-merge-completed",
            "percent": 100,
        },
    }


def enrich_files(files: list[dict[str, Any]], strategy: str = NO_EXPANSION, progress_callback=None, is_cancelled=None) -> dict[str, Any]:
    return _enrich_row_streams(files, strategy, _inline_rows, progress_callback, is_cancelled)


def enrich_workspace_files(
    files: list[dict[str, Any]],
    cache: WorkspaceFileCache,
    strategy: str = NO_EXPANSION,
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

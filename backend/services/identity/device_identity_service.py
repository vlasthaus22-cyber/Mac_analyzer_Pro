from __future__ import annotations

import ipaddress
import re
from typing import Any, Iterable


CANONICAL_ALIASES = {
    "smartroomId": ("smartroomId", "smartroom_id", "Smartroom_ID"),
    "switchIp": ("switchIp", "switch_ip", "ip_switch"),
    "switchPort": ("switchPort", "switch_port", "port"),
    "serialNumber": ("serialNumber", "serial_number", "serial", "serial_no"),
    "deviceId": ("deviceId", "device_id", "equipment_id", "asset_id"),
    "deviceName": ("deviceName", "device_name", "name"),
    "hostname": ("hostname", "host_name", "dns_name"),
}

STABLE_FIELDS = ("mac", "serialNumber", "deviceId", "hostname")
MERGE_FIELDS = (
    "mac", "vendor", "model", "ip", "address", "room", "smartroomId", "switchIp",
    "switchPort", "hostname", "serialNumber", "deviceId", "deviceName",
)


def text(value: Any) -> str:
    return str(value or "").strip()


def normalize_mac(value: Any) -> str:
    normalized = re.sub(r"[^0-9A-Fa-f]", "", text(value)).upper()
    if len(normalized) == 10:
        normalized = "00" + normalized
    if len(normalized) == 11:
        normalized = "0" + normalized
    if len(normalized) == 8:
        normalized = "0000" + normalized
    return normalized if len(normalized) == 12 else ""


def normalize_ip(value: Any) -> str:
    candidate = text(value).strip("[]").split("%", 1)[0]
    try:
        return ipaddress.ip_address(candidate).compressed
    except ValueError:
        return ""


def normalize_token(value: Any) -> str:
    return re.sub(r"\s+", " ", text(value)).casefold()


def canonical_value(device: dict[str, Any], field: str) -> str:
    for alias in CANONICAL_ALIASES.get(field, (field,)):
        value = text(device.get(alias))
        if value:
            if field == "mac":
                return normalize_mac(value)
            if field in {"ip", "switchIp"}:
                return normalize_ip(value) or value
            if field in {"hostname", "serialNumber", "deviceId"}:
                return normalize_token(value)
            return value
    return ""


def identity_candidates(device: dict[str, Any]) -> list[str]:
    mac = normalize_mac(device.get("mac") or device.get("macFormatted"))
    serial = canonical_value(device, "serialNumber")
    device_id = canonical_value(device, "deviceId")
    hostname = canonical_value(device, "hostname")
    candidates: list[str] = []
    if mac:
        candidates.append("mac:" + mac)
    if serial:
        candidates.append("serial:" + serial)
    if device_id:
        candidates.append("device:" + device_id)
    if hostname and serial:
        candidates.append("host-serial:" + hostname + "|" + serial)
    return candidates


def identity_key(device: dict[str, Any]) -> str:
    candidates = identity_candidates(device)
    return candidates[0] if candidates else ""


def build_identity_index(devices: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    ambiguous: set[str] = set()
    for device in devices:
        if not isinstance(device, dict):
            continue
        for candidate in identity_candidates(device):
            previous = index.get(candidate)
            if previous is not None and previous is not device:
                ambiguous.add(candidate)
            else:
                index[candidate] = device
    for candidate in ambiguous:
        index.pop(candidate, None)
    return index


def find_identity_match(device: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    matches = {id(index[candidate]): index[candidate] for candidate in identity_candidates(device) if candidate in index}
    return next(iter(matches.values())) if len(matches) == 1 else None


def pair_device_sets(
    previous_devices: Iterable[dict[str, Any]], current_devices: Iterable[dict[str, Any]]
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Pair two fleets by unambiguous strong identifiers.

    A changed MAC can still be matched by serial number or device ID. Ambiguous
    aliases are deliberately ignored so a weak collision never merges devices.
    """
    previous = [item for item in previous_devices if isinstance(item, dict)]
    current = [item for item in current_devices if isinstance(item, dict)]
    previous_index = build_identity_index(previous)
    used_previous: set[int] = set()
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    added: list[dict[str, Any]] = []
    for device in current:
        match = find_identity_match(device, previous_index)
        if match is None or id(match) in used_previous:
            added.append(device)
            continue
        used_previous.add(id(match))
        pairs.append((match, device))
    removed = [device for device in previous if id(device) not in used_previous]
    return pairs, added, removed


def merge_device_records(
    previous: dict[str, Any] | None,
    incoming: dict[str, Any],
    *,
    source: str = "",
    role: str = "",
    prefer_existing: bool = False,
) -> dict[str, Any]:
    merged = dict(previous or {})
    field_sources = dict(merged.get("fieldSources") or {})
    conflicts = list(merged.get("conflicts") or [])
    source_files = list(merged.get("sourceFiles") or ([text(merged.get("source"))] if text(merged.get("source")) else []))
    source_roles = list(merged.get("sourceRoles") or [])
    normalized_source = text(source or incoming.get("source"))
    normalized_role = text(role or incoming.get("sourceRole"))
    if normalized_source and normalized_source not in source_files:
        source_files.append(normalized_source)
    if normalized_role and normalized_role not in source_roles:
        source_roles.append(normalized_role)

    for key, value in incoming.items():
        if key in {"fieldSources", "conflicts", "sourceFiles", "sourceRoles"} or value in ("", None):
            continue
        existing = merged.get(key)
        has_existing = existing not in ("", None)
        if has_existing and str(existing).strip() != str(value).strip() and key in MERGE_FIELDS:
            selected = existing if prefer_existing else value
            conflict = {
                "field": key,
                "selected": selected,
                "selectedSource": field_sources.get(key) if prefer_existing else normalized_source,
                "alternative": value if prefer_existing else existing,
                "alternativeSource": normalized_source if prefer_existing else field_sources.get(key, ""),
            }
            if conflict not in conflicts:
                conflicts.append(conflict)
        if prefer_existing and has_existing:
            continue
        merged[key] = value
        if normalized_source and key in MERGE_FIELDS:
            field_sources[key] = normalized_source

    merged["fieldSources"] = field_sources
    merged["sourceFiles"] = source_files
    merged["sourceRoles"] = source_roles
    merged["conflicts"] = conflicts
    merged["hasConflict"] = bool(conflicts)
    merged["identityKey"] = identity_key(merged)
    merged["source"] = source_files[0] if len(source_files) == 1 else " + ".join(source_files)
    return merged


def preserve_known_values(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    """Fill only missing values from a confidently matched previous final state."""
    if not previous:
        return current
    result = merge_device_records(current, previous, source="previous-final", role="history", prefer_existing=True)
    for field in MERGE_FIELDS:
        if text(current.get(field)):
            continue
        if text(previous.get(field)):
            result.setdefault("fieldSources", {})[field] = "previous-final"
    result["previousFinalMatched"] = True
    return result

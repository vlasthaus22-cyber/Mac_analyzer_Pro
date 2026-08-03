from __future__ import annotations

from typing import Any, Iterable

from .enrichment_service import compile_mapping, normalize_mac, read_mapped


DDIO_FIELDS = ("reservationMac", "leaseMac", "ip")


def normalize_switch_changes(changes: Any) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for item in changes if isinstance(changes, list) else []:
        if not isinstance(item, dict):
            continue
        mac = normalize_mac(item.get("mac"))
        before = str(item.get("before") or "").strip()
        after = str(item.get("after") or "").strip()
        if mac and before and after and before != after:
            normalized[mac] = {"before": before, "after": after}
    return normalized


def validate_ddio_mapping(mapping: Any) -> dict[str, int]:
    compiled = compile_mapping(mapping if isinstance(mapping, dict) else {})
    result = {field: compiled[field] for field in DDIO_FIELDS if field in compiled}
    if "ip" not in result:
        raise ValueError("DDIO: выберите колонку IP-адреса")
    if "reservationMac" not in result and "leaseMac" not in result:
        raise ValueError("DDIO: выберите хотя бы одну MAC-колонку (резервация или аренда)")
    return result


def build_ddio_overlay(
    rows: Iterable[list[Any]],
    mapping: Any,
    switch_changes: Any,
    current_ip_by_mac: dict[str, Any] | None = None,
) -> dict[str, dict[str, str]]:
    """Build a display-only DDIO hint map without mutating device records."""
    changes = normalize_switch_changes(switch_changes)
    if not changes:
        return {}
    compiled = validate_ddio_mapping(mapping)
    candidates: dict[str, dict[str, str]] = {}
    for row in rows:
        if not isinstance(row, list):
            continue
        ip = read_mapped(row, compiled, "ip")
        if not ip:
            continue
        reservation_mac = normalize_mac(read_mapped(row, compiled, "reservationMac"))
        lease_mac = normalize_mac(read_mapped(row, compiled, "leaseMac"))
        if reservation_mac in changes and reservation_mac not in candidates:
            candidates[reservation_mac] = {"ip": ip, "match": "reservation"}
        if lease_mac in changes:
            candidates[lease_mac] = {"ip": ip, "match": "lease"}

    current_ips = current_ip_by_mac if isinstance(current_ip_by_mac, dict) else {}
    overlay: dict[str, dict[str, str]] = {}
    for mac, change in changes.items():
        candidate = candidates.get(mac)
        if not candidate:
            continue
        current_ip = str(current_ips.get(mac) or "").strip()
        if current_ip and current_ip == candidate["ip"]:
            continue
        overlay[mac] = {
            "ip": candidate["ip"],
            "match": candidate["match"],
            "previousSwitchIp": change["before"],
            "currentSwitchIp": change["after"],
        }
    return overlay


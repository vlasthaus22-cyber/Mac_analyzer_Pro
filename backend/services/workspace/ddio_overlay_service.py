from __future__ import annotations

from typing import Any, Iterable

from .enrichment_service import compile_mapping, normalize_mac, read_mapped


DDIO_FIELDS = ("reservationMac", "reservationIp", "leaseMac", "leaseIp", "ip")


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
    reservation_complete = "reservationMac" in result and ("reservationIp" in result or "ip" in result)
    lease_complete = "leaseMac" in result and ("leaseIp" in result or "ip" in result)
    if not reservation_complete and not lease_complete:
        raise ValueError("DDIO: выберите полную пару MAC + IP для резервации или аренды")
    return result


def build_ddio_overlay(
    rows: Iterable[list[Any]],
    mapping: Any,
    switch_changes: Any,
    current_ip_by_mac: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build a display-only DDIO hint map without mutating device records."""
    changes = normalize_switch_changes(switch_changes)
    if not changes:
        return {}
    compiled = validate_ddio_mapping(mapping)
    candidates: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, list):
            continue
        reservation_mac = normalize_mac(read_mapped(row, compiled, "reservationMac"))
        lease_mac = normalize_mac(read_mapped(row, compiled, "leaseMac"))
        reservation_ip_field = "reservationIp" if "reservationIp" in compiled else "ip"
        lease_ip_field = "leaseIp" if "leaseIp" in compiled else "ip"
        reservation_ip = read_mapped(row, compiled, reservation_ip_field)
        lease_ip = read_mapped(row, compiled, lease_ip_field)
        if reservation_mac in changes and reservation_ip:
            candidate = candidates.setdefault(reservation_mac, {"ip": reservation_ip, "match": "reservation", "possibleIps": []})
            candidate["possibleIps"] = list(dict.fromkeys([*candidate.get("possibleIps", []), reservation_ip]))
        if lease_mac in changes and lease_ip:
            candidate = candidates.setdefault(lease_mac, {"ip": lease_ip, "match": "lease", "possibleIps": []})
            candidate.update({"ip": lease_ip, "match": "lease"})
            candidate["possibleIps"] = list(dict.fromkeys([*candidate.get("possibleIps", []), lease_ip]))

    current_ips = current_ip_by_mac if isinstance(current_ip_by_mac, dict) else {}
    overlay: dict[str, dict[str, Any]] = {}
    for mac, change in changes.items():
        candidate = candidates.get(mac)
        if not candidate:
            continue
        current_ip = str(current_ips.get(mac) or "").strip()
        possible_ips = [value for value in candidate.get("possibleIps", [candidate["ip"]]) if value and value != current_ip]
        if not possible_ips:
            continue
        overlay[mac] = {
            "ip": candidate["ip"] if candidate["ip"] in possible_ips else possible_ips[0],
            "possibleIps": possible_ips,
            "match": candidate["match"],
            "previousSwitchIp": change["before"],
            "currentSwitchIp": change["after"],
        }
    return overlay

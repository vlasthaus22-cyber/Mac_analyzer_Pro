from __future__ import annotations

from typing import Any, Iterable

from backend.services.identity.device_identity_service import normalize_ip

from .enrichment_service import compile_mapping, normalize_mac, read_mapped


DDIO_FIELDS = ("deviceId", "reservationMac", "reservationIp", "leaseMac", "leaseIp", "ip")


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
    device_complete = "deviceId" in result and any(field in result for field in ("reservationIp", "leaseIp", "ip"))
    if not reservation_complete and not lease_complete and not device_complete:
        raise ValueError("DDIO: выберите полную пару MAC + IP для резервации или аренды")
    return result


def build_ddio_overlay(
    rows: Iterable[list[Any]],
    mapping: Any,
    switch_changes: Any,
    current_ip_by_mac: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build DDIO switch-change hints without mutating device records."""
    changes = normalize_switch_changes(switch_changes)
    if not changes:
        return {}
    candidates = build_ddio_device_index(rows, mapping)
    return build_ddio_overlay_from_index(candidates, changes, current_ip_by_mac)


def build_ddio_device_index(
    rows: Iterable[list[Any]], mapping: Any
) -> dict[str, dict[str, Any]]:
    """Index every DDIO MAC/device id, not only rows with a switch change."""
    compiled = validate_ddio_mapping(mapping)
    candidates: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, list):
            continue
        reservation_mac = normalize_mac(read_mapped(row, compiled, "reservationMac"))
        lease_mac = normalize_mac(read_mapped(row, compiled, "leaseMac"))
        reservation_ip_field = "reservationIp" if "reservationIp" in compiled else "ip"
        lease_ip_field = "leaseIp" if "leaseIp" in compiled else "ip"
        reservation_ip = normalize_ip(read_mapped(row, compiled, reservation_ip_field))
        lease_ip = normalize_ip(read_mapped(row, compiled, lease_ip_field))
        device_id = read_mapped(row, compiled, "deviceId").casefold() if "deviceId" in compiled else ""
        if reservation_mac and reservation_ip:
            candidate = candidates.setdefault(reservation_mac, {"ip": reservation_ip, "match": "reservation", "possibleIps": []})
            candidate["possibleIps"] = list(dict.fromkeys([*candidate.get("possibleIps", []), reservation_ip]))
        if lease_mac and lease_ip:
            candidate = candidates.setdefault(lease_mac, {"ip": lease_ip, "match": "lease", "possibleIps": []})
            candidate.update({"ip": lease_ip, "match": "lease"})
            candidate["possibleIps"] = list(dict.fromkeys([*candidate.get("possibleIps", []), lease_ip]))
        if device_id:
            values = [value for value in (reservation_ip, lease_ip) if value]
            if values:
                candidates["device-id:" + device_id] = {
                    "ip": values[-1],
                    "match": "device-id",
                    "possibleIps": list(dict.fromkeys(values)),
                }
    return candidates


def apply_ddio_ip_fallback(
    devices: list[dict[str, Any]], index: dict[str, dict[str, Any]]
) -> int:
    """Fill a missing device IP from DDIO while preserving provenance."""
    updated = 0
    for device in devices:
        if str(device.get("ip") or "").strip():
            continue
        mac = normalize_mac(device.get("mac") or device.get("macFormatted"))
        device_id = str(device.get("deviceId") or device.get("device_id") or "").strip().casefold()
        candidate = index.get(mac) or (index.get("device-id:" + device_id) if device_id else None)
        if not candidate or not candidate.get("ip"):
            continue
        device["ip"] = candidate["ip"]
        device["ipSource"] = "ddio"
        device.setdefault("fieldSources", {})["ip"] = "DDIO"
        device["possibleIps"] = list(candidate.get("possibleIps") or [candidate["ip"]])
        updated += 1
    return updated


def build_ddio_overlay_from_index(
    candidates: dict[str, dict[str, Any]],
    switch_changes: Any,
    current_ip_by_mac: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    changes = switch_changes if isinstance(switch_changes, dict) else normalize_switch_changes(switch_changes)

    overlay: dict[str, dict[str, Any]] = {}
    for mac, change in changes.items():
        candidate = candidates.get(mac)
        if not candidate:
            continue
        possible_ips = [value for value in candidate.get("possibleIps", [candidate["ip"]]) if value]
        if not possible_ips:
            continue
        overlay[mac] = {
            "ip": candidate["ip"] if candidate["ip"] in possible_ips else possible_ips[0],
            "possibleIps": possible_ips,
            "match": candidate["match"],
            "source": "DDIO",
            "previousSwitchIp": change["before"],
            "currentSwitchIp": change["after"],
        }
    return overlay

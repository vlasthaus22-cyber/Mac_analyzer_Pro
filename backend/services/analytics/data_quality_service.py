import ipaddress
import re
from collections import Counter
from typing import Any


MAC_RE = re.compile(r"^[0-9A-F]{12}$")


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _mac(value: Any) -> str:
    return re.sub(r"[^0-9A-F]", "", _text(value).upper())


def _is_unknown_vendor(value: Any) -> bool:
    text = _text(value).lower()
    return text in {"", "unknown", "not found", "n/a", "не определено", "неизвестно"}


def _valid_ip(value: Any) -> bool:
    text = _text(value)
    if not text:
        return True
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return False
    return True


def _issue(issue_id: str, title: str, count: int, severity: str, recommendation: str) -> dict[str, Any]:
    return {
        "id": issue_id,
        "title": title,
        "count": count,
        "severity": severity,
        "recommendation": recommendation,
    }


def analyze_data_quality(devices: list[dict[str, Any]], invalid: list[Any] | None = None) -> dict[str, Any]:
    invalid = invalid or []
    normalized_devices = [device for device in devices if isinstance(device, dict)]
    total = len(normalized_devices)
    macs = [_mac(device.get("mac") or device.get("macFormatted")) for device in normalized_devices]
    mac_counts = Counter(mac for mac in macs if mac)
    duplicate_devices = sum(count - 1 for count in mac_counts.values() if count > 1)
    malformed_macs = sum(1 for mac in macs if mac and not MAC_RE.match(mac))
    missing_mac = sum(1 for mac in macs if not mac)
    unknown_vendors = sum(1 for device in normalized_devices if _is_unknown_vendor(device.get("vendor")))
    missing_models = sum(1 for device in normalized_devices if not _text(device.get("model")))
    missing_ips = sum(1 for device in normalized_devices if not _text(device.get("ip")))
    malformed_ips = sum(1 for device in normalized_devices if not _valid_ip(device.get("ip")))
    missing_switches = sum(1 for device in normalized_devices if not _text(device.get("switchIp")))
    malformed_switches = sum(1 for device in normalized_devices if not _valid_ip(device.get("switchIp")))
    missing_rooms = sum(1 for device in normalized_devices if not _text(device.get("room")))
    missing_ports = sum(1 for device in normalized_devices if not _text(device.get("switchPort")))
    source_counts = Counter(_text(device.get("source")) or "unknown" for device in normalized_devices)
    dominant_source = source_counts.most_common(1)[0] if source_counts else ("", 0)

    issues = [
        _issue("invalid_rows", "Invalid source rows", len(invalid), "high", "Review rejected rows and column mapping before saving history."),
        _issue("duplicate_macs", "Duplicate MAC addresses", duplicate_devices, "high", "Merge duplicate records or keep the newest switch/port observation."),
        _issue("malformed_macs", "Malformed MAC values", malformed_macs + missing_mac, "high", "Normalize MAC format and verify the MAC column detector."),
        _issue("unknown_vendors", "Unknown vendors", unknown_vendors, "medium", "Run OUI/API enrichment or add custom vendor mappings."),
        _issue("missing_models", "Missing models", missing_models, "medium", "Learn model prefixes from history or add model mappings."),
        _issue("missing_ips", "Missing IP addresses", missing_ips, "medium", "Import IP data or enable additional enrichment columns."),
        _issue("malformed_ips", "Malformed IP addresses", malformed_ips, "high", "Correct IP columns and remove non-IP text values."),
        _issue("missing_switches", "Missing switch IP", missing_switches, "medium", "Map switch columns and import switch inventory data."),
        _issue("malformed_switches", "Malformed switch IP", malformed_switches, "medium", "Check switch IP mapping and source column selection."),
        _issue("missing_rooms", "Missing rooms", missing_rooms, "low", "Use IP-to-address mapping or room columns to improve location analytics."),
        _issue("missing_ports", "Missing switch ports", missing_ports, "low", "Map switch port columns for topology and movement tracking."),
    ]
    issues = [issue for issue in issues if issue["count"] > 0]

    if total:
        completeness_fields = ("vendor", "model", "ip", "room", "switchIp", "switchPort")
        filled = sum(1 for device in normalized_devices for field in completeness_fields if _text(device.get(field)) and not (field == "vendor" and _is_unknown_vendor(device.get(field))))
        completeness = round(filled / (total * len(completeness_fields)) * 100, 2)
    else:
        completeness = 0.0

    penalty = 0
    weights = {"high": 10, "medium": 6, "low": 3}
    for issue in issues:
        ratio = issue["count"] / max(1, total)
        penalty += min(weights[issue["severity"]] * 3, weights[issue["severity"]] * ratio * 10)
    score = max(0, min(100, round(100 - penalty, 2)))
    if total == 0:
        score = 0
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"

    recommendations = [issue["recommendation"] for issue in sorted(issues, key=lambda item: {"high": 0, "medium": 1, "low": 2}[item["severity"]])[:6]]
    if dominant_source[1] == total and total > 25:
        recommendations.append("Compare this upload with another source to catch hidden column or inventory drift.")

    return {
        "score": score,
        "grade": grade,
        "summary": {
            "devices": total,
            "invalidRows": len(invalid),
            "uniqueMacs": len(mac_counts),
            "duplicates": duplicate_devices,
            "completeness": completeness,
            "sources": len(source_counts),
        },
        "issues": issues,
        "recommendations": recommendations,
        "dominantSource": {"name": dominant_source[0], "devices": dominant_source[1]},
    }

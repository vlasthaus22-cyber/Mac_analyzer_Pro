"""Apply detector suggestions to a final result without replacing user data."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def apply_missing_detection_fields(
    devices: list[dict[str, Any]],
    detector: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Fill only missing address/vendor/model fields using one prepared detector."""
    updated_devices: list[dict[str, Any]] = []
    filled = {"address": 0, "vendor": 0, "model": 0}
    changed_devices = 0
    for item in devices:
        current = dict(item) if isinstance(item, dict) else {}
        detected = detector(current)
        changed = False
        vendor = _text(current.get("vendor"))
        detected_vendor = _text(detected.get("vendor"))
        if vendor in {"", "Unknown", "Не определено"} and detected_vendor not in {"", "Unknown", "Не определено"}:
            for field in ("vendor", "vendorSource", "vendorConfidence", "vendorMatchedPrefix"):
                current[field] = detected.get(field)
            filled["vendor"] += 1
            changed = True
        if not _text(current.get("model")) and _text(detected.get("model")):
            for field in ("model", "modelSource", "modelConfidence", "modelMatchedPrefix"):
                current[field] = detected.get(field)
            filled["model"] += 1
            changed = True
        if not _text(current.get("address")) and _text(detected.get("address")):
            current["address"] = detected.get("address")
            current["addressSource"] = _text(detected.get("addressSource")) or (
                "ip_mapping" if _text(current.get("switchIp") or current.get("switch_ip")) else "history"
            )
            if detected.get("addressConfidence") is not None:
                current["addressConfidence"] = detected.get("addressConfidence")
            current["fieldSources"] = {
                **(current.get("fieldSources") or {}),
                "address": current["addressSource"],
            }
            filled["address"] += 1
            changed = True
        if changed:
            changed_devices += 1
        updated_devices.append(current)
    return {
        "devices": updated_devices,
        "summary": {"devices": len(updated_devices), "changedDevices": changed_devices, **filled},
    }

import re
from typing import Any


def normalize_hex(value: Any) -> str:
    return re.sub(r"[^0-9A-Fa-f]", "", str(value or "")).upper()


def format_oui(value: Any, length: int = 3, style: str = "plain") -> str:
    normalized = normalize_hex(value)
    byte_length = max(3, min(int(length or 3), 6))
    prefix = normalized[: byte_length * 2]
    if len(prefix) < byte_length * 2:
        return ""
    fmt = (style or "plain").lower()
    pairs = [prefix[index:index + 2] for index in range(0, len(prefix), 2)]
    if fmt == "colon":
        return ":".join(pairs)
    if fmt == "dash":
        return "-".join(pairs)
    if fmt in {"dot", "cisco-dot"}:
        groups = [prefix[index:index + 4] for index in range(0, len(prefix), 4)]
        return ".".join(groups)
    return prefix


def format_oui_for_devices(devices: list[dict[str, Any]], length: int = 3, style: str = "plain") -> list[dict[str, str]]:
    result = []
    for device in devices:
        mac = device.get("mac") or device.get("macFormatted") or device.get("oui")
        result.append({
            "mac": normalize_hex(mac)[:12],
            "oui": format_oui(mac, length, style),
        })
    return result

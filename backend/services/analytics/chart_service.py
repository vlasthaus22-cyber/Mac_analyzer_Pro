import html
import json
from datetime import datetime
from typing import Any


def _text(value: Any, fallback: str = "") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def _count(values: list[str], limit: int = 12) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for value in values:
        key = value or "Unknown"
        counts[key] = counts.get(key, 0) + 1
    return [
        {"label": label, "value": value}
        for label, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _timeline(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points = []
    for snapshot in sorted(snapshots, key=lambda item: _text(item.get("createdAt") or item.get("created_at"))):
        devices = snapshot.get("devices", [])
        if not isinstance(devices, list):
            devices = []
        count = int(snapshot.get("deviceCount") or snapshot.get("device_count") or len(devices))
        points.append({
            "label": _text(snapshot.get("createdAt") or snapshot.get("created_at") or snapshot.get("name")),
            "value": count,
        })
    return points


def build_chart_payload(devices: list[dict[str, Any]], snapshots: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    snapshots = snapshots or []
    valid_devices = [device for device in devices if isinstance(device, dict)]
    invalid_mac_count = sum(1 for device in valid_devices if not _text(device.get("mac") or device.get("macFormatted")))
    unknown_vendor_count = sum(1 for device in valid_devices if _text(device.get("vendor"), "Unknown") == "Unknown")

    charts = [
        {"id": "vendors", "title": "Производители", "type": "bar", "items": _count([_text(device.get("vendor"), "Unknown") for device in valid_devices])},
        {"id": "models", "title": "Модели", "type": "bar", "items": _count([_text(device.get("model"), "Не определено") for device in valid_devices])},
        {"id": "rooms", "title": "Помещения", "type": "donut", "items": _count([_text(device.get("room"), "Не указано") for device in valid_devices])},
        {"id": "switches", "title": "Коммутаторы", "type": "bar", "items": _count([_text(device.get("switchIp") or device.get("switch_ip"), "Не указан") for device in valid_devices])},
        {
            "id": "quality",
            "title": "Качество данных",
            "type": "bar",
            "items": [
                {"label": "Устройств", "value": len(valid_devices)},
                {"label": "Неизвестный вендор", "value": unknown_vendor_count},
                {"label": "Без MAC", "value": invalid_mac_count},
                {"label": "Без IP", "value": sum(1 for device in valid_devices if not _text(device.get("ip")))},
                {"label": "Без помещения", "value": sum(1 for device in valid_devices if not _text(device.get("room")))},
            ],
        },
        {"id": "timeline", "title": "Динамика снимков", "type": "line", "items": _timeline(snapshots)},
    ]
    return {
        "summary": {
            "devices": len(valid_devices),
            "vendors": len({ _text(device.get("vendor")) for device in valid_devices if _text(device.get("vendor")) }),
            "models": len({ _text(device.get("model")) for device in valid_devices if _text(device.get("model")) }),
            "rooms": len({ _text(device.get("room")) for device in valid_devices if _text(device.get("room")) }),
            "snapshots": len(snapshots),
        },
        "charts": charts,
    }


def export_charts_svg(payload: dict[str, Any]) -> dict[str, str]:
    charts = payload.get("charts", [])
    width = 960
    row_height = 150
    height = max(220, 80 + row_height * len(charts))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="32" y="42" font-family="Arial" font-size="24" font-weight="700">MAC Analyzer Charts</text>',
        f'<text x="32" y="66" font-family="Arial" font-size="12" fill="#667085">Created: {html.escape(datetime.utcnow().isoformat(timespec="seconds"))}Z</text>',
    ]
    y = 105
    for chart in charts:
        items = chart.get("items", [])[:8]
        max_value = max([int(item.get("value") or 0) for item in items] + [1])
        parts.append(f'<text x="32" y="{y}" font-family="Arial" font-size="18" font-weight="700">{html.escape(_text(chart.get("title")))}</text>')
        bar_y = y + 18
        for item in items:
            label = html.escape(_text(item.get("label")))
            value = int(item.get("value") or 0)
            bar_width = int(620 * value / max_value) if max_value else 0
            parts.append(f'<text x="32" y="{bar_y + 14}" font-family="Arial" font-size="12" fill="#344054">{label}</text>')
            parts.append(f'<rect x="210" y="{bar_y}" width="{bar_width}" height="18" rx="4" fill="#2563eb"/>')
            parts.append(f'<text x="{220 + bar_width}" y="{bar_y + 14}" font-family="Arial" font-size="12" fill="#111827">{value}</text>')
            bar_y += 24
        y += row_height
    parts.append("</svg>")
    return {
        "filename": "mac-charts.svg",
        "mimeType": "image/svg+xml",
        "content": "".join(parts),
    }


def export_charts_json(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "filename": "mac-charts.json",
        "mimeType": "application/json",
        "content": json.dumps(payload, ensure_ascii=False, indent=2),
    }

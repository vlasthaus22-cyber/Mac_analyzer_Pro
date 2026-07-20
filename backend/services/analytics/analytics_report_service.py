"""Text analytics report ported from the PyQt AnalyticsDialog."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any


UNKNOWN_VALUES = {"", "Unknown", "Не указано"}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _field(device: dict[str, Any], *names: str) -> str:
    for name in names:
        value = _text(device.get(name))
        if value:
            return value
    return ""


def _is_filled(value: Any) -> bool:
    return _text(value) not in UNKNOWN_VALUES


def _ranked(counter: Counter[str], total: int, limit: int = 20) -> list[dict[str, Any]]:
    return [
        {"label": label, "count": count, "percent": round(count / total * 100, 1)}
        for label, count in counter.most_common(limit)
    ]


def build_analytics_report(devices: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the same report sections and percentages as AnalyticsDialog."""
    if not isinstance(devices, list):
        raise ValueError("devices must be an array")
    if any(not isinstance(device, dict) for device in devices):
        raise ValueError("every device must be an object")

    total = len(devices)
    if not total:
        return {
            "total": 0,
            "vendors": [],
            "models": [],
            "rooms": [],
            "roomOccupancy": {
                "assignedDevices": 0,
                "unassignedDevices": 0,
                "assignedPercent": 0.0,
                "uniqueRooms": 0,
                "averageDevicesPerRoom": 0.0,
                "mostOccupied": None,
                "rooms": [],
            },
            "coverage": {
                "uniqueVendors": 0,
                "uniqueModels": 0,
                "address": {"count": 0, "percent": 0.0},
                "room": {"count": 0, "percent": 0.0},
                "ip": {"count": 0, "percent": 0.0},
                "switch": {"count": 0, "percent": 0.0},
            },
            "reportText": "Нет данных",
        }

    vendors = Counter(_field(device, "vendor") or "Unknown" for device in devices)
    models = Counter(value for device in devices if (value := _field(device, "model")))
    rooms = Counter(value for device in devices if (value := _field(device, "room")))
    with_address = sum(_is_filled(_field(device, "address")) for device in devices)
    with_room = sum(_is_filled(_field(device, "room")) for device in devices)
    with_ip = sum(_is_filled(_field(device, "ip")) for device in devices)
    with_switch = sum(_is_filled(_field(device, "switchIp", "switch_ip")) for device in devices)

    ranked_vendors = _ranked(vendors, total)
    ranked_models = _ranked(models, total)
    ranked_rooms = _ranked(rooms, total)
    occupied_rooms = Counter(
        room for device in devices
        if (room := _field(device, "room")) and _is_filled(room)
    )
    room_occupancy_rows = [
        {
            "label": label,
            "count": count,
            "percentOfAssigned": round(count / max(1, with_room) * 100, 1),
            "percentOfAll": round(count / total * 100, 1),
        }
        for label, count in occupied_rooms.most_common(50)
    ]
    room_occupancy = {
        "assignedDevices": with_room,
        "unassignedDevices": total - with_room,
        "assignedPercent": round(with_room / total * 100, 1),
        "uniqueRooms": len(occupied_rooms),
        "averageDevicesPerRoom": round(with_room / max(1, len(occupied_rooms)), 1) if occupied_rooms else 0.0,
        "mostOccupied": room_occupancy_rows[0] if room_occupancy_rows else None,
        "rooms": room_occupancy_rows,
    }
    coverage = {
        "uniqueVendors": len(vendors),
        "uniqueModels": len(models),
        "address": {"count": with_address, "percent": round(with_address / total * 100, 1)},
        "room": {"count": with_room, "percent": round(with_room / total * 100, 1)},
        "ip": {"count": with_ip, "percent": round(with_ip / total * 100, 1)},
        "switch": {"count": with_switch, "percent": round(with_switch / total * 100, 1)},
    }

    lines = ["=== АНАЛИТИКА ПО УСТРОЙСТВАМ ===", "", f"Всего устройств: {total}", "", "=== ПРОИЗВОДИТЕЛИ ==="]
    lines.extend(f"  {item['label']}: {item['count']} ({item['percent']:.1f}%)" for item in ranked_vendors)
    lines.extend(["", "=== МОДЕЛИ ==="])
    lines.extend(f"  {item['label']}: {item['count']} ({item['percent']:.1f}%)" for item in ranked_models)
    lines.extend(["", "=== ПОМЕЩЕНИЯ ==="])
    lines.extend(f"  {item['label']}: {item['count']} ({item['percent']:.1f}%)" for item in ranked_rooms)
    lines.extend([
        "",
        "=== ЗАПОЛНЕННОСТЬ ===",
        f"  Производитель: {coverage['uniqueVendors']} уникальных",
        f"  Модель: {coverage['uniqueModels']} уникальных",
        f"  Адрес: {with_address} ({coverage['address']['percent']:.1f}%)",
        f"  Помещение: {with_room} ({coverage['room']['percent']:.1f}%)",
        f"  IP-адрес: {with_ip} ({coverage['ip']['percent']:.1f}%)",
        f"  Коммутатор: {with_switch} ({coverage['switch']['percent']:.1f}%)",
        "",
        "=== ЗАПОЛНЕННОСТЬ ПОМЕЩЕНИЙ ===",
        f"  Распределено по помещениям: {with_room} ({room_occupancy['assignedPercent']:.1f}%)",
        f"  Без помещения: {room_occupancy['unassignedDevices']}",
        f"  Уникальных помещений: {room_occupancy['uniqueRooms']}",
        f"  Среднее устройств на помещение: {room_occupancy['averageDevicesPerRoom']:.1f}",
    ])
    return {
        "total": total,
        "vendors": ranked_vendors,
        "models": ranked_models,
        "rooms": ranked_rooms,
        "roomOccupancy": room_occupancy,
        "coverage": coverage,
        "reportText": "\n".join(lines),
    }


def export_analytics_report_txt(report: dict[str, Any]) -> dict[str, str]:
    return {
        "filename": f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        "mimeType": "text/plain",
        "content": _text(report.get("reportText"), "Нет данных"),
    }

"""Smartroom room identity normalization.

The product treats a Smartroom identifier as the full room name.  Keeping the
numbered suffix is important: ``Переговорная 1`` and ``Переговорная 2`` are
different rooms and must never be grouped under a shortened label.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


def normalized_room_name(value: Any) -> str:
    """Return a display-safe room name without removing meaningful suffixes."""
    return re.sub(r"\s+", " ", str(value or "").strip())


def smartroom_identity(
    room: Any,
    smartroom_id: Any,
    mappings: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    """Return identical ``(room, smartroom_id)`` values for one exact room."""
    room_name = normalized_room_name(room)
    legacy_id = normalized_room_name(smartroom_id)
    mapping = mappings if isinstance(mappings, Mapping) else {}
    canonical = room_name or normalized_room_name(mapping.get(legacy_id)) or legacy_id
    return canonical, canonical


def synchronize_smartroom_device(
    device: dict[str, Any],
    mappings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize a device in place and retain an old-id lookup when present."""
    legacy_id = normalized_room_name(device.get("smartroomId") or device.get("smartroom_id"))
    room, smartroom_id = smartroom_identity(device.get("room"), legacy_id, mappings)
    device["room"] = room
    device["smartroomId"] = smartroom_id
    device.pop("smartroom_id", None)
    if isinstance(mappings, dict) and room:
        mappings[room] = room
        if legacy_id:
            mappings[legacy_id] = room
    return device

"""Smartroom identifier and room-name normalization.

``smartroomId`` is a stable room identity used for counting and matching.
``room`` is the separate display name.  Neither field may overwrite the other.
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
    """Return a normalized room name and the original Smartroom identifier."""
    room_name = normalized_room_name(room)
    normalized_id = normalized_room_name(smartroom_id)
    mapping = mappings if isinstance(mappings, Mapping) else {}
    resolved_room = room_name or normalized_room_name(mapping.get(normalized_id))
    return resolved_room, normalized_id


def synchronize_smartroom_device(
    device: dict[str, Any],
    mappings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize both independent fields and learn an ID-to-room mapping."""
    original_id = normalized_room_name(device.get("smartroomId") or device.get("smartroom_id"))
    room, smartroom_id = smartroom_identity(device.get("room"), original_id, mappings)
    device["room"] = room
    device["smartroomId"] = smartroom_id
    device.pop("smartroom_id", None)
    if isinstance(mappings, dict) and smartroom_id and room:
        mappings[smartroom_id] = room
    return device

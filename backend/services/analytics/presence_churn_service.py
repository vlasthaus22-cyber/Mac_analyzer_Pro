"""Presence churn analytics across ordered final snapshots."""

from __future__ import annotations

import re
from typing import Any


def _mac(value: Any) -> str:
    normalized = re.sub(r"[^0-9A-F]", "", str(value or "").upper())
    return normalized if len(normalized) == 12 else ""


def build_presence_churn(snapshots: list[dict[str, Any]], query: str = "", limit: int = 500) -> dict[str, Any]:
    previous: set[str] = set()
    records: dict[str, dict[str, Any]] = {}
    for snapshot in snapshots or []:
        current: dict[str, dict[str, Any]] = {}
        for device in snapshot.get("devices") or []:
            mac = _mac(device.get("mac") or device.get("macFormatted"))
            if mac and mac not in current:
                current[mac] = device
        stamp = str(snapshot.get("fileCreatedAt") or snapshot.get("createdAt") or snapshot.get("savedAt") or "")
        for mac in previous - current.keys():
            item = records.get(mac)
            if item and item["presentLast"]:
                item["disappearances"] += 1
                item["transitions"].append({"type": "absent", "snapshotId": str(snapshot.get("id") or ""), "name": str(snapshot.get("name") or ""), "date": stamp})
                item["presentLast"] = False
        for mac, device in current.items():
            item = records.setdefault(mac, {"mac": mac, "macFormatted": ":".join(mac[i:i + 2] for i in range(0, 12, 2)), "presentCount": 0, "disappearances": 0, "reappearances": 0, "transitions": [], "presentLast": False, "everSeen": False, "firstSeen": stamp})
            if item["everSeen"] and not item["presentLast"]:
                item["reappearances"] += 1
                item["transitions"].append({"type": "present", "snapshotId": str(snapshot.get("id") or ""), "name": str(snapshot.get("name") or ""), "date": stamp})
            for target, *keys in (("vendor", "vendor"), ("model", "model"), ("ip", "ip"), ("room", "room"), ("address", "address"), ("smartroomId", "smartroomId", "smartroom_id")):
                value = next((str(device.get(key) or "").strip() for key in keys if str(device.get(key) or "").strip()), "")
                if value:
                    item[target] = value
            item["presentCount"] += 1
            item["lastSeen"] = stamp
            item["presentLast"] = True
            item["everSeen"] = True
        previous = set(current)
    needle = str(query or "").strip().lower()
    items = []
    for item in records.values():
        if not (item["disappearances"] and item["reappearances"]):
            continue
        row = {**item, "transitionCount": item["disappearances"] + item["reappearances"], "absentCount": max(0, len(snapshots) - item["presentCount"])}
        if needle and needle not in " ".join(str(value) for value in row.values()).lower():
            continue
        items.append(row)
    items.sort(key=lambda item: (-item["transitionCount"], -item["reappearances"], item["mac"]))
    return {"snapshotCount": len(snapshots), "total": len(items), "items": items[:max(1, int(limit or 500))]}

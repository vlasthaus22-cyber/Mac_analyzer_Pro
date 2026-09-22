"""Small bounded cache for decoded SQLite snapshot bodies.

The cache avoids decoding the same large JSON snapshot for every Analytics
panel while keeping memory bounded. Entries are invalidated by the database
row version, so an upsert can never return stale devices.
"""

from __future__ import annotations

from collections import OrderedDict
from threading import RLock
from typing import Any, Hashable


class SnapshotDeviceCache:
    def __init__(self, max_entries: int = 2, max_devices: int = 200_000, max_bytes: int = 96 * 1024 * 1024):
        self.max_entries = max(1, int(max_entries))
        self.max_devices = max(1, int(max_devices))
        self.max_bytes = max(1, int(max_bytes))
        self._entries: OrderedDict[str, tuple[Hashable, list[dict[str, Any]], int, int]] = OrderedDict()
        self._device_count = 0
        self._byte_count = 0
        self._lock = RLock()

    def get(self, snapshot_id: str, version: Hashable) -> list[dict[str, Any]] | None:
        with self._lock:
            entry = self._entries.get(snapshot_id)
            if entry is None or entry[0] != version:
                if entry is not None:
                    self._remove(snapshot_id)
                return None
            self._entries.move_to_end(snapshot_id)
            return entry[1]

    def put(self, snapshot_id: str, version: Hashable, devices: list[dict[str, Any]], byte_count: int = 0) -> None:
        if not snapshot_id or not isinstance(devices, list):
            return
        device_count = len(devices)
        payload_bytes = max(0, int(byte_count or 0))
        if device_count > self.max_devices or payload_bytes > self.max_bytes:
            self.invalidate(snapshot_id)
            return
        with self._lock:
            self._remove(snapshot_id)
            self._entries[snapshot_id] = (version, devices, device_count, payload_bytes)
            self._device_count += device_count
            self._byte_count += payload_bytes
            while (
                len(self._entries) > self.max_entries
                or self._device_count > self.max_devices
                or self._byte_count > self.max_bytes
            ):
                oldest = next(iter(self._entries))
                self._remove(oldest)

    def invalidate(self, snapshot_id: str | None = None) -> None:
        with self._lock:
            if snapshot_id is None:
                self._entries.clear()
                self._device_count = 0
                self._byte_count = 0
            else:
                self._remove(snapshot_id)

    def _remove(self, snapshot_id: str) -> None:
        entry = self._entries.pop(snapshot_id, None)
        if entry is not None:
            self._device_count -= entry[2]
            self._byte_count -= entry[3]

    def summary(self) -> dict[str, int]:
        with self._lock:
            return {"entries": len(self._entries), "devices": self._device_count, "bytes": self._byte_count}

"""Lazy offline lookup for the bundled IEEE Registration Authority data."""

from __future__ import annotations

import gzip
import json
import re
import threading
from pathlib import Path
from typing import Any


_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def registry_path(root: Path) -> Path:
    return Path(root) / "data" / "reference" / "ieee_registry.json.gz"


def load_registry(root: Path) -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is None:
            path = registry_path(root)
            if not path.is_file():
                _cache = {"vendors": [], "assignments": {}, "counts": {}, "total": 0}
            else:
                with gzip.open(path, "rt", encoding="utf-8") as source:
                    payload = json.load(source)
                vendors = payload.get("vendors") or []
                indexes: dict[int, dict[str, str]] = {}
                for raw_length, flat in (payload.get("assignments") or {}).items():
                    length = int(raw_length)
                    indexes[length] = {
                        str(flat[index]): str(vendors[int(flat[index + 1])])
                        for index in range(0, len(flat), 2)
                    }
                payload["indexes"] = indexes
                _cache = payload
    return _cache


def lookup_ieee_vendor(root: Path, mac_value: Any) -> dict[str, str] | None:
    mac = re.sub(r"[^0-9A-Fa-f]", "", str(mac_value or "")).upper()
    if len(mac) != 12:
        return None
    registry = load_registry(root)
    for length in (9, 7, 6):
        prefix = mac[:length]
        vendor = registry.get("indexes", {}).get(length, {}).get(prefix)
        if vendor:
            return {"vendor": vendor, "prefix": prefix, "source": "ieee"}
    return None


def ieee_registry_status(root: Path) -> dict[str, Any]:
    payload = load_registry(root)
    path = registry_path(root)
    return {
        "available": path.is_file(),
        "path": str(path),
        "generatedAt": payload.get("generatedAt"),
        "counts": payload.get("counts", {}),
        "total": int(payload.get("total") or 0),
    }


def clear_registry_cache() -> None:
    global _cache
    with _lock:
        _cache = None

"""Bounded cache for imported workspace tables with durable restart recovery."""

from __future__ import annotations

import json
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any


class WorkspaceCacheMiss(KeyError):
    """Raised when a browser token is unknown or has expired."""


class WorkspaceFileCache:
    _TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,128}$")

    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_entries: int = 24,
        max_rows: int = 500_000,
        storage_directory: str | Path | None = None,
    ):
        self.ttl_seconds = max(60, int(ttl_seconds))
        self.max_entries = max(1, int(max_entries))
        self.max_rows = max(1, int(max_rows))
        self.storage_directory = Path(storage_directory).resolve() if storage_directory else None
        self._entries: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        if self.storage_directory:
            self.storage_directory.mkdir(parents=True, exist_ok=True)
            self._prune_persisted()
            self._enforce_persisted_limit()

    def put(self, filename: str, table: dict[str, Any]) -> str:
        headers = list(table.get("headers") or [])
        rows = list(table.get("rows") or [])
        token = secrets.token_urlsafe(24)
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            self._entries[token] = {
                "filename": str(filename or "file"),
                "headers": headers,
                "rows": rows,
                "sheet": table.get("sheet", ""),
                "rowCount": len(rows),
                "created": now,
                "accessed": now,
            }
            self._persist(token, self._entries[token])
            self._enforce_limits()
        return token

    def get(self, token: str) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            cache_token = str(token or "")
            entry = self._entries.get(cache_token)
            if entry is None:
                entry = self._load_persisted(cache_token, now)
            if entry is None:
                raise WorkspaceCacheMiss(cache_token)
            entry["accessed"] = now
            self._touch_persisted(cache_token)
            return {
                "filename": entry["filename"],
                "headers": entry["headers"],
                "rows": entry["rows"],
                "sheet": entry["sheet"],
                "rowCount": entry["rowCount"],
            }

    def stats(self) -> dict[str, Any]:
        with self._lock:
            self._prune(time.monotonic())
            return {
                "entries": len(self._entries),
                "persistentEntries": len(self._persisted_paths()),
                "rows": sum(int(entry["rowCount"]) for entry in self._entries.values()),
                "ttlSeconds": self.ttl_seconds,
                "maxEntries": self.max_entries,
                "maxRows": self.max_rows,
                "storageDirectory": str(self.storage_directory) if self.storage_directory else "",
            }

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            for path in self._persisted_paths():
                path.unlink(missing_ok=True)

    def discard(self, token: str) -> None:
        """Remove one owned cache entry without disturbing other browser sessions."""
        cache_token = str(token or "")
        with self._lock:
            self._entries.pop(cache_token, None)
            self._delete_persisted(cache_token)

    def _prune(self, now: float) -> None:
        expired = [
            token for token, entry in self._entries.items()
            if now - float(entry["accessed"]) >= self.ttl_seconds
        ]
        for token in expired:
            self._entries.pop(token, None)
            self._delete_persisted(token)

    def _enforce_limits(self) -> None:
        def row_count() -> int:
            return sum(int(entry["rowCount"]) for entry in self._entries.values())

        while self._entries and (len(self._entries) > self.max_entries or (len(self._entries) > 1 and row_count() > self.max_rows)):
            oldest = min(self._entries, key=lambda token: float(self._entries[token]["accessed"]))
            self._entries.pop(oldest, None)
            self._delete_persisted(oldest)
        self._enforce_persisted_limit()

    def _persisted_paths(self) -> list[Path]:
        if not self.storage_directory:
            return []
        return [path for path in self.storage_directory.glob("*.json") if path.is_file()]

    def _disk_path(self, token: str) -> Path | None:
        if not self.storage_directory or not self._TOKEN_PATTERN.fullmatch(token):
            return None
        return self.storage_directory / f"{token}.json"

    def _persist(self, token: str, entry: dict[str, Any]) -> None:
        path = self._disk_path(token)
        if path is None:
            return
        temporary = path.with_suffix(".tmp")
        payload = {
            "filename": entry["filename"],
            "headers": entry["headers"],
            "rows": entry["rows"],
            "sheet": entry["sheet"],
            "rowCount": entry["rowCount"],
        }
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
        temporary.replace(path)

    def _load_persisted(self, token: str, now: float) -> dict[str, Any] | None:
        path = self._disk_path(token)
        if path is None or not path.exists():
            return None
        try:
            if time.time() - path.stat().st_mtime >= self.ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            with path.open("r", encoding="utf-8") as stream:
                payload = json.load(stream)
            rows = payload.get("rows")
            headers = payload.get("headers")
            if not isinstance(rows, list) or not isinstance(headers, list):
                raise ValueError("invalid workspace cache table")
            entry = {
                "filename": str(payload.get("filename") or "file"),
                "headers": headers,
                "rows": rows,
                "sheet": payload.get("sheet", ""),
                "rowCount": len(rows),
                "created": now,
                "accessed": now,
            }
            self._entries[token] = entry
            self._enforce_limits()
            return self._entries.get(token)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            return None

    def _touch_persisted(self, token: str) -> None:
        path = self._disk_path(token)
        if path and path.exists():
            path.touch()

    def _delete_persisted(self, token: str) -> None:
        path = self._disk_path(token)
        if path:
            path.unlink(missing_ok=True)

    def _prune_persisted(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        for path in self._persisted_paths():
            try:
                if path.stat().st_mtime <= cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                continue

    def _enforce_persisted_limit(self) -> None:
        paths = self._persisted_paths()
        if len(paths) <= self.max_entries:
            return
        paths.sort(key=lambda path: path.stat().st_mtime)
        for path in paths[: len(paths) - self.max_entries]:
            token = path.stem
            self._entries.pop(token, None)
            path.unlink(missing_ok=True)


def resolve_workspace_files(files: list[dict[str, Any]], cache: WorkspaceFileCache) -> list[dict[str, Any]]:
    """Expand cached browser file tokens into the row layout used by enrich_files."""
    resolved: list[dict[str, Any]] = []
    missing: list[str] = []
    for file_info in files:
        current = dict(file_info)
        token = str(current.get("fileToken") or "")
        supplied_rows = current.get("rows")
        if token and not supplied_rows:
            try:
                cached = cache.get(token)
            except WorkspaceCacheMiss:
                missing.append(token)
                continue
            current["rows"] = [cached["headers"], *cached["rows"]]
            current.setdefault("sheet", cached["sheet"])
            current.setdefault("name", cached["filename"])
        resolved.append(current)
    if missing:
        raise WorkspaceCacheMiss(",".join(missing))
    return resolved

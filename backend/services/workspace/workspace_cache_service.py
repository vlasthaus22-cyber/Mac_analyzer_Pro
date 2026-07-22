"""SQLite-backed workspace tables with bounded browser payloads."""

from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterator


class WorkspaceCacheMiss(KeyError):
    """Raised when a browser token is unknown or has expired."""


class WorkspaceFileCache:
    """Persist imported rows in SQLite and expose streaming row access.

    The browser retains only a token and a short preview. Full input tables are
    never held by this cache after ``put`` returns and are read row by row while
    an enrichment job is running.
    """

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
        if self.storage_directory:
            self.storage_directory.mkdir(parents=True, exist_ok=True)
            self.database_path = self.storage_directory / "workspace_cache.db"
        else:
            self.database_path = None
        self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False) if self.database_path is None else None
        self._lock = threading.RLock()
        self._initialize()
        self._prune()
        self._enforce_limits()

    def _connect(self) -> sqlite3.Connection:
        connection = self._memory_connection or sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if self.database_path is not None:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    def _close(self, connection: sqlite3.Connection) -> None:
        if connection is not self._memory_connection:
            connection.close()

    def _initialize(self) -> None:
        with self._lock:
            connection = self._connect()
            try:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS workspace_files (
                        token TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        headers_json TEXT NOT NULL,
                        sheet TEXT NOT NULL DEFAULT '',
                        row_count INTEGER NOT NULL,
                        created_at REAL NOT NULL,
                        accessed_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS workspace_rows (
                        token TEXT NOT NULL,
                        row_number INTEGER NOT NULL,
                        row_json TEXT NOT NULL,
                        PRIMARY KEY (token, row_number),
                        FOREIGN KEY (token) REFERENCES workspace_files(token) ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS idx_workspace_files_accessed
                    ON workspace_files(accessed_at);
                    """
                )
                connection.commit()
            finally:
                self._close(connection)

    def put(self, filename: str, table: dict[str, Any]) -> str:
        headers = list(table.get("headers") or [])
        rows = table.get("rows") or []
        token = secrets.token_urlsafe(24)
        now = time.time()
        with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    "INSERT INTO workspace_files (token, filename, headers_json, sheet, row_count, created_at, accessed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (token, str(filename or "file"), json.dumps(headers, ensure_ascii=False), str(table.get("sheet") or ""), len(rows), now, now),
                )
                connection.executemany(
                    "INSERT INTO workspace_rows (token, row_number, row_json) VALUES (?, ?, ?)",
                    ((token, index, json.dumps(list(row), ensure_ascii=False, separators=(",", ":"))) for index, row in enumerate(rows)),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                self._close(connection)
            self._prune(now)
            self._enforce_limits(protected_token=token)
        return token

    def metadata(self, token: str, touch: bool = True) -> dict[str, Any]:
        cache_token = str(token or "")
        with self._lock:
            self._prune()
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT filename, headers_json, sheet, row_count FROM workspace_files WHERE token = ?",
                    (cache_token,),
                ).fetchone()
                if row is None:
                    raise WorkspaceCacheMiss(cache_token)
                if touch:
                    connection.execute("UPDATE workspace_files SET accessed_at = ? WHERE token = ?", (time.time(), cache_token))
                    connection.commit()
                return {
                    "filename": row["filename"],
                    "headers": json.loads(row["headers_json"] or "[]"),
                    "sheet": row["sheet"],
                    "rowCount": int(row["row_count"]),
                }
            finally:
                self._close(connection)

    def iter_rows(self, token: str, batch_size: int = 1000) -> Iterator[list[Any]]:
        cache_token = str(token or "")
        self.metadata(cache_token)
        with self._lock:
            connection = self._connect()
            try:
                cursor = connection.execute(
                    "SELECT row_json FROM workspace_rows WHERE token = ? ORDER BY row_number",
                    (cache_token,),
                )
                while True:
                    batch = cursor.fetchmany(max(1, int(batch_size)))
                    if not batch:
                        break
                    for row in batch:
                        value = json.loads(row["row_json"] or "[]")
                        yield value if isinstance(value, list) else []
            finally:
                self._close(connection)

    def get(self, token: str) -> dict[str, Any]:
        metadata = self.metadata(token)
        return {**metadata, "rows": list(self.iter_rows(token))}

    def stats(self) -> dict[str, Any]:
        with self._lock:
            self._prune()
            connection = self._connect()
            try:
                summary = connection.execute(
                    "SELECT COUNT(*) AS entries, COALESCE(SUM(row_count), 0) AS rows FROM workspace_files"
                ).fetchone()
                size_bytes = self.database_path.stat().st_size if self.database_path and self.database_path.exists() else 0
                return {
                    "entries": int(summary["entries"]),
                    "persistentEntries": int(summary["entries"]) if self.database_path else 0,
                    "rows": int(summary["rows"]),
                    "memoryRows": 0,
                    "ttlSeconds": self.ttl_seconds,
                    "maxEntries": self.max_entries,
                    "maxRows": self.max_rows,
                    "storageDirectory": str(self.storage_directory) if self.storage_directory else "",
                    "databasePath": str(self.database_path) if self.database_path else ":memory:",
                    "databaseBytes": size_bytes,
                }
            finally:
                self._close(connection)

    def clear(self) -> None:
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("DELETE FROM workspace_files")
                connection.commit()
            finally:
                self._close(connection)

    def discard(self, token: str) -> None:
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("DELETE FROM workspace_files WHERE token = ?", (str(token or ""),))
                connection.commit()
            finally:
                self._close(connection)

    def _prune(self, now: float | None = None) -> None:
        cutoff = (now or time.time()) - self.ttl_seconds
        connection = self._connect()
        try:
            connection.execute("DELETE FROM workspace_files WHERE accessed_at <= ?", (cutoff,))
            connection.commit()
        finally:
            self._close(connection)

    def _enforce_limits(self, protected_token: str = "") -> None:
        connection = self._connect()
        try:
            while True:
                summary = connection.execute(
                    "SELECT COUNT(*) AS entries, COALESCE(SUM(row_count), 0) AS rows FROM workspace_files"
                ).fetchone()
                if int(summary["entries"]) <= self.max_entries and int(summary["rows"]) <= self.max_rows:
                    break
                candidate = connection.execute(
                    "SELECT token FROM workspace_files WHERE token <> ? ORDER BY accessed_at, created_at LIMIT 1",
                    (protected_token,),
                ).fetchone()
                if candidate is None:
                    break
                connection.execute("DELETE FROM workspace_files WHERE token = ?", (candidate["token"],))
            connection.commit()
        finally:
            self._close(connection)


def resolve_workspace_files(files: list[dict[str, Any]], cache: WorkspaceFileCache) -> list[dict[str, Any]]:
    """Compatibility resolver for routes that still require complete row arrays."""
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


def prepare_workspace_files(files: list[dict[str, Any]], cache: WorkspaceFileCache) -> list[dict[str, Any]]:
    """Validate tokens and attach metadata without loading full tables."""
    prepared: list[dict[str, Any]] = []
    missing: list[str] = []
    for file_info in files:
        current = dict(file_info)
        token = str(current.get("fileToken") or "")
        if token and not current.get("rows"):
            try:
                cached = cache.metadata(token)
            except WorkspaceCacheMiss:
                missing.append(token)
                continue
            current.setdefault("sheet", cached["sheet"])
            current.setdefault("name", cached["filename"])
            current["headers"] = cached["headers"]
            current["rowCount"] = cached["rowCount"]
        prepared.append(current)
    if missing:
        raise WorkspaceCacheMiss(",".join(missing))
    return prepared


def workspace_row_iterator(file_info: dict[str, Any], cache: WorkspaceFileCache) -> Iterator[list[Any]]:
    token = str(file_info.get("fileToken") or "")
    supplied_rows = file_info.get("rows")
    if token and not supplied_rows:
        yield from cache.iter_rows(token)
        return
    rows = supplied_rows or []
    start = 1 if rows and isinstance(rows[0], list) else 0
    for row in rows[start:]:
        if isinstance(row, list):
            yield row

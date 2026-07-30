"""Engineering-mode session lifecycle and permission validation."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Any, Callable, ContextManager, Optional


DEFAULT_ENGINEERING_PERMISSIONS = (
    "delete:history",
    "delete:snapshots",
    "delete:mappings",
    "delete:tasks",
    "delete:ip-mappings",
    "delete:api-cache",
    "write:settings",
    "write:migration",
)


def engineering_token_hash(token: Any) -> str:
    token_text = str(token).strip() if token is not None else ""
    return hashlib.sha256(token_text.encode("utf-8")).hexdigest()


def normalize_engineering_ttl(ttl_minutes: Any = 480) -> int:
    try:
        normalized = int(ttl_minutes or 480)
    except (TypeError, ValueError):
        normalized = 480
    return min(1440, max(1, normalized))


class EngineeringSessionService:
    def __init__(
        self,
        connection_factory: Callable[[], ContextManager[Any]],
        utc_now: Callable[[], str],
        permissions: tuple[str, ...] | list[str] = DEFAULT_ENGINEERING_PERMISSIONS,
        datetime_now: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        self._connection_factory = connection_factory
        self._utc_now = utc_now
        self._permissions = tuple(permissions)
        self._datetime_now = datetime_now

    def issue(self, ttl_minutes: Any = 480) -> dict[str, Any]:
        token = secrets.token_urlsafe(32)
        created_at = self._utc_now()
        expires_at = (
            self._datetime_now() + timedelta(minutes=normalize_engineering_ttl(ttl_minutes))
        ).replace(microsecond=0).isoformat() + "Z"
        session = {
            "token": token,
            "role": "engineer",
            "permissions": list(self._permissions),
            "expiresAt": expires_at,
            "createdAt": created_at,
        }
        with self._connection_factory() as conn:
            conn.execute(
                "INSERT INTO engineering_sessions "
                "(token_hash, role, permissions_json, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    engineering_token_hash(token),
                    session["role"],
                    json.dumps(session["permissions"]),
                    created_at,
                    expires_at,
                ),
            )
        return session

    def validate(self, token: Any, permission: str = "") -> Optional[dict[str, Any]]:
        token_text = str(token).strip() if token is not None else ""
        if not token_text:
            return None
        with self._connection_factory() as conn:
            row = conn.execute(
                "SELECT role, permissions_json, created_at, expires_at, revoked_at "
                "FROM engineering_sessions WHERE token_hash = ?",
                (engineering_token_hash(token_text),),
            ).fetchone()
        if not row or row["revoked_at"]:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", ""))
        if expires_at <= self._datetime_now():
            return None
        permissions = json.loads(row["permissions_json"])
        if permission and permission not in permissions:
            return None
        return {
            "role": row["role"],
            "permissions": permissions,
            "createdAt": row["created_at"],
            "expiresAt": row["expires_at"],
        }

    def revoke(self, token: Any) -> bool:
        with self._connection_factory() as conn:
            cursor = conn.execute(
                "UPDATE engineering_sessions SET revoked_at = ? "
                "WHERE token_hash = ? AND revoked_at IS NULL",
                (self._utc_now(), engineering_token_hash(token)),
            )
        return cursor.rowcount > 0

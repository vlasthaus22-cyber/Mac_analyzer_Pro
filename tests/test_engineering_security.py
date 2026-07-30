from datetime import datetime, timedelta

from server import (
    ENGINEERING_PERMISSIONS,
    ENGINEERING_SESSION_SERVICE,
    db_connection,
    engineering_token_hash,
    init_database,
    issue_engineering_session,
    normalize_engineering_ttl,
    revoke_engineering_session,
    utc_now,
    validate_engineering_session,
)


def test_engineering_domain_logic_is_owned_by_system_service():
    assert engineering_token_hash.__module__ == "backend.services.system.engineering_service"
    assert normalize_engineering_ttl.__module__ == "backend.services.system.engineering_service"
    assert ENGINEERING_SESSION_SERVICE.__class__.__module__ == "backend.services.system.engineering_service"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM engineering_sessions")
        conn.execute("DELETE FROM app_logs WHERE action = 'Engineering login'")


def test_engineering_session_token_permissions_and_revocation():
    init_database()
    cleanup()

    session = issue_engineering_session(ttl_minutes=15)
    assert session["role"] == "engineer"
    assert "delete:history" in session["permissions"]
    assert session["permissions"] == ENGINEERING_PERMISSIONS

    token_hash = engineering_token_hash(session["token"])
    with db_connection() as conn:
        row = conn.execute("SELECT token_hash, permissions_json, revoked_at FROM engineering_sessions").fetchone()
    assert row["token_hash"] == token_hash
    assert row["token_hash"] != session["token"]
    assert row["revoked_at"] is None

    assert validate_engineering_session(session["token"], "delete:history")["role"] == "engineer"
    assert validate_engineering_session(session["token"], "missing:permission") is None
    assert validate_engineering_session("bad-token", "delete:history") is None

    assert revoke_engineering_session(session["token"]) is True
    assert validate_engineering_session(session["token"], "delete:history") is None
    cleanup()


def test_expired_engineering_session_is_rejected():
    init_database()
    cleanup()
    token = "expired-token"
    expired_at = (datetime.utcnow() - timedelta(minutes=1)).replace(microsecond=0).isoformat() + "Z"
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO engineering_sessions (token_hash, role, permissions_json, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (engineering_token_hash(token), "engineer", '["delete:history"]', utc_now(), expired_at),
        )

    assert validate_engineering_session(token, "delete:history") is None
    cleanup()


def test_engineering_session_ttl_is_bounded():
    assert normalize_engineering_ttl(0) == 480
    assert normalize_engineering_ttl(-20) == 1
    assert normalize_engineering_ttl(60) == 60
    assert normalize_engineering_ttl(99999) == 1440
    assert normalize_engineering_ttl("bad") == 480


if __name__ == "__main__":
    test_engineering_domain_logic_is_owned_by_system_service()
    test_engineering_session_token_permissions_and_revocation()
    test_expired_engineering_session_is_rejected()
    test_engineering_session_ttl_is_bounded()
    print("engineering security test passed")

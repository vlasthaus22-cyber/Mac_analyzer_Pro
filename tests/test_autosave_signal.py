import signal

from server import (
    WORKSPACE_FILE_CACHE,
    db_connection,
    handle_shutdown_signal,
    init_database,
    load_autosave_state,
    save_autosave_state,
)


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM app_autosaves WHERE slot = ?", ("test-slot",))
        conn.execute("DELETE FROM snapshots WHERE id = ?", ("test-autosave-snapshot",))
        conn.execute("DELETE FROM app_logs WHERE action IN (?, ?)", ("Autosave", "Backend shutdown signal"))


def test_autosave_state_and_signal_logging():
    init_database()
    cleanup()

    result = save_autosave_state(
        {"theme": "dark", "devices": [{"mac": "AABBCC000001"}]},
        slot="test-slot",
        reason="unit-test",
    )
    assert result["slot"] == "test-slot"
    assert result["bytes"] > 20

    autosave = load_autosave_state("test-slot")
    assert autosave["state"]["theme"] == "dark"
    assert autosave["state"]["devices"][0]["mac"] == "AABBCC000001"
    assert autosave["reason"] == "unit-test"

    token = WORKSPACE_FILE_CACHE.put("test.xlsx", {"headers": ["MAC"], "rows": [["AABBCC000001"]]})
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("test-autosave-snapshot", "Autosave", "test.xlsx", 1, '[{"mac":"AABBCC000001"}]', "2026-01-01T00:00:00Z"),
        )
    save_autosave_state(
        {"activeSnapshotId": "test-autosave-snapshot", "devices": [], "files": [{"fileToken": token, "rows": [], "mapping": {"mac": 0}}]},
        slot="test-slot",
        reason="compact",
    )
    hydrated = load_autosave_state("test-slot")["state"]
    assert hydrated["devices"][0]["mac"] == "AABBCC000001"
    assert hydrated["files"][0]["rows"] == [["MAC"], ["AABBCC000001"]]

    compact = load_autosave_state("test-slot", hydrate=False)["state"]
    assert compact["devices"] == []
    assert compact["files"][0]["rows"] == []
    assert compact["resultSnapshotId"] == "test-autosave-snapshot"
    assert compact["resultDeviceCount"] == 1

    save_autosave_state({"theme": "light"}, slot="test-slot", reason="overwrite")
    assert load_autosave_state("test-slot")["state"]["theme"] == "light"

    handle_shutdown_signal(signal.SIGTERM)
    with db_connection() as conn:
        log_row = conn.execute(
            "SELECT details FROM app_logs WHERE action = ? ORDER BY id DESC LIMIT 1",
            ("Backend shutdown signal",),
        ).fetchone()
    assert "signal=" in log_row["details"]

    cleanup()
    WORKSPACE_FILE_CACHE.discard(token)


if __name__ == "__main__":
    test_autosave_state_and_signal_logging()
    print("autosave signal test passed")

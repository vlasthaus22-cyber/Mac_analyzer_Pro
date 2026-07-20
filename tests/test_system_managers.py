import signal

from server import (
    app_log_records,
    db_connection,
    delete_app_setting,
    delete_autosave_state,
    handle_shutdown_signal,
    init_database,
    list_autosave_states,
    load_app_settings,
    load_autosave_state,
    log_action,
    save_app_settings,
    save_autosave_state,
    signal_status,
)


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM app_settings WHERE key IN (?, ?)", ("manager-test", "manager-theme"))
        conn.execute("DELETE FROM app_autosaves WHERE slot IN (?, ?)", ("manager-slot", "manager-extra"))
        conn.execute(
            "DELETE FROM app_logs WHERE action IN (?, ?, ?, ?, ?)",
            ("Manager action", "Settings updated", "Settings deleted", "Autosave", "Autosave deleted"),
        )


def test_settings_logger_autosave_and_signal_managers():
    init_database()
    cleanup()

    saved = save_app_settings({
        "manager-test": {"enabled": True, "limit": 7},
        "manager-theme": "dark",
    })
    assert set(saved["saved"]) == {"manager-test", "manager-theme"}
    loaded = load_app_settings(["manager-test", "manager-theme"])
    assert loaded["settings"]["manager-test"]["limit"] == 7
    assert loaded["settings"]["manager-theme"] == "dark"

    event = log_action("Manager action", "manager detail")
    assert event["action"] == "Manager action"
    logs = app_log_records(query_text="manager", limit=20)
    assert logs["summary"]["count"] >= 1
    assert any(row["action"] == "Manager action" for row in logs["logs"])

    save_autosave_state({"view": "workspace"}, "manager-slot", "manual-test")
    save_autosave_state({"view": "data"}, "manager-extra", "manual-test")
    autosaves = list_autosave_states()
    assert {"manager-slot", "manager-extra"}.issubset(set(autosaves["summary"]["slots"]))
    assert load_autosave_state("manager-slot")["state"]["view"] == "workspace"
    assert delete_autosave_state("manager-extra") is True
    assert load_autosave_state("manager-extra") is None

    handle_shutdown_signal(signal.SIGTERM)
    status = signal_status()
    assert status["lastSignal"] == signal.SIGTERM
    assert status["lastSignalAt"]

    assert delete_app_setting("manager-theme") is True
    assert "manager-theme" not in load_app_settings(["manager-theme"])["settings"]

    cleanup()


if __name__ == "__main__":
    test_settings_logger_autosave_and_signal_managers()
    print("system managers test passed")

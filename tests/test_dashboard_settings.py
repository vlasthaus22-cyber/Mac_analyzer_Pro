from server import dashboard_history_context, dashboard_settings, db_connection, init_database, save_dashboard_settings


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM app_settings WHERE key = 'dashboard'")
        conn.execute("DELETE FROM mac_movements WHERE source = 'dashboard-period-test'")
        conn.execute("DELETE FROM mac_history WHERE source = 'dashboard-period-test'")


def test_dashboard_settings_persist_in_sqlite():
    init_database()
    cleanup()


def test_dashboard_history_context_queries_the_selected_period_and_enriches_device_context():
    init_database()
    cleanup()
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO mac_history (mac, mac_formatted, vendor, model, room, source, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("AABBCC000001", "AA:BB:CC:00:00:01", "Cisco", "Model A", "101", "dashboard-period-test", "2025-01-10T08:00:00Z"),
        )
        conn.executemany(
            "INSERT INTO mac_movements (mac, field_name, from_value, to_value, source, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("AABBCC000001", "model", "A", "B", "dashboard-period-test", "2025-01-10T09:00:00Z"),
                ("AABBCC000001", "model", "B", "C", "dashboard-period-test", "2025-02-10T09:00:00Z"),
            ],
        )

    movements, _ = dashboard_history_context({
        "changeMode": "period", "changeDateFrom": "2025-01-01", "changeDateTo": "2025-01-31",
    })
    selected = [row for row in movements if row["source"] == "dashboard-period-test"]
    assert len(selected) == 1
    assert selected[0]["changed_at"] == "2025-01-10T09:00:00Z"
    assert selected[0]["history_vendor"] == "Cisco"
    assert selected[0]["history_room"] == "101"
    cleanup()

    saved = save_dashboard_settings({
        "vendor": "Cisco",
        "room": "101",
        "status": "changed",
        "chartLimit": 4,
        "showUnknown": False,
        "visibleCards": {"missing": False, "rooms": False},
        "visibleCharts": {"fields": False},
        "autoRefresh": False,
        "refreshInterval": 420,
        "changeMode": "snapshots",
        "changeDateFrom": "2026-06-01",
        "changeDateTo": "2026-07-01",
        "baselineSnapshotId": "snapshot-old",
        "comparisonSnapshotId": "snapshot-new",
    })
    loaded = dashboard_settings()

    assert saved == loaded
    assert loaded["vendor"] == "Cisco"
    assert loaded["room"] == "101"
    assert loaded["status"] == "changed"
    assert loaded["chartLimit"] == 4
    assert loaded["showUnknown"] is False
    assert loaded["visibleCards"]["missing"] is False
    assert loaded["visibleCards"]["rooms"] is False
    assert loaded["visibleCards"]["total"] is True
    assert loaded["visibleCharts"]["fields"] is False
    assert loaded["visibleCharts"]["dynamics"] is True
    assert loaded["autoRefresh"] is False
    assert loaded["refreshInterval"] == 300
    assert loaded["changeMode"] == "snapshots"
    assert loaded["changeDateFrom"] == "2026-06-01"
    assert loaded["changeDateTo"] == "2026-07-01"
    assert loaded["baselineSnapshotId"] == "snapshot-old"
    assert loaded["comparisonSnapshotId"] == "snapshot-new"

    cleanup()


if __name__ == "__main__":
    test_dashboard_settings_persist_in_sqlite()
    test_dashboard_history_context_queries_the_selected_period_and_enriches_device_context()
    print("dashboard settings test passed")

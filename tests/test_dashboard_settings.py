from server import dashboard_settings, db_connection, init_database, save_dashboard_settings


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM app_settings WHERE key = 'dashboard'")


def test_dashboard_settings_persist_in_sqlite():
    init_database()
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
    print("dashboard settings test passed")

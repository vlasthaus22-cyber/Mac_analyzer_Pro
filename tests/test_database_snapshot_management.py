import json

from server import dashboard_snapshot_context, database_maintenance, database_summary, db_connection, delete_snapshots, init_database, open_compact_snapshot_payload, open_snapshot_payload, resolve_payload_devices, snapshot_select_payload


SNAPSHOTS = ("snapshot-mgmt-1", "snapshot-mgmt-2")
LARGE_SNAPSHOT = "snapshot-mgmt-large"


def cleanup():
    with db_connection() as conn:
        for snapshot_id in SNAPSHOTS:
            conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
        conn.execute("DELETE FROM snapshots WHERE id = ?", (LARGE_SNAPSHOT,))
        conn.execute("DELETE FROM app_logs WHERE action = ?", ("Delete snapshots",))


def insert_snapshot(snapshot_id, source):
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (snapshot_id, snapshot_id, source, 1, json.dumps([{"mac": snapshot_id}]), "2026-01-01T00:00:00Z"),
        )


def snapshot_count():
    with db_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM snapshots WHERE id IN (?, ?)",
            SNAPSHOTS,
        ).fetchone()[0]


def test_database_snapshot_bulk_delete():
    init_database()
    cleanup()
    insert_snapshot(SNAPSHOTS[0], "source-a")
    insert_snapshot(SNAPSHOTS[1], "source-b")

    assert snapshot_count() == 2
    assert delete_snapshots(ids=[SNAPSHOTS[0]]) == 1
    assert snapshot_count() == 1
    assert delete_snapshots() >= 1
    assert snapshot_count() == 0

    with db_connection() as conn:
        row = conn.execute(
            "SELECT details FROM app_logs WHERE action = ? ORDER BY id DESC LIMIT 1",
            ("Delete snapshots",),
        ).fetchone()
    assert "deleted=" in row["details"]
    cleanup()


def test_database_summary_and_maintenance():
    init_database()
    cleanup()
    insert_snapshot(SNAPSHOTS[0], "source-a")

    summary = database_summary()
    assert summary["summary"]["snapshots"] >= 1
    assert summary["database"]["sizeBytes"] >= 0
    assert "snapshots" in summary["database"]["tables"]
    assert summary["database"]["pageCount"] >= 1

    result = database_maintenance(vacuum=False, optimize=True, integrity=True)
    assert result["integrity"] == "ok"
    assert result["after"]["pageCount"] >= 1
    assert result["reclaimedBytes"] >= 0

    cleanup()


def test_open_snapshot_payload_resolves_local_state_and_sqlite():
    init_database()
    cleanup()


def test_stale_snapshot_reference_falls_back_without_breaking_api_routes():
    init_database()
    cleanup()

    devices = resolve_payload_devices({
        "snapshotId": "deleted-snapshot-reference",
        "devices": [{"mac": "FALLBACK"}],
    })

    assert devices == [{"mac": "FALLBACK"}]
    insert_snapshot(SNAPSHOTS[0], "source-a")

    local = open_snapshot_payload("local-snapshot", [{"id": "local-snapshot", "name": "Local", "devices": [{"mac": "LOCAL"}]}])
    assert local["snapshot"]["name"] == "Local"
    assert local["devices"] == [{"mac": "LOCAL"}]
    assert local["invalid"] == []

    saved = open_snapshot_payload(SNAPSHOTS[0], [])
    assert saved["snapshot"]["id"] == SNAPSHOTS[0]
    assert saved["snapshot"]["deviceCount"] == 1
    assert saved["devices"][0]["mac"] == SNAPSHOTS[0]

    cleanup()


def test_snapshot_select_payload_prepares_ready_options():
    payload = snapshot_select_payload([
        {"id": "mapping", "name": "Mapping: rooms.xlsx", "createdAt": "2026-01-03T11:30:00Z"},
        {"id": "second", "name": "Analysis: Second", "createdAt": "2026-01-02T11:30:00Z"},
        {"id": "first", "name": "Анализ: First", "createdAt": "2026-01-01T10:00:00Z"},
    ])

    assert payload["count"] == 2
    assert payload["baselineSelectedIndex"] == 0
    assert payload["comparisonSelectedIndex"] == 1
    assert '<option value="first">Анализ: First · 01.01.2026, 10:00:00</option>' in payload["optionsHtml"]
    assert '<option value="second">Analysis: Second · 02.01.2026, 11:30:00</option>' in payload["optionsHtml"]
    assert "mapping" not in payload["optionsHtml"]


def test_large_snapshot_open_is_compact_for_browser():
    init_database()
    cleanup()


def test_dashboard_context_hydrates_only_previous_and_current_final_results():
    init_database()
    cleanup()
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (SNAPSHOTS[0], "Анализ: before.xlsx", "before.xlsx", 1, json.dumps([{"mac": "AABBCC000001", "model": "A"}]), "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (SNAPSHOTS[1], "Анализ: current.xlsx", "current.xlsx", 2, json.dumps([{"mac": "AABBCC000001", "model": "B"}, {"mac": "AABBCC000002"}]), "2025-01-01T00:00:00Z"),
        )

    options, hydrated, settings = dashboard_snapshot_context(
        [{"id": SNAPSHOTS[1], "backendStored": True}, {"id": SNAPSHOTS[0], "backendStored": True}],
        SNAPSHOTS[1],
        {"changeMode": "period"},
    )

    assert [item["id"] for item in options][-2:] == list(SNAPSHOTS)
    assert [item["id"] for item in hydrated] == list(SNAPSHOTS)
    assert [len(item["devices"]) for item in hydrated] == [1, 2]
    assert settings["changeMode"] == "snapshots"
    assert settings["baselineSnapshotId"] == SNAPSHOTS[0]
    assert settings["comparisonSnapshotId"] == SNAPSHOTS[1]
    cleanup()
    devices = [
        {"mac": f"020000{index:06X}", "vendor": "Load Test", "ip": f"10.20.{index // 254}.{index % 254 + 1}"}
        for index in range(5000)
    ]
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (LARGE_SNAPSHOT, "Large", "memory-test.xlsx", len(devices), json.dumps(devices), "2026-01-03T00:00:00Z"),
        )

    compact = open_compact_snapshot_payload(LARGE_SNAPSHOT, [], 25)
    assert compact["compactResult"] is True
    assert compact["resultReference"]["snapshotId"] == LARGE_SNAPSHOT
    assert compact["resultReference"]["deviceCount"] == 5000
    assert compact["resultPage"]["pagination"]["total"] == 5000
    assert len(compact["devices"]) == 25
    assert len(json.dumps(compact, ensure_ascii=False)) < 150_000
    cleanup()


if __name__ == "__main__":
    test_database_snapshot_bulk_delete()
    test_database_summary_and_maintenance()
    test_open_snapshot_payload_resolves_local_state_and_sqlite()
    test_snapshot_select_payload_prepares_ready_options()
    test_large_snapshot_open_is_compact_for_browser()
    test_dashboard_context_hydrates_only_previous_and_current_final_results()
    print("database snapshot management test passed")

import json

from server import (
    db_connection,
    init_database,
    export_snapshot_history,
    performance_statistics,
    save_performance_metric,
    save_statistics_snapshot,
    statistics_panel_payload,
    statistics_snapshot_history,
    statistics_summary,
    temporal_statistics,
    utc_now,
)


SNAPSHOT_IDS = ("stats-test-1", "stats-test-2", "stats-service-1")


def cleanup():
    with db_connection() as conn:
        for snapshot_id in SNAPSHOT_IDS:
            conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
        conn.execute("DELETE FROM snapshots WHERE source IN (?, ?)", ("stats-test", "stats-service"))
        conn.execute("DELETE FROM performance_metrics WHERE details LIKE 'stats-test%' OR details LIKE 'stats-service%'")


def insert_snapshot(snapshot_id, created_at, devices):
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                snapshot_id,
                snapshot_id,
                "stats-test",
                len(devices),
                json.dumps(devices, ensure_ascii=False),
                created_at,
            ),
        )


def test_statistics_summary_trends_and_metrics():
    init_database()
    cleanup()

    insert_snapshot(
        SNAPSHOT_IDS[0],
        "2026-01-01T10:00:00Z",
        [
            {"mac": "AABBCC000001", "vendor": "Cisco", "model": "A", "room": "101", "switchIp": "10.0.0.1"},
            {"mac": "AABBCC000002", "vendor": "Cisco", "model": "B", "room": "101", "switchIp": "10.0.0.1"},
        ],
    )
    insert_snapshot(
        SNAPSHOT_IDS[1],
        "2026-01-02T10:00:00Z",
        [
            {"mac": "AABBCC000002", "vendor": "Cisco", "model": "B", "room": "101", "switchIp": "10.0.0.1"},
            {"mac": "AABBCC000003", "vendor": "Apple", "model": "C", "room": "202", "switchIp": "10.0.0.2"},
        ],
    )
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO performance_metrics (operation, duration_ms, details, created_at) VALUES (?, ?, ?, ?)",
            ("analyze", 10.0, "stats-test metric 1", utc_now()),
        )
        conn.execute(
            "INSERT INTO performance_metrics (operation, duration_ms, details, created_at) VALUES (?, ?, ?, ?)",
            ("analyze", 30.0, "stats-test metric 2", utc_now()),
        )

    stats = statistics_summary(source="stats-test")

    assert stats["summary"]["snapshots"] == 2
    assert stats["summary"]["uniqueMacs"] == 3
    trend_by_id = {item["id"]: item for item in stats["trends"]}
    assert trend_by_id[SNAPSHOT_IDS[0]]["added"] == 2
    assert trend_by_id[SNAPSHOT_IDS[1]]["added"] == 1
    assert trend_by_id[SNAPSHOT_IDS[1]]["removed"] == 1
    assert {"name": "Cisco", "count": 3} in stats["distributions"]["vendors"]
    analyze_perf = next(item for item in stats["performance"] if item["operation"] == "analyze")
    assert analyze_perf["count"] >= 2
    assert analyze_perf["avgMs"] >= 20.0

    temporal = temporal_statistics(period="day", source="stats-test")
    assert temporal["summary"]["periods"] == 2
    assert temporal["summary"]["uniqueMacs"] == 3
    day_by_key = {item["period"]: item for item in temporal["periods"]}
    assert day_by_key["2026-01-01"]["added"] == 2
    assert day_by_key["2026-01-02"]["added"] == 1
    assert day_by_key["2026-01-02"]["removed"] == 1
    assert day_by_key["2026-01-02"]["snapshotCount"] == 1

    weekly = temporal_statistics(period="week", source="stats-test")
    assert weekly["summary"]["periods"] == 1
    assert weekly["periods"][0]["uniqueMacs"] == 3

    panel = statistics_panel_payload(source="stats-test")
    assert panel["summary"]["snapshots"] == 2
    assert panel["historySummary"]["snapshots"] == 2
    assert panel["trendRows"][-1]["added"] == 1
    assert panel["trendRows"][-1]["removed"] == 1
    assert panel["trendRows"][-1]["percent"] == 100
    assert panel["temporalRows"][-1]["period"] == "2026-01-02"
    assert panel["temporalRows"][-1]["uniqueMacs"] == 2
    assert panel["temporalRows"][-1]["percent"] == 100

    try:
        temporal_statistics(period="hour", source="stats-test")
    except ValueError as error:
        assert "day, week, or month" in str(error)
    else:
        raise AssertionError("invalid temporal period must fail")

    cleanup()


def test_statistics_database_service_functions():
    init_database()
    cleanup()

    snapshot = save_statistics_snapshot(
        [
            {"mac": "CCDDEE000001", "vendor": "Juniper", "room": "301"},
            {"mac": "CCDDEE000002", "vendor": "Juniper", "room": "302"},
        ],
        name="Stats service snapshot",
        source="stats-service",
        snapshot_id=SNAPSHOT_IDS[2],
        created_at="2026-02-01T12:00:00Z",
    )
    metric = save_performance_metric("export_html", 42.25, "stats-service export", "2026-02-01T12:00:01Z")

    assert snapshot["id"] == SNAPSHOT_IDS[2]
    assert snapshot["deviceCount"] == 2
    assert metric["operation"] == "export_html"
    assert metric["durationMs"] == 42.25

    history = statistics_snapshot_history(query_text="Juniper", source="stats-service")
    assert history["summary"]["snapshots"] == 1
    assert history["summary"]["uniqueMacs"] == 2
    assert history["snapshots"][0]["id"] == SNAPSHOT_IDS[2]
    assert history["snapshots"][0]["uniqueMacs"] == 2

    html_export = export_snapshot_history(query_text="Juniper", source="stats-service", export_format="html")
    assert html_export["filename"] == "mac-history.html"
    assert html_export["mimeType"] == "text/html"
    assert "Stats service snapshot" in html_export["content"]
    assert "Juniper" not in html_export["content"]

    csv_export = export_snapshot_history(source="stats-service", export_format="csv")
    assert csv_export["filename"] == "mac-history.csv"
    assert "id,createdAt,name,source,deviceCount,uniqueMacs" in csv_export["content"]
    assert SNAPSHOT_IDS[2] in csv_export["content"]

    performance = performance_statistics("export_html")
    operation = next(item for item in performance["operations"] if item["operation"] == "export_html")
    assert operation["count"] >= 1
    assert operation["maxMs"] >= 42.25
    assert performance["summary"]["metrics"] >= 1

    cleanup()


if __name__ == "__main__":
    test_statistics_summary_trends_and_metrics()
    test_statistics_database_service_functions()
    print("statistics database test passed")

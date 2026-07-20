from server import db_connection, enrich_device, history_panel_payload, history_statistics, init_database, save_history, save_statistics_snapshot, search_history_records, statistics_snapshot_history


MAC = "AABBCC990001"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM mac_movements WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM mac_history WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM vendor_model_history WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM snapshots WHERE id = ?", ("history-table-test",))


def test_history_statistics_groups_filters_and_movements():
    init_database()
    cleanup()

    first = enrich_device({
        "mac": MAC,
        "vendor": "Stats Vendor",
        "model": "Stats Model",
        "ip": "10.10.0.1",
        "room": "501",
        "switchIp": "192.0.2.1",
        "switchPort": "Gi1/0/1",
    })
    second = enrich_device({
        "mac": MAC,
        "vendor": "Stats Vendor",
        "model": "Stats Model",
        "ip": "10.10.0.2",
        "room": "501",
        "switchIp": "192.0.2.1",
        "switchPort": "Gi1/0/2",
    })
    save_history([first], "history-stats-test-1")
    save_history([second], "history-stats-test-2")

    stats = history_statistics("Stats Vendor")
    assert stats["totals"]["records"] == 2
    assert stats["totals"]["uniqueMacs"] == 1
    assert stats["vendors"][0]["name"] == "Stats Vendor"
    assert stats["vendors"][0]["count"] == 2
    assert stats["models"][0]["name"] == "Stats Model"
    assert stats["rooms"][0]["name"] == "501"
    assert stats["switches"][0]["switchIp"] == "192.0.2.1"

    movement_stats = history_statistics("10.10.0.2")
    assert movement_stats["totals"]["movements"] >= 1
    assert movement_stats["movementFields"][0]["field"] in {"ip", "switchPort"}
    assert movement_stats["recentMovements"]

    search = search_history_records("10.10.0.2")
    assert search["statistics"]["movements"] >= 1
    assert any(item["to_value"] == "10.10.0.2" for item in search["movements"])

    panel = history_panel_payload("Stats Vendor")
    assert panel["summaryTables"]["vendors"][0]["name"] == "Stats Vendor"
    assert panel["summaryTables"]["models"][0]["name"] == "Stats Model"
    assert "<td>Stats Vendor</td>" in panel["summaryTables"]["vendorRowsHtml"]
    assert "<td>Stats Model</td>" in panel["summaryTables"]["modelRowsHtml"]
    assert "Backend history is empty" in panel["summaryTables"]["emptyRowsHtml"]
    assert panel["historyStats"]["totals"]["records"] == 2
    assert panel["historySearch"]["statistics"]["records"] == 2
    assert f'data-mac="{MAC}"' in panel["historySearch"]["tableRowsHtml"]
    assert "Stats Vendor" in panel["historySearch"]["tableRowsHtml"]
    assert "SQLite history is empty" in panel["historySearch"]["emptyTableRowsHtml"]
    assert panel["vendorModelStats"]["totals"]["records"] == 2
    assert panel["vendorModelHistory"]["statistics"]["records"] == 2
    assert "Stats Vendor" in panel["vendorModelHistory"]["tableRowsHtml"]
    assert "Stats Model" in panel["vendorModelHistory"]["tableRowsHtml"]
    assert "Vendor/model history is empty" in panel["vendorModelHistory"]["emptyTableRowsHtml"]

    cleanup()


def test_snapshot_history_payload_contains_backend_table_rows():
    init_database()
    cleanup()
    save_statistics_snapshot([{"mac": MAC}], "History Table", "history-table-source", "history-table-test", "2026-01-03T12:30:00Z")

    payload = statistics_snapshot_history(query_text="History Table", limit=10)

    assert payload["summary"]["snapshots"] == 1
    assert 'data-load-snapshot="history-table-test"' in payload["tableRowsHtml"]
    assert "03.01.2026, 12:30:00" in payload["tableRowsHtml"]
    assert "History Table" in payload["tableRowsHtml"]
    assert payload["emptyTableRowsHtml"].startswith("<tr>")

    cleanup()


if __name__ == "__main__":
    test_history_statistics_groups_filters_and_movements()
    test_snapshot_history_payload_contains_backend_table_rows()
    print("history statistics test passed")

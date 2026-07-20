from server import (
    database_history_records,
    db_connection,
    delete_database_history_records,
    enrich_device,
    init_database,
    save_history,
)


MACS = ("E2A1B2C3D401", "E2A1B2C3D402", "E2A1B2C3D403")
SOURCES = ("database-manager-a.xlsx", "database-manager-b.xlsx")


def cleanup():
    with db_connection() as conn:
        placeholders = ",".join("?" for _ in MACS)
        conn.execute(f"DELETE FROM mac_history WHERE mac IN ({placeholders})", MACS)
        conn.execute(f"DELETE FROM mac_movements WHERE mac IN ({placeholders})", MACS)
        conn.execute(f"DELETE FROM vendor_model_history WHERE mac IN ({placeholders})", MACS)
        conn.execute("DELETE FROM app_logs WHERE action = ?", ("Delete database history",))


def seed_history():
    save_history([
        enrich_device({"mac": MACS[0], "vendor": "Manager Vendor", "model": "Edge 100", "room": "Lab 7"}),
        enrich_device({"mac": MACS[1], "vendor": "Manager Vendor", "model": "Edge 200", "room": "Lab 8"}),
    ], SOURCES[0], "2026-04-05T10:00:00Z")
    save_history([
        enrich_device({"mac": MACS[2], "vendor": "Other Vendor", "model": "Core 300", "room": "Server 1"}),
    ], SOURCES[1], "2026-04-06T11:00:00Z")


def test_database_history_filters_and_server_rendered_table():
    init_database()
    cleanup()
    seed_history()

    result = database_history_records({
        "source": "manager-a",
        "vendor": "Manager Vendor",
        "model": "Edge",
        "room": "Lab",
        "dateFrom": "2026-04-05",
        "dateTo": "2026-04-05",
    })

    assert result["total"] == 2
    assert result["count"] == 2
    assert result["summary"]["unique_macs"] == 2
    assert 'data-db-history-select' in result["rowsHtml"]
    assert 'data-delete-db-history-id=' in result["rowsHtml"]
    assert "Manager Vendor" in result["rowsHtml"]
    assert "Уникальных MAC" in result["summaryHtml"]

    mac_result = database_history_records({"mac": "E2:A1:B2:C3:D4:03"})
    assert mac_result["total"] == 1
    assert mac_result["records"][0]["mac"] == MACS[2]
    cleanup()


def test_database_history_selected_and_filtered_delete_are_scoped():
    init_database()
    cleanup()
    seed_history()

    first = database_history_records({"mac": MACS[0]})["records"][0]
    assert delete_database_history_records([first["id"]], {}) == 1
    assert database_history_records({"mac": MACS[0]})["total"] == 0
    assert database_history_records({"source": SOURCES[0]})["total"] == 1

    assert delete_database_history_records([], {"source": SOURCES[0]}) == 1
    assert database_history_records({"source": SOURCES[0]})["total"] == 0
    assert database_history_records({"source": SOURCES[1]})["total"] == 1

    try:
        delete_database_history_records([], {})
    except ValueError as error:
        assert "Select records or set at least one filter" in str(error)
    else:
        raise AssertionError("Empty delete must require selected rows or an active filter")

    with db_connection() as conn:
        log = conn.execute(
            "SELECT details FROM app_logs WHERE action = ? ORDER BY id DESC LIMIT 1",
            ("Delete database history",),
        ).fetchone()
    assert "mode=filtered" in log["details"]
    cleanup()


if __name__ == "__main__":
    test_database_history_filters_and_server_rendered_table()
    test_database_history_selected_and_filtered_delete_are_scoped()
    print("database history management test passed")

import base64

from server import (
    db_connection,
    delete_enhanced_movement_history,
    enhanced_movement_history,
    enrich_device,
    export_enhanced_movement_history,
    init_database,
    save_enhanced_history_column_settings,
    save_history,
)


MAC = "E6A1B2C3D4F5"
SOURCES = ("enhanced-history-before.xlsx", "enhanced-history-after.xlsx")


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM mac_movements WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM mac_history WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM vendor_model_history WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM app_logs WHERE action = ?", ("Delete filtered movements",))


def seed_movements():
    save_history([enrich_device({
        "mac": MAC,
        "vendor": "Enhanced Vendor A",
        "model": "",
        "ip": "192.0.2.50",
        "room": "Lab 10",
    })], SOURCES[0], "2026-05-01T10:00:00Z")
    updated = enrich_device({
        "mac": MAC,
        "vendor": "Enhanced Vendor B",
        "model": "Model Added",
        "ip": "",
        "room": "Lab 10",
    })
    updated["ip"] = ""
    save_history([updated], SOURCES[1], "2026-05-02T11:30:00Z")


def test_enhanced_history_grouping_filters_and_xlsx_export():
    init_database()
    cleanup()
    seed_movements()

    result = enhanced_movement_history({"query": "Enhanced Vendor B", "dateFrom": "2026-05-02", "dateTo": "2026-05-02"})
    assert result["count"] == 3
    assert result["groups"] == 1
    assert result["statistics"] == {"added": 1, "removed": 1, "modified": 1, "uniqueMacs": 1}
    assert 'data-toggle-movement-group=' in result["rowsHtml"]
    assert 'data-movement-child=' in result["rowsHtml"]
    assert 'movement-added' in result["rowsHtml"]
    assert 'movement-removed' in result["rowsHtml"]
    assert 'movement-modified' in result["rowsHtml"]
    assert "Enhanced Vendor B" in result["rowsHtml"]

    added = enhanced_movement_history({"changeType": "added", "field": "model"})
    assert added["count"] == 1
    assert added["records"][0]["to_value"] == "Model Added"

    removed = enhanced_movement_history({"changeType": "removed", "field": "ip"})
    assert removed["count"] == 1
    assert removed["records"][0]["from_value"] == "192.0.2.50"

    exported = export_enhanced_movement_history({"query": "Enhanced Vendor B"}, "xlsx")
    assert exported["filename"] == "filtered-history.xlsx"
    assert exported["binary"] is True
    assert base64.b64decode(exported["content"]).startswith(b"PK")
    cleanup()


def test_enhanced_history_scoped_delete_and_column_settings():
    init_database()
    cleanup()
    seed_movements()
    records = enhanced_movement_history({"query": MAC})["records"]

    assert delete_enhanced_movement_history([records[0]["id"]]) == 1
    assert enhanced_movement_history({"query": MAC})["count"] == 2
    try:
        delete_enhanced_movement_history([])
    except ValueError as error:
        assert "No shown movement records" in str(error)
    else:
        raise AssertionError("Deleting without shown movement IDs must fail")

    with db_connection() as conn:
        original = conn.execute("SELECT value, updated_at FROM app_settings WHERE key = ?", ("enhanced_history_columns",)).fetchone()
    settings = save_enhanced_history_column_settings({
        "visible": ["mac", "dates", "field", "after"],
        "widths": {"mac": 212, "after": 333},
    })
    assert settings["visible"] == ["mac", "dates", "field", "after"]
    assert settings["widths"]["mac"] == 212
    assert settings["widths"]["after"] == 333
    assert 'data-movement-column-toggle="mac" checked' in settings["controlsHtml"]
    with db_connection() as conn:
        if original:
            conn.execute(
                "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                ("enhanced_history_columns", original["value"], original["updated_at"]),
            )
        else:
            conn.execute("DELETE FROM app_settings WHERE key = ?", ("enhanced_history_columns",))
    cleanup()


if __name__ == "__main__":
    test_enhanced_history_grouping_filters_and_xlsx_export()
    test_enhanced_history_scoped_delete_and_column_settings()
    print("enhanced history management test passed")

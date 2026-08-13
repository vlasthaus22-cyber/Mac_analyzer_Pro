import json

from server import (
    column_preferences_panel_payload,
    db_connection,
    init_database,
    list_column_preferences,
    load_column_preferences,
    move_column_preference,
    reset_column_preferences,
    save_column_preferences,
    utc_now,
)


VIEW_NAME = "column-manager-test"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM column_preferences WHERE view_name = ?", (VIEW_NAME,))


def test_column_manager_order_visibility_and_custom_columns():
    init_database()
    cleanup()

    saved = save_column_preferences(
        VIEW_NAME,
        {
            "order": ["vendor", "macFormatted", "custom_owner", "ip"],
            "visible": ["macFormatted", "custom_owner"],
            "custom": [{"key": "custom_owner", "title": "Owner", "sourceIndex": 7}],
            "widths": {"vendor": 210, "macFormatted": 175, "custom_owner": 900},
        },
    )

    assert saved["order"][:4] == ["vendor", "macFormatted", "custom_owner", "ip"]
    assert saved["visible"] == ["macFormatted", "custom_owner"]
    assert saved["custom"] == [{"key": "custom_owner", "title": "Owner", "sourceIndex": 7}]
    assert saved["widths"]["vendor"] == 210
    assert saved["widths"]["macFormatted"] == 175
    assert saved["widths"]["custom_owner"] == 600

    loaded = load_column_preferences(VIEW_NAME)
    assert loaded["visible"] == ["macFormatted", "custom_owner"]
    assert loaded["custom"][0]["title"] == "Owner"
    assert loaded["order"].index("custom_owner") < loaded["order"].index("ip")
    assert loaded["widths"]["custom_owner"] == 600
    panel = column_preferences_panel_payload(loaded, {"custom_owner": "Owner"})
    assert 'data-column-width="vendor"' in panel["listHtml"]
    assert 'value="210"' in panel["listHtml"]

    with db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO column_preferences (view_name, columns_json, updated_at) VALUES (?, ?, ?)",
            (VIEW_NAME, json.dumps(["ip", "vendor"]), utc_now()),
        )
    legacy = load_column_preferences(VIEW_NAME)
    assert legacy["visible"] == ["ip", "vendor"]
    assert legacy["order"][:2] == ["ip", "vendor"]
    assert "macFormatted" in legacy["order"]
    assert legacy["widths"]["macFormatted"] == 180

    cleanup()


def test_column_manager_list_move_and_reset():
    init_database()
    cleanup()

    save_column_preferences(
        VIEW_NAME,
        {
            "order": ["macFormatted", "vendor", "ip", "source"],
            "visible": ["macFormatted", "vendor", "ip"],
            "widths": {"macFormatted": 190, "vendor": 205, "ip": 135},
        },
    )

    moved = move_column_preference(VIEW_NAME, "ip", "up")
    assert moved["preferences"]["order"][:4] == ["macFormatted", "ip", "vendor", "source"]
    assert moved["preferences"]["widths"]["vendor"] == 205
    moved = move_column_preference(VIEW_NAME, "macFormatted", "down")
    assert moved["preferences"]["order"][:4] == ["ip", "macFormatted", "vendor", "source"]

    listed = list_column_preferences()
    view_names = {item["view"] for item in listed["views"]}
    assert VIEW_NAME in view_names
    assert listed["summary"]["views"] >= 1

    reset = reset_column_preferences(VIEW_NAME)
    assert reset["deleted"] is True
    assert reset["preferences"]["visible"] == ["macFormatted", "oui", "vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort", "hostname", "serialNumber", "deviceId", "deviceName", "source"]
    assert load_column_preferences(VIEW_NAME)["updatedAt"] is None

    cleanup()


if __name__ == "__main__":
    test_column_manager_order_visibility_and_custom_columns()
    test_column_manager_list_move_and_reset()
    print("column manager test passed")

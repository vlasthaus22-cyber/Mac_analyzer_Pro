from server import bootstrap_payload, db_connection, init_database, save_column_preferences


def test_bootstrap_payload_prepares_frontend_state():
    init_database()
    with db_connection() as conn:
        previous = conn.execute("SELECT columns_json, updated_at FROM column_preferences WHERE view_name = 'results'").fetchone()
    try:
        save_column_preferences(
            "results",
            {
                "visible": ["macFormatted", "vendor", "custom_bootstrap"],
                "order": ["macFormatted", "vendor", "custom_bootstrap"],
                "custom": [{"key": "custom_bootstrap", "title": "Bootstrap", "sourceIndex": 2}],
            },
        )
        payload = bootstrap_payload()

        assert "snapshots" in payload
        assert payload["columns"]["visible"] == ["macFormatted", "vendor", "custom_bootstrap"]
        assert payload["customColumns"] == ["custom_bootstrap"]
        assert payload["customColumnMappings"] == {"custom_bootstrap": 2}
        assert payload["customLabels"] == {"custom_bootstrap": "Bootstrap"}
    finally:
        with db_connection() as conn:
            if previous:
                conn.execute(
                    "INSERT INTO column_preferences (view_name, columns_json, updated_at) VALUES ('results', ?, ?) "
                    "ON CONFLICT(view_name) DO UPDATE SET columns_json=excluded.columns_json, updated_at=excluded.updated_at",
                    (previous["columns_json"], previous["updated_at"]),
                )
            else:
                conn.execute("DELETE FROM column_preferences WHERE view_name = 'results'")


if __name__ == "__main__":
    test_bootstrap_payload_prepares_frontend_state()
    print("bootstrap payload test passed")

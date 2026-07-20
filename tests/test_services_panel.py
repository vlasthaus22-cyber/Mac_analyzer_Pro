from server import init_database, services_panel_payload


def test_services_panel_payload_aggregates_backend_services():
    init_database()
    panel = services_panel_payload()

    for key in ("ip", "tasks", "notifications", "logs", "metrics", "database", "autosaves", "signals", "legacy"):
        assert key in panel
    assert "mappings" in panel["ip"]
    assert "statistics" in panel["ip"]
    assert "tasks" in panel["tasks"]
    assert "channels" in panel["notifications"]
    assert "logs" in panel["logs"]
    assert "metrics" in panel["metrics"]
    assert "summary" in panel["database"]
    assert "autosaves" in panel["autosaves"]
    assert "signal" in panel["signals"]
    assert "summary" in panel["legacy"]


if __name__ == "__main__":
    test_services_panel_payload_aggregates_backend_services()
    print("services panel test passed")

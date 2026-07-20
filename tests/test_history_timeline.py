from server import db_connection, enrich_device, history_timeline, init_database, save_history


MAC = "DDEEFF110001"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM mac_movements WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM mac_history WHERE mac = ?", (MAC,))


def test_history_timeline_combines_records_movements_and_summary():
    init_database()
    cleanup()

    first = enrich_device({
        "mac": MAC,
        "vendor": "Timeline Vendor",
        "model": "T-1",
        "ip": "10.20.0.1",
        "room": "401",
        "switchPort": "Gi1/0/1",
    })
    second = enrich_device({
        "mac": MAC,
        "vendor": "Timeline Vendor",
        "model": "T-1",
        "ip": "10.20.0.2",
        "room": "402",
        "switchPort": "Gi1/0/2",
    })
    save_history([first], "timeline-source-1")
    save_history([second], "timeline-source-2")

    result = history_timeline(MAC)

    assert result["summary"]["records"] == 2
    assert result["summary"]["movements"] >= 2
    assert result["summary"]["timeline"] == len(result["timeline"])
    assert any(item["type"] == "record" for item in result["timeline"])
    assert any(item["type"] == "movement" and item["field"] == "ip" and item["after"] == "10.20.0.2" for item in result["timeline"])
    assert any(item["field"] in {"ip", "room", "switchPort"} for item in result["summary"]["fields"])
    assert result["summary"]["sources"][0]["count"] >= 1

    cleanup()


if __name__ == "__main__":
    test_history_timeline_combines_records_movements_and_summary()
    print("history timeline test passed")

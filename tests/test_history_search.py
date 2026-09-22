from server import (
    db_connection,
    enrich_device,
    init_database,
    save_history,
    search_history_records,
)


def cleanup(*macs):
    with db_connection() as conn:
        for mac in macs:
            conn.execute("DELETE FROM mac_movements WHERE mac = ?", (mac,))
            conn.execute("DELETE FROM mac_history WHERE mac = ?", (mac,))


def test_history_search_filters_and_statistics():
    init_database()
    mac_alpha = "AABBCCEE2001"
    mac_beta = "AABBCCEE2002"
    cleanup(mac_alpha, mac_beta)

    save_history([
        enrich_device({
            "mac": mac_alpha,
            "vendor": "Alpha Networks",
            "model": "AX-100",
            "ip": "192.0.2.10",
            "address": "Floor 1",
            "room": "101",
            "hostname": "history-alpha-host",
            "serialNumber": "HISTORY-SERIAL-A",
            "deviceId": "HISTORY-DEVICE-A",
            "deviceName": "History Alpha Panel",
        }),
    ], "history-search-test", recorded_at="2026-07-01T00:00:00Z")
    save_history([
        enrich_device({
            "mac": mac_beta,
            "vendor": "Beta Systems",
            "model": "BX-200",
            "ip": "192.0.2.20",
            "address": "Floor 2",
            "room": "202",
        }),
    ], "history-search-test", recorded_at="2026-08-01T00:00:00Z")

    by_vendor = search_history_records("Alpha", limit="bad-limit")
    assert by_vendor["statistics"]["records"] == 1
    assert by_vendor["statistics"]["uniqueMacs"] == 1
    assert by_vendor["history"][0]["mac"] == mac_alpha
    assert by_vendor["statistics"]["vendors"][0] == {"name": "Alpha Networks", "count": 1}

    by_ip = search_history_records("192.0.2.20")
    assert by_ip["statistics"]["records"] == 1
    assert by_ip["history"][0]["mac"] == mac_beta

    by_mac_fragment = search_history_records("AA:BB:CC:EE:20:01")
    assert by_mac_fragment["statistics"]["records"] == 1
    assert by_mac_fragment["history"][0]["mac"] == mac_alpha

    for query in ("history-alpha-host", "HISTORY-SERIAL-A", "HISTORY-DEVICE-A", "History Alpha Panel"):
        result = search_history_records(query)
        assert result["statistics"]["records"] == 1
        assert result["history"][0]["mac"] == mac_alpha

    july = search_history_records("", "2026-07-01", "2026-07-31")
    assert [item["mac"] for item in july["history"]] == [mac_alpha]

    cleanup(mac_alpha, mac_beta)


if __name__ == "__main__":
    test_history_search_filters_and_statistics()
    print("history search test passed")

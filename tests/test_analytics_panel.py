from server import analytics_panel_payload, enrich_device, init_database


def test_analytics_panel_payload_prepares_charts_and_clusters():
    init_database()
    devices = [
        enrich_device({"mac": "AABBCC000101", "vendor": "Cisco", "model": "A", "room": "101", "switchIp": "10.0.0.1"}),
        enrich_device({"mac": "AABBCC000102", "vendor": "Cisco", "model": "A", "room": "101", "switchIp": "10.0.0.1"}),
        enrich_device({"mac": "DDEEFF000103", "vendor": "Apple", "model": "B", "room": "202", "switchIp": "10.0.0.2"}),
    ]
    panel = analytics_panel_payload(devices, [{"id": "s1", "name": "Snapshot", "devices": devices}])

    assert panel["primaryCharts"]["vendors"][0]["label"] == "Cisco"
    assert panel["backendCharts"][0]["preview"]
    assert panel["clusterRows"][0]["count"] == 2
    assert panel["clusterRows"][0]["percent"] == 100
    assert panel["clusterSummary"]["clusters"] >= 1


if __name__ == "__main__":
    test_analytics_panel_payload_prepares_charts_and_clusters()
    print("analytics panel test passed")

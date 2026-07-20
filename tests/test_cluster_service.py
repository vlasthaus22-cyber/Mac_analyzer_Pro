from cluster_service import build_clusters, export_clusters_csv


DEVICES = [
    {"mac": "AABBCC000001", "macFormatted": "AA:BB:CC:00:00:01", "vendor": "Cisco", "model": "A", "room": "101", "switchIp": "10.1.1.1"},
    {"mac": "AABBCC000002", "macFormatted": "AA:BB:CC:00:00:02", "vendor": "Cisco", "model": "B", "room": "101", "switchIp": "10.1.1.1"},
    {"mac": "AABBCC000003", "macFormatted": "AA:BB:CC:00:00:03", "vendor": "Cisco", "model": "B", "room": "102", "switchIp": "10.1.1.1"},
    {"mac": "AABBCC000004", "macFormatted": "AA:BB:CC:00:00:04", "vendor": "Apple", "model": "C", "room": "101", "switchIp": "10.1.1.2"},
]


def test_build_clusters_summary_details_and_export():
    payload = build_clusters(DEVICES, ["vendor", "room", "switchIp"])

    assert payload["summary"]["clusters"] == 3
    assert payload["summary"]["largestCluster"] == 2
    first = payload["clusters"][0]
    assert first["label"] == "Cisco · 101 · 10.1.1.1"
    assert first["count"] == 2
    assert first["uniqueMacs"] == 2
    assert len(first["devices"]) == 2

    min_payload = build_clusters(DEVICES, ["vendor"], min_size=2)
    assert min_payload["summary"]["clusters"] == 1
    assert min_payload["clusters"][0]["label"] == "Cisco"

    exported = export_clusters_csv(payload)
    assert exported["mimeType"] == "text/csv"
    assert "Cluster,Devices,Unique MAC" in exported["content"]
    assert "Cisco" in exported["content"]


if __name__ == "__main__":
    test_build_clusters_summary_details_and_export()
    print("cluster service test passed")

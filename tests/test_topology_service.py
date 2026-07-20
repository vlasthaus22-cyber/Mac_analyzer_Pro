from topology_service import build_topology, export_topology_html


DEVICES = [
    {"mac": "AABBCC000001", "macFormatted": "AA:BB:CC:00:00:01", "vendor": "Cisco", "ip": "10.0.0.1", "room": "101", "switchIp": "192.168.1.10", "switchPort": "1"},
    {"mac": "AABBCC000002", "macFormatted": "AA:BB:CC:00:00:02", "vendor": "Apple", "ip": "10.0.0.2", "room": "101", "switchIp": "192.168.1.10", "switchPort": "2"},
    {"mac": "AABBCC000003", "macFormatted": "AA:BB:CC:00:00:03", "vendor": "Dell", "ip": "10.0.0.3", "room": "202", "switchIp": "192.168.1.20", "switchPort": "1"},
    {"mac": "AABBCC000004", "macFormatted": "AA:BB:CC:00:00:04", "vendor": "Unknown", "ip": "10.0.0.4", "room": "", "switchIp": "", "switchPort": ""},
]


def test_build_topology_nodes_ports_links_and_export():
    topology = build_topology(DEVICES)

    assert topology["summary"] == {"switches": 2, "ports": 3, "linkedDevices": 3, "unassignedDevices": 1}
    first = topology["nodes"][0]
    assert first["switchIp"] == "192.168.1.10"
    assert first["deviceCount"] == 2
    assert first["rooms"] == ["101"]
    assert len(topology["links"]) == 3
    assert topology["unassigned"][0]["mac"] == "AABBCC000004"

    exported = export_topology_html(topology)
    assert exported["mimeType"] == "text/html"
    assert "MAC Analyzer Topology" in exported["content"]
    assert "192.168.1.10" in exported["content"]


if __name__ == "__main__":
    test_build_topology_nodes_ports_links_and_export()
    print("topology service test passed")

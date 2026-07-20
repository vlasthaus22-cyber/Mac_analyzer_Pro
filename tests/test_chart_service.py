from chart_service import build_chart_payload, export_charts_json, export_charts_svg


DEVICES = [
    {"mac": "AABBCC000001", "vendor": "Cisco", "model": "A", "room": "101", "ip": "10.0.0.1", "switchIp": "10.1.1.1"},
    {"mac": "AABBCC000002", "vendor": "Cisco", "model": "B", "room": "101", "ip": "", "switchIp": "10.1.1.1"},
    {"mac": "AABBCC000003", "vendor": "Apple", "model": "C", "room": "202", "ip": "10.0.0.3", "switchIp": "10.1.1.2"},
    {"mac": "", "vendor": "Unknown", "model": "", "room": "", "ip": "", "switchIp": ""},
]

SNAPSHOTS = [
    {"name": "first", "createdAt": "2026-01-01T10:00:00Z", "devices": DEVICES[:2]},
    {"name": "second", "createdAt": "2026-01-02T10:00:00Z", "devices": DEVICES[:3]},
]


def test_build_chart_payload_and_exports():
    payload = build_chart_payload(DEVICES, SNAPSHOTS)

    assert payload["summary"]["devices"] == 4
    assert payload["summary"]["vendors"] == 3
    charts = {chart["id"]: chart for chart in payload["charts"]}
    assert charts["vendors"]["type"] == "bar"
    assert {"label": "Cisco", "value": 2} in charts["vendors"]["items"]
    assert charts["rooms"]["type"] == "donut"
    assert charts["timeline"]["type"] == "line"
    assert charts["timeline"]["items"][-1]["value"] == 3
    assert {"label": "Без IP", "value": 2} in charts["quality"]["items"]

    svg = export_charts_svg(payload)
    assert svg["mimeType"] == "image/svg+xml"
    assert "<svg" in svg["content"]
    assert "MAC Analyzer Charts" in svg["content"]

    exported_json = export_charts_json(payload)
    assert exported_json["mimeType"] == "application/json"
    assert '"charts"' in exported_json["content"]


if __name__ == "__main__":
    test_build_chart_payload_and_exports()
    print("chart service test passed")

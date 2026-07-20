import base64
from io import BytesIO

from PIL import Image

from dashboard_service import analyze_dashboard_changes, build_dashboard_metrics_payload, build_dashboard_payload, export_dashboard_html, export_dashboard_png, filter_dashboard_devices, normalize_dashboard_settings


DEVICES = [
    {"mac": "AABBCC000001", "vendor": "Cisco", "model": "A", "room": "101", "switchIp": "10.1.1.1"},
    {"mac": "AABBCC000002", "vendor": "Cisco", "model": "B", "room": "102", "switchIp": "10.1.1.1"},
    {"mac": "AABBCC000003", "vendor": "Apple", "model": "C", "room": "101", "switchIp": "10.1.1.2"},
    {"mac": "AABBCC000004", "vendor": "Unknown", "model": "", "room": "", "switchIp": ""},
]


def test_dashboard_filters_metrics_and_export():
    settings = normalize_dashboard_settings({"vendor": "Cisco", "room": "", "chartLimit": 2, "showUnknown": False})
    filtered = filter_dashboard_devices(DEVICES, settings)
    assert len(filtered) == 2

    payload = build_dashboard_payload(DEVICES, [], settings)
    assert payload["settings"]["chartLimit"] == 2
    assert payload["metrics"]["devices"] == 2
    assert payload["metrics"]["vendors"] == 1
    assert [device["mac"] for device in payload["devices"]] == ["AABBCC000001", "AABBCC000002"]
    assert "Cisco" in payload["filters"]["vendors"]
    assert payload["filters"]["rooms"] == ["101", "102"]
    assert '<option value="Cisco" selected>Cisco</option>' in payload["filterOptionsHtml"]["vendors"]
    assert '<option value="">Все производители</option>' in payload["filterOptionsHtml"]["vendors"]
    assert '<option value="101">101</option>' in payload["filterOptionsHtml"]["rooms"]
    assert all(len(chart["items"]) <= 2 for chart in payload["charts"])

    exported = export_dashboard_html(payload)
    assert exported["mimeType"] == "text/html"
    assert "MAC Analyzer Dashboard" in exported["content"]
    assert "Metrics" in exported["content"]


def test_dashboard_metrics_payload_counts_known_and_invalid_records():
    payload = build_dashboard_metrics_payload(DEVICES, invalid=[{"row": 9}], snapshots=[], settings={})

    assert payload["metrics"]["devices"] == 4
    assert payload["metrics"]["vendors"] == 3
    assert payload["metrics"]["knownDevices"] == 3
    assert payload["metrics"]["unknownVendor"] == 1
    assert payload["metrics"]["knownPercent"] == 75
    assert payload["metrics"]["invalid"] == 1


def test_dashboard_reproduces_python_status_filters_and_history_charts():
    current = DEVICES[:2]
    snapshots = [{
        "createdAt": "2026-07-12T08:00:00Z",
        "devices": [*current, {"mac": "AABBCC000099", "vendor": "Juniper", "room": "103"}],
    }]
    movements = [{
        "mac": "AABBCC000001",
        "field_name": "switch_port",
        "from_value": "1",
        "to_value": "2",
        "changed_at": "2026-07-13T09:00:00Z",
    }]

    payload = build_dashboard_payload(current, snapshots, {"status": "all"}, movements)
    assert payload["metrics"]["total"] == 2
    assert payload["metrics"]["changed"] == 1
    assert payload["metrics"]["missing"] == 1
    assert payload["metrics"]["unchanged"] == 1
    assert payload["statusCounts"] == {"all": 2, "changed": 1, "missing": 1, "unchanged": 1}
    assert payload["statusCharts"]["dynamics"] == [{"label": "2026-07-13", "value": 1}]
    assert payload["statusCharts"]["fields"] == [{"label": "Порт", "value": 1}]
    assert payload["statusCharts"]["missing"] == [{"label": "Juniper", "value": 1}]

    changed = build_dashboard_payload(current, snapshots, {"status": "changed"}, movements)
    missing = build_dashboard_payload(current, snapshots, {"status": "missing"}, movements)
    unchanged = build_dashboard_payload(current, snapshots, {"status": "unchanged"}, movements)
    assert [row["mac"] for row in changed["devices"]] == ["AABBCC000001"]
    assert [row["mac"] for row in missing["devices"]] == ["AABBCC000099"]
    assert [row["mac"] for row in unchanged["devices"]] == ["AABBCC000002"]


def test_dashboard_png_export_contains_real_image_and_expected_dimensions():
    payload = build_dashboard_payload(DEVICES, [], {"status": "all"})
    exported = export_dashboard_png(payload)
    raw = base64.b64decode(exported["content"])

    assert exported["binary"] is True
    assert exported["mimeType"] == "image/png"
    assert exported["filename"].startswith("dashboard_")
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(raw)) as image:
        assert image.format == "PNG"
        assert image.size == (2000, 1200)


def test_dashboard_change_analysis_filters_period_and_marks_critical_network_move():
    movements = [
        {"mac": "AABBCC000001", "field_name": "switch_port", "from_value": "Gi1", "to_value": "Gi9", "changed_at": "2026-07-10T09:00:00Z"},
        {"mac": "AABBCC000002", "field_name": "model", "from_value": "A", "to_value": "B", "changed_at": "2026-06-01T09:00:00Z"},
    ]
    result = analyze_dashboard_changes([], movements, {"changeMode": "period", "changeDateFrom": "2026-07-01", "changeDateTo": "2026-07-31"})

    assert result["summary"] == {"added": 0, "removed": 0, "modified": 1, "critical": 1, "total": 1}
    assert result["changes"][0]["field"] == "switchPort"
    assert result["changes"][0]["severity"] == "critical"
    assert result["changes"][0]["before"] == "Gi1"
    assert result["changes"][0]["after"] == "Gi9"


def test_dashboard_change_analysis_compares_selected_snapshots():
    snapshots = [
        {"id": "old", "name": "Old", "createdAt": "2026-07-01T08:00:00Z", "devices": [
            {"mac": "AABBCC000001", "vendor": "Cisco", "switchPort": "Gi1"},
            {"mac": "AABBCC000099", "vendor": "Juniper"},
        ]},
        {"id": "new", "name": "New", "createdAt": "2026-07-12T08:00:00Z", "devices": [
            {"mac": "AABBCC000001", "vendor": "Cisco", "switchPort": "Gi2"},
            {"mac": "AABBCC000002", "vendor": "Apple"},
        ]},
    ]
    result = analyze_dashboard_changes(snapshots, [], {"changeMode": "snapshots", "baselineSnapshotId": "old", "comparisonSnapshotId": "new"})

    assert result["summary"] == {"added": 1, "removed": 1, "modified": 1, "critical": 2, "total": 3}
    assert result["baselineSnapshotId"] == "old"
    assert result["comparisonSnapshotId"] == "new"
    assert {item["type"] for item in result["changes"]} == {"added", "removed", "modified"}
    assert [item["id"] for item in result["snapshotOptions"]] == ["old", "new"]


if __name__ == "__main__":
    test_dashboard_filters_metrics_and_export()
    test_dashboard_metrics_payload_counts_known_and_invalid_records()
    test_dashboard_reproduces_python_status_filters_and_history_charts()
    test_dashboard_png_export_contains_real_image_and_expected_dimensions()
    test_dashboard_change_analysis_filters_period_and_marks_critical_network_move()
    test_dashboard_change_analysis_compares_selected_snapshots()
    print("dashboard service test passed")

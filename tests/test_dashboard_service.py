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

    query_settings = normalize_dashboard_settings({"query": "aabbcc:00:00:03"})
    assert query_settings["query"] == "aabbcc:00:00:03"
    assert [device["mac"] for device in filter_dashboard_devices(DEVICES, query_settings)] == ["AABBCC000003"]
    assert [device["mac"] for device in filter_dashboard_devices(DEVICES, {"query": "102"})] == ["AABBCC000002"]


def test_dashboard_metrics_payload_counts_known_and_invalid_records():
    payload = build_dashboard_metrics_payload(DEVICES, invalid=[{"row": 9}], snapshots=[], settings={})

    assert payload["metrics"]["devices"] == 4
    assert payload["metrics"]["vendors"] == 2
    assert payload["metrics"]["models"] == 3
    assert payload["metrics"]["rooms"] == 2
    assert payload["metrics"]["switches"] == 2
    assert payload["metrics"]["knownDevices"] == 3
    assert payload["metrics"]["unknownVendor"] == 1
    assert payload["metrics"]["knownPercent"] == 75
    assert payload["metrics"]["invalid"] == 1
    assert payload["metrics"]["withRoom"] == 3
    assert payload["metrics"]["withSwitch"] == 3
    assert payload["metrics"]["withModel"] == 3
    assert payload["metrics"]["uniqueOui3"] == 1
    assert payload["metrics"]["uniqueOui4"] == 1
    assert payload["metrics"]["uniqueOui5"] == 1
    assert payload["distributions"]["vendors"][:2] == [
        {"label": "Cisco", "value": 2},
        {"label": "Apple", "value": 1},
    ]
    assert payload["distributions"]["rooms"][0] == {"label": "101", "value": 2}
    assert payload["distributions"]["switches"][0] == {"label": "10.1.1.1", "value": 2}
    assert payload["distributions"]["oui3"] == [{"label": "AABBCC", "value": 4}]

    same_name = build_dashboard_metrics_payload([
        {"mac": "001122000011", "room": "Переговорная", "smartroomId": "ROOM-A"},
        {"mac": "001122000012", "room": "Переговорная", "smartroomId": "ROOM-B"},
    ])
    assert same_name["metrics"]["rooms"] == 2
    assert same_name["distributions"]["rooms"] == [{"label": "Переговорная", "value": 2}]


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


def test_dashboard_change_analysis_filters_period_without_marking_port_change_critical():
    movements = [
        {"mac": "AABBCC000001", "field_name": "switch_port", "from_value": "Gi1", "to_value": "Gi9", "changed_at": "2026-07-10T09:00:00Z"},
        {"mac": "AABBCC000002", "field_name": "model", "from_value": "A", "to_value": "B", "changed_at": "2026-06-01T09:00:00Z"},
    ]
    result = analyze_dashboard_changes([], movements, {"changeMode": "period", "changeDateFrom": "2026-07-01", "changeDateTo": "2026-07-31"})

    assert result["summary"] == {
        "added": 0, "removed": 0, "modified": 1, "critical": 0, "total": 1,
        "changedRooms": 0, "changedRoomValues": [],
    }
    assert result["changes"][0]["field"] == "switchPort"
    assert result["changes"][0]["severity"] == "medium"
    assert result["changes"][0]["before"] == "Gi1"
    assert result["changes"][0]["after"] == "Gi9"


def test_dashboard_normalizes_russian_history_and_ignores_missing_new_values():
    movements = [
        {
            "mac": "AABBCC000001", "type": "Изменено", "field": "IP коммутатора",
            "before": " 10.0.0.1 ", "after": "10.0.0.2", "changedAt": "2026-07-10T09:00:00Z",
        },
        {
            "mac": "AABBCC000002", "type": "Изменено", "field": "Модель",
            "before": "Known", "after": "", "changedAt": "2026-07-10T09:01:00Z",
        },
    ]
    result = analyze_dashboard_changes(
        [], movements, {"changeMode": "period", "changeDateFrom": "2026-07-01", "changeDateTo": "2026-07-31"}
    )

    assert result["summary"]["modified"] == 1
    assert result["summary"]["critical"] == 1
    assert len(result["changes"]) == 1
    assert result["changes"][0]["type"] == "modified"
    assert result["changes"][0]["field"] == "switchIp"
    assert result["changes"][0]["severity"] == "critical"


def test_newly_filled_switch_ip_is_not_a_false_critical_change():
    snapshots = [
        {"id": "old", "createdAt": "2026-07-01T00:00:00Z", "devices": [{"mac": "AABBCC000001", "switchIp": ""}]},
        {"id": "new", "createdAt": "2026-07-02T00:00:00Z", "devices": [{"mac": "AABBCC000001", "switchIp": "10.0.0.2"}]},
    ]
    result = analyze_dashboard_changes(
        snapshots, [], {"changeMode": "snapshots", "baselineSnapshotId": "old", "comparisonSnapshotId": "new"}
    )
    change = next(item for item in result["changes"] if item["field"] == "switchIp")
    assert change["severity"] == "medium"
    assert result["summary"]["critical"] == 0


def test_dashboard_change_analysis_compares_selected_snapshots():
    snapshots = [
        {"id": "old", "name": "Old", "createdAt": "2026-07-01T08:00:00Z", "devices": [
            {"mac": "AABBCC000001", "vendor": "Cisco", "ip": "192.0.2.10", "room": "101", "switchIp": "10.0.0.1", "switchPort": "Gi1"},
            {"mac": "AABBCC000099", "vendor": "Juniper"},
        ]},
        {"id": "new", "name": "New", "createdAt": "2026-07-12T08:00:00Z", "devices": [
            {"mac": "AABBCC000001", "vendor": "Cisco", "ip": "192.0.2.10", "room": "101", "switchIp": "10.0.0.2", "switchPort": "Gi2"},
            {"mac": "AABBCC000002", "vendor": "Apple"},
        ]},
    ]
    result = analyze_dashboard_changes(snapshots, [], {"changeMode": "snapshots", "baselineSnapshotId": "old", "comparisonSnapshotId": "new"})

    assert result["summary"] == {
        "added": 1, "removed": 1, "modified": 1, "critical": 1, "total": 3,
        "changedRooms": 1, "changedRoomValues": ["101"],
    }
    assert result["baselineSnapshotId"] == "old"
    assert result["comparisonSnapshotId"] == "new"
    assert {item["type"] for item in result["changes"]} == {"added", "removed", "modified"}
    assert [item["id"] for item in result["snapshotOptions"]] == ["old", "new"]
    switch_change = next(item for item in result["changes"] if item["field"] == "switchIp")
    assert switch_change["severity"] == "critical"
    assert switch_change["beforeDevice"]["room"] == "101"
    assert switch_change["afterDevice"]["ip"] == "192.0.2.10"
    assert next(item for item in result["changes"] if item["type"] == "removed")["severity"] == "high"


def test_dashboard_uses_previous_and_current_final_snapshots_for_all_status_metrics():
    before = {
        "id": "final-before", "name": "Анализ: before.xlsx", "snapshotOrder": 10,
        "createdAt": "2026-07-01T08:00:00Z", "devices": [
            {"mac": "AABBCC000001", "vendor": "Cisco", "model": "A", "room": "101"},
            {"mac": "AABBCC000099", "vendor": "Juniper", "model": "X", "room": "103"},
        ],
    }
    current = {
        "id": "final-current", "name": "Анализ: current.xlsx", "snapshotOrder": 11,
        "createdAt": "2026-07-12T08:00:00Z", "devices": [
            {"mac": "AABBCC000001", "vendor": "Cisco", "model": "B", "room": "101"},
            {"mac": "AABBCC000002", "vendor": "Apple", "model": "C", "room": "102"},
        ],
    }
    metadata = [
        {key: value for key, value in before.items() if key != "devices"},
        {key: value for key, value in current.items() if key != "devices"},
    ]
    payload = build_dashboard_payload(
        current["devices"],
        metadata,
        {"changeMode": "snapshots"},
        movements=[{"mac": "FFFFFFFFFFFF", "field": "model", "before": "old", "after": "noise"}],
        change_snapshots=[before, current],
        snapshot_options=metadata,
    )

    assert payload["changeAnalysis"]["baselineSnapshotId"] == "final-before"
    assert payload["changeAnalysis"]["comparisonSnapshotId"] == "final-current"
    assert payload["metrics"]["total"] == 2
    assert payload["metrics"]["changed"] == 1
    assert payload["metrics"]["missing"] == 1
    assert payload["metrics"]["unchanged"] == 0
    assert payload["changeAnalysis"]["summary"] == {
        "added": 1, "removed": 1, "modified": 1, "critical": 0, "total": 3,
        "changedRooms": 3, "changedRoomValues": ["101", "102", "103"],
    }
    assert {item["mac"] for item in payload["devices"]} == {"AABBCC000001", "AABBCC000002"}


def test_dashboard_reports_unique_macs_across_uploads_and_latest_count():
    snapshots = [
        {"id": "one", "name": "Анализ: one.xlsx", "createdAt": "2026-07-01T08:00:00Z", "devices": [
            {"mac": "AABBCC000001"}, {"mac": "AABBCC000002"},
        ]},
        {"id": "two", "name": "Анализ: two.xlsx", "createdAt": "2026-07-02T08:00:00Z", "devices": [
            {"mac": "AABBCC000002"}, {"mac": "AABBCC000003"},
        ]},
    ]
    payload = build_dashboard_payload(snapshots[-1]["devices"], snapshots, {"changeMode": "snapshots"})

    assert payload["metrics"]["total"] == 2
    assert payload["metrics"]["totalAcross"] == 3
    assert payload["uploadFleet"]["latestCount"] == 2
    assert [item["count"] for item in payload["uploadFleet"]["series"]] == [2, 2]
    assert [item["delta"] for item in payload["uploadFleet"]["series"]] == [0, 0]


def test_dashboard_tracks_smartroom_change_without_false_device_replacement():
    snapshots = [
        {
            "id": "old",
            "name": "Анализ: old.xlsx",
            "kind": "analysis",
            "createdAt": "2026-07-01T08:00:00Z",
            "devices": [{"mac": "001122334455", "room": "101", "smartroomId": "SR-OLD"}],
        },
        {
            "id": "new",
            "name": "Анализ: new.xlsx",
            "kind": "analysis",
            "createdAt": "2026-07-02T08:00:00Z",
            "devices": [{"mac": "001122334455", "room": "101", "smartroomId": "SR-NEW"}],
        },
    ]
    result = analyze_dashboard_changes(
        snapshots, [], {"changeMode": "snapshots", "baselineSnapshotId": "old", "comparisonSnapshotId": "new"}
    )
    assert result["summary"]["changedRooms"] == 1
    assert result["summary"]["changedRoomValues"] == ["101"]
    assert result["summary"]["added"] == 0
    assert result["summary"]["removed"] == 0
    assert result["summary"]["modified"] == 1
    assert result["changes"][0]["field"] == "smartroomId"
    assert {item["identity"] for item in result["changes"]} == {"mac:001122334455"}


if __name__ == "__main__":
    test_dashboard_filters_metrics_and_export()
    test_dashboard_metrics_payload_counts_known_and_invalid_records()
    test_dashboard_reproduces_python_status_filters_and_history_charts()
    test_dashboard_png_export_contains_real_image_and_expected_dimensions()
    test_dashboard_change_analysis_filters_period_without_marking_port_change_critical()
    test_dashboard_normalizes_russian_history_and_ignores_missing_new_values()
    test_newly_filled_switch_ip_is_not_a_false_critical_change()
    test_dashboard_change_analysis_compares_selected_snapshots()
    test_dashboard_uses_previous_and_current_final_snapshots_for_all_status_metrics()
    test_dashboard_reports_unique_macs_across_uploads_and_latest_count()
    test_dashboard_tracks_smartroom_change_without_false_device_replacement()
    print("dashboard service test passed")

from device_analytics_service import build_device_analytics, export_device_analytics_html


def test_device_analytics_builds_mac_chronology():
    mac = "AABBCC000001"
    payload = build_device_analytics(
        mac,
        devices=[{"mac": mac, "macFormatted": "AA:BB:CC:00:00:01", "vendor": "Vendor B", "model": "Model B"}],
        snapshots=[
            {
                "id": "snapshot-1",
                "name": "Initial import",
                "source": "file-one.csv",
                "createdAt": "2024-01-01T10:00:00Z",
                "devices": [{"mac": mac, "vendor": "Vendor A", "model": "Model A"}],
            }
        ],
        history=[
            {
                "mac": mac,
                "recorded_at": "2024-01-02T10:00:00Z",
                "vendor": "Vendor B",
                "model": "Model B",
                "ip": "10.0.0.2",
                "address": "Room 2",
                "source": "file-two.csv",
            }
        ],
        movements=[
            {
                "mac": mac,
                "changed_at": "2024-01-03T10:00:00Z",
                "field_name": "vendor",
                "from_value": "Vendor A",
                "to_value": "Vendor B",
                "source": "file-two.csv",
            }
        ],
        model_mappings={"AABBCC0000": "Model B"},
    )

    assert payload["metrics"]["chronologyEvents"] == 3
    assert [item["type"] for item in payload["chronology"]] == ["movement", "history", "snapshot"]
    assert payload["chronology"][0]["event"] == "Изменение поля"
    assert "Vendor A" in payload["chronologyRowsHtml"]
    assert "Запись истории" in payload["chronologyRowsHtml"]
    assert "Chronology events" in payload["chronologySummaryHtml"]

    exported = export_device_analytics_html(payload)
    assert "MAC chronology" in exported["content"]
    assert "Vendor B" in exported["content"]


if __name__ == "__main__":
    test_device_analytics_builds_mac_chronology()
    print("device analytics chronology test passed")

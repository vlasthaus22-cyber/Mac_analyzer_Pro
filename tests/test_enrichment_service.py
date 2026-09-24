from backend.services.workspace.enrichment_service import enrich_files


FILES = [
    {
        "name": "primary.csv",
        "mapping": {"mac": 0, "vendor": 1, "ip": 2},
        "rows": [
            ["mac", "vendor", "ip"],
            ["AA:BB:CC:00:00:01", "Vendor A", "10.0.0.1"],
            ["bad-mac", "Broken", "10.0.0.9"],
        ],
    },
    {
        "name": "extra.csv",
        "mapping": {"mac": 0, "address": 1, "room": 2},
        "rows": [
            ["mac", "address", "room"],
            ["AA:BB:CC:00:00:01", "Rack 1", "101"],
            ["AA:BB:CC:00:00:02", "Rack 2", "102"],
        ],
    },
]


def test_enrichment_primary_and_merge_strategies():
    primary = enrich_files(FILES, "primary")
    assert primary["progress"]["files"] == 2
    assert primary["progress"]["rows"] == 4
    assert primary["progress"]["valid"] == 2
    assert primary["progress"]["invalid"] == 1
    assert primary["devices"][0]["mac"] == "AABBCC000001"
    assert primary["devices"][0]["address"] == "Rack 1"
    assert primary["devices"][1]["address"] == "Rack 2"
    assert primary["devices"][0]["room"] == "101"

    merged = enrich_files(FILES, "merge")
    assert merged["progress"]["valid"] == 2
    assert [device["mac"] for device in merged["devices"]] == ["AABBCC000001", "AABBCC000002"]
    assert merged["devices"][1]["address"] == "Rack 2"
    assert merged["devices"][0]["source"] == "primary.csv + extra.csv"
    assert merged["devices"][1]["source"] == "extra.csv"


def test_enrichment_preserves_device_authentication_time_column():
    result = enrich_files([{
        "name": "auth.csv",
        "mapping": {"mac": 0, "authenticationTime": 1},
        "rows": [["MAC", "Время аутентификации устройства"], ["00:11:22:33:44:55", "2026-09-13 10:15:00"]],
    }])
    assert result["devices"][0]["authenticationTime"] == "2026-09-13 10:15:00"
    serial = enrich_files([{
        "name": "auth.xlsx", "mapping": {"mac": 0, "authenticationTime": 1},
        "rows": [["MAC", "Auth"], ["00:11:22:33:44:66", "46000.5"]],
    }])
    assert serial["devices"][0]["authenticationTime"] == "2025-12-09T12:00:00Z"


def test_smartroom_secondary_interface_mac_matches_one_primary_device():
    result = enrich_files([
        {
            "name": "main.xlsx", "role": "primary",
            "mapping": {"mac": 0, "ip": 1},
            "rows": [["MAC", "IP"], ["00:11:22:33:44:55", ""]],
        },
        {
            "name": "smartroom.xlsx", "role": "smartroom",
            "mapping": {"mac": 0, "secondaryMac": 1, "smartroomId": 2, "room": 3},
            "rows": [["MAC 1", "MAC 2", "Smartroom ID", "Room"], ["AA:BB:CC:DD:EE:FF", "00-11-22-33-44-55", "SR-101", "Переговорная 101"]],
        },
    ])
    assert len(result["devices"]) == 1
    device = result["devices"][0]
    assert device["mac"] == "001122334455"
    assert device["secondaryMac"] == "AABBCCDDEEFF"
    assert device["smartroomId"] == "SR-101"
    assert result["diagnostics"]["counts"]["smartroomMatched"] == 1


def test_smartroom_device_type_is_merged_into_the_final_device():
    result = enrich_files([
        {"name": "main.csv", "role": "primary", "mapping": {"mac": 0}, "rows": [["MAC"], ["00:11:22:33:44:55"]]},
        {"name": "rooms.csv", "role": "smartroom", "mapping": {"mac": 0, "deviceType": 1}, "rows": [["MAC", "Тип модели"], ["00:11:22:33:44:55", "Video Conference"]]},
    ])
    assert len(result["devices"]) == 1
    assert result["devices"][0]["deviceType"] == "Video Conference"


if __name__ == "__main__":
    test_enrichment_primary_and_merge_strategies()
    test_enrichment_preserves_device_authentication_time_column()
    test_smartroom_secondary_interface_mac_matches_one_primary_device()
    print("enrichment service test passed")

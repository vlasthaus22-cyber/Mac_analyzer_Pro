from server import (
    apply_detection_to_devices,
    apply_ip_mappings_to_devices,
    autodetect_ip_mappings,
    db_connection,
    export_ip_mappings_csv,
    import_ip_mappings,
    init_database,
    ip_mapping_statistics,
)


TEST_IPS = ("203.0.113.10", "203.0.113.11", "203.0.113.12")


def cleanup():
    with db_connection() as conn:
        for switch_ip in TEST_IPS:
            conn.execute("DELETE FROM ip_address_mappings WHERE switch_ip = ?", (switch_ip,))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = 'A1B2C3'")
        conn.execute("DELETE FROM model_mappings WHERE prefix = 'A1B2C3D4E5'")


def mapping_address(switch_ip):
    with db_connection() as conn:
        row = conn.execute(
            "SELECT physical_address, source FROM ip_address_mappings WHERE switch_ip = ?",
            (switch_ip,),
        ).fetchone()
    return dict(row) if row else None


def test_ip_mapping_import_export_and_autodetect():
    init_database()
    cleanup()

    csv_result = import_ip_mappings(
        "switches.csv",
        "switch_ip,physical_address\n203.0.113.10,Server room\nnot-an-ip,Skip me\n",
    )
    assert csv_result == {"imported": 1, "skipped": 1}
    assert mapping_address("203.0.113.10") == {"physical_address": "Server room", "source": "import"}

    json_result = import_ip_mappings(
        "switches.json",
        '[{"ip":"203.0.113.11","location":"Rack 7"}]',
    )
    assert json_result == {"imported": 1, "skipped": 0}
    assert mapping_address("203.0.113.11") == {"physical_address": "Rack 7", "source": "import"}

    auto_result = autodetect_ip_mappings([
        {"switchIp": "203.0.113.12", "address": "Floor A"},
        {"switchIp": "203.0.113.12", "address": "Floor B"},
        {"switchIp": "203.0.113.12", "address": "Floor B"},
        {"switchIp": "bad", "address": "Ignored"},
    ])
    assert auto_result["imported"] == 1
    assert auto_result["mappings"] == [{"switchIp": "203.0.113.12", "address": "Floor B"}]
    assert mapping_address("203.0.113.12") == {"physical_address": "Floor B", "source": "auto"}

    applied = apply_ip_mappings_to_devices([
        {"mac": "AA:BB:CC:00:00:01", "switchIp": "203.0.113.10", "address": ""},
        {"mac": "AA:BB:CC:00:00:02", "switchIp": "203.0.113.12", "address": "Old"},
        {"mac": "AA:BB:CC:00:00:03", "switchIp": "203.0.113.99", "address": ""},
    ])
    by_mac = {item["mac"]: item for item in applied["devices"]}
    assert by_mac["AA:BB:CC:00:00:01"]["address"] == "Server room"
    assert by_mac["AA:BB:CC:00:00:01"]["addressSource"] == "ip_mapping"
    assert by_mac["AA:BB:CC:00:00:02"]["address"] == "Floor B"
    assert applied["summary"]["matched"] == 2
    assert applied["summary"]["filled"] == 1
    assert applied["summary"]["missingSwitches"] == ["203.0.113.99"]

    with db_connection() as conn:
        conn.execute(
            "INSERT INTO vendor_mappings (oui, vendor, source, updated_at) VALUES ('A1B2C3', 'Detected Vendor', 'test', '2026-08-10T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO model_mappings (prefix, model, source, updated_at) VALUES ('A1B2C3D4E5', 'Detected Model', 'test', '2026-08-10T00:00:00Z')"
        )
    detected = apply_detection_to_devices([
        {"mac": "A1:B2:C3:D4:E5:F6", "switchIp": "203.0.113.10", "address": "", "vendor": "Unknown", "model": ""},
        {"mac": "A1:B2:C3:D4:E5:01", "switchIp": "", "address": "Manual room", "vendor": "Manual Vendor", "model": "Manual Model"},
    ])
    assert detected["devices"][0]["address"] == "Server room"
    assert detected["devices"][0]["vendor"] == "Detected Vendor"
    assert detected["devices"][0]["model"] == "Detected Model"
    assert detected["summary"] == {"devices": 2, "changedDevices": 1, "address": 1, "vendor": 1, "model": 1}
    assert detected["devices"][1]["address"] == "Manual room"
    assert detected["devices"][1]["vendor"] == "Manual Vendor"
    assert detected["devices"][1]["model"] == "Manual Model"

    stats = ip_mapping_statistics(applied["devices"])
    assert stats["totalMappings"] >= 3
    assert stats["deviceSwitches"] == 3
    assert stats["matchedSwitches"] == 2
    assert stats["missingSwitches"] == 1
    assert "203.0.113.99" in stats["missing"]

    csv_export = export_ip_mappings_csv()
    assert "203.0.113.10,Server room,import" in csv_export
    assert "203.0.113.12,Floor B,auto" in csv_export

    cleanup()


if __name__ == "__main__":
    test_ip_mapping_import_export_and_autodetect()
    print("ip mapping import export test passed")

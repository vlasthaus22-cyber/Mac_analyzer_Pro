from server import (
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

from server import (
    db_connection,
    build_enrichment_context,
    enrich_device,
    history_enrichment_settings,
    init_database,
    learn_vendor_model_mappings,
    mappings,
    save_history_enrichment_settings,
    save_history,
    save_statistics_snapshot,
    vendor_model_history_suggestion,
    vendor_model_history,
    vendor_model_upload_history,
    vendor_model_statistics,
)


def cleanup(*macs):
    with db_connection() as conn:
        for mac in macs:
            conn.execute("DELETE FROM vendor_model_history WHERE mac = ?", (mac,))
            conn.execute("DELETE FROM mac_movements WHERE mac = ?", (mac,))
            conn.execute("DELETE FROM mac_history WHERE mac = ?", (mac,))
            for prefix_length in (6, 8, 10):
                conn.execute("DELETE FROM vendor_mappings WHERE oui = ? AND source = 'learned'", (mac[:prefix_length],))
            conn.execute("DELETE FROM model_mappings WHERE prefix = ? AND source = 'learned'", (mac[:10],))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", ("DADAD1",))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", ("DADAD100",))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", ("DADAD10000",))
        conn.execute("DELETE FROM model_mappings WHERE prefix = ?", ("DADAD1",))
        conn.execute("DELETE FROM model_mappings WHERE prefix = ?", ("DADAD100",))
        conn.execute("DELETE FROM model_mappings WHERE prefix = ?", ("DADAD10000",))
        conn.execute("DELETE FROM vendor_model_history WHERE mac LIKE 'E1E2E3AA%'")
        conn.execute("DELETE FROM vendor_model_history WHERE mac LIKE 'E1E2E4AA%'")
        conn.execute("DELETE FROM mac_history WHERE mac LIKE 'E1E2E3AA%'")
        conn.execute("DELETE FROM mac_history WHERE mac LIKE 'E1E2E4AA%'")
        conn.execute("DELETE FROM snapshots WHERE source IN (?, ?)", ("vendor-model-history-test", "vendor-model-history-upload-test"))
        conn.execute("DELETE FROM app_settings WHERE key = 'history_enrichment'")
        conn.execute("DELETE FROM smartroom_room_mappings WHERE smartroom_id LIKE 'TEST-SR-%' OR room IN ('B-402', 'C-403')")


def test_vendor_model_history_and_learning():
    init_database()
    mac_one = "DADAD1000001"
    mac_two = "DADAD1000002"
    cleanup(mac_one, mac_two)

    devices = [
        enrich_device({"mac": mac_one, "vendor": "Acme Lab Switches", "model": "ALS-48"}),
        enrich_device({"mac": mac_two, "vendor": "Acme Lab Switches", "model": "ALS-48"}),
    ]
    save_history(devices, "vendor-model-history-test")

    history = vendor_model_history("Acme", limit="bad-limit")
    assert history["statistics"]["records"] == 2
    assert history["statistics"]["uniqueMacs"] == 2
    assert history["statistics"]["vendors"][0] == {"name": "Acme Lab Switches", "count": 2}
    assert history["statistics"]["models"][0] == {"name": "ALS-48", "count": 2}
    stats = vendor_model_statistics("Acme")
    assert stats["totals"]["records"] == 2
    assert stats["totals"]["uniqueMacs"] == 2
    assert stats["vendors"][0]["name"] == "Acme Lab Switches"
    assert stats["models"][0]["name"] == "ALS-48"
    assert stats["sources"][0]["name"] == "vendor-model-history-test"
    save_statistics_snapshot(devices, "Vendor model upload", "vendor-model-history-test", "vendor-model-upload-snapshot")
    uploads = vendor_model_upload_history("Acme")
    upload = next(item for item in uploads["uploads"] if item["source"] == "vendor-model-history-test")
    assert upload["records"] == 2
    assert upload["uniqueMacs"] == 2
    assert upload["vendors"] == 1
    assert upload["models"] == 1
    assert upload["snapshots"] >= 1
    assert uploads["summary"]["uploads"] >= 1

    # save_history learns repeated observations immediately. Vendors use OUI3,
    # OUI4 and MAC5; model identity follows the PyQt MAC5 rule only.
    learned = learn_vendor_model_mappings(min_count=2, source="vendor-model-history-test")
    assert learned == {"vendors": 0, "models": 0}
    vendor_mappings = mappings("vendors")
    model_mappings = mappings("models")
    for prefix in ("DADAD1", "DADAD100", "DADAD10000"):
        assert vendor_mappings[prefix] == "Acme Lab Switches"
    assert model_mappings["DADAD10000"] == "ALS-48"
    assert "DADAD1" not in model_mappings
    assert "DADAD100" not in model_mappings

    cleanup(mac_one, mac_two)


def test_history_enricher_uses_vendor_model_history_without_mac_history():
    init_database()
    mac_source = "E1E2E3AABB01"
    mac_similar = "E1E2E3AABB02"
    cleanup(mac_source, mac_similar)

    save_history([
        enrich_device({"mac": mac_source, "vendor": "History Enriched Vendor", "model": "HE-9000"}),
    ], "vendor-model-history-enricher-test")
    with db_connection() as conn:
        conn.execute("DELETE FROM mac_history WHERE mac IN (?, ?)", (mac_source, mac_similar))
        conn.execute("DELETE FROM mac_movements WHERE mac IN (?, ?)", (mac_source, mac_similar))

    exact = enrich_device({"mac": mac_source})
    similar = enrich_device({"mac": mac_similar})
    suggestion = vendor_model_history_suggestion(mac_similar)

    assert exact["vendor"] == "History Enriched Vendor"
    assert exact["vendorSource"] == "vendor_model_history_exact"
    assert exact["model"] == "HE-9000"
    assert exact["modelSource"] == "vendor_model_history_exact"
    assert similar["vendor"] == "History Enriched Vendor"
    assert similar["vendorSource"] == "vendor_model_history_prefix"
    assert suggestion["matchedPrefix"] == "E1E2E3AABB"

    cleanup(mac_source, mac_similar)


def test_history_enrichment_settings_control_exact_and_prefix_matching():
    init_database()
    mac_source = "E1E2E4AABB01"
    mac_similar = "E1E2E4AABB02"
    mac_oui_only = "E1E2E4CCDD03"
    cleanup(mac_source, mac_similar, mac_oui_only)

    save_history([
        enrich_device({"mac": mac_source, "vendor": "Configurable History Vendor", "model": "CH-9000"}),
    ], "vendor-model-history-settings-test")
    with db_connection() as conn:
        conn.execute("DELETE FROM mac_history WHERE mac IN (?, ?, ?)", (mac_source, mac_similar, mac_oui_only))
        conn.execute("DELETE FROM mac_movements WHERE mac IN (?, ?, ?)", (mac_source, mac_similar, mac_oui_only))

    disabled = save_history_enrichment_settings({"enabled": False})
    assert disabled["enabled"] is False
    assert vendor_model_history_suggestion(mac_source) == {}
    assert enrich_device({"mac": mac_source})["vendor"] == "Unknown"

    mac5_only = save_history_enrichment_settings({"enabled": True, "priorityHistory": True, "useMac5Match": True, "useOuiMatch": False})
    assert mac5_only["useOuiMatch"] is False
    assert vendor_model_history_suggestion(mac_similar)["matchedPrefix"] == "E1E2E4AABB"
    assert vendor_model_history_suggestion(mac_oui_only) == {}

    oui_enabled = save_history_enrichment_settings({"enabled": True, "priorityHistory": True, "useMac5Match": False, "useOuiMatch": True})
    assert oui_enabled["useMac5Match"] is False
    assert vendor_model_history_suggestion(mac_similar)["matchedPrefix"] == "E1E2E4"
    assert enrich_device({"mac": mac_oui_only})["vendorSource"] == "vendor_model_history_prefix"

    priority_fallback = save_history_enrichment_settings({"enabled": True, "priorityHistory": False, "useMac5Match": True, "useOuiMatch": True})
    assert priority_fallback["priorityHistory"] is False
    device_with_file_vendor = enrich_device({"mac": mac_similar, "vendor": "File Vendor"})
    assert device_with_file_vendor["vendor"] == "File Vendor"
    assert device_with_file_vendor["vendorSource"] == "file"
    device_without_file_vendor = enrich_device({"mac": mac_similar})
    assert device_without_file_vendor["vendor"] == "Configurable History Vendor"
    assert device_without_file_vendor["vendorSource"] == "vendor_model_history_prefix"

    save_history_enrichment_settings({})
    assert history_enrichment_settings()["enabled"] is True
    cleanup(mac_source, mac_similar, mac_oui_only)


def test_save_history_records_enrichment_before_after_even_when_value_is_cleared():
    init_database()
    mac = "E1E2E4AACC01"
    cleanup(mac)

    first = enrich_device({"mac": mac, "vendor": "Before Vendor", "model": "Before Model", "ip": "10.10.10.1"})
    save_history([first], "history-before-enrichment")
    cleared = {**first, "vendor": "", "model": "", "ip": "", "source": "history-after-enrichment"}
    save_history([cleared], "history-after-enrichment")

    with db_connection() as conn:
        rows = [dict(row) for row in conn.execute(
            "SELECT field_name, from_value, to_value, source FROM mac_movements WHERE mac = ? ORDER BY id",
            (mac,),
        ).fetchall()]

    assert {"field_name": "vendor", "from_value": "Before Vendor", "to_value": "", "source": "history-after-enrichment"} in rows
    assert {"field_name": "model", "from_value": "Before Model", "to_value": "", "source": "history-after-enrichment"} in rows
    assert {"field_name": "ip", "from_value": "10.10.10.1", "to_value": "", "source": "history-after-enrichment"} in rows
    cleanup(mac)


def test_save_history_uses_file_date_for_records_movements_and_vendor_model_history():
    init_database()
    mac = "E1E2E4AADD01"
    file_date_one = "2024-04-05T06:07:08Z"
    file_date_two = "2024-04-06T06:07:08Z"
    cleanup(mac)

    first = enrich_device({"mac": mac, "vendor": "File Date Vendor", "model": "FD-1"})
    save_history([first], "file-date-one.csv", file_date_one)
    second = {**first, "vendor": "File Date Vendor 2", "model": "FD-2"}
    save_history([second], "file-date-two.csv", file_date_two)

    with db_connection() as conn:
        history_rows = [dict(row) for row in conn.execute("SELECT source, recorded_at FROM mac_history WHERE mac = ? ORDER BY id", (mac,)).fetchall()]
        movement = dict(conn.execute("SELECT field_name, changed_at FROM mac_movements WHERE mac = ? AND field_name = 'vendor' ORDER BY id DESC LIMIT 1", (mac,)).fetchone())
        vendor_model = dict(conn.execute("SELECT source, observed_at FROM vendor_model_history WHERE mac = ? ORDER BY id DESC LIMIT 1", (mac,)).fetchone())

    assert history_rows[0] == {"source": "file-date-one.csv", "recorded_at": file_date_one}
    assert history_rows[1] == {"source": "file-date-two.csv", "recorded_at": file_date_two}
    assert movement["changed_at"] == file_date_two
    assert vendor_model == {"source": "file-date-two.csv", "observed_at": file_date_two}
    cleanup(mac)


def test_enrichment_restores_latest_non_empty_history_fields_and_switch_address():
    init_database()
    source_mac = "F2E3D4C5B601"
    same_switch_mac = "F2E3D4C5B602"
    switch_ip = "198.51.100.241"
    cleanup(source_mac, same_switch_mac)
    with db_connection() as conn:
        conn.execute("DELETE FROM ip_address_mappings WHERE switch_ip = ?", (switch_ip,))
        conn.execute(
            """
            INSERT INTO mac_history
                (mac, mac_formatted, oui, vendor, model, ip, address, room,
                 smartroom_id, switch_ip, switch_port, source, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_mac, "F2:E3:D4:C5:B6:01", source_mac[:6],
                "Previous Export Vendor", "PE-48", "192.0.2.10",
                "Корпус А, этаж 3", "А-305", "SR-305", switch_ip, "Gi1/0/7",
                "previous-complete.xlsx", "2025-01-01T10:00:00Z",
            ),
        )
        # A later incomplete export must not hide useful values from the
        # earlier complete export.
        conn.execute(
            """
            INSERT INTO mac_history
                (mac, mac_formatted, oui, vendor, model, ip, address, room,
                 smartroom_id, switch_ip, switch_port, source, recorded_at)
            VALUES (?, ?, ?, '', '', '', '', '', '', ?, '', ?, ?)
            """,
            (
                source_mac, "F2:E3:D4:C5:B6:01", source_mac[:6], switch_ip,
                "later-incomplete.xlsx", "2025-02-01T10:00:00Z",
            ),
        )

    restored = enrich_device({"mac": source_mac, "switchIp": switch_ip})
    assert restored["vendor"] == "Previous Export Vendor"
    assert restored["model"] == "PE-48"
    assert restored["address"] == "Корпус А, этаж 3"
    assert restored["room"] == "А-305"
    assert restored["smartroomId"] == "SR-305"
    assert restored["switchPort"] == "Gi1/0/7"
    assert enrich_device({"mac": source_mac})["switchIp"] == switch_ip

    # The learned physical location also applies to another device observed
    # on the same switch IP, without requiring a manually imported mapping.
    same_switch = enrich_device({"mac": same_switch_mac, "switchIp": switch_ip})
    assert same_switch["address"] == "Корпус А, этаж 3"

    # Values supplied by the current export always remain authoritative.
    current = enrich_device({
        "mac": source_mac,
        "vendor": "Current Vendor",
        "model": "CURRENT-1",
        "address": "Текущий адрес",
        "switchIp": switch_ip,
    })
    assert current["vendor"] == "Current Vendor"
    assert current["model"] == "CURRENT-1"
    assert current["address"] == "Текущий адрес"

    cleanup(source_mac, same_switch_mac)
    with db_connection() as conn:
        conn.execute("DELETE FROM ip_address_mappings WHERE switch_ip = ?", (switch_ip,))


def test_save_history_learns_switch_address_and_smartroom_room_mapping():
    init_database()
    source_mac = "F2E3D4C5B611"
    target_mac = "F2E3D4C5B612"
    switch_ip = "198.51.100.242"
    smartroom_id = "TEST-SR-402"
    cleanup(source_mac, target_mac)
    with db_connection() as conn:
        conn.execute("DELETE FROM ip_address_mappings WHERE switch_ip = ?", (switch_ip,))

    save_history([enrich_device({
        "mac": source_mac, "switchIp": switch_ip, "address": "Building B, floor 4",
        "smartroomId": smartroom_id, "room": "B-402",
    })], "mapping-learning-test")
    enriched = enrich_device({"mac": target_mac, "switchIp": switch_ip, "smartroomId": smartroom_id})
    assert enriched["address"] == "Building B, floor 4"
    assert enriched["room"] == "B-402"
    assert enriched["smartroomId"] == smartroom_id

    batch_context = build_enrichment_context([
        {"mac": source_mac, "switchIp": "198.51.100.243", "address": "Building C", "smartroomId": "TEST-SR-403", "room": "C-403"},
        {"mac": target_mac, "switchIp": "198.51.100.243", "smartroomId": "TEST-SR-403"},
    ])
    batch_enriched = enrich_device({"mac": target_mac, "switchIp": "198.51.100.243", "smartroomId": "TEST-SR-403"}, batch_context)
    assert batch_enriched["address"] == "Building C"
    assert batch_enriched["room"] == "C-403"
    assert batch_enriched["smartroomId"] == "TEST-SR-403"

    cleanup(source_mac, target_mac)
    with db_connection() as conn:
        conn.execute("DELETE FROM ip_address_mappings WHERE switch_ip = ?", (switch_ip,))


def test_explicit_ddio_switch_change_uses_export_pair_instead_of_stale_database_state():
    init_database()
    mac = "F2E3D4C5B621"
    cleanup(mac)
    save_history([enrich_device({"mac": mac, "switchIp": "10.20.30.0"})], "older-database-state", "2026-08-04T10:00:00Z")
    save_history(
        [enrich_device({"mac": mac, "switchIp": "10.20.30.2"})],
        "ddio-explicit-test", "2026-08-05T10:00:00Z",
        {mac: {"ip": "192.0.2.77", "match": "reservation"}},
        [{"mac": mac, "before": "10.20.30.1", "after": "10.20.30.2"}],
    )
    with db_connection() as conn:
        movements = [dict(row) for row in conn.execute(
            "SELECT field_name, from_value, to_value, ddio_candidate_ip, ddio_match FROM mac_movements WHERE mac = ? AND field_name = 'switchIp' ORDER BY id",
            (mac,),
        ).fetchall()]
    assert movements == [{
        "field_name": "switchIp", "from_value": "10.20.30.1", "to_value": "10.20.30.2",
        "ddio_candidate_ip": "192.0.2.77", "ddio_match": "reservation",
    }]
    cleanup(mac)


if __name__ == "__main__":
    test_vendor_model_history_and_learning()
    test_history_enricher_uses_vendor_model_history_without_mac_history()
    test_history_enrichment_settings_control_exact_and_prefix_matching()
    test_save_history_records_enrichment_before_after_even_when_value_is_cleared()
    test_save_history_uses_file_date_for_records_movements_and_vendor_model_history()
    test_enrichment_restores_latest_non_empty_history_fields_and_switch_address()
    test_save_history_learns_switch_address_and_smartroom_room_mapping()
    test_explicit_ddio_switch_change_uses_export_pair_instead_of_stale_database_state()
    print("vendor model history test passed")

from server import db_connection, init_database, process_single_file_analysis
from backend.services.workspace.single_file_service import analyze_single_file, analyze_single_file_table


TEST_SOURCE = "single-backend-test.csv"


def cleanup_backend_rows():
    with db_connection() as conn:
        conn.execute("DELETE FROM snapshots WHERE source = ?", (TEST_SOURCE,))
        conn.execute("DELETE FROM mac_history WHERE source = ?", (TEST_SOURCE,))
        conn.execute("DELETE FROM mac_movements WHERE source = ?", (TEST_SOURCE,))
        conn.execute("DELETE FROM vendor_model_history WHERE source = ?", (TEST_SOURCE,))
        conn.execute("DELETE FROM performance_metrics WHERE details LIKE ?", (f"source={TEST_SOURCE}%",))
        conn.execute("DELETE FROM app_logs WHERE action = ?", ("Single file analysis",))


def test_single_file_analysis_import_detect_and_build_devices():
    content = (
        "MAC Address,Vendor,IP Address,Room\n"
        "AA:BB:CC:00:00:01,Acme,10.0.0.1,101\n"
        "not-a-mac,Broken,10.0.0.2,102\n"
    ).encode("utf-8")

    result = analyze_single_file("single.csv", content)

    assert result["headers"] == ["MAC Address", "Vendor", "IP Address", "Room"]
    assert result["mapping"]["mac"] == 0
    assert result["mapping"]["vendor"] == 1
    assert result["mapping"]["ip"] == 2
    assert result["mapping"]["room"] == 3
    assert result["progress"]["rows"] == 2
    assert result["progress"]["valid"] == 1
    assert result["progress"]["invalid"] == 1
    assert result["devices"][0]["mac"] == "AABBCC000001"
    assert result["devices"][0]["vendor"] == "Acme"
    assert result["devices"][0]["ip"] == "10.0.0.1"
    assert result["summary"]["valid"] == 1
    assert result["summary"]["invalid"] == 1
    assert result["summary"]["detectedColumns"]


def test_single_file_analysis_manual_mapping_override():
    content = (
        "Port,Location,Device ID,Maker\n"
        "Gi1/0/1,305,AA-BB-CC-00-00-03,ManualVendor\n"
    ).encode("utf-8")

    result = analyze_single_file(
        "manual.csv",
        content,
        mapping_override={"switchPort": 0, "room": 1, "mac": 2, "vendor": 3},
    )

    assert result["mappingMode"] == "manual"
    assert result["mapping"]["mac"] == 2
    assert result["devices"][0]["mac"] == "AABBCC000003"
    assert result["devices"][0]["vendor"] == "ManualVendor"
    assert result["devices"][0]["room"] == "305"
    assert result["devices"][0]["switchPort"] == "Gi1/0/1"


def test_single_file_table_analysis_reuses_parsed_import():
    table = {
        "headers": ["MAC Address", "Vendor", "Room"],
        "rows": [["AA:BB:CC:00:00:05", "CachedVendor", "505"]],
        "sheet": "",
    }

    result = analyze_single_file_table("cached.csv", table)

    assert result["summary"]["valid"] == 1
    assert result["devices"][0]["vendor"] == "CachedVendor"
    assert result["devices"][0]["room"] == "505"


def test_single_file_compact_backend_result_keeps_full_snapshot():
    init_database()
    cleanup_backend_rows()
    table = {
        "headers": ["MAC Address", "Vendor", "Room"],
        "rows": [[f"AA:BB:CC:00:{index // 256:02X}:{index % 256:02X}", "CompactVendor", str(index)] for index in range(300)],
        "sheet": "",
    }

    result = process_single_file_analysis(
        TEST_SOURCE,
        None,
        table=table,
        compact_result=True,
        result_page_size=25,
        save_history_enabled=False,
        notify=False,
    )

    assert result["compactResult"] is True
    assert result["rowCount"] == 300
    assert len(result["rows"]) == 100
    assert len(result["devices"]) == 25
    assert result["resultReference"]["deviceCount"] == 300
    assert result["resultReference"]["snapshotId"] == result["snapshot"]["id"]
    cleanup_backend_rows()


def test_single_file_backend_process_saves_snapshot_and_metric():
    init_database()
    cleanup_backend_rows()
    content = (
        "MAC Address,Vendor,Room\n"
        "AA:BB:CC:00:00:04,BackendVendor,404\n"
    ).encode("utf-8")

    result = process_single_file_analysis(
        TEST_SOURCE,
        content,
        save_history_enabled=True,
        save_snapshot_enabled=True,
        notify=False,
    )

    assert result["summary"]["valid"] == 1
    assert "single-metrics" in result["summaryHtml"]
    assert "MAC-адрес" in result["detectedColumnsHtml"]
    assert "<tr>" in result["previewHeadHtml"]
    assert "BackendVendor" in result["previewBodyHtml"]
    assert "строк" in result["previewCountText"]
    assert result["snapshot"]["source"] == TEST_SOURCE
    with db_connection() as conn:
        snapshot_count = conn.execute("SELECT COUNT(*) FROM snapshots WHERE source = ?", (TEST_SOURCE,)).fetchone()[0]
        history_count = conn.execute("SELECT COUNT(*) FROM mac_history WHERE source = ?", (TEST_SOURCE,)).fetchone()[0]
        metric_count = conn.execute(
            "SELECT COUNT(*) FROM performance_metrics WHERE operation = ? AND details LIKE ?",
            ("single_file_analyze", f"source={TEST_SOURCE}%"),
        ).fetchone()[0]
    assert snapshot_count == 1
    assert history_count == 1
    assert metric_count >= 1
    cleanup_backend_rows()


if __name__ == "__main__":
    test_single_file_analysis_import_detect_and_build_devices()
    test_single_file_analysis_manual_mapping_override()
    test_single_file_table_analysis_reuses_parsed_import()
    test_single_file_compact_backend_result_keeps_full_snapshot()
    test_single_file_backend_process_saves_snapshot_and_metric()
    print("single file service test passed")

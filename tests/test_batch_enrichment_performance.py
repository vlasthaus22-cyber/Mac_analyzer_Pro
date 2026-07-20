import time

import server
from backend.services.workspace.enrichment_service import enrich_files


VENDOR_PREFIX = "A9B8C701"
MODEL_PREFIX = "A9B8C70100"


def cleanup():
    with server.db_connection() as connection:
        connection.execute("DELETE FROM vendor_mappings WHERE oui IN (?, ?)", ("A9B8C7", VENDOR_PREFIX))
        connection.execute("DELETE FROM model_mappings WHERE prefix = ?", (MODEL_PREFIX,))
        connection.execute("DELETE FROM mac_history WHERE oui = 'A9B8C7'")
        connection.execute("DELETE FROM vendor_model_history WHERE oui = 'A9B8C7'")


def test_large_batch_uses_one_detection_context_connection_and_auto_detects():
    server.init_database()
    cleanup()
    now = server.utc_now()
    with server.db_connection() as connection:
        connection.execute(
            "INSERT INTO vendor_mappings (oui, vendor, source, updated_at) VALUES (?, ?, 'custom', ?)",
            ("A9B8C7", "Indexed Vendor 3", now),
        )
        connection.execute(
            "INSERT INTO vendor_mappings (oui, vendor, source, updated_at) VALUES (?, ?, 'custom', ?)",
            (VENDOR_PREFIX, "Indexed Vendor 4", now),
        )
        connection.execute(
            "INSERT INTO model_mappings (prefix, model, source, updated_at) VALUES (?, ?, 'custom', ?)",
            (MODEL_PREFIX, "Indexed Model", now),
        )
    devices = [{"mac": VENDOR_PREFIX + f"{index:04X}"} for index in range(0x1000, 0x1000 + 1000)]
    original_connection = server.db_connection
    connection_count = 0

    def counted_connection():
        nonlocal connection_count
        connection_count += 1
        return original_connection()

    try:
        server.db_connection = counted_connection
        started = time.perf_counter()
        context = server.build_enrichment_context(devices)
        enriched = [server.enrich_device(device, context) for device in devices]
        duration = time.perf_counter() - started
    finally:
        server.db_connection = original_connection
        cleanup()

    assert connection_count == 1
    assert duration < 3.0
    assert all(item["vendor"] == "Indexed Vendor 4" for item in enriched)
    assert all(item["model"] == "Indexed Model" for item in enriched)
    assert all(item["vendorMatchedPrefix"] == VENDOR_PREFIX for item in enriched)
    assert all(item["modelSource"] == "prefix_compatible" for item in enriched)


def test_progress_updates_are_throttled_for_large_files():
    rows = [["mac"]] + [[f"AABBCC{index:06X}"] for index in range(5000)]
    updates = []
    result = enrich_files([{"name": "large.csv", "mapping": {"mac": 0}, "rows": rows}], progress_callback=updates.append)

    assert result["progress"]["valid"] == 5000
    assert result["progress"]["percent"] == 100
    assert 50 <= len(updates) <= 110


if __name__ == "__main__":
    test_large_batch_uses_one_detection_context_connection_and_auto_detects()
    test_progress_updates_are_throttled_for_large_files()
    print("batch enrichment performance test passed")

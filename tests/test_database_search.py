from server import database_device_lookup, database_search, db_connection, enrich_device, init_database, save_history, utc_now


MAC = "C0FFEE000001"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM mac_history WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM mac_movements WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM vendor_model_history WHERE mac = ?", (MAC,))
        conn.execute("DELETE FROM ip_address_mappings WHERE switch_ip = ?", ("198.51.100.10",))


def test_database_search_across_sqlite_tables():
    init_database()
    cleanup()

    save_history([
        enrich_device({
            "mac": MAC,
            "vendor": "Search Vendor",
            "model": "Search Model",
            "ip": "198.51.100.20",
            "address": "Search Rack",
        })
    ], "database-search-test")
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO ip_address_mappings (switch_ip, physical_address, source, updated_at) VALUES (?, ?, ?, ?)",
            ("198.51.100.10", "Search Building", "test", utc_now()),
        )

    by_mac = database_search("C0:FF:EE:00:00:01")
    assert by_mac["count"] >= 1
    assert any(item["type"] == "device" and item["mac"] == MAC for item in by_mac["results"])

    by_vendor = database_search("Search Vendor")
    assert any(item["type"] in {"device", "vendorModel"} and item["mac"] == MAC for item in by_vendor["results"])

    by_ip_mapping = database_search("Search Building")
    assert any(item["type"] == "ipMapping" and item["title"] == "198.51.100.10" for item in by_ip_mapping["results"])

    lookup = database_device_lookup("C0:FF:EE:00:00:01")
    assert lookup["mac"] == MAC
    assert lookup["vendor"] == "Search Vendor"
    assert lookup["model"] == "Search Model"
    assert lookup["ip"] == "198.51.100.20"
    assert lookup["address"] == "Search Rack"
    assert lookup["database"]["historyRecords"] >= 1
    assert lookup["lookupSource"] == "mac_history"

    cleanup()


if __name__ == "__main__":
    test_database_search_across_sqlite_tables()
    print("database search test passed")

from server import database_device_or_lookup, db_connection, enrich_device, init_database, save_history


KNOWN_MAC = "AABBCC000077"
UNKNOWN_MAC = "AABBCC000078"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM mac_history WHERE mac IN (?, ?)", (KNOWN_MAC, UNKNOWN_MAC))
        conn.execute("DELETE FROM mac_movements WHERE mac IN (?, ?)", (KNOWN_MAC, UNKNOWN_MAC))
        conn.execute("DELETE FROM vendor_model_history WHERE mac IN (?, ?)", (KNOWN_MAC, UNKNOWN_MAC))


def test_database_device_lookup_falls_back_to_enriched_device():
    init_database()
    cleanup()

    save_history([{**enrich_device({"mac": KNOWN_MAC}), "vendor": "KnownVendor", "model": "KnownModel"}], "database-device-test")
    known = database_device_or_lookup(KNOWN_MAC)
    assert known["found"] is True
    assert known["device"]["vendor"] == "KnownVendor"
    assert known["device"]["database"]["found"] is True

    fallback = database_device_or_lookup(UNKNOWN_MAC)
    assert fallback["found"] is False
    assert fallback["device"]["mac"] == UNKNOWN_MAC
    assert fallback["device"]["database"]["historyRecords"] == 0
    assert fallback["source"]

    cleanup()


if __name__ == "__main__":
    test_database_device_lookup_falls_back_to_enriched_device()
    print("database device lookup test passed")

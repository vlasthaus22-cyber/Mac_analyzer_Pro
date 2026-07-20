from server import db_connection, delete_history_records, enrich_device, init_database, save_history


def count_rows(table, mac):
    with db_connection() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE mac = ?", (mac,)).fetchone()[0]


def cleanup(*macs):
    with db_connection() as conn:
        for mac in macs:
            conn.execute("DELETE FROM mac_movements WHERE mac = ?", (mac,))
            conn.execute("DELETE FROM mac_history WHERE mac = ?", (mac,))


def test_delete_one_mac_keeps_other_history():
    init_database()
    mac_delete = "AABBCCDD1001"
    mac_keep = "AABBCCDD1002"
    cleanup(mac_delete, mac_keep)

    first_batch = [
        enrich_device({"mac": mac_delete, "vendor": "Vendor A", "model": "Model 1", "ip": "10.0.0.1"}),
        enrich_device({"mac": mac_keep, "vendor": "Vendor B", "model": "Model 2", "ip": "10.0.0.2"}),
    ]
    save_history(first_batch, "history-delete-test-1")
    second_batch = [
        enrich_device({"mac": mac_delete, "vendor": "Vendor A", "model": "Model 1", "ip": "10.0.0.11"}),
        enrich_device({"mac": mac_keep, "vendor": "Vendor B", "model": "Model 2", "ip": "10.0.0.22"}),
    ]
    save_history(second_batch, "history-delete-test-2")

    assert count_rows("mac_history", mac_delete) == 2
    assert count_rows("mac_movements", mac_delete) >= 1
    assert count_rows("mac_history", mac_keep) == 2

    deleted = delete_history_records(mac_delete)

    assert deleted >= 3
    assert count_rows("mac_history", mac_delete) == 0
    assert count_rows("mac_movements", mac_delete) == 0
    assert count_rows("mac_history", mac_keep) == 2
    assert count_rows("mac_movements", mac_keep) >= 1

    cleanup(mac_delete, mac_keep)


if __name__ == "__main__":
    test_delete_one_mac_keeps_other_history()
    print("history delete test passed")

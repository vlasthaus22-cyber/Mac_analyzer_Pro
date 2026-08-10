import tempfile
from pathlib import Path

import server


def test_device_inventory_preserves_known_fields_and_exports_every_mac():
    original = server.DATABASE_PATH
    try:
        with tempfile.TemporaryDirectory() as directory:
            server.DATABASE_PATH = Path(directory) / "inventory.db"
            server.init_database()
            server.save_history([{
                "mac": "AABBCC000001", "vendor": "Vendor One", "model": "Model One",
                "address": "Building A", "switchIp": "10.0.0.1",
            }], "first.csv", "2026-08-01T10:00:00Z")
            server.save_history([{
                "mac": "AABBCC000001", "ip": "192.0.2.10", "switchIp": "10.0.0.2",
            }, {
                "mac": "AABBCC000002", "vendor": "Vendor Two",
            }], "second.csv", "2026-08-02T10:00:00Z")

            page = server.all_devices_page(0, 1)
            assert page["total"] == 2
            assert page["nextOffset"] == 1
            first = page["items"][0]
            assert first["vendor"] == "Vendor One"
            assert first["model"] == "Model One"
            assert first["address"] == "Building A"
            assert first["ip"] == "192.0.2.10"
            assert first["switchIp"] == "10.0.0.2"
            assert first["seenCount"] == 2

            second_page = server.all_devices_page(page["nextOffset"], 10)
            assert len(second_page["items"]) == 1
            assert second_page["nextOffset"] is None
    finally:
        server.DATABASE_PATH = original


if __name__ == "__main__":
    test_device_inventory_preserves_known_fields_and_exports_every_mac()
    print("device inventory tests passed")

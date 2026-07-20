from server import db_connection, enrich_device, init_database, utc_now


init_database()
with db_connection() as conn:
    conn.execute(
        "INSERT OR REPLACE INTO ip_address_mappings (switch_ip, physical_address, source, updated_at) VALUES (?, ?, ?, ?)",
        ("10.10.10.1", "Server room", "test", utc_now()),
    )
device = enrich_device({"mac": "B827EB000001", "switchIp": "10.10.10.1"})
assert device["address"] == "Server room"
print("ip mapper test passed")

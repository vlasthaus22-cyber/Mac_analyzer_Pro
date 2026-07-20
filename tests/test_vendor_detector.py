from server import BUILTIN_MODELS, BUILTIN_VENDORS, db_connection, enrich_device, init_database, utc_now


init_database()
assert len(BUILTIN_VENDORS) == 32
assert len(BUILTIN_MODELS) == 61
assert BUILTIN_VENDORS["001E58"] == "Sony Corporation"
assert BUILTIN_VENDORS["001E13"] == "Nintendo"
assert BUILTIN_MODELS["0010B5FF"] == "Dell XPS 15"
assert BUILTIN_MODELS["00231420"] == "Lenovo Yoga 9i"
device = enrich_device({"mac": "00:11:22:33:44:55"})
assert device["vendor"] == "Cisco Systems"
assert device["model"] == "Cisco Catalyst 2960"
assert device["vendorSource"] in {"oui", "history"}
assert device["modelSource"] in {"prefix", "history"}

with db_connection() as conn:
    conn.execute("DELETE FROM vendor_mappings WHERE oui IN ('001122AABB', 'F1F2F3')")
    conn.execute("DELETE FROM model_mappings WHERE prefix = 'AABBCC1200'")
    conn.execute("DELETE FROM mac_history WHERE mac LIKE 'F1F2F31122%'")
    conn.execute("DELETE FROM vendor_model_history WHERE mac LIKE 'F1F2F31122%'")
    conn.execute(
        "INSERT INTO vendor_mappings (oui, vendor, source, updated_at) VALUES (?, ?, 'custom', ?)",
        ("001122AABB", "Cisco Specific MAC5", utc_now()),
    )
    conn.execute(
        """
        INSERT INTO mac_history
        (mac, mac_formatted, oui, vendor, model, ip, address, room, switch_ip, switch_port, source, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("F1F2F3112244", "F1:F2:F3:11:22:44", "F1F2F3", "Similar History Vendor", "", "", "", "", "", "", "test", utc_now()),
    )
    conn.execute(
        "INSERT INTO model_mappings (prefix, model, source, updated_at) VALUES (?, ?, 'custom', ?)",
        ("AABBCC1200", "Compatible MAC5 Model", utc_now()),
    )

mac5_device = enrich_device({"mac": "00:11:22:AA:BB:CC"})
similar_device = enrich_device({"mac": "F1:F2:F3:11:22:55"})
text_vendor_device = enrich_device({"mac": "12:34:56:78:90:AB", "model": "Cisco Catalyst 9300 switch"})
compatible_model_device = enrich_device({"mac": "AA:BB:CC:12:34:01"})

assert mac5_device["vendor"] == "Cisco Specific MAC5"
assert mac5_device["vendorSource"] == "mac5"
assert mac5_device["vendorMatchedPrefix"] == "001122AABB"
assert mac5_device["vendorConfidence"] > 0.9
assert similar_device["vendor"] == "Similar History Vendor"
assert similar_device["vendorSource"] == "similar"
assert similar_device["vendorMatchedPrefix"] == "F1F2F31122"
assert text_vendor_device["vendor"] == "Cisco"
assert text_vendor_device["vendorSource"] == "text"
assert compatible_model_device["model"] == "Compatible MAC5 Model"
assert compatible_model_device["modelSource"] == "prefix_compatible"
assert compatible_model_device["modelMatchedPrefix"] == "AABBCC1200"

with db_connection() as conn:
    conn.execute("DELETE FROM vendor_mappings WHERE oui = '001122AABB'")
    conn.execute("DELETE FROM model_mappings WHERE prefix = 'AABBCC1200'")
    conn.execute("DELETE FROM mac_history WHERE mac LIKE 'F1F2F31122%'")
    conn.execute("DELETE FROM vendor_model_history WHERE mac LIKE 'F1F2F31122%'")

print("vendor detector test passed")

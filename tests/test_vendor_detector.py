import gzip
import json
from pathlib import Path

from server import db_connection, enrich_device, init_database, utc_now


init_database()
with gzip.open(Path(__file__).resolve().parents[1] / "data" / "reference" / "ieee_registry.json.gz", "rt", encoding="utf-8") as source:
    ieee = json.load(source)
official_prefix = ieee["assignments"]["6"][0]
official_vendor = ieee["vendors"][ieee["assignments"]["6"][1]]
device = enrich_device({"mac": official_prefix + "123456"})
assert device["vendor"] == official_vendor
assert device["vendorSource"] == "oui"
assert device["vendorMatchedPrefix"] == official_prefix

with db_connection() as conn:
    conn.execute("DELETE FROM vendor_mappings WHERE oui IN ('001122AABB', 'F1F2F3')")
    conn.execute("DELETE FROM model_mappings WHERE prefix = 'DEADC01200'")
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
        ("DEADC01200", "Compatible MAC5 Model", utc_now()),
    )

mac5_device = enrich_device({"mac": "00:11:22:AA:BB:CC"})
similar_device = enrich_device({"mac": "F1:F2:F3:11:22:55"})
text_vendor_device = enrich_device({"mac": "12:34:56:78:90:AB", "model": "Cisco Catalyst 9300 switch"})
compatible_model_device = enrich_device({"mac": "DE:AD:C0:12:34:01"})

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
assert compatible_model_device["modelMatchedPrefix"] == "DEADC01200"

with db_connection() as conn:
    conn.execute("DELETE FROM vendor_mappings WHERE oui = '001122AABB'")
    conn.execute("DELETE FROM model_mappings WHERE prefix = 'DEADC01200'")
    conn.execute("DELETE FROM mac_history WHERE mac LIKE 'F1F2F31122%'")
    conn.execute("DELETE FROM vendor_model_history WHERE mac LIKE 'F1F2F31122%'")

print("vendor detector test passed")

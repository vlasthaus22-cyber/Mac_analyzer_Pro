from server import enrich_device, init_database, save_history


init_database()
save_history([enrich_device({"mac": "ACDE48000001", "ip": "10.1.1.10", "room": "A-101"})], "history-test")
device = enrich_device({"mac": "ACDE48000001"})
assert device["ip"] == "10.1.1.10"
assert device["room"] == "A-101"
print("history enricher test passed")

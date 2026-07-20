from external_api_service import test_mac_vendor_api
from server import api_cache_get, api_cache_set, api_cache_summary, clear_api_cache, db_connection, init_database, utc_now


init_database()
clear_api_cache("external_vendor:test:")


def test_api_cache_storage_summary_and_clear():
    api_cache_set("external_vendor:test:001122334455", "Cisco Systems")
    row = api_cache_get("external_vendor:test:001122334455")
    assert row["value"] == "Cisco Systems"
    summary = api_cache_summary()
    assert summary["total"] >= 1
    assert any(item["cache_key"] == "external_vendor:test:001122334455" for item in summary["items"])
    assert clear_api_cache("external_vendor:test:") >= 1
    assert api_cache_get("external_vendor:test:001122334455") is None


def test_mac_vendor_api_uses_cache_and_live_lookup():
    cache = {"external_vendor:macvendors:AABBCC000001": {"value": "Cached Vendor", "cached_at": "2999-01-01T00:00:00Z"}}
    looked_up = []

    def cache_get(key):
        return cache.get(key)

    def cache_set(key, value):
        cache[key] = {"value": value, "cached_at": "2999-01-01T00:00:00Z"}

    def lookup(mac, _settings):
        looked_up.append(mac)
        return "Live Vendor"

    cached = test_mac_vendor_api("AA:BB:CC:00:00:01", {"enabled": True, "provider": "macvendors"}, cache_get, cache_set, lookup)
    live = test_mac_vendor_api("AA:BB:CC:00:00:02", {"enabled": True, "provider": "macvendors"}, cache_get, cache_set, lookup)
    disabled = test_mac_vendor_api("AA:BB:CC:00:00:03", {"enabled": False, "provider": "macvendors"}, cache_get, cache_set, lookup)

    assert cached["source"] == "cache"
    assert cached["vendor"] == "Cached Vendor"
    assert live["source"] == "api"
    assert live["vendor"] == "Live Vendor"
    assert disabled["ok"] is False
    assert looked_up == ["AABBCC000002"]


test_api_cache_storage_summary_and_clear()
test_mac_vendor_api_uses_cache_and_live_lookup()
print("api cache test passed")

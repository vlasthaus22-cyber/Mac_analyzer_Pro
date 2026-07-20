from external_api_service import external_api_provider_options, external_enrich_devices, normalize_external_api_settings


DEVICES = [
    {"mac": "AABBCC000001", "macFormatted": "AA:BB:CC:00:00:01", "vendor": "Unknown"},
    {"mac": "AABBCC000002", "macFormatted": "AA:BB:CC:00:00:02", "vendor": "Known"},
    {"mac": "AABBCC000003", "macFormatted": "AA:BB:CC:00:00:03", "vendor": "Unknown"},
]


def test_external_enrichment_settings_cache_selection_and_rate_limit():
    providers = external_api_provider_options(False)
    assert [item["key"] for item in providers] == ["macvendors", "maclookup", "mac2vendor"]
    assert providers[2]["url"] == "https://mac2vendor.com/api/v1/lookup/{mac}"
    assert providers[2]["description"] == "mac2vendor.com"
    assert normalize_external_api_settings({"provider": "mac2vendor"})["provider"] == "mac2vendor"
    settings = normalize_external_api_settings({"enabled": True, "provider": "macvendors", "rateLimit": 1, "cacheTtlDays": 30})
    cache = {
        "external_vendor:macvendors:AABBCC000003": {"value": "Cached Vendor", "cached_at": "2999-01-01T00:00:00Z"}
    }
    looked_up = []

    def cache_get(key):
        return cache.get(key)

    def cache_set(key, value):
        cache[key] = {"value": value, "cached_at": "2999-01-01T00:00:00Z"}

    def lookup(mac, _settings):
        looked_up.append(mac)
        return "Live Vendor " + mac[-2:]

    result = external_enrich_devices(DEVICES, settings, cache_get, cache_set, lookup, selected_macs=["AABBCC000001", "AABBCC000003"])

    by_mac = {device["mac"]: device for device in result["devices"]}
    assert by_mac["AABBCC000001"]["vendor"] == "Live Vendor 01"
    assert by_mac["AABBCC000003"]["vendor"] == "Cached Vendor"
    assert by_mac["AABBCC000002"]["vendor"] == "Known"
    assert looked_up == ["AABBCC000001"]
    assert result["summary"]["candidates"] == 2
    assert result["summary"]["lookups"] == 1
    assert result["summary"]["cached"] == 1
    assert result["summary"]["updated"] == 2


def test_external_enrichment_selects_unknown_devices_when_macs_are_not_provided():
    settings = normalize_external_api_settings({"enabled": True, "provider": "macvendors", "rateLimit": 10})
    looked_up = []

    def lookup(mac, _settings):
        looked_up.append(mac)
        return "Resolved " + mac[-2:]

    result = external_enrich_devices(DEVICES, settings, lambda _key: None, lambda _key, _value: None, lookup)

    by_mac = {device["mac"]: device for device in result["devices"]}
    assert by_mac["AABBCC000001"]["vendor"] == "Resolved 01"
    assert by_mac["AABBCC000002"]["vendor"] == "Known"
    assert by_mac["AABBCC000003"]["vendor"] == "Resolved 03"
    assert looked_up == ["AABBCC000001", "AABBCC000003"]
    assert result["summary"]["candidates"] == 2
    assert result["summary"]["updated"] == 2


if __name__ == "__main__":
    test_external_enrichment_settings_cache_selection_and_rate_limit()
    test_external_enrichment_selects_unknown_devices_when_macs_are_not_provided()
    print("external api service test passed")

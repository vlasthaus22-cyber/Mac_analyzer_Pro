from datetime import datetime, timedelta
from typing import Any, Callable


API_PROVIDER_OPTIONS = [
    {"key": "macvendors", "description": "macvendors.com", "url": "https://api.macvendors.com/{mac}", "requiresKey": False},
    {"key": "maclookup", "description": "maclookup.app", "url": "https://api.maclookup.app/v2/macs/{mac}/", "requiresKey": False},
    {"key": "mac2vendor", "description": "mac2vendor.com", "url": "https://mac2vendor.com/api/v1/lookup/{mac}", "requiresKey": False},
]
SUPPORTED_PROVIDERS = {item["key"] for item in API_PROVIDER_OPTIONS} | {"custom"}


def external_api_provider_options(include_custom: bool = True) -> list[dict[str, Any]]:
    options = [dict(item) for item in API_PROVIDER_OPTIONS]
    if include_custom:
        options.append({"key": "custom", "description": "Пользовательский endpoint", "url": "", "requiresKey": False})
    return options


def normalize_mac(value: Any) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch in "0123456789ABCDEF")


def format_mac(mac: str) -> str:
    clean = normalize_mac(mac)
    if len(clean) == 12:
        return ":".join(clean[index:index + 2] for index in range(0, 12, 2))
    return clean


def normalize_external_api_settings(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = settings or {}
    provider = str(settings.get("provider") or "macvendors").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        provider = "macvendors"
    try:
        rate_limit = int(settings.get("rateLimit") or 25)
    except (TypeError, ValueError):
        rate_limit = 25
    try:
        cache_ttl_days = int(settings.get("cacheTtlDays") or 30)
    except (TypeError, ValueError):
        cache_ttl_days = 30
    return {
        "enabled": bool(settings.get("enabled", False)),
        "provider": provider,
        "endpoint": str(settings.get("endpoint") or "").strip(),
        "apiKey": str(settings.get("apiKey") or "").strip(),
        "rateLimit": max(1, min(rate_limit, 500)),
        "cacheTtlDays": max(1, min(cache_ttl_days, 365)),
        "onlyUnknown": bool(settings.get("onlyUnknown", True)),
    }


def cache_key(provider: str, mac: str) -> str:
    return f"external_vendor:{provider}:{normalize_mac(mac)}"


def cached_value_is_fresh(cached_at: str, ttl_days: int) -> bool:
    try:
        cached_dt = datetime.fromisoformat(str(cached_at).replace("Z", ""))
    except ValueError:
        return False
    return cached_dt > datetime.utcnow() - timedelta(days=ttl_days)


CacheGet = Callable[[str], dict[str, str] | None]
CacheSet = Callable[[str, str], None]
LookupClient = Callable[[str, dict[str, Any]], str | None]


def external_enrich_devices(
    devices: list[dict[str, Any]],
    settings: dict[str, Any],
    cache_get: CacheGet,
    cache_set: CacheSet,
    lookup_client: LookupClient,
    selected_macs: list[str] | None = None,
) -> dict[str, Any]:
    normalized_settings = normalize_external_api_settings(settings)
    selected = {normalize_mac(mac) for mac in (selected_macs or []) if normalize_mac(mac)}
    enriched_devices = [dict(device) for device in devices if isinstance(device, dict)]
    summary = {
        "candidates": 0,
        "lookups": 0,
        "cached": 0,
        "updated": 0,
        "skipped": 0,
        "provider": normalized_settings["provider"],
        "enabled": normalized_settings["enabled"],
    }

    for device in enriched_devices:
        mac = normalize_mac(device.get("mac") or device.get("macFormatted"))
        if not mac:
            summary["skipped"] += 1
            continue
        if selected and mac not in selected:
            continue
        if normalized_settings["onlyUnknown"] and str(device.get("vendor") or "").strip() not in {"", "Unknown", "Не определено"}:
            continue
        summary["candidates"] += 1
        key = cache_key(normalized_settings["provider"], mac)
        cached = cache_get(key)
        vendor = None
        if cached and cached_value_is_fresh(cached.get("cached_at", ""), normalized_settings["cacheTtlDays"]):
            vendor = cached.get("value")
            summary["cached"] += 1
        elif normalized_settings["enabled"] and summary["lookups"] < normalized_settings["rateLimit"]:
            vendor = lookup_client(mac, normalized_settings)
            summary["lookups"] += 1
            if vendor:
                cache_set(key, vendor)
        else:
            summary["skipped"] += 1

        if vendor:
            device["vendor"] = vendor
            device["vendorSource"] = "external_cache" if cached and vendor == cached.get("value") else "external_api"
            device["vendorConfidence"] = 0.95
            device["macFormatted"] = device.get("macFormatted") or format_mac(mac)
            summary["updated"] += 1

    return {"devices": enriched_devices, "summary": summary, "settings": normalized_settings}


def test_mac_vendor_api(
    mac: str,
    settings: dict[str, Any],
    cache_get: CacheGet,
    cache_set: CacheSet,
    lookup_client: LookupClient,
    force_live: bool = False,
) -> dict[str, Any]:
    normalized_settings = normalize_external_api_settings(settings)
    normalized_mac = normalize_mac(mac)
    if len(normalized_mac) != 12:
        return {
            "ok": False,
            "provider": normalized_settings["provider"],
            "mac": normalized_mac,
            "error": "MAC address must contain 12 hex characters",
            "cached": False,
            "lookups": 0,
        }
    key = cache_key(normalized_settings["provider"], normalized_mac)
    cached = cache_get(key)
    if cached and not force_live and cached_value_is_fresh(cached.get("cached_at", ""), normalized_settings["cacheTtlDays"]):
        return {
            "ok": True,
            "provider": normalized_settings["provider"],
            "mac": normalized_mac,
            "macFormatted": format_mac(normalized_mac),
            "vendor": cached.get("value", ""),
            "source": "cache",
            "cacheKey": key,
            "cached": True,
            "lookups": 0,
        }
    if not normalized_settings["enabled"]:
        return {
            "ok": False,
            "provider": normalized_settings["provider"],
            "mac": normalized_mac,
            "macFormatted": format_mac(normalized_mac),
            "error": "External API is disabled",
            "cacheKey": key,
            "cached": False,
            "lookups": 0,
        }
    vendor = lookup_client(normalized_mac, normalized_settings)
    if vendor:
        cache_set(key, vendor)
        return {
            "ok": True,
            "provider": normalized_settings["provider"],
            "mac": normalized_mac,
            "macFormatted": format_mac(normalized_mac),
            "vendor": vendor,
            "source": "api",
            "cacheKey": key,
            "cached": False,
            "lookups": 1,
        }
    return {
        "ok": False,
        "provider": normalized_settings["provider"],
        "mac": normalized_mac,
        "macFormatted": format_mac(normalized_mac),
        "error": "Provider returned no vendor",
        "cacheKey": key,
        "cached": False,
        "lookups": 1,
    }

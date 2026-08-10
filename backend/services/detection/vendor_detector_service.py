import re
from collections import Counter
from typing import Any

from .detection_index_service import indexed_compatible_model, indexed_prefix_rule


UNKNOWN_VENDOR_VALUES = {"", "unknown", "not found", "n/a", "не определено", "неизвестно"}
VENDOR_KEYWORDS = {
    "Apple": ["apple", "iphone", "ipad", "macbook", "imac", "mac", "ios", "ipod", "airport"],
    "Samsung": ["samsung", "galaxy", "note", "s series", "gear", "odyssey", "ssd"],
    "Huawei": ["huawei", "honor", "mate", "p series", "mediapad", "ascend"],
    "Xiaomi": ["xiaomi", "mi ", "redmi", "poco", "black shark", "mijia"],
    "Lenovo": ["lenovo", "thinkpad", "ideapad", "yoga", "legion", "thinkcentre"],
    "Dell": ["dell", "xps", "latitude", "inspiron", "precision", "alienware", "poweredge"],
    "HP": ["hp", "hewlett packard", "elitebook", "probook", "spectre", "envy", "pavilion", "laserjet"],
    "Acer": ["acer", "aspire", "predator", "nitro", "swift", "travelmate"],
    "ASUS": ["asus", "rog", "zenbook", "vivobook", "tuf", "prime", "expertbook"],
    "Microsoft": ["microsoft", "surface", "xbox", "hololens", "windows", "lumia"],
    "Cisco": ["cisco", "catalyst", "meraki", "asa", "nexus", "router", "switch", "firepower"],
    "Juniper": ["juniper", "mx", "ex", "srx", "qfx", "netscreen"],
    "TP-Link": ["tp-link", "tplink", "archer", "deco", "kasa", "tapo"],
    "Netgear": ["netgear", "orbi", "nighthawk", "prosafe", "insight"],
    "Intel": ["intel", "core i", "xeon", "pentium", "celeron", "ethernet"],
    "AMD": ["amd", "ryzen", "threadripper", "epyc", "radeon", "athlon"],
    "NVIDIA": ["nvidia", "geforce", "quadro", "tesla", "rtx", "gtx"],
    "Raspberry Pi": ["raspberry", "rpi", "pi 3", "pi 4", "pi 5", "pico"],
    "Arduino": ["arduino", "uno", "mega", "nano", "esp"],
    "ESP32": ["esp32", "esp8266", "espressif"],
}


def normalize_mac(value: Any) -> str:
    return re.sub(r"[^0-9A-Fa-f]", "", str(value or "")).upper()


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _known_vendor(value: Any) -> bool:
    return _text(value).lower() not in UNKNOWN_VENDOR_VALUES


def _source_for_vendor_rule(prefix: str, rule_source: str) -> str:
    source = _text(rule_source).lower()
    if len(prefix) >= 10:
        return "mac5"
    if source in {"custom", "learned"}:
        return source
    return "oui"


def normalize_detector_settings(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = settings if isinstance(settings, dict) else {}
    return {
        "enabled": bool(raw.get("enabled", True)),
        "useOui3": bool(raw.get("useOui3", raw.get("use_oui_3byte", True))),
        "useMac5": bool(raw.get("useMac5", raw.get("use_oui_5byte", True))),
        "useText": bool(raw.get("useText", raw.get("use_text_analysis", True))),
        "useInference": bool(raw.get("useInference", raw.get("use_inference", True))),
        "confidenceThreshold": max(0.0, min(float(raw.get("confidenceThreshold", raw.get("confidence_threshold", 0.6)) or 0.6), 1.0)),
    }


def detector_rule_allowed(prefix: str, settings: dict[str, Any]) -> bool:
    length = len(normalize_mac(prefix))
    if length <= 6:
        return bool(settings.get("useOui3", True))
    return bool(settings.get("useMac5", True))


def longest_prefix_rule(mac: str, rules: list[dict[str, Any]], key: str, value_key: str) -> dict[str, Any] | None:
    normalized = normalize_mac(mac)
    candidates = []
    for rule in rules:
        prefix = normalize_mac(rule.get(key))
        value = _text(rule.get(value_key))
        if prefix and value and normalized.startswith(prefix):
            candidates.append({**rule, key: prefix, value_key: value})
    if not candidates:
        return None
    return max(candidates, key=lambda item: (len(normalize_mac(item.get(key))), _text(item.get("source")) == "custom"))


def infer_similar_vendor(mac: str, observations: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = normalize_mac(mac)
    for prefix_length, confidence in ((10, 0.78), (8, 0.7), (6, 0.62)):
        prefix = normalized[:prefix_length]
        if len(prefix) < prefix_length:
            continue
        vendors = [
            _text(item.get("vendor"))
            for item in observations
            if normalize_mac(item.get("mac")).startswith(prefix) and _known_vendor(item.get("vendor"))
        ]
        if vendors:
            vendor, count = Counter(vendors).most_common(1)[0]
            return {
                "value": vendor,
                "source": "similar",
                "confidence": confidence,
                "matchedPrefix": prefix,
                "matches": count,
            }
    return None


def detect_vendor_from_text(text_values: list[Any] | tuple[Any, ...]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for raw_text in text_values or []:
        text = _text(raw_text)
        if not text:
            continue
        text_lower = text.lower()
        for vendor, keywords in VENDOR_KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if not matches:
                continue
            confidence = min((matches / max(1, len(keywords))) * 2, 1.0) * 0.8
            if not best or confidence > best["confidence"]:
                best = {
                    "value": vendor,
                    "source": "text",
                    "confidence": confidence,
                    "matchedPrefix": "",
                    "matchedText": text[:80],
                }
    return best


def compatible_mac5_model(mac: str, model_rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = normalize_mac(mac)
    prefix8 = normalized[:8]
    if len(prefix8) < 8:
        return None
    candidates = []
    for rule in model_rules:
        prefix = normalize_mac(rule.get("prefix"))
        model = _text(rule.get("model"))
        if len(prefix) >= 10 and model and prefix.startswith(prefix8):
            candidates.append({**rule, "prefix": prefix, "model": model})
    if not candidates:
        return None
    return max(candidates, key=lambda item: (len(normalize_mac(item.get("prefix"))), _text(item.get("source")) == "custom"))


def detect_vendor(
    mac: str,
    explicit_vendor: Any,
    history_vendor: Any,
    vendor_rules: list[dict[str, Any]],
    similar_observations: list[dict[str, Any]] | None = None,
    text_values: list[Any] | tuple[Any, ...] | None = None,
    settings: dict[str, Any] | None = None,
    rule_index: dict[str, Any] | None = None,
    similar_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_settings = normalize_detector_settings(settings)
    normalized = normalize_mac(mac)
    if _known_vendor(explicit_vendor):
        return {"value": _text(explicit_vendor), "source": "file", "confidence": 1.0, "matchedPrefix": ""}
    if _known_vendor(history_vendor):
        return {"value": _text(history_vendor), "source": "history", "confidence": 0.96, "matchedPrefix": normalized}
    if not normalized_settings["enabled"]:
        return {"value": "Unknown", "source": "disabled", "confidence": 0.0, "matchedPrefix": ""}
    threshold = normalized_settings["confidenceThreshold"]
    allowed_vendor_rules = [rule for rule in vendor_rules if detector_rule_allowed(rule.get("oui"), normalized_settings)]
    rule = indexed_prefix_rule(normalized, rule_index) if rule_index else longest_prefix_rule(normalized, allowed_vendor_rules, "oui", "vendor")
    if rule and not detector_rule_allowed(rule.get("oui"), normalized_settings):
        rule = longest_prefix_rule(normalized, allowed_vendor_rules, "oui", "vendor")
    if rule:
        prefix = normalize_mac(rule.get("oui"))
        source = _source_for_vendor_rule(prefix, _text(rule.get("source")))
        confidence = 0.97 if len(prefix) >= 10 else (0.94 if source == "custom" else 0.9)
        if confidence >= threshold:
            return {"value": rule["vendor"], "source": source, "confidence": confidence, "matchedPrefix": prefix}
    text_vendor = detect_vendor_from_text(text_values or []) if normalized_settings["useText"] else None
    if text_vendor and text_vendor["confidence"] >= threshold:
        return text_vendor
    similar = (similar_result or infer_similar_vendor(normalized, similar_observations or [])) if normalized_settings["useInference"] else None
    if similar and similar["confidence"] >= threshold:
        return similar
    return {"value": "Unknown", "source": "unknown", "confidence": 0.0, "matchedPrefix": ""}


def detect_model(mac: str, explicit_model: Any, history_model: Any, model_rules: list[dict[str, Any]], settings: dict[str, Any] | None = None, rule_index: dict[str, Any] | None = None, similar_result: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized_settings = normalize_detector_settings(settings)
    normalized = normalize_mac(mac)
    if _text(explicit_model):
        return {"value": _text(explicit_model), "source": "file", "confidence": 1.0, "matchedPrefix": ""}
    if _text(history_model):
        return {"value": _text(history_model), "source": "history", "confidence": 0.96, "matchedPrefix": normalized}
    threshold = normalized_settings["confidenceThreshold"]
    if normalized_settings["enabled"] and normalized_settings["useMac5"]:
        rule = indexed_prefix_rule(normalized, rule_index) if rule_index else longest_prefix_rule(normalized, model_rules, "prefix", "model")
        if rule:
            prefix = normalize_mac(rule.get("prefix"))
            confidence = 0.93
            if confidence >= threshold:
                return {"value": rule["model"], "source": "prefix", "confidence": confidence, "matchedPrefix": prefix}
        compatible_rule = indexed_compatible_model(normalized, rule_index) if rule_index else compatible_mac5_model(normalized, model_rules)
        if compatible_rule:
            prefix = normalize_mac(compatible_rule.get("prefix"))
            confidence = 0.75
            if confidence >= threshold:
                return {"value": compatible_rule["model"], "source": "prefix_compatible", "confidence": confidence, "matchedPrefix": prefix}
    if normalized_settings["enabled"] and normalized_settings["useInference"] and similar_result and _text(similar_result.get("model")):
        confidence = float(similar_result.get("confidence") or 0.0) * 0.9
        if confidence >= threshold:
            return {"value": _text(similar_result.get("model")), "source": "similar", "confidence": confidence, "matchedPrefix": _text(similar_result.get("matchedPrefix"))}
    if not normalized_settings["enabled"]:
        return {"value": "", "source": "disabled", "confidence": 0.0, "matchedPrefix": ""}
    return {"value": "", "source": "unknown", "confidence": 0.0, "matchedPrefix": ""}

import ipaddress
import re
from collections import defaultdict


FIELD_PATTERNS = {
    "mac": r"mac|mac.?address|hardware|ethernet|device.?id|client.?id|mac.?Р°РґСЂРµСЃ",
    "vendor": r"vendor|manufacturer|brand|maker|producer|РїСЂРѕРёР·РІРѕРґРёС‚РµР»СЊ",
    "model": r"model|device|type|equipment|platform|РјРѕРґРµР»СЊ|СѓСЃС‚СЂРѕР№СЃС‚РІРѕ",
    "switchIp": r"switch.*ip|ip.*switch|switch|gateway|node.?ip|РєРѕРјРјСѓС‚Р°С‚РѕСЂ",
    "ip": r"^ip$|ip.?address|host.?ip|client.?ip|endpoint|address.?ip|ip.?Р°РґСЂРµСЃ",
    "address": r"address|location|place|site|building|rack|street|Р°РґСЂРµСЃ|Р»РѕРєР°С†РёСЏ",
    "room": r"room|office|cabinet|floor|auditorium|РїРѕРјРµС‰|РєР°Р±РёРЅРµС‚",
    "smartroomId": r"smart.?room.*id|id.*smart.?room|smartroom",
    "switchPort": r"switch.*port|port|interface|iface|ifname|if.?name|РїРѕСЂС‚",
}

FIELD_ORDER = ["mac", "vendor", "model", "switchIp", "ip", "address", "room", "smartroomId", "switchPort"]

FIELD_LABELS = {
    "mac": "MAC address",
    "vendor": "vendor",
    "model": "model",
    "switchIp": "switch IP",
    "ip": "host IP",
    "address": "address",
    "room": "room",
    "smartroomId": "Smartroom ID",
    "switchPort": "switch port",
}

FIELD_KEYWORDS = {
    "mac": {"mac", "hardware", "ethernet", "device", "client", "id"},
    "vendor": {"vendor", "manufacturer", "brand", "maker", "producer"},
    "model": {"model", "device", "type", "equipment", "platform", "series"},
    "switchIp": {"switch", "gateway", "node", "router", "uplink"},
    "ip": {"ip", "host", "client", "endpoint", "address"},
    "address": {"address", "location", "place", "site", "building", "rack", "street"},
    "room": {"room", "office", "cabinet", "floor", "auditorium"},
    "smartroomId": {"smartroom", "smart", "room", "id"},
    "switchPort": {"port", "interface", "iface", "ifname", "if"},
}

NEGATIVE_KEYWORDS = {
    "ip": {"switch", "gateway", "router"},
    "switchIp": {"host", "client", "endpoint", "address"},
    "address": {"ip", "mac"},
    "room": {"ip", "mac", "port"},
    "smartroomId": {"ip", "mac", "port"},
    "model": {"ip", "mac", "port"},
}


def _normalize_headers(headers):
    normalized = []
    for index, header in enumerate(headers):
        if isinstance(header, dict):
            normalized.append(str(header.get("name", header.get("title", index))))
        else:
            normalized.append(str(header))
    return normalized


def _sample_values(rows, index, limit=80):
    values = []
    for row in rows[:limit]:
        if isinstance(row, dict):
            value = row.get(index)
        elif index < len(row):
            value = row[index]
        else:
            continue
        if value is not None and str(value).strip():
            values.append(value)
    return values


def _is_mac(value):
    normalized = re.sub(r"[^0-9A-Fa-f]", "", str(value))
    return len(normalized) == 12 and bool(re.fullmatch(r"[0-9A-Fa-f]{12}", normalized))


def _is_ip(value):
    try:
        return ipaddress.ip_address(str(value).strip()).version == 4
    except ValueError:
        return False


def _is_port(value):
    return bool(re.fullmatch(r"(?:gi|fa|te|eth|xe|ge)?\s*\d+(?:/\d+){0,3}", str(value).strip(), re.I))


def _tokens(header):
    return {
        token
        for token in re.split(r"[^0-9A-Za-z]+", str(header).lower())
        if token
    }


def _text_rate(values):
    if not values:
        return 0.0
    useful = 0
    for value in values:
        text = str(value).strip()
        if text and not _is_ip(text) and not _is_mac(text) and not _is_port(text):
            useful += 1
    return useful / len(values)


def _profile(values):
    total = len(values)
    if not total:
        return {
            "filled": 0.0,
            "mac": 0.0,
            "ip": 0.0,
            "port": 0.0,
            "text": 0.0,
            "numeric": 0.0,
        }
    numeric = 0
    for value in values:
        try:
            float(str(value).replace(",", "."))
            numeric += 1
        except ValueError:
            pass
    return {
        "filled": 1.0,
        "mac": sum(1 for value in values if _is_mac(value)) / total,
        "ip": sum(1 for value in values if _is_ip(value)) / total,
        "port": sum(1 for value in values if _is_port(value)) / total,
        "text": _text_rate(values),
        "numeric": numeric / total,
    }


def _sample_score(field, profile, header_score):
    if field == "mac":
        return profile["mac"]
    if field == "ip":
        return profile["ip"]
    if field == "switchIp":
        return profile["ip"] if header_score else profile["ip"] * 0.35
    if field == "switchPort":
        return profile["port"]
    if field in {"vendor", "model", "address", "room", "smartroomId"}:
        return min(profile["text"], 0.45)
    return 0.0


def _semantic_boost(field, header, profile):
    words = _tokens(header)
    boost = 0.0
    reasons = []

    matches = sorted(words & FIELD_KEYWORDS.get(field, set()))
    if matches:
        boost += min(0.28, 0.12 + 0.05 * len(matches))
        reasons.append("header keywords: " + ", ".join(matches[:4]))

    negatives = sorted(words & NEGATIVE_KEYWORDS.get(field, set()))
    if negatives:
        boost -= min(0.25, 0.08 + 0.05 * len(negatives))
        reasons.append("penalty keywords: " + ", ".join(negatives[:4]))

    if field == "mac" and profile["mac"] >= 0.8:
        boost += 0.22
        reasons.append("sample values look like MAC addresses")
    elif field in {"ip", "switchIp"} and profile["ip"] >= 0.8:
        boost += 0.18
        reasons.append("sample values look like IPv4 addresses")
    elif field == "switchPort" and profile["port"] >= 0.75:
        boost += 0.18
        reasons.append("sample values look like switch ports")
    elif field in {"vendor", "model", "address", "room", "smartroomId"} and profile["text"] >= 0.8:
        boost += 0.1
        reasons.append("sample values are descriptive text")

    if field == "room" and ({"room", "office", "floor", "cabinet"} & words):
        boost += 0.16
        reasons.append("room/location wording")
    if field == "address" and ({"rack", "building", "site", "street", "location"} & words):
        boost += 0.14
        reasons.append("physical location wording")
    if field == "switchIp" and ({"switch", "gateway", "router", "node"} & words):
        boost += 0.18
        reasons.append("network equipment wording")
    if field == "ip" and ({"host", "client", "endpoint"} & words):
        boost += 0.18
        reasons.append("endpoint wording")

    return boost, reasons


def _candidate_reason(field, header_score, sample_score, semantic_reasons):
    reasons = []
    if header_score:
        reasons.append("header matches " + FIELD_LABELS.get(field, field))
    if sample_score >= 0.75:
        reasons.append("sample data strongly matches")
    elif sample_score >= 0.35:
        reasons.append("sample data partially matches")
    reasons.extend(semantic_reasons)
    return "; ".join(reasons) or "weak heuristic match"


def _build_scores(headers, rows, ai=False):
    names = _normalize_headers(headers)
    scores = {field: [] for field in FIELD_PATTERNS}
    profiles = {}

    for index, header in enumerate(names):
        profiles[index] = _profile(_sample_values(rows, index))

    for field, pattern in FIELD_PATTERNS.items():
        for index, header in enumerate(names):
            profile = profiles[index]
            header_score = 0.55 if re.search(pattern, header, re.I) else 0.0
            sample_score = _sample_score(field, profile, header_score)
            semantic = 0.0
            semantic_reasons = []
            if ai:
                semantic, semantic_reasons = _semantic_boost(field, header, profile)
            confidence = min(1.0, max(0.0, round(header_score + sample_score * 0.65 + semantic, 3)))
            if confidence:
                scores[field].append({
                    "index": index,
                    "header": header,
                    "confidence": confidence,
                    "headerScore": round(header_score, 3),
                    "sampleScore": round(sample_score, 3),
                    "semanticScore": round(semantic, 3),
                    "profile": profile,
                    "reason": _candidate_reason(field, header_score, sample_score, semantic_reasons),
                })
        scores[field].sort(key=lambda item: (-item["confidence"], item["index"]))
    return scores


def _select_mapping(scores, ai=False):
    mapping = {}
    used_indexes = {}
    conflicts = []
    warnings = []
    threshold = 0.35

    for field in FIELD_ORDER:
        candidates = scores.get(field, [])
        if not candidates:
            warnings.append({"field": field, "message": "column not detected"})
            continue

        winner = None
        skipped_conflicts = []
        for candidate in candidates:
            if candidate["confidence"] < threshold:
                break
            if ai and field in {"vendor", "model", "room"} and candidate["headerScore"] == 0:
                if candidate["confidence"] < 0.5:
                    continue
            if candidate["index"] not in used_indexes:
                winner = candidate
                break
            skipped_conflicts.append(candidate)
            if not ai:
                break

        if not winner:
            top = candidates[0]
            if top["confidence"] < threshold:
                warnings.append({"field": field, "message": "low confidence", "confidence": top["confidence"]})
                continue
            owner = used_indexes.get(top["index"])
            conflicts.append({
                "index": top["index"],
                "header": top["header"],
                "fields": [owner, field] if owner else [field],
                "candidates": [
                    {
                        "field": field,
                        "index": item["index"],
                        "header": item["header"],
                        "confidence": item["confidence"],
                    }
                    for item in candidates[:3]
                ],
                "resolution": "manual review required",
            })
            continue

        if skipped_conflicts:
            conflicts.append({
                "index": skipped_conflicts[0]["index"],
                "header": skipped_conflicts[0]["header"],
                "fields": [used_indexes.get(skipped_conflicts[0]["index"]), field],
                "candidates": [
                    {
                        "field": field,
                        "index": item["index"],
                        "header": item["header"],
                        "confidence": item["confidence"],
                    }
                    for item in candidates[:3]
                ],
                "resolution": f"resolved to column {winner['index']}",
            })

        mapping[field] = winner["index"]
        used_indexes[winner["index"]] = field

    return mapping, conflicts, warnings


def _ai_summary(scores, mapping, conflicts):
    suggestions = []
    alternatives = defaultdict(list)
    explanations = []

    for field in FIELD_ORDER:
        candidates = scores.get(field, [])
        selected_index = mapping.get(field)
        selected = next((item for item in candidates if item["index"] == selected_index), None)
        if selected:
            suggestions.append({
                "field": field,
                "index": selected["index"],
                "header": selected["header"],
                "confidence": selected["confidence"],
                "reason": selected["reason"],
            })
            explanations.append(
                f"{FIELD_LABELS.get(field, field)} -> {selected['header']} ({selected['confidence']})"
            )
        for item in candidates[:4]:
            if item["index"] != selected_index:
                alternatives[field].append({
                    "index": item["index"],
                    "header": item["header"],
                    "confidence": item["confidence"],
                    "reason": item["reason"],
                })

    if conflicts:
        explanations.append(f"{len(conflicts)} column conflict(s) need review")

    return {
        "enabled": True,
        "suggestions": suggestions,
        "alternatives": dict(alternatives),
        "explanations": explanations,
    }


def detect(headers, rows=None, ai=False):
    rows = rows or []
    scores = _build_scores(headers, rows, ai=ai)
    mapping, conflicts, warnings = _select_mapping(scores, ai=ai)

    result = {**mapping}
    result.update({
        "mapping": mapping,
        "scores": scores,
        "conflicts": conflicts,
        "warnings": warnings,
        "mode": "auto+ai" if ai else "auto",
    })
    if ai:
        result["ai"] = _ai_summary(scores, mapping, conflicts)
    return result


def detect_ai(headers, rows=None):
    return detect(headers, rows, ai=True)

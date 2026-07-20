"""In-memory indexes for fast vendor/model detection over large batches."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any


UNKNOWN_VALUES = {"", "unknown", "not found", "n/a", "не определено", "неизвестно"}


def normalize_mac(value: Any) -> str:
    return re.sub(r"[^0-9A-Fa-f]", "", str(value or "")).upper()


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _known(value: Any) -> bool:
    return _text(value).lower() not in UNKNOWN_VALUES


def compile_rule_index(rules: list[dict[str, Any]], key: str, value_key: str) -> dict[str, Any]:
    by_prefix: dict[str, dict[str, Any]] = {}
    compatible: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in rules or []:
        prefix = normalize_mac(raw.get(key))
        value = _text(raw.get(value_key))
        if not prefix or not value:
            continue
        rule = {**raw, key: prefix, value_key: value}
        previous = by_prefix.get(prefix)
        if previous is None or _text(rule.get("source")) == "custom":
            by_prefix[prefix] = rule
        if key == "prefix" and len(prefix) >= 10:
            compatible[prefix[:8]].append(rule)
    for candidates in compatible.values():
        candidates.sort(key=lambda item: (len(item[key]), _text(item.get("source")) == "custom"), reverse=True)
    return {
        "key": key,
        "valueKey": value_key,
        "byPrefix": by_prefix,
        "lengths": sorted({len(prefix) for prefix in by_prefix}, reverse=True),
        "compatible": dict(compatible),
    }


def indexed_prefix_rule(mac: str, index: dict[str, Any] | None) -> dict[str, Any] | None:
    normalized = normalize_mac(mac)
    if not index:
        return None
    by_prefix = index.get("byPrefix") or {}
    for length in index.get("lengths") or []:
        rule = by_prefix.get(normalized[: int(length)])
        if rule:
            return rule
    return None


def indexed_compatible_model(mac: str, index: dict[str, Any] | None) -> dict[str, Any] | None:
    normalized = normalize_mac(mac)
    if len(normalized) < 8 or not index:
        return None
    candidates = (index.get("compatible") or {}).get(normalized[:8]) or []
    return candidates[0] if candidates else None


def build_similarity_index(observations: list[dict[str, Any]]) -> dict[int, dict[str, dict[str, Counter]]]:
    result: dict[int, dict[str, dict[str, Counter]]] = {10: {}, 8: {}, 6: {}}
    accumulators: dict[int, dict[str, dict[str, Counter]]] = {
        length: defaultdict(lambda: {"vendors": Counter(), "models": Counter(), "pairs": Counter()})
        for length in result
    }
    for item in observations or []:
        mac = normalize_mac(item.get("mac"))
        vendor = _text(item.get("vendor"))
        model = _text(item.get("model"))
        try:
            weight = max(1, int(item.get("count") or 1))
        except (TypeError, ValueError):
            weight = 1
        known_vendor = _known(vendor)
        if not mac or (not known_vendor and not model):
            continue
        for length in result:
            prefix = mac[:length]
            if len(prefix) != length:
                continue
            bucket = accumulators[length][prefix]
            if known_vendor:
                bucket["vendors"][vendor] += weight
            if model:
                bucket["models"][model] += weight
            if known_vendor or model:
                bucket["pairs"][(vendor, model)] += weight
    for length, prefixes in accumulators.items():
        result[length] = dict(prefixes)
    return result


def similarity_detection(mac: str, index: dict[int, dict[str, dict[str, Counter]]] | None) -> dict[str, Any]:
    normalized = normalize_mac(mac)
    confidence_by_length = {10: 0.78, 8: 0.70, 6: 0.62}
    for length in (10, 8, 6):
        prefix = normalized[:length]
        bucket = (index or {}).get(length, {}).get(prefix)
        if not bucket:
            continue
        vendors = bucket.get("vendors") or Counter()
        models = bucket.get("models") or Counter()
        if vendors or models:
            vendor, vendor_count = vendors.most_common(1)[0] if vendors else ("", 0)
            matching_models = Counter()
            for (pair_vendor, pair_model), count in (bucket.get("pairs") or Counter()).items():
                if pair_model and (not vendor or pair_vendor == vendor):
                    matching_models[pair_model] += count
            model, model_count = matching_models.most_common(1)[0] if matching_models else ((models.most_common(1)[0]) if models else ("", 0))
            return {
                "value": vendor,
                "vendor": vendor,
                "model": model,
                "source": "similar",
                "confidence": confidence_by_length[length],
                "matchedPrefix": prefix,
                "matches": max(vendor_count, model_count),
            }
    return {}


def build_vendor_model_history_index(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact: dict[str, dict[str, Any]] = {}
    prefix_counts: dict[int, dict[str, Counter]] = {10: defaultdict(Counter), 8: defaultdict(Counter), 6: defaultdict(Counter)}
    for row in rows or []:
        mac = normalize_mac(row.get("mac"))
        vendor, model = _text(row.get("vendor")), _text(row.get("model"))
        try:
            weight = max(1, int(row.get("count") or 1))
        except (TypeError, ValueError):
            weight = 1
        if not mac or (not vendor and not model):
            continue
        if len(mac) == 12 and not row.get("aggregate"):
            exact.setdefault(mac, {"vendor": vendor, "model": model})
        for length in prefix_counts:
            if len(mac) >= length:
                prefix_counts[length][mac[:length]][(vendor, model)] += weight
    return {"exact": exact, "prefixCounts": {length: dict(values) for length, values in prefix_counts.items()}}


def indexed_history_suggestion(mac: str, index: dict[str, Any] | None, settings: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_mac(mac)
    if not normalized or not settings.get("enabled", True) or not index:
        return {}
    exact = (index.get("exact") or {}).get(normalized)
    if exact:
        return {**exact, "source": "vendor_model_history_exact", "confidence": 0.93, "matchedPrefix": normalized, "matches": 1}
    plan: list[tuple[int, float]] = []
    if settings.get("useMac5Match", True):
        plan.extend(((10, 0.82), (8, 0.76)))
    if settings.get("useOuiMatch", True):
        plan.append((6, 0.68))
    for length, confidence in plan:
        prefix = normalized[:length]
        counts = (index.get("prefixCounts") or {}).get(length, {}).get(prefix)
        if counts:
            (vendor, model), matches = sorted(counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))[0]
            return {"vendor": vendor, "model": model, "source": "vendor_model_history_prefix", "confidence": confidence, "matchedPrefix": prefix, "matches": matches}
    return {}

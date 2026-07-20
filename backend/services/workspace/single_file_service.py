from collections import Counter
from typing import Any

from backend.services.detection.column_detector_service import detect
from .enrichment_service import enrich_files
from .file_import_service import read_table


FIELDS = ["mac", "vendor", "model", "ip", "address", "room", "switchIp", "switchPort"]


def normalize_mapping(mapping: dict[str, Any] | None, headers: list[str]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    if not isinstance(mapping, dict):
        return normalized
    for field in FIELDS:
        value = mapping.get(field)
        if value in ("", None):
            continue
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= index < len(headers):
            normalized[field] = index
    return normalized


def summarize_single_file(
    filename: str,
    headers: list[str],
    rows: list[list[Any]],
    mapping: dict[str, Any],
    devices: list[dict[str, Any]],
    invalid: list[dict[str, Any]],
    detection: dict[str, Any],
) -> dict[str, Any]:
    def filled(field: str) -> int:
        return sum(1 for item in devices if str(item.get(field, "")).strip() and item.get(field) != "Unknown")

    def top(field: str) -> list[dict[str, Any]]:
        counts = Counter(str(item.get(field) or "Unknown") for item in devices)
        return [{"name": name, "count": count} for name, count in counts.most_common(10)]

    detected_columns = []
    for field in FIELDS:
        index = mapping.get(field)
        if index is None:
            continue
        confidence = 1.0
        for candidate in detection.get("scores", {}).get(field, []):
            if candidate.get("index") == index:
                confidence = candidate.get("confidence", confidence)
                break
        detected_columns.append({
            "field": field,
            "index": index,
            "header": headers[index] if 0 <= int(index) < len(headers) else str(index),
            "confidence": confidence,
        })

    return {
        "filename": filename,
        "rows": len(rows),
        "columns": len(headers),
        "valid": len(devices),
        "invalid": len(invalid),
        "uniqueMacs": len({item.get("mac") for item in devices if item.get("mac")}),
        "withVendor": filled("vendor"),
        "withModel": filled("model"),
        "withAddress": filled("address"),
        "withRoom": filled("room"),
        "withSwitch": filled("switchIp"),
        "vendors": top("vendor"),
        "models": top("model"),
        "rooms": top("room"),
        "detectedColumns": detected_columns,
        "missingFields": [field for field in FIELDS if field not in mapping],
        "warnings": detection.get("warnings", []),
        "conflicts": detection.get("conflicts", []),
    }


def analyze_single_file(
    filename: str,
    content: bytes,
    sheet: str | None = None,
    mapping_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    table = read_table(filename, content, sheet)
    return analyze_single_file_table(filename, table, mapping_override)


def analyze_single_file_table(
    filename: str,
    table: dict[str, Any],
    mapping_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyze an already parsed table without retaining another encoded file copy."""
    headers = [str(header) for header in table.get("headers", [])]
    rows = table.get("rows", [])
    detection = detect(headers, rows, ai=True)
    override = normalize_mapping(mapping_override, headers)
    mapping = override or detection.get("mapping", {})
    file_info = {
        "name": filename,
        "headers": [{"name": header, "index": index} for index, header in enumerate(headers)],
        "rows": [headers, *rows],
        "mapping": mapping,
    }
    enriched = enrich_files([file_info], "primary")
    return {
        "filename": filename,
        "headers": headers,
        "rows": rows,
        "mapping": mapping,
        "detection": detection,
        "devices": enriched["devices"],
        "invalid": enriched["invalid"],
        "progress": enriched["progress"],
        "preview": {
            "headers": headers,
            "rows": rows[:10],
        },
        "summary": summarize_single_file(
            filename,
            headers,
            rows,
            mapping,
            enriched["devices"],
            enriched["invalid"],
            detection,
        ),
        "mappingMode": "manual" if override else "auto",
    }

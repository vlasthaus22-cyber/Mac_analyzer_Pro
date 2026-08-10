"""External OUI reference parsing and SQLite synchronization."""

from __future__ import annotations

import csv
import hashlib
import io
import re
from pathlib import Path
from typing import Any


SUPPORTED_PREFIX_LENGTHS = {6, 7, 8, 9, 10}


def normalize_prefix(value: Any) -> str:
    prefix = re.sub(r"[^0-9A-Fa-f]", "", str(value or "")).upper()
    return prefix if len(prefix) in SUPPORTED_PREFIX_LENGTHS else ""


def _decode(content: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1251", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _csv_mappings(text: str) -> dict[str, str]:
    mappings: dict[str, str] = {}
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return mappings
    normalized_headers = {re.sub(r"[^a-z0-9]", "", name.lower()): name for name in reader.fieldnames if name}
    prefix_header = next((normalized_headers[key] for key in ("assignment", "oui", "prefix", "macprefix") if key in normalized_headers), None)
    vendor_header = next((normalized_headers[key] for key in ("organizationname", "organization", "vendor", "manufacturer") if key in normalized_headers), None)
    if not prefix_header or not vendor_header:
        return mappings
    for row in reader:
        prefix = normalize_prefix(row.get(prefix_header))
        vendor = str(row.get(vendor_header) or "").strip()
        if prefix and vendor:
            mappings[prefix] = vendor
    return mappings


def _text_mappings(text: str) -> dict[str, str]:
    mappings: dict[str, str] = {}
    for line in text.splitlines():
        if "(hex)" in line:
            prefix_text, vendor_text = line.split("(hex)", 1)
        elif "\t" in line:
            prefix_text, vendor_text = line.split("\t", 1)
        elif ";" in line:
            prefix_text, vendor_text = line.split(";", 1)
        else:
            continue
        prefix = normalize_prefix(prefix_text)
        vendor = vendor_text.strip().strip('"')
        if prefix and vendor:
            mappings[prefix] = vendor
    return mappings


def parse_oui_reference(content: bytes, filename: str = "oui.txt") -> dict[str, Any]:
    text = _decode(content)
    mappings = _csv_mappings(text) if str(filename).lower().endswith(".csv") else {}
    if not mappings:
        mappings = _text_mappings(text)
    return {
        "mappings": mappings,
        "count": len(mappings),
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def import_oui_reference(connection: Any, content: bytes, filename: str = "oui.txt") -> dict[str, Any]:
    parsed = parse_oui_reference(content, filename)
    mappings = parsed.pop("mappings")
    if not mappings:
        raise ValueError("В справочнике не найдены колонки Assignment/OUI и Organization/Vendor или строки '(hex)'.")
    inserted = 0
    updated = 0
    preserved = 0
    for prefix, vendor in mappings.items():
        existing = connection.execute("SELECT vendor, source FROM vendor_mappings WHERE oui = ?", (prefix,)).fetchone()
        if existing is None:
            connection.execute(
                "INSERT INTO vendor_mappings (oui, vendor, source, updated_at) VALUES (?, ?, 'reference', datetime('now'))",
                (prefix, vendor),
            )
            inserted += 1
        elif str(existing["source"] or "") in {"builtin", "reference"}:
            if str(existing["vendor"] or "") != vendor or str(existing["source"] or "") != "reference":
                connection.execute(
                    "UPDATE vendor_mappings SET vendor = ?, source = 'reference', updated_at = datetime('now') WHERE oui = ?",
                    (vendor, prefix),
                )
                updated += 1
        else:
            preserved += 1
    return {**parsed, "filename": Path(filename).name, "inserted": inserted, "updated": updated, "preserved": preserved}


def reference_status(connection: Any, reference_directory: Path) -> dict[str, Any]:
    source_counts = {
        str(row["source"]): int(row["total"])
        for row in connection.execute("SELECT source, COUNT(*) AS total FROM vendor_mappings GROUP BY source").fetchall()
    }
    files = [
        {"name": path.name, "bytes": path.stat().st_size, "modifiedAt": path.stat().st_mtime}
        for path in sorted(Path(reference_directory).glob("oui.*"))
        if path.is_file()
    ]
    return {
        "directory": str(Path(reference_directory)),
        "files": files,
        "sourceCounts": source_counts,
        "referenceMappings": source_counts.get("reference", 0),
        "totalMappings": sum(source_counts.values()),
    }

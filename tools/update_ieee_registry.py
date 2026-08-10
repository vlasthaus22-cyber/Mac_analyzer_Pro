#!/usr/bin/env python3
"""Download the public IEEE assignment registries and build offline assets.

The generated browser module intentionally excludes CID assignments from MAC
vendor matching: IEEE CIDs identify protocols, not universally unique devices.
CID records are still counted in the bundled catalogue metadata.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "MA-L": "https://standards-oui.ieee.org/oui/oui.csv",
    "MA-M": "https://standards-oui.ieee.org/oui28/mam.csv",
    "MA-S": "https://standards-oui.ieee.org/oui36/oui36.csv",
    "IAB": "https://standards-oui.ieee.org/iab/iab.csv",
    "CID": "https://standards-oui.ieee.org/cid/cid.csv",
}
MATCHABLE = ("MA-S", "IAB", "MA-M", "MA-L")


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "MAC-Analyzer-Pro IEEE registry updater"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def parse_csv(content: bytes) -> list[tuple[str, str]]:
    text = content.decode("utf-8-sig")
    rows: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(text)):
        prefix = "".join(character for character in str(row.get("Assignment") or "").upper() if character in "0123456789ABCDEF")
        vendor = str(row.get("Organization Name") or "").strip()
        if prefix and vendor:
            rows[prefix] = vendor
    return sorted(rows.items())


def javascript_asset(payload: dict) -> str:
    vendors = payload["vendors"]
    assignments = payload["assignments"]
    metadata = {
        "schemaVersion": payload["schemaVersion"],
        "generatedAt": payload["generatedAt"],
        "counts": payload["counts"],
        "total": payload["total"],
        "source": "IEEE Registration Authority",
    }
    return """(() => {\n  \"use strict\";\n  const vendors = %s;\n  const rows = %s;\n  const metadata = %s;\n  let indexes;\n  function normalize(value) {\n    const mac = String(value ?? \"\").toUpperCase().replace(/[^0-9A-F]/g, \"\");\n    return mac.length === 12 ? mac : \"\";\n  }\n  function ensureIndexes() {\n    if (indexes) return indexes;\n    indexes = {};\n    for (const [length, flat] of Object.entries(rows)) {\n      const map = new Map();\n      for (let index = 0; index < flat.length; index += 2) map.set(flat[index], vendors[flat[index + 1]]);\n      indexes[length] = map;\n    }\n    return indexes;\n  }\n  function lookup(value) {\n    const mac = normalize(value);\n    if (!mac) return null;\n    const current = ensureIndexes();\n    for (const length of [9, 7, 6]) {\n      const vendor = current[length]?.get(mac.slice(0, length));\n      if (vendor) return { vendor, prefix: mac.slice(0, length), source: \"IEEE\" };\n    }\n    return null;\n  }\n  window.MacAnalyzerIeeeRegistry = Object.freeze({ lookup, status: () => ({ ...metadata }), normalize });\n  document.documentElement.dataset.ieeeRegistry = \"ready\";\n})();\n""" % (
        json.dumps(vendors, ensure_ascii=False, separators=(",", ":")),
        json.dumps(assignments, ensure_ascii=False, separators=(",", ":")),
        json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
    )


def build(fetch=download) -> dict:
    records: dict[str, list[tuple[str, str]]] = {}
    source_info = []
    for registry, url in SOURCES.items():
        content = fetch(url)
        parsed = parse_csv(content)
        records[registry] = parsed
        source_info.append({
            "registry": registry,
            "url": url,
            "count": len(parsed),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })

    vendor_names = sorted({vendor for registry in MATCHABLE for _, vendor in records[registry]})
    vendor_ids = {vendor: index for index, vendor in enumerate(vendor_names)}
    assignments: dict[str, list[object]] = {"6": [], "7": [], "9": []}
    # More specific registries win. IAB and MA-S are both 36-bit and do not
    # overlap in the public registry, but deterministic setdefault preserves it.
    match_rows: dict[int, dict[str, int]] = {6: {}, 7: {}, 9: {}}
    for registry in MATCHABLE:
        for prefix, vendor in records[registry]:
            if len(prefix) in match_rows:
                match_rows[len(prefix)].setdefault(prefix, vendor_ids[vendor])
    for length, values in match_rows.items():
        flat = assignments[str(length)]
        for prefix, vendor_id in sorted(values.items()):
            flat.extend((prefix, vendor_id))

    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "schemaVersion": 1,
        "generatedAt": generated,
        "sources": source_info,
        "counts": {registry: len(items) for registry, items in records.items()},
        "total": sum(len(items) for items in records.values()),
        "vendors": vendor_names,
        "assignments": assignments,
    }
    reference = ROOT / "data" / "reference"
    frontend = ROOT / "frontend"
    reference.mkdir(parents=True, exist_ok=True)
    frontend.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with (reference / "ieee_registry.json.gz").open("wb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as archive:
            archive.write(serialized)
    (reference / "IEEE_REGISTRY_INFO.json").write_text(
        json.dumps({key: payload[key] for key in ("schemaVersion", "generatedAt", "sources", "counts", "total")}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (frontend / "ieee-vendor-registry.js").write_text(javascript_asset(payload), encoding="utf-8")
    return {
        "generatedAt": generated,
        "counts": payload["counts"],
        "total": payload["total"],
        "vendors": len(vendor_names),
        "gzipBytes": (reference / "ieee_registry.json.gz").stat().st_size,
        "javascriptBytes": (frontend / "ieee-vendor-registry.js").stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(build(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

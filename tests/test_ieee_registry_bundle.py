import gzip
import json
from pathlib import Path

import server
from backend.services.detection.ieee_registry_service import clear_registry_cache, ieee_registry_status, lookup_ieee_vendor
from backend.services.detection.reference_data_service import normalize_prefix


ROOT = Path(__file__).resolve().parents[1]


def test_full_ieee_registry_is_bundled_and_matches_all_supported_assignment_sizes():
    path = ROOT / "data" / "reference" / "ieee_registry.json.gz"
    assert path.is_file()
    with gzip.open(path, "rt", encoding="utf-8") as source:
        payload = json.load(source)

    assert payload["total"] > 50_000
    assert set(payload["counts"]) == {"MA-L", "MA-M", "MA-S", "IAB", "CID"}
    assert payload["counts"]["MA-L"] > 30_000
    assert set(payload["assignments"]) == {"6", "7", "9"}
    assert normalize_prefix("AA-BB-CC-D") == "AABBCCD"
    assert normalize_prefix("AA-BB-CC-D-E") == "AABBCCDE"
    assert normalize_prefix("AA-BB-CC-D-EF") == "AABBCCDEF"

    clear_registry_cache()
    for length in (9, 7, 6):
        flat = payload["assignments"][str(length)]
        prefix = flat[0]
        expected = payload["vendors"][flat[1]]
        match = lookup_ieee_vendor(ROOT, prefix + "0" * (12 - length))
        assert match == {"vendor": expected, "prefix": prefix, "source": "ieee"}

    status = ieee_registry_status(ROOT)
    assert status["available"] is True
    assert status["total"] == payload["total"]


def test_backend_enrichment_uses_ieee_without_bulk_inserting_registry():
    server.init_database()
    with gzip.open(ROOT / "data" / "reference" / "ieee_registry.json.gz", "rt", encoding="utf-8") as source:
        payload = json.load(source)
    prefix = payload["assignments"]["6"][0]
    expected = payload["vendors"][payload["assignments"]["6"][1]]
    result = server.enrich_device({"mac": prefix + "123456"})
    assert result["vendor"] == expected
    assert result["vendorMatchedPrefix"] == prefix


if __name__ == "__main__":
    test_full_ieee_registry_is_bundled_and_matches_all_supported_assignment_sizes()
    test_backend_enrichment_uses_ieee_without_bulk_inserting_registry()
    print("IEEE registry bundle tests passed")

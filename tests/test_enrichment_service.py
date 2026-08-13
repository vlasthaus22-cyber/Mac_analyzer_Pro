from backend.services.workspace.enrichment_service import enrich_files


FILES = [
    {
        "name": "primary.csv",
        "mapping": {"mac": 0, "vendor": 1, "ip": 2},
        "rows": [
            ["mac", "vendor", "ip"],
            ["AA:BB:CC:00:00:01", "Vendor A", "10.0.0.1"],
            ["bad-mac", "Broken", "10.0.0.9"],
        ],
    },
    {
        "name": "extra.csv",
        "mapping": {"mac": 0, "address": 1, "room": 2},
        "rows": [
            ["mac", "address", "room"],
            ["AA:BB:CC:00:00:01", "Rack 1", "101"],
            ["AA:BB:CC:00:00:02", "Rack 2", "102"],
        ],
    },
]


def test_enrichment_primary_and_merge_strategies():
    primary = enrich_files(FILES, "primary")
    assert primary["progress"]["files"] == 2
    assert primary["progress"]["rows"] == 4
    assert primary["progress"]["valid"] == 2
    assert primary["progress"]["invalid"] == 1
    assert primary["devices"][0]["mac"] == "AABBCC000001"
    assert primary["devices"][0]["address"] == "Rack 1"
    assert primary["devices"][1]["address"] == "Rack 2"
    assert primary["devices"][0]["room"] == "101"

    merged = enrich_files(FILES, "merge")
    assert merged["progress"]["valid"] == 2
    assert [device["mac"] for device in merged["devices"]] == ["AABBCC000001", "AABBCC000002"]
    assert merged["devices"][1]["address"] == "Rack 2"
    assert merged["devices"][0]["source"] == "primary.csv + extra.csv"
    assert merged["devices"][1]["source"] == "extra.csv"


if __name__ == "__main__":
    test_enrichment_primary_and_merge_strategies()
    print("enrichment service test passed")

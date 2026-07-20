from backend.services.detection.column_detector_service import detect
from server import column_conflict_review_payload


HEADERS = ["Device ID", "Host IP", "Switch IP", "Location", "Device Type", "Vendor Name"]
ROWS = [
    ["00:11:22:33:44:55", "192.0.2.10", "10.0.0.1", "Rack A", "Catalyst 9200", "Cisco"],
    ["00:11:22:33:44:66", "192.0.2.11", "10.0.0.1", "Rack B", "Catalyst 9300", "Cisco"],
]


def test_column_conflict_review_contains_recommendations_examples_and_selects():
    detection = detect(HEADERS, ROWS, ai=True)
    review = column_conflict_review_payload(HEADERS, ROWS, detection)

    assert len(review["fields"]) == 8
    assert review["autoMapping"]["mac"] == 0
    assert review["autoMapping"]["ip"] == 1
    assert review["autoMapping"]["switchIp"] == 2
    mac = next(item for item in review["fields"] if item["field"] == "mac")
    assert mac["required"] is True
    assert mac["recommendedIndex"] == 0
    assert mac["confidence"] > 50
    assert "00:11:22:33:44:55" in mac["samples"]
    assert mac["alternatives"]
    assert 'data-conflict-field="mac"' in review["rowsHtml"]
    assert 'data-conflict-column="mac"' in review["rowsHtml"]
    assert 'data-ai-index="0"' in review["rowsHtml"]
    assert '<option value="0" selected>Device ID</option>' in review["rowsHtml"]
    assert "MAC-адрес" in review["rowsHtml"]
    assert "Примеры" not in review["rowsHtml"]


def test_column_conflict_review_keeps_all_headers_for_manual_override():
    detection = detect(HEADERS, ROWS, ai=True)
    review = column_conflict_review_payload(HEADERS, ROWS, detection)

    model = next(item for item in review["fields"] if item["field"] == "model")
    assert model["recommendedIndex"] == 4
    assert model["samples"] == ["Catalyst 9200", "Catalyst 9300"]
    for header in HEADERS:
        assert review["rowsHtml"].count(f">{header}</option>") == 8
    assert review["emptyRowsHtml"].startswith('<tr><td colspan="4"')


if __name__ == "__main__":
    test_column_conflict_review_contains_recommendations_examples_and_selects()
    test_column_conflict_review_keeps_all_headers_for_manual_override()
    print("column conflict review test passed")

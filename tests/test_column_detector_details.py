from backend.services.detection.column_detector_service import detect


def test_column_detector_scores_conflicts_and_mapping():
    result = detect(
        ["Switch IP", "Location", "Port", "Vendor", "Mystery"],
        [
            ["10.0.0.1", "Rack A", "Gi1/0/1", "Cisco", "00:11:22:33:44:55"],
            ["10.0.0.2", "Rack B", "Gi1/0/2", "Cisco", "00:11:22:33:44:66"],
        ],
    )

    assert result["mapping"]["mac"] == 4
    assert result["mapping"]["switchIp"] == 0
    assert result["mapping"]["switchPort"] == 2
    assert result["mapping"]["vendor"] == 3
    assert result["scores"]["mac"][0]["confidence"] > 0.5
    assert any(conflict["index"] == 0 for conflict in result["conflicts"])
    assert any(item["field"] == "model" for item in result["warnings"])


if __name__ == "__main__":
    test_column_detector_scores_conflicts_and_mapping()
    print("column detector details test passed")

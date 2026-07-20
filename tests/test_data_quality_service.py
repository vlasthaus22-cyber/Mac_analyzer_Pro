from data_quality_service import analyze_data_quality


def test_data_quality_detects_duplicates_missing_fields_and_recommendations():
    devices = [
        {"mac": "AA:BB:CC:00:00:01", "vendor": "Cisco", "ip": "10.0.0.1", "room": "101", "switchIp": "10.0.0.10", "switchPort": "Gi1/0/1"},
        {"mac": "AA:BB:CC:00:00:01", "vendor": "Unknown", "ip": "bad-ip", "room": "", "switchIp": "", "switchPort": ""},
        {"mac": "", "vendor": "", "ip": "", "room": "", "switchIp": "", "switchPort": ""},
    ]

    report = analyze_data_quality(devices, invalid=[{"row": 4}])
    issues = {item["id"]: item for item in report["issues"]}

    assert report["summary"]["devices"] == 3
    assert report["summary"]["invalidRows"] == 1
    assert report["summary"]["duplicates"] == 1
    assert report["summary"]["uniqueMacs"] == 1
    assert report["score"] < 100
    assert issues["duplicate_macs"]["count"] == 1
    assert issues["unknown_vendors"]["count"] == 2
    assert issues["malformed_ips"]["count"] == 1
    assert issues["missing_switches"]["count"] == 2
    assert report["recommendations"]


def test_data_quality_empty_dataset_is_grade_d():
    report = analyze_data_quality([], [])

    assert report["score"] == 0
    assert report["grade"] == "D"
    assert report["summary"]["devices"] == 0


if __name__ == "__main__":
    test_data_quality_detects_duplicates_missing_fields_and_recommendations()
    test_data_quality_empty_dataset_is_grade_d()
    print("data quality service test passed")

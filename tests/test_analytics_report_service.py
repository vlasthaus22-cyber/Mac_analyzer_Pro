from analytics_report_service import build_analytics_report, export_analytics_report_txt


def test_analytics_report_matches_pyqt_sections_and_percentages():
    devices = [
        {"vendor": "Cisco", "model": "C9200", "room": "101", "address": "Main", "ip": "10.0.0.1", "switchIp": "10.0.1.1"},
        {"vendor": "Cisco", "model": "C9200", "room": "101", "address": "", "ip": "10.0.0.2", "switch_ip": "10.0.1.1"},
        {"vendor": "Unknown", "model": "", "room": "Не указано", "address": "Unknown", "ip": "", "switchIp": ""},
        {"vendor": "Apple", "model": "Mac mini", "room": "202", "address": "Branch", "ip": "10.0.0.4", "switchIp": "10.0.2.1"},
    ]

    report = build_analytics_report(devices)

    assert report["total"] == 4
    assert report["vendors"][0] == {"label": "Cisco", "count": 2, "percent": 50.0}
    assert report["models"][0] == {"label": "C9200", "count": 2, "percent": 50.0}
    assert report["coverage"]["uniqueVendors"] == 3
    assert report["coverage"]["uniqueModels"] == 2
    assert report["coverage"]["address"] == {"count": 2, "percent": 50.0}
    assert report["coverage"]["room"] == {"count": 3, "percent": 75.0}
    assert report["coverage"]["ip"] == {"count": 3, "percent": 75.0}
    assert report["coverage"]["switch"] == {"count": 3, "percent": 75.0}
    assert report["roomOccupancy"]["assignedDevices"] == 3
    assert report["roomOccupancy"]["unassignedDevices"] == 1
    assert report["roomOccupancy"]["assignedPercent"] == 75.0
    assert report["roomOccupancy"]["uniqueRooms"] == 2
    assert report["roomOccupancy"]["averageDevicesPerRoom"] == 1.5
    assert report["roomOccupancy"]["mostOccupied"] == {
        "label": "101",
        "count": 2,
        "percentOfAssigned": 66.7,
        "percentOfAll": 50.0,
    }
    assert "=== АНАЛИТИКА ПО УСТРОЙСТВАМ ===" in report["reportText"]
    assert "Cisco: 2 (50.0%)" in report["reportText"]
    assert "Коммутатор: 3 (75.0%)" in report["reportText"]
    assert "=== ЗАПОЛНЕННОСТЬ ПОМЕЩЕНИЙ ===" in report["reportText"]
    assert "Распределено по помещениям: 3 (75.0%)" in report["reportText"]

    exported = export_analytics_report_txt(report)
    assert exported["filename"].startswith("analytics_report_")
    assert exported["filename"].endswith(".txt")
    assert exported["mimeType"] == "text/plain"
    assert exported["content"] == report["reportText"]


def test_analytics_report_empty_and_validation():
    assert build_analytics_report([])["reportText"] == "Нет данных"
    try:
        build_analytics_report({})
    except ValueError as error:
        assert str(error) == "devices must be an array"
    else:
        raise AssertionError("ValueError was not raised")


if __name__ == "__main__":
    test_analytics_report_matches_pyqt_sections_and_percentages()
    test_analytics_report_empty_and_validation()
    print("analytics report service test passed")

from backend.services.detection.column_detector_service import detect


def test_requested_mass_enrichment_headers_are_detected_exactly():
    result = detect(["CallingStarionID", "NasIP", "NasPortID", "B_ReceiptTime"])
    assert result["mapping"]["mac"] == 0
    assert result["mapping"]["switchIp"] == 1
    assert result["mapping"]["switchPort"] == 2
    assert result["mapping"]["authenticationTime"] == 3


def test_requested_smartroom_headers_are_detected_exactly():
    result = detect(["MAC", "IP адрес", "Производитель", "Модель", "Адрес комнаты", "Название комнаты", "ID комнаты"])
    assert result["mapping"]["mac"] == 0
    assert result["mapping"]["vendor"] == 2
    assert result["mapping"]["model"] == 3
    assert result["mapping"]["address"] == 4
    assert result["mapping"]["room"] == 5
    assert result["mapping"]["smartroomId"] == 6


result = detect(["unknown", "location"], [["00:11:22:33:44:55", "10.0.0.1"]])
assert result["mac"] == 0
assert result["ip"] == 1
authentication = detect(
    ["MAC address", "Время аутентификации устройства"],
    [["00:11:22:33:44:55", "2026-09-13 10:15:00"]],
)
assert authentication["authenticationTime"] == 1
dual_mac = detect(
    ["MAC основного интерфейса", "MAC дополнительного интерфейса", "Smartroom ID"],
    [["AA:BB:CC:DD:EE:FF", "00:11:22:33:44:55", "SR-101"]],
)
assert dual_mac["mac"] == 0
assert dual_mac["secondaryMac"] == 1
print("column detector test passed")

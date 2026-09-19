from backend.services.detection.column_detector_service import detect


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

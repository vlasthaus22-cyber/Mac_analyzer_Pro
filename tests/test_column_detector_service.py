from backend.services.detection.column_detector_service import detect


result = detect(["unknown", "location"], [["00:11:22:33:44:55", "10.0.0.1"]])
assert result["mac"] == 0
assert result["ip"] == 1
print("column detector test passed")

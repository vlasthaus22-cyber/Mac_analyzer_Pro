from backend.services.detection.column_detector_service import detect, detect_ai


def test_ai_detector_resolves_host_and_switch_ip_columns():
    result = detect(
        ["Device ID", "Host", "Switch", "Iface", "Place"],
        [
            ["00:11:22:33:44:55", "192.168.10.11", "10.0.0.1", "Gi1/0/1", "Rack A"],
            ["00:11:22:33:44:66", "192.168.10.12", "10.0.0.1", "Gi1/0/2", "Rack B"],
            ["00:11:22:33:44:77", "192.168.10.13", "10.0.0.2", "Gi1/0/3", "Rack C"],
        ],
        ai=True,
    )

    assert result["mode"] == "auto+ai"
    assert result["mapping"]["mac"] == 0
    assert result["mapping"]["ip"] == 1
    assert result["mapping"]["switchIp"] == 2
    assert result["mapping"]["switchPort"] == 3
    assert result["mapping"]["address"] == 4
    assert result["ai"]["enabled"] is True
    assert any(item["field"] == "mac" and item["reason"] for item in result["ai"]["suggestions"])
    assert not any(set(conflict["fields"]) == {"ip", "switchIp"} for conflict in result["conflicts"])


def test_detect_ai_wrapper_keeps_old_mapping_shape():
    result = detect_ai(
        ["MAC", "Client IP", "Vendor"],
        [["AA-BB-CC-DD-EE-FF", "172.16.0.10", "Cisco"]],
    )

    assert result["mac"] == 0
    assert result["ip"] == 1
    assert result["vendor"] == 2
    assert result["ai"]["suggestions"]


if __name__ == "__main__":
    test_ai_detector_resolves_host_and_switch_ip_columns()
    test_detect_ai_wrapper_keeps_old_mapping_shape()
    print("column detector ai test passed")

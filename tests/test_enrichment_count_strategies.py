from backend.services.workspace.ddio_overlay_service import apply_ddio_ip_fallback, build_ddio_device_index
from backend.services.workspace.enrichment_service import (
    ALLOW_EXPANSION,
    NO_EXPANSION,
    enrich_files,
    normalize_enrichment_strategy,
)


def _mac(index: int) -> str:
    return f"A1B2C3{index:06X}"


def _files(main_count: int = 100, smartroom_new: int = 50):
    primary = [["MAC", "Serial", "Device ID"]] + [
        [_mac(index), f"SER-{index}", f"DEV-{index}"] for index in range(main_count)
    ]
    smartroom = [["MAC", "Serial", "Device ID", "Room"]] + [
        [_mac(index), f"SER-{index}", f"DEV-{index}", f"Room {index}"]
        for index in range(main_count + smartroom_new)
    ]
    return [
        {
            "name": "main.csv", "role": "primary",
            "mapping": {"mac": 0, "serialNumber": 1, "deviceId": 2}, "rows": primary,
        },
        {
            "name": "smartroom.csv", "role": "smartroom",
            "mapping": {"mac": 0, "serialNumber": 1, "deviceId": 2, "room": 3}, "rows": smartroom,
        },
    ]


def test_a_no_expansion_keeps_main_unique_count():
    result = enrich_files(_files(100, 50), NO_EXPANSION)
    assert len(result["devices"]) == 100
    assert result["diagnostics"]["counts"]["mainUniqueDevices"] == 100
    assert result["diagnostics"]["counts"]["smartroomMatched"] == 100
    assert result["diagnostics"]["counts"]["smartroomCreated"] == 0
    assert result["diagnostics"]["counts"]["smartroomUnmatched"] == 50
    assert {item["code"] for item in result["creationDecisions"]} == {"NOT_CREATED_FROM_SMARTROOM"}


def test_b_allow_expansion_adds_only_strongly_identified_smartroom_devices():
    result = enrich_files(_files(100, 20), ALLOW_EXPANSION)
    assert len(result["devices"]) == 120
    assert result["diagnostics"]["counts"]["smartroomCreated"] == 20
    created = [item for item in result["creationDecisions"] if item["code"] == "CREATED_FROM_SMARTROOM"]
    assert len(created) == 20
    assert all(item["strongIdentifiers"] for item in created)


def test_c_ddio_never_creates_final_devices_in_allow_expansion():
    result = enrich_files(_files(100, 0), ALLOW_EXPANSION)
    ddio_rows = [[_mac(1000 + index), f"192.0.2.{index % 250 + 1}"] for index in range(1000)]
    ddio_index = build_ddio_device_index(ddio_rows, {"leaseMac": 0, "leaseIp": 1})
    assert apply_ddio_ip_fallback(result["devices"], ddio_index) == 0
    assert len(result["devices"]) == 100


def test_d_multiple_ddio_ips_are_one_child_collection():
    result = enrich_files(_files(1, 0), NO_EXPANSION)
    ddio_index = build_ddio_device_index(
        [[_mac(0), f"192.0.2.{index}"] for index in range(1, 6)],
        {"leaseMac": 0, "leaseIp": 1},
    )
    assert apply_ddio_ip_fallback(result["devices"], ddio_index) == 1
    assert len(result["devices"]) == 1
    assert result["devices"][0]["possibleIps"] == [
        "192.0.2.1", "192.0.2.2", "192.0.2.3", "192.0.2.4", "192.0.2.5",
    ]


def test_e_multiple_smartroom_rows_enrich_one_final_device():
    files = _files(1, 0)
    files[1]["rows"].append([_mac(0), "SER-0", "DEV-0", "Alternative Room"])
    result = enrich_files(files, ALLOW_EXPANSION)
    assert len(result["devices"]) == 1
    assert result["devices"][0]["hasConflict"] is True
    assert result["diagnostics"]["counts"]["smartroomMatched"] == 2


def test_real_main_duplicates_are_normalized_without_merging_weak_matches():
    files = _files(2, 0)
    files[0]["rows"].append(["A1:B2:C3:00:00:00", "ser-0", "dev-0"])
    files[0]["rows"].append([_mac(2), "SER-2", "DEV-2"])
    result = enrich_files(files, NO_EXPANSION)
    assert len(result["devices"]) == 3
    assert result["diagnostics"]["counts"]["mainRawRows"] == 4
    assert result["diagnostics"]["counts"]["mainUniqueDevices"] == 3


def test_strategy_aliases_are_explicit_and_unknown_values_fail_closed():
    assert normalize_enrichment_strategy("primary") == ALLOW_EXPANSION
    assert normalize_enrichment_strategy("merge") == ALLOW_EXPANSION
    assert normalize_enrichment_strategy("ALLOW_EXPANSION") == ALLOW_EXPANSION
    assert normalize_enrichment_strategy("NO_EXPANSION") == NO_EXPANSION
    assert normalize_enrichment_strategy("unexpected") == NO_EXPANSION


def test_repeated_runs_and_strategy_switch_keep_main_ids_and_expected_counts():
    files = _files(100, 20)
    no_expansion_first = enrich_files(files, NO_EXPANSION)
    expansion = enrich_files(files, ALLOW_EXPANSION)
    no_expansion_second = enrich_files(files, NO_EXPANSION)

    assert [len(no_expansion_first["devices"]), len(expansion["devices"]), len(no_expansion_second["devices"])] == [100, 120, 100]
    first_main_ids = {item["deviceId"]: item["internalDeviceId"] for item in no_expansion_first["devices"]}
    expanded_main_ids = {
        item["deviceId"]: item["internalDeviceId"]
        for item in expansion["devices"]
        if item["deviceId"] in first_main_ids
    }
    second_main_ids = {item["deviceId"]: item["internalDeviceId"] for item in no_expansion_second["devices"]}
    assert expanded_main_ids == first_main_ids == second_main_ids
    assert no_expansion_first["devices"] == no_expansion_second["devices"]


if __name__ == "__main__":
    test_a_no_expansion_keeps_main_unique_count()
    test_b_allow_expansion_adds_only_strongly_identified_smartroom_devices()
    test_c_ddio_never_creates_final_devices_in_allow_expansion()
    test_d_multiple_ddio_ips_are_one_child_collection()
    test_e_multiple_smartroom_rows_enrich_one_final_device()
    test_real_main_duplicates_are_normalized_without_merging_weak_matches()
    test_strategy_aliases_are_explicit_and_unknown_values_fail_closed()
    test_repeated_runs_and_strategy_switch_keep_main_ids_and_expected_counts()
    print("enrichment count strategy tests passed")

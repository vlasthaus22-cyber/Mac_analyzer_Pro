from backend.services.workspace.enrichment_service import enrich_files, row_to_device


def test_empty_rows_are_skipped_and_not_reported_as_bad_macs():
    file_info = {"name": "main.csv", "role": "primary", "mapping": {"mac": 0}}
    assert row_to_device(["", "  "], file_info, 0)["skipped"] is True

    result = enrich_files([
        {
            **file_info,
            "rows": [["MAC", "Room"], ["", ""], ["00:11:22:33:44:55", "101"]],
        }
    ])
    assert len(result["devices"]) == 1
    assert result["invalid"] == []
    assert result["diagnostics"]["counts"]["emptyRowsSkipped"] == 1


def test_invalid_identity_contains_a_human_readable_explanation():
    file_info = {
        "name": "main.xlsx",
        "role": "primary",
        "mapping": {"mac": 0, "serialNumber": 1, "deviceId": 2},
    }
    invalid = row_to_device(["GG:11", "", ""], file_info, 5)
    assert invalid["errorCode"] == "INVALID_MAC"
    assert invalid["rawMac"] == "GG:11"
    assert invalid["macHexLength"] == 2
    assert "2 из 12" in invalid["explanation"]
    assert invalid["suggestion"]

    identified_by_serial = row_to_device(["GG:11", "SERIAL-1", ""], file_info, 6)
    assert not identified_by_serial.get("invalid")
    assert identified_by_serial["serialNumber"] == "SERIAL-1"


if __name__ == "__main__":
    test_empty_rows_are_skipped_and_not_reported_as_bad_macs()
    test_invalid_identity_contains_a_human_readable_explanation()
    print("record validation tests passed")

from server import filter_result_devices


def test_result_filter_handles_query_vendor_and_validity():
    devices = [
        {"mac": "AABBCC000001", "vendor": "Cisco", "model": "C9300", "room": "101"},
        {"mac": "DDEEFF000002", "vendor": "Apple", "model": "iPad", "room": "202"},
    ]
    invalid = [{"row": 3, "source": "bad.csv", "raw": "not-a-mac"}]

    cisco = filter_result_devices(devices, invalid, {"query": "9300", "vendor": "Cisco", "ouiLength": 4, "ouiStyle": "dash"})
    assert cisco["summary"] == {"total": 1, "valid": 1, "invalid": 0, "vendors": 2}
    assert cisco["items"][0]["mac"] == "AABBCC000001"
    assert cisco["items"][0]["oui"] == "AA-BB-CC-00"
    assert cisco["items"][0]["valid"] is True
    assert cisco["vendors"] == ["Apple", "Cisco"]
    assert 'data-sort-field="macFormatted"' in cisco["headerHtml"]
    assert 'aria-sort="none"' in cisco["headerHtml"]
    assert 'data-mac="AABBCC000001"' in cisco["tableRowsHtml"]
    assert "<td>AA:BB:CC:00:00:01</td>" in cisco["tableRowsHtml"]
    assert "<td>AA-BB-CC-00</td>" in cisco["tableRowsHtml"]
    assert '<option value="Cisco" selected>Cisco</option>' in cisco["vendorOptionsHtml"]

    invalid_only = filter_result_devices(devices, invalid, {"query": "bad.csv", "validity": "invalid"})
    assert invalid_only["summary"]["total"] == 1
    assert invalid_only["summary"]["invalid"] == 1
    assert invalid_only["items"][0]["valid"] is False
    assert "not-a-mac" in invalid_only["tableRowsHtml"]

    valid_only = filter_result_devices(devices, invalid, {"validity": "valid"})
    assert valid_only["summary"]["total"] == 2
    assert all(item["valid"] for item in valid_only["items"])

    custom = filter_result_devices(
        devices,
        [],
        {},
        ["macFormatted", "vendor", "customRack"],
        {"customRack": "Стойка"},
    )
    assert custom["columns"] == ["macFormatted", "vendor", "customRack"]
    assert 'data-sort-field="customRack"' in custom["headerHtml"]
    assert "Стойка" in custom["headerHtml"]

    sorted_devices = filter_result_devices(
        devices,
        [],
        {"sortField": "room", "sortDirection": "desc"},
        ["macFormatted", "room"],
    )
    assert [item["room"] for item in sorted_devices["items"]] == ["202", "101"]
    assert 'data-sort-field="room"' in sorted_devices["headerHtml"]
    assert 'aria-sort="descending"' in sorted_devices["headerHtml"]

    with_empty = filter_result_devices(
        devices + [{"mac": "001122000003", "vendor": "Empty", "room": ""}],
        [],
        {"sortField": "room", "sortDirection": "desc"},
        ["macFormatted", "room"],
    )
    assert [item["room"] for item in with_empty["items"]] == ["202", "101", ""]


def test_result_filter_paginates_large_sets_without_rendering_every_row():
    devices = [{"mac": f"AABBCC{index:06X}", "vendor": "Cisco"} for index in range(1200)]
    page = filter_result_devices(devices, [], {"offset": 500, "limit": 250})

    assert len(page["items"]) == 250
    assert page["summary"]["total"] == 1200
    assert page["pagination"] == {
        "total": 1200,
        "offset": 500,
        "limit": 250,
        "page": 3,
        "pages": 5,
        "hasPrevious": True,
        "hasNext": True,
    }


if __name__ == "__main__":
    test_result_filter_handles_query_vendor_and_validity()
    test_result_filter_paginates_large_sets_without_rendering_every_row()
    print("results filter service test passed")

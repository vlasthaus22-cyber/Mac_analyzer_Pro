from comparison_service import compare_devices, compare_many_devices, compare_many_snapshots, compare_snapshots, export_comparison


BASELINE = [
    {
        "mac": "AABBCC000001",
        "macFormatted": "AA:BB:CC:00:00:01",
        "vendor": "Acme",
        "model": "A1",
        "ip": "10.0.0.1",
        "source": "baseline.csv",
    },
    {
        "mac": "AABBCC000002",
        "macFormatted": "AA:BB:CC:00:00:02",
        "vendor": "OldVendor",
        "ip": "10.0.0.2",
        "source": "baseline.csv",
    },
]

CURRENT = [
    {
        "macFormatted": "AA-BB-CC-00-00-01",
        "vendor": "Acme",
        "model": "A2",
        "ip": "10.0.0.10",
        "source": "current.csv",
    },
    {
        "mac": "AABBCC000003",
        "macFormatted": "AA:BB:CC:00:00:03",
        "vendor": "NewVendor",
        "ip": "10.0.0.3",
        "source": "current.csv",
    },
]


def test_compare_devices_added_removed_modified():
    result = compare_devices(BASELINE, CURRENT, ["vendor", "model", "ip"])

    assert result["summary"] == {"added": 1, "removed": 1, "modified": 2, "total": 4}
    assert [change["status"] for change in result["changes"]].count("modified") == 2
    assert "<td>AA-BB-CC-00-00-01</td>" in result["changesRowsHtml"]
    assert "Результат сравнения" in result["summaryHtml"]
    assert any(change["field"] == "model" and change["before"] == "A1" and change["after"] == "A2" for change in result["changes"])
    assert any(change["status"] == "added" and change["mac"] == "AABBCC000003" for change in result["changes"])
    assert any(change["status"] == "removed" and change["mac"] == "AABBCC000002" for change in result["changes"])


def test_export_comparison_formats():
    changes = compare_devices(BASELINE, CURRENT, ["vendor", "model", "ip"])["changes"]

    csv_result = export_comparison(changes, "csv")
    assert csv_result["mimeType"] == "text/csv"
    assert "MAC," in csv_result["content"]
    assert "Изменено" in csv_result["content"]

    txt_result = export_comparison(changes, "txt")
    assert "Тип изменения: Добавлено" in txt_result["content"]

    excel_result = export_comparison(changes, "excel")
    assert excel_result["filename"].endswith(".xml")
    assert "<Workbook" in excel_result["content"]


def test_compare_many_devices_keeps_per_file_mapping_and_limit():
    result = compare_many_devices(
        BASELINE,
        [
            {"id": "first", "name": "first.csv", "mapping": {"mac": 0, "model": 1}, "devices": CURRENT},
            {"id": "second", "name": "second.csv", "mapping": {"mac": 2, "ip": 3}, "devices": BASELINE},
        ],
        ["vendor", "model", "ip"],
    )

    assert result["summary"] == {"added": 1, "removed": 1, "modified": 2, "total": 4}
    assert len(result["sets"]) == 2
    assert result["sets"][0]["mapping"] == {"mac": 0, "model": 1}
    assert result["sets"][1]["summary"]["total"] == 0
    assert "Массовое сравнение" in result["summaryHtml"]
    assert "first.csv" in result["summaryHtml"]
    assert all(change["comparisonName"] == "first.csv" for change in result["sets"][0]["changes"])

    try:
        compare_many_devices(BASELINE, [{"devices": []} for _ in range(11)])
    except ValueError as error:
        assert "maximum is 10" in str(error)
    else:
        raise AssertionError("more than 10 comparisons must fail")


def test_compare_snapshots_resolves_devices_and_export_by_ids():
    snapshots = [
        {"id": "base", "name": "Base", "source": "base.csv", "devices": BASELINE},
        {"id": "current", "name": "Current", "source": "current.csv", "devices": CURRENT},
    ]

    result = compare_snapshots(snapshots, "base", "current", ["vendor", "model", "ip"], "csv")

    assert result["summary"] == {"added": 1, "removed": 1, "modified": 2, "total": 4}
    assert result["baseline"]["name"] == "Base"
    assert result["current"]["deviceCount"] == 2
    assert result["export"]["filename"] == "mac-comparison.csv"


def test_compare_many_snapshots_resolves_selected_ids_and_mapping():
    snapshots = [
        {"id": "base", "name": "Base", "source": "base.csv", "devices": BASELINE},
        {"id": "first", "name": "First", "mapping": {"mac": 0}, "devices": CURRENT},
        {"id": "second", "name": "Second", "columnMapping": {"ip": 3}, "devices": BASELINE},
    ]

    result = compare_many_snapshots(snapshots, "base", ["base", "first", "second"], ["vendor", "model", "ip"])

    assert result["baseline"]["name"] == "Base"
    assert result["summary"] == {"added": 1, "removed": 1, "modified": 2, "total": 4}
    assert len(result["sets"]) == 2
    assert result["sets"][0]["mapping"] == {"mac": 0}
    assert result["sets"][1]["mapping"] == {"ip": 3}


if __name__ == "__main__":
    test_compare_devices_added_removed_modified()
    test_export_comparison_formats()
    test_compare_many_devices_keeps_per_file_mapping_and_limit()
    test_compare_snapshots_resolves_devices_and_export_by_ids()
    test_compare_many_snapshots_resolves_selected_ids_and_mapping()
    print("comparison service test passed")

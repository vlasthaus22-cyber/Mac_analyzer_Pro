import base64

from export_manager_service import export_managed, supported_export_formats


DEVICES = [
    {
        "macFormatted": "AA:BB:CC:00:00:01",
        "vendor": "Acme",
        "model": "AX-1",
        "ip": "10.0.0.1",
    }
]

COLUMNS = [
    {"key": "macFormatted", "title": "MAC"},
    {"key": "oui", "title": "OUI"},
    {"key": "vendor", "title": "Vendor"},
    {"key": "ip", "title": "IP"},
]


def test_export_manager_all_formats_and_metadata():
    formats = supported_export_formats()
    format_names = {item["format"] for item in formats["formats"]}
    assert {"csv", "txt", "html", "json", "yaml", "xlsx", "pdf", "spreadsheetml"}.issubset(format_names)

    for export_format in ["csv", "txt", "html", "json", "yaml", "spreadsheetml"]:
        result = export_managed(DEVICES, COLUMNS, export_format)
        assert result["format"] == export_format
        assert result["binary"] is False
        assert result["encoding"] == "utf-8"
        assert result["size"] == len(result["content"].encode("utf-8"))
        assert result["filename"].startswith("mac-analysis.")

    xml = export_managed(DEVICES, COLUMNS, "spreadsheetml")
    assert xml["mimeType"] == "application/vnd.ms-excel"
    assert "<Workbook" in xml["content"]
    assert "AA:BB:CC:00:00:01" in xml["content"]
    assert "AA:BB:CC:00" in export_managed(DEVICES, COLUMNS, "csv", oui_settings={"length": 4, "style": "colon"})["content"]

    xlsx = export_managed(DEVICES, COLUMNS, "xlsx")
    assert xlsx["binary"] is True
    assert xlsx["encoding"] == "base64"
    assert base64.b64decode(xlsx["content"]).startswith(b"PK")

    pdf = export_managed(DEVICES, COLUMNS, "pdf")
    assert pdf["binary"] is True
    assert base64.b64decode(pdf["content"]).startswith(b"%PDF")

    alias = export_managed(DEVICES, COLUMNS, "excel")
    assert alias["format"] == "xlsx"

    try:
        export_managed(DEVICES, COLUMNS, "docx")
    except ValueError as error:
        assert "Unsupported" in str(error)
    else:
        raise AssertionError("unsupported format must fail")


if __name__ == "__main__":
    test_export_manager_all_formats_and_metadata()
    print("export manager service test passed")

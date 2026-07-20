from export_service import export_text


DEVICES = [
    {
        "macFormatted": "AA:BB:CC:00:00:01",
        "vendor": 'Acme "Switch"',
        "model": "AX-1",
        "ip": "10.0.0.1",
    }
]
COLUMNS = [
    {"key": "macFormatted", "title": "MAC"},
    {"key": "vendor", "title": "Vendor"},
    {"key": "ip", "title": "IP"},
]


def test_export_text_formats():
    csv_result = export_text(DEVICES, COLUMNS, "csv")
    assert csv_result["mimeType"] == "text/csv"
    assert "MAC,Vendor,IP" in csv_result["content"]
    assert '"Acme ""Switch"""' in csv_result["content"]

    txt_result = export_text(DEVICES, COLUMNS, "txt")
    assert "Device 1" in txt_result["content"]
    assert "Vendor: Acme \"Switch\"" in txt_result["content"]

    json_result = export_text(DEVICES, COLUMNS, "json")
    assert '"macFormatted": "AA:BB:CC:00:00:01"' in json_result["content"]

    yaml_result = export_text(DEVICES, COLUMNS, "yaml")
    assert 'vendor: "Acme \\"Switch\\""' in yaml_result["content"]

    html_result = export_text(DEVICES, COLUMNS, "html")
    assert "<th>MAC</th>" in html_result["content"]
    assert "Acme &quot;Switch&quot;" in html_result["content"]

    try:
        export_text(DEVICES, COLUMNS, "docx")
    except ValueError as error:
        assert "Unsupported" in str(error)
    else:
        raise AssertionError("unsupported format must fail")


if __name__ == "__main__":
    test_export_text_formats()
    print("export service test passed")

import json
from io import BytesIO

from backend.services.workspace.file_import_service import read_table
from openpyxl import Workbook


def test_read_table_supports_csv_tsv_and_json():
    csv_data = read_table("devices.csv", b"MAC,Vendor,Model\nAA:BB:CC:00:00:01,Cisco,C9300\n")
    assert csv_data["headers"] == ["MAC", "Vendor", "Model"]
    assert csv_data["rows"] == [["AA:BB:CC:00:00:01", "Cisco", "C9300"]]

    tsv_data = read_table("devices.tsv", b"MAC\tVendor\nDD:EE:FF:00:00:02\tApple\n")
    assert tsv_data["headers"] == ["MAC", "Vendor"]
    assert tsv_data["rows"][0] == ["DD:EE:FF:00:00:02", "Apple"]

    json_payload = json.dumps({"devices": [{"mac": "112233000003", "vendor": "Juniper", "room": "101"}]}).encode()
    json_data = read_table("devices.json", json_payload)
    assert json_data["headers"] == ["mac", "vendor", "room"]
    assert json_data["rows"] == [["112233000003", "Juniper", "101"]]


def test_read_table_handles_windows_csv_and_plain_text_fallbacks():
    cp1251 = "MAC;Производитель;Модель\nAA:BB:CC:00:00:05;Сигма;Точка\n".encode("cp1251")
    cp1251_data = read_table("devices.csv", cp1251)
    assert cp1251_data["headers"] == ["MAC", "Производитель", "Модель"]
    assert cp1251_data["rows"] == [["AA:BB:CC:00:00:05", "Сигма", "Точка"]]

    pipe_data = read_table("devices.txt", b"MAC|Vendor|Model\nAA:BB:CC:00:00:06|PipeVendor|PipeModel\n")
    assert pipe_data["headers"] == ["MAC", "Vendor", "Model"]
    assert pipe_data["rows"] == [["AA:BB:CC:00:00:06", "PipeVendor", "PipeModel"]]


def test_read_table_reports_clear_errors_for_bad_files():
    for filename, content, message in (
        ("empty.csv", b"", "Файл пустой"),
        ("headers.csv", b",,\n", "Первая строка файла не содержит заголовков"),
        ("bad.json", b"[1, 2, 3]", "JSON-записи должны быть объектами"),
    ):
        try:
            read_table(filename, content)
        except ValueError as error:
            assert message in str(error)
        else:
            raise AssertionError(f"{filename} should fail")


def test_read_table_supports_xlsx_for_main_file_import():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Devices"
    sheet.append(["MAC", "Vendor", "Model"])
    sheet.append(["AA:BB:CC:00:00:04", "Cisco", "C9500"])
    buffer = BytesIO()
    workbook.save(buffer)

    data = read_table("devices.xlsx", buffer.getvalue())

    assert data["sheet"] == "Devices"
    assert data["headers"] == ["MAC", "Vendor", "Model"]
    assert data["rows"] == [["AA:BB:CC:00:00:04", "Cisco", "C9500"]]


if __name__ == "__main__":
    test_read_table_supports_csv_tsv_and_json()
    test_read_table_handles_windows_csv_and_plain_text_fallbacks()
    test_read_table_reports_clear_errors_for_bad_files()
    test_read_table_supports_xlsx_for_main_file_import()
    print("file import service test passed")

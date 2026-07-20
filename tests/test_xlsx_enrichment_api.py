import base64
import json
import threading
import urllib.request
from urllib.parse import quote
from http.server import ThreadingHTTPServer
from io import BytesIO

from openpyxl import Workbook

from server import AppHandler, WORKSPACE_FILE_CACHE, db_connection


def workbook_bytes(headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Devices"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def post_json(base_url, path, payload):
    request = urllib.request.Request(
        base_url + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": "null"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 200
        assert response.headers["Access-Control-Allow-Origin"] == "null"
        return json.loads(response.read().decode("utf-8"))


def post_binary_file(base_url, filename, content, preview_rows=100):
    request = urllib.request.Request(
        base_url + "/api/files/import-binary",
        data=content,
        headers={
            "Content-Type": "application/octet-stream",
            "Origin": "null",
            "X-File-Name": quote(filename),
            "X-Preview-Rows": str(preview_rows),
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 200
        assert response.headers["Access-Control-Allow-Origin"] == "null"
        return json.loads(response.read().decode("utf-8"))


def test_two_xlsx_files_are_visible_and_enrich_matching_primary_mac():
    server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        base_url = f"http://{host}:{port}"
        main = post_json(
            base_url,
            "/api/files/import",
            {
                "filename": "main.xlsx",
                "content": base64.b64encode(
                    workbook_bytes(
                        ["MAC Address", "Vendor", "Name"],
                        [["AA:BB:CC:00:00:21", "BaseVendor", "Device 21"]],
                    )
                ).decode("ascii"),
            },
        )
        enrichment = post_json(
            base_url,
            "/api/files/import",
            {
                "filename": "enrichment.xlsx",
                "content": base64.b64encode(
                    workbook_bytes(
                        ["MAC Address", "IP Address", "Room", "Switch IP"],
                        [
                            ["AA:BB:CC:00:00:21", "10.21.0.5", "Room 21", "192.168.21.1"],
                            ["AA:BB:CC:00:00:99", "10.99.0.5", "Room 99", "192.168.99.1"],
                        ],
                    )
                ).decode("ascii"),
            },
        )

        files = [
            {
                "id": "main",
                "name": "main.xlsx",
                "role": "primary",
                "fileToken": main["fileToken"],
                "rowCount": main["rowCount"],
                "mapping": {"mac": 0, "vendor": 1},
            },
            {
                "id": "enrichment",
                "name": "enrichment.xlsx",
                "role": "enrichment",
                "fileToken": enrichment["fileToken"],
                "rowCount": enrichment["rowCount"],
                "mapping": {"mac": 0, "ip": 1, "room": 2, "switchIp": 3},
            },
        ]
        panel = post_json(base_url, "/api/workspace/files", {"files": files})
        assert panel["primaryCount"] == 1
        assert panel["enrichmentCount"] == 1
        assert "main.xlsx" in panel["fileRowsHtml"]
        assert "enrichment.xlsx" in panel["fileRowsHtml"]
        assert "1 rows" in panel["fileRowsHtml"]
        assert "2 rows" in panel["fileRowsHtml"]

        result = post_json(
            base_url,
            "/api/enrichment/run",
            {
                "files": files,
                "strategy": "primary",
                "fields": {
                    "vendor": True,
                    "model": True,
                    "ip": True,
                    "address": True,
                    "room": True,
                    "switchIp": True,
                    "switchPort": True,
                },
                "source": "main.xlsx",
                "saveHistory": False,
                "notify": False,
            },
        )
        assert result["status"] == "completed"
        assert len(result["devices"]) == 1
        device = result["devices"][0]
        assert device["mac"] == "AABBCC000021"
        assert device["ip"] == "10.21.0.5"
        assert device["room"] == "Room 21"
        assert device["switchIp"] == "192.168.21.1"

        WORKSPACE_FILE_CACHE.discard(main["fileToken"])
        WORKSPACE_FILE_CACHE.discard(enrichment["fileToken"])
        full_files = [
            {**files[0], "rows": [main["headers"], *main["rows"]]},
            {**files[1], "rows": [enrichment["headers"], *enrichment["rows"]]},
        ]
        refreshed = post_json(
            base_url,
            "/api/enrichment/run",
            {
                "files": full_files,
                "strategy": "primary",
                "fields": {"vendor": True, "model": True, "ip": True, "address": True, "room": True, "switchIp": True, "switchPort": True},
                "source": "main.xlsx",
                "saveHistory": False,
                "notify": False,
                "refreshFileCache": True,
            },
        )
        assert len(refreshed["fileTokens"]) == 2
        assert all(item["fileToken"] for item in refreshed["fileTokens"])
    finally:
        for imported_file in (locals().get("main"), locals().get("enrichment")):
            if imported_file:
                WORKSPACE_FILE_CACHE.discard(imported_file.get("fileToken", ""))
        for refreshed_file in (locals().get("refreshed") or {}).get("fileTokens", []):
            WORKSPACE_FILE_CACHE.discard(refreshed_file.get("fileToken", ""))
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_compact_enrichment_keeps_full_result_in_sqlite_snapshot():
    server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    snapshot_id = ""
    try:
        host, port = server.server_address
        base_url = f"http://{host}:{port}"
        rows = [
            [f"02:00:00:00:{index // 256:02X}:{index % 256:02X}", f"10.0.{index // 254}.{index % 254 + 1}"]
            for index in range(200)
        ]
        imported = post_binary_file(
            base_url,
            "compact-memory-test.xlsx",
            workbook_bytes(["MAC Address", "IP Address"], rows),
            preview_rows=25,
        )
        assert imported["compactResult"] is True
        assert imported["rowCount"] == 200
        assert imported["previewRowCount"] == 25
        assert len(imported["rows"]) == 25
        files = [{
            "id": "compact-primary",
            "name": "compact-memory-test.xlsx",
            "role": "primary",
            "fileToken": imported["fileToken"],
            "rowCount": imported["rowCount"],
            "mapping": {"mac": 0, "ip": 1},
        }]

        result = post_json(
            base_url,
            "/api/enrichment/run",
            {
                "files": files,
                "strategy": "primary",
                "fields": {"vendor": True, "model": True, "ip": True},
                "source": "compact-memory-test.xlsx",
                "saveHistory": False,
                "notify": False,
                "compactResult": True,
                "resultPageSize": 25,
            },
        )
        snapshot_id = result["resultReference"]["snapshotId"]
        assert result["compactResult"] is True
        assert snapshot_id
        assert result["resultReference"]["deviceCount"] == 200
        assert result["resultSummary"]["devices"] == 200
        assert len(result["devices"]) == 25
        assert len(result["resultPage"]["items"]) == 25
        assert result["resultPage"]["pagination"]["total"] == 200
        assert len(json.dumps(result, ensure_ascii=False)) < 150_000

        page = post_json(
            base_url,
            "/api/results/filter",
            {"snapshotId": snapshot_id, "filters": {"offset": 175, "limit": 25}},
        )
        assert page["pagination"]["total"] == 200
        assert page["pagination"]["page"] == 8
        assert len(page["items"]) == 25

        exported = post_json(
            base_url,
            "/api/export",
            {"snapshotId": snapshot_id, "format": "csv", "columns": ["macFormatted", "ip"]},
        )
        assert exported["binary"] is False
        assert len(exported["content"].splitlines()) == 201
    finally:
        if locals().get("imported"):
            WORKSPACE_FILE_CACHE.discard(imported.get("fileToken", ""))
        if snapshot_id:
            with db_connection() as conn:
                conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
                conn.execute("DELETE FROM performance_metrics WHERE details LIKE 'source=compact-memory-test.xlsx%'")
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_large_binary_import_response_is_bounded_to_preview_rows():
    server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        base_url = f"http://{host}:{port}"
        rows = [
            [f"02:AA:BB:{index // 65536:02X}:{index // 256 % 256:02X}:{index % 256:02X}", f"10.20.{index // 254 % 254}.{index % 254 + 1}", "Cisco", f"Room {index % 100}"]
            for index in range(5_000)
        ]

        imported = post_binary_file(
            base_url,
            "large-memory-bound.xlsx",
            workbook_bytes(["MAC Address", "IP Address", "Vendor", "Room"], rows),
            preview_rows=100,
        )

        assert imported["rowCount"] == 5_000
        assert imported["previewRowCount"] == 100
        assert len(imported["rows"]) == 100
        assert len(json.dumps(imported, ensure_ascii=False)) < 100_000
    finally:
        if locals().get("imported"):
            WORKSPACE_FILE_CACHE.discard(imported.get("fileToken", ""))
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    test_two_xlsx_files_are_visible_and_enrich_matching_primary_mac()
    test_compact_enrichment_keeps_full_result_in_sqlite_snapshot()
    test_large_binary_import_response_is_bounded_to_preview_rows()
    print("xlsx enrichment API test passed")

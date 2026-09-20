import json
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from server import AppHandler, init_database


def post_json(base_url, path, payload):
    request = urllib.request.Request(
        base_url + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_batch_folder_scan_and_csv_import_api():
    init_database()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        primary = root / "main"
        smartroom = root / "smartroom"
        ddio = root / "ddio"
        for folder in (primary, smartroom, ddio):
            folder.mkdir()
        (primary / "main_20260920.csv").write_text(
            "MAC,Model,IP\n00:11:22:33:44:55,Room Kit,10.0.0.10\n",
            encoding="utf-8",
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            base_url = f"http://{host}:{port}/api"
            code, scanned = post_json(base_url, "/batch/folders/scan", {
                "paths": {"primary": str(primary), "smartroom": str(smartroom), "ddio": str(ddio)},
            })
            assert code == 200
            assert len(scanned["files"]) == 1
            descriptor = scanned["files"][0]
            assert descriptor["date"] == "2026-09-20T00:00:00Z"
            assert descriptor["dateSource"] == "filename"
            code, imported = post_json(base_url, "/batch/folders/import", {"token": descriptor["backendToken"]})
            assert code == 200
            assert imported["rowCount"] == 1
            assert imported["mapping"]["mac"] == 0
            assert imported["mapping"]["model"] == 1
            assert imported["fileToken"]
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

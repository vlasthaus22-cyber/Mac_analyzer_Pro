import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from server import AppHandler, workspace_files_panel_payload


def test_workspace_panel_groups_primary_and_enrichment_files():
    payload = workspace_files_panel_payload(
        [
            {"id": "main", "name": "main.xlsx", "role": "primary", "rows": [["MAC"], ["AABBCCDDEEFF"]]},
            {"id": "extra", "name": "extra.xlsx", "role": "enrichment", "rows": [["MAC", "IP"], ["AABBCCDDEEFF", "10.0.0.1"]]},
        ]
    )

    assert payload["primaryCount"] == 1
    assert payload["enrichmentCount"] == 1
    assert 'data-file-group="primary"' in payload["fileRowsHtml"]
    assert 'data-file-group="enrichment"' in payload["fileRowsHtml"]
    assert 'data-file-role="primary"' in payload["fileRowsHtml"]
    assert 'data-file-role="enrichment"' in payload["fileRowsHtml"]
    assert "main.xlsx" in payload["fileRowsHtml"]
    assert "extra.xlsx" in payload["fileRowsHtml"]


def test_local_html_origin_can_call_backend_api():
    server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/health",
            headers={"Origin": "null"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert response.headers["Access-Control-Allow-Origin"] == "null"
            assert payload["status"] == "ok"

        preflight = urllib.request.Request(
            f"http://{host}:{port}/api/files/import",
            headers={
                "Origin": "null",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            method="OPTIONS",
        )
        with urllib.request.urlopen(preflight, timeout=5) as response:
            assert response.status == 204
            assert response.headers["Access-Control-Allow-Origin"] == "null"
            assert "POST" in response.headers["Access-Control-Allow-Methods"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    test_workspace_panel_groups_primary_and_enrichment_files()
    test_local_html_origin_can_call_backend_api()
    print("workspace file roles test passed")

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from parity_service import build_parity_report, build_parity_status
from server import AppHandler, init_database


def request_json(base_url, path):
    request = urllib.request.Request(base_url + path, method="GET")
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_parity_registry_and_pyqt_equivalents_are_complete():
    status = build_parity_status(Path("."))
    audit = Path("MIGRATION_AUDIT.md").read_text(encoding="utf-8")
    status_file = Path("PARITY_STATUS.json").read_text(encoding="utf-8")
    expected_report = build_parity_report(Path("."))["content"] + "\n"

    assert status["registry"]["unchecked"] == []
    assert status["registry"]["checked"] == 74
    assert status["registry"]["total"] == 74
    assert status["summary"]["missingEquivalents"] == 0
    assert status["summary"]["webComplete"] == status["summary"]["pyqtBlocks"]
    assert status["status"] == "complete"
    assert "Status" in status["summaryHtml"]
    assert "PyQt blocks" in status["summaryHtml"]
    assert "Database management" in status["detailsHtml"]
    assert "Нет данных parity" in status["emptyDetailsHtml"]
    assert "Status: complete." in audit
    assert "PyQt blocks covered by web equivalents: 31/31." in audit
    assert "PARITY_REGISTRY.md requirements: 74/74." in audit
    assert "missingEquivalents=0" in audit
    assert status_file == expected_report


def test_parity_status_endpoint():
    init_database()
    server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        base_url = f"http://{host}:{port}"
        code, payload = request_json(base_url, "/api/parity/status")
        report_code, report = request_json(base_url, "/api/parity/report")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert code == 200
    assert payload["status"] == "complete"
    assert payload["summary"]["missingEquivalents"] == 0
    assert payload["registry"]["unchecked"] == []
    assert payload["registry"]["checked"] == 74
    assert "Status" in payload["summaryHtml"]
    assert "Database management" in payload["detailsHtml"]
    assert report_code == 200
    assert report["filename"] == "mac-analyzer-parity-report.json"
    assert '"status": "complete"' in report["content"]


if __name__ == "__main__":
    test_parity_registry_and_pyqt_equivalents_are_complete()
    test_parity_status_endpoint()
    print("parity status test passed")

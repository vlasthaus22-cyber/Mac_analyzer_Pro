import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from backend.services.system.diagnostics_service import REQUIRED_TABLES, build_system_diagnostics
from server import AppHandler, STORAGE, db_connection, init_database


def request_json(base_url, path):
    with urllib.request.urlopen(base_url + path, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_system_diagnostics_checks_runtime_storage_sqlite_parity_and_memory_guards():
    init_database()
    result = build_system_diagnostics(Path("."), STORAGE, db_connection)

    assert result["status"] == "healthy"
    assert result["summary"]["failed"] == 0
    assert result["summary"]["warnings"] == 0
    assert result["summary"]["readinessPercent"] == 100
    assert result["summary"]["parityPercent"] == 100
    assert result["summary"]["pyqtBlocks"] == result["summary"]["webComplete"]
    assert result["summary"]["registryChecked"] == result["summary"]["registryTotal"]
    assert len(REQUIRED_TABLES) >= 14
    assert all(item["passed"] for item in result["checks"])
    assert any(item["name"] == "Защита от Out of Memory" for item in result["checks"])
    assert "Потоковый XLSX" in result["detailsHtml"]
    assert "Готовность" in result["summaryHtml"]


def test_system_diagnostics_endpoint_is_read_only_and_healthy():
    init_database()
    server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        code, result = request_json(f"http://{host}:{port}", "/api/system/diagnostics")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert code == 200
    assert result["status"] == "healthy"
    assert result["summary"]["readinessPercent"] == 100
    assert result["summary"]["failed"] == 0


if __name__ == "__main__":
    test_system_diagnostics_checks_runtime_storage_sqlite_parity_and_memory_guards()
    test_system_diagnostics_endpoint_is_read_only_and_healthy()
    print("system diagnostics test passed")

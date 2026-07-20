import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from server import AppHandler, db_connection


def request_json(base_url, path, payload=None, token="", method="POST"):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(
        base_url + path,
        data=json.dumps(payload or {}).encode("utf-8") if method != "GET" else None,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_user_and_engineering_api_access_are_distinct():
    previous_password = os.environ.get("MAC_ANALYZER_ENGINEERING_PASSWORD")
    os.environ["MAC_ANALYZER_ENGINEERING_PASSWORD"] = "mode-test-password"
    server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        base_url = f"http://{host}:{port}"

        try:
            request_json(base_url, "/api/engineering/login", {"password": "wrong"})
        except urllib.error.HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("wrong engineering password must be rejected")

        try:
            request_json(base_url, "/api/api-cache/clear", {"prefix": "__mode_test__"})
        except urllib.error.HTTPError as error:
            assert error.code == 403
        else:
            raise AssertionError("user mode must not clear API cache")

        status, session = request_json(
            base_url,
            "/api/engineering/login",
            {"password": "mode-test-password", "ttlMinutes": 99999},
        )
        assert status == 200
        assert session["role"] == "engineer"
        assert session["permissions"]
        token = session["token"]

        _, current = request_json(base_url, "/api/engineering/session", token=token, method="GET")
        assert current["active"] is True
        assert current["session"]["role"] == "engineer"

        status, cleared = request_json(
            base_url,
            "/api/api-cache/clear",
            {"prefix": "__mode_test__"},
            token=token,
        )
        assert status == 200
        assert cleared["ok"] is True

        _, logout = request_json(base_url, "/api/engineering/logout", token=token)
        assert logout["revoked"] is True
        _, current = request_json(base_url, "/api/engineering/session", token=token, method="GET")
        assert current["active"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        with db_connection() as connection:
            connection.execute("DELETE FROM engineering_sessions")
        if previous_password is None:
            os.environ.pop("MAC_ANALYZER_ENGINEERING_PASSWORD", None)
        else:
            os.environ["MAC_ANALYZER_ENGINEERING_PASSWORD"] = previous_password


if __name__ == "__main__":
    test_user_and_engineering_api_access_are_distinct()
    print("engineering mode API test passed")

import base64

from scheduler_service import prepare_queue_files, queue_summary, run_file_queue


def test_prepare_queue_files_encodes_browser_rows():
    prepared = prepare_queue_files([
        {"name": "browser.csv", "rows": [["MAC Address", "Vendor"], ["AA:BB:CC:00:00:01", 'Acme "Switch"']]},
        {"filename": "ready.csv", "content": base64.b64encode(b"MAC,Vendor\n").decode("ascii")},
    ])

    assert [item["filename"] for item in prepared] == ["browser.csv", "ready.csv"]
    decoded = base64.b64decode(prepared[0]["content"]).decode("utf-8")
    assert "MAC Address,Vendor" in decoded
    assert '"Acme ""Switch"""' in decoded


def test_run_file_queue_processes_done_and_errors():
    encoded = base64.b64encode(b"MAC Address,Vendor\nAA:BB:CC:00:00:01,Cisco\n").decode("ascii")
    calls = []

    def analyzer(filename, content):
        calls.append((filename, content))
        return {"devices": [{"mac": "AABBCC000001"}], "invalid": []}

    result = run_file_queue(
        [
            {"id": "ok", "filename": "ok.csv", "content_base64": encoded},
            {"id": "bad", "filename": "bad.csv", "content_base64": "not-base64"},
        ],
        analyzer,
    )

    assert result["processed"] == 2
    assert result["done"] == 1
    assert result["errors"] == 1
    assert result["results"][0]["devices"] == 1
    assert result["results"][1]["status"] == "error"
    assert calls == [("ok.csv", b"MAC Address,Vendor\nAA:BB:CC:00:00:01,Cisco\n")]


def test_queue_summary_counts_known_and_custom_statuses():
    summary = queue_summary([
        {"status": "pending"},
        {"status": "done"},
        {"status": "done"},
        {"status": "custom"},
    ])

    assert summary["total"] == 4
    assert summary["pending"] == 1
    assert summary["done"] == 2
    assert summary["error"] == 0
    assert summary["custom"] == 1


if __name__ == "__main__":
    test_prepare_queue_files_encodes_browser_rows()
    test_run_file_queue_processes_done_and_errors()
    test_queue_summary_counts_known_and_custom_statuses()
    print("scheduler service test passed")

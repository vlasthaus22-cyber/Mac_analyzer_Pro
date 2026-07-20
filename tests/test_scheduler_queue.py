import base64
import json

from server import add_task_files, db_connection, init_database, run_task_now, task_queue, utc_now


TASK_ID = "scheduler-test-task"
TEST_MAC = "AABBCC000001"
TEST_MAC_2 = "AABBCC000002"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM task_file_queue WHERE task_id = ?", (TASK_ID,))
        conn.execute("DELETE FROM scheduled_tasks WHERE id = ?", (TASK_ID,))
        conn.execute("DELETE FROM mac_history WHERE mac = ?", (TEST_MAC,))
        conn.execute("DELETE FROM mac_history WHERE mac = ?", (TEST_MAC_2,))


def test_scheduler_queue_runs_files_and_saves_history():
    init_database()
    cleanup()
    encoded = base64.b64encode(
        "MAC Address,Vendor,IP Address,Room\nAA:BB:CC:00:00:01,Cisco,10.0.0.1,101\n".encode("utf-8")
    ).decode("ascii")

    with db_connection() as conn:
        conn.execute(
            "INSERT INTO scheduled_tasks (id, name, interval_minutes, enabled, payload_json, next_run_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (TASK_ID, "Scheduler test", 5, 1, json.dumps({}), utc_now(), utc_now()),
        )

    added = add_task_files(TASK_ID, [{"filename": "scheduler-test.csv", "content": encoded}])
    assert added["queued"] == 1
    assert added["summary"]["pending"] == 1

    added_rows = add_task_files(TASK_ID, [{"name": "scheduler-rows.csv", "rows": [["MAC Address", "Vendor"], ["AA:BB:CC:00:00:02", "Juniper"]]}])
    assert added_rows["queued"] == 1
    assert added_rows["summary"]["pending"] == 2

    result = run_task_now(TASK_ID)
    assert result["processed"] == 2
    assert result["done"] == 2
    assert result["errors"] == 0
    assert result["queue"]["done"] == 2

    queued = task_queue(TASK_ID)
    assert queued[0]["status"] == "done"
    assert queued[0]["result_json"]

    with db_connection() as conn:
        history = conn.execute("SELECT vendor, ip, room, source FROM mac_history WHERE mac = ?", (TEST_MAC,)).fetchone()
    assert dict(history) == {
        "vendor": "Cisco",
        "ip": "10.0.0.1",
        "room": "101",
        "source": "scheduler-test.csv",
    }
    cleanup()


if __name__ == "__main__":
    test_scheduler_queue_runs_files_and_saves_history()
    print("scheduler queue test passed")

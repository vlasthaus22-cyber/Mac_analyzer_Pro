from server import db_connection, init_database, utc_now


init_database()
task_id = "test-scheduled-analysis"
with db_connection() as conn:
    conn.execute(
        "INSERT OR REPLACE INTO scheduled_tasks (id, name, interval_minutes, enabled, payload_json, next_run_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (task_id, "Test analysis", 30, 1, "{}", utc_now(), utc_now()),
    )
with db_connection() as conn:
    task = conn.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,)).fetchone()
assert task["interval_minutes"] == 30
assert task["enabled"] == 1
print("scheduler storage test passed")

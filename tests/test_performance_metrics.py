from server import db_connection, init_database, utc_now


init_database()
with db_connection() as conn:
    conn.execute(
        "INSERT INTO performance_metrics (operation, duration_ms, details, created_at) VALUES (?, ?, ?, ?)",
        ("test", 12.5, "metrics verification", utc_now()),
    )
with db_connection() as conn:
    row = conn.execute("SELECT operation, duration_ms FROM performance_metrics ORDER BY id DESC LIMIT 1").fetchone()
assert row["operation"] == "test"
assert row["duration_ms"] == 12.5
print("performance metrics test passed")

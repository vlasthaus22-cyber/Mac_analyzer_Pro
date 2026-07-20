from server import db_connection, init_database, log_action


init_database()
log_action("Test action", "logger verification")
with db_connection() as conn:
    row = conn.execute("SELECT action, details FROM app_logs ORDER BY id DESC LIMIT 1").fetchone()
assert row["action"] == "Test action"
assert row["details"] == "logger verification"
print("app logger test passed")

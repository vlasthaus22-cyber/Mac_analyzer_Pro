import json

from server import db_connection, init_database, utc_now


init_database()
columns = ["macFormatted", "vendor", "ip"]
with db_connection() as conn:
    conn.execute(
        "INSERT OR REPLACE INTO column_preferences (view_name, columns_json, updated_at) VALUES (?, ?, ?)",
        ("results", json.dumps(columns), utc_now()),
    )
with db_connection() as conn:
    row = conn.execute("SELECT columns_json FROM column_preferences WHERE view_name = ?", ("results",)).fetchone()
assert json.loads(row["columns_json"]) == columns
print("column preferences test passed")

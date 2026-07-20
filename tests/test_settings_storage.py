import json

from server import db_connection, init_database, utc_now


init_database()
with db_connection() as conn:
    conn.execute(
        "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("theme", json.dumps("dark"), utc_now()),
    )
with db_connection() as conn:
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", ("theme",)).fetchone()
assert json.loads(row["value"]) == "dark"
print("settings storage test passed")

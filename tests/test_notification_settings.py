import json

from server import db_connection, init_database, utc_now


init_database()
config = {"botToken": "test-token", "chatId": "test-chat"}
with db_connection() as conn:
    conn.execute(
        "INSERT OR REPLACE INTO notification_settings (channel, config_json, enabled, updated_at) VALUES (?, ?, ?, ?)",
        ("telegram", json.dumps(config), 1, utc_now()),
    )
with db_connection() as conn:
    row = conn.execute("SELECT config_json, enabled FROM notification_settings WHERE channel = ?", ("telegram",)).fetchone()
assert json.loads(row["config_json"]) == config
assert row["enabled"] == 1
print("notification settings test passed")

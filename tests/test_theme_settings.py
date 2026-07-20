from server import db_connection, init_database, normalize_theme, save_theme_settings, theme_settings


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM app_settings WHERE key = 'theme'")
        conn.execute("DELETE FROM app_logs WHERE action = 'Theme changed'")


def test_theme_settings_are_validated_and_persisted():
    init_database()
    cleanup()

    assert normalize_theme("dark") == "dark"
    assert normalize_theme("LIGHT") == "light"
    assert normalize_theme("bad-value") == "light"
    current = theme_settings()
    assert current["theme"] == "light"
    assert current["active"]["name"] == "Светлая"
    assert [item["key"] for item in current["themes"]] == ["dark", "light"]
    assert current["themes"][0]["background"] == "#1e1e1e"
    assert current["themes"][1]["accent"] == "#2c6b9e"

    saved = save_theme_settings("dark")
    assert saved["theme"] == "dark"
    assert saved["active"]["name"] == "Темная"
    assert theme_settings()["theme"] == "dark"

    saved = save_theme_settings("bad-value")
    assert saved["theme"] == "light"
    assert theme_settings()["theme"] == "light"

    with db_connection() as conn:
        logs = conn.execute("SELECT COUNT(*) FROM app_logs WHERE action = 'Theme changed'").fetchone()[0]
    assert logs >= 2
    cleanup()


if __name__ == "__main__":
    test_theme_settings_are_validated_and_persisted()
    print("theme settings test passed")

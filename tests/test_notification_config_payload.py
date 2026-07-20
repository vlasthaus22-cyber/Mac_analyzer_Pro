import json

from server import notification_config_from_payload


def test_notification_config_text_and_legacy_payloads():
    channel, config = notification_config_from_payload(
        {"channel": "Telegram", "configText": json.dumps({"botToken": "token", "chatId": "42"})}
    )
    assert channel == "telegram"
    assert config == {"botToken": "token", "chatId": "42"}

    channel, config = notification_config_from_payload({"channel": "slack", "configText": ""})
    assert channel == "slack"
    assert config == {}

    channel, config = notification_config_from_payload({"channel": "email", "smtpHost": "smtp", "to": "ops@example.test"})
    assert channel == "email"
    assert config == {"smtpHost": "smtp", "to": "ops@example.test"}


if __name__ == "__main__":
    test_notification_config_text_and_legacy_payloads()
    print("notification config payload test passed")

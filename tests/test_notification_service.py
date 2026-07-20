from notification_service import build_analysis_event, dispatch_notification_event, validate_notification_config


def test_notification_event_validation_and_dispatch():
    event = build_analysis_event(
        [{"vendor": "Cisco"}, {"vendor": "Unknown"}, {"vendor": "Apple"}],
        invalid=[{"row": 3}],
        source="unit-test.csv",
    )
    assert event["summary"] == {
        "source": "unit-test.csv",
        "devices": 3,
        "invalid": 1,
        "vendors": 3,
        "unknownVendors": 1,
    }
    assert validate_notification_config("email", {"smtpHost": "smtp", "from": "a", "password": "p", "to": "b"}) == []
    assert "telegram.chatId is required" in validate_notification_config("telegram", {"botToken": "token"})
    sent = []

    def sender(channel, config, payload):
        sent.append((channel, config, payload["type"]))

    result = dispatch_notification_event(
        event,
        [
            {"channel": "email", "enabled": True, "config": {"smtpHost": "smtp", "from": "a", "password": "p", "to": "b"}},
            {"channel": "telegram", "enabled": False, "config": {}},
            {"channel": "slack", "enabled": True, "config": {"webhookUrl": "bad-url"}},
        ],
        sender,
    )

    assert result["sent"] == 1
    assert result["skipped"] == 1
    assert result["errors"] == 1
    assert sent == [("email", {"smtpHost": "smtp", "from": "a", "password": "p", "to": "b"}, "analysis_completed")]


if __name__ == "__main__":
    test_notification_event_validation_and_dispatch()
    print("notification service test passed")

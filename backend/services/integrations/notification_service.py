from typing import Any, Callable


SUPPORTED_CHANNELS = {"email", "telegram", "slack"}


def normalize_channel(channel: Any) -> str:
    value = str(channel or "").strip().lower()
    return value if value in SUPPORTED_CHANNELS else ""


def validate_notification_config(channel: str, config: dict[str, Any]) -> list[str]:
    normalized = normalize_channel(channel)
    errors: list[str] = []
    if not normalized:
        return ["Unsupported notification channel"]
    if normalized == "email":
        for field in ("smtpHost", "from", "password", "to"):
            if not str(config.get(field) or "").strip():
                errors.append(f"email.{field} is required")
    elif normalized == "telegram":
        for field in ("botToken", "chatId"):
            if not str(config.get(field) or "").strip():
                errors.append(f"telegram.{field} is required")
    elif normalized == "slack":
        webhook = str(config.get("webhookUrl") or "").strip()
        if not webhook:
            errors.append("slack.webhookUrl is required")
        elif not webhook.startswith("https://hooks.slack.com/"):
            errors.append("slack.webhookUrl must be a Slack incoming webhook")
    return errors


def build_analysis_event(devices: list[dict[str, Any]], invalid: list[Any] | None = None, source: str = "") -> dict[str, Any]:
    invalid = invalid or []
    vendors = {str(device.get("vendor") or "") for device in devices if str(device.get("vendor") or "").strip()}
    unknown = sum(1 for device in devices if str(device.get("vendor") or "").strip() in {"", "Unknown", "Не определено"})
    source_text = str(source or "manual analysis")
    return {
        "type": "analysis_completed",
        "subject": "MAC Analyzer: analysis completed",
        "text": (
            f"Analysis completed for {source_text}. "
            f"Devices: {len(devices)}. Invalid rows: {len(invalid)}. "
            f"Vendors: {len(vendors)}. Unknown vendors: {unknown}."
        ),
        "summary": {
            "source": source_text,
            "devices": len(devices),
            "invalid": len(invalid),
            "vendors": len(vendors),
            "unknownVendors": unknown,
        },
    }


NotificationSender = Callable[[str, dict[str, Any], dict[str, Any]], None]


def dispatch_notification_event(
    event: dict[str, Any],
    channels: list[dict[str, Any]],
    sender: NotificationSender,
) -> dict[str, Any]:
    results = []
    for channel_config in channels:
        channel = normalize_channel(channel_config.get("channel"))
        enabled = bool(channel_config.get("enabled"))
        config = channel_config.get("config") if isinstance(channel_config.get("config"), dict) else {}
        if not enabled:
            results.append({"channel": channel or channel_config.get("channel"), "status": "skipped", "reason": "disabled"})
            continue
        errors = validate_notification_config(channel, config)
        if errors:
            results.append({"channel": channel or channel_config.get("channel"), "status": "error", "errors": errors})
            continue
        try:
            sender(channel, config, event)
        except Exception as error:  # noqa: BLE001
            results.append({"channel": channel, "status": "error", "errors": [str(error)]})
            continue
        results.append({"channel": channel, "status": "sent"})
    return {
        "event": event,
        "results": results,
        "sent": sum(1 for item in results if item["status"] == "sent"),
        "errors": sum(1 for item in results if item["status"] == "error"),
        "skipped": sum(1 for item in results if item["status"] == "skipped"),
    }

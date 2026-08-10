import html
from datetime import datetime
from typing import Any


def normalize_mac(value: Any) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch in "0123456789ABCDEF")


def format_mac(value: Any) -> str:
    clean = normalize_mac(value)
    if len(clean) == 12:
        return ":".join(clean[index:index + 2] for index in range(0, 12, 2))
    return str(value or "")


def _text(value: Any, fallback: str = "") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def _display_datetime(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%d.%m.%Y, %H:%M:%S")
    except ValueError:
        return text


DEVICE_FIELD_LABELS = {
    "vendor": "Производитель",
    "vendorSource": "Источник вендора",
    "vendorConfidence": "Уверенность вендора",
    "model": "Модель",
    "modelSource": "Источник модели",
    "modelConfidence": "Уверенность модели",
    "ip": "IP",
    "address": "Адрес",
    "room": "Помещение",
    "smartroomId": "Smartroom ID",
    "switchIp": "IP коммутатора",
    "switchPort": "Порт",
    "source": "Источник",
}


def device_metrics_html(metrics: dict[str, Any]) -> str:
    items = [
        ("Снимков", metrics.get("appearances")),
        ("Источников", metrics.get("sources")),
        ("Истории", metrics.get("historyRecords")),
        ("Перемещений", metrics.get("movements")),
    ]
    return "".join(
        f'<article class="metric"><span>{html.escape(label)}</span><strong>{html.escape(str(value or 0))}</strong></article>'
        for label, value in items
    )


def chronology_summary_html(metrics: dict[str, Any]) -> str:
    items = [
        ("History records", metrics.get("historyRecords")),
        ("Field changes", metrics.get("movements")),
        ("Snapshot appearances", metrics.get("appearances")),
        ("Chronology events", metrics.get("chronologyEvents")),
    ]
    return "".join(
        '<div class="bar-label">'
        f'<span>{html.escape(label)}</span>'
        f'<strong>{html.escape(str(value or 0))}</strong>'
        '</div>'
        for label, value in items
    )


def mac_history_stats_html(stats: dict[str, Any]) -> str:
    items = [
        ("Всего появлений", stats.get("totalAppearances")),
        ("Первое появление", _display_datetime(stats.get("firstSeen")) or "-"),
        ("Последнее появление", _display_datetime(stats.get("lastSeen")) or "-"),
        ("Файлов", stats.get("uniqueFiles")),
        ("Изменений", stats.get("totalMovements")),
    ]
    return "".join(
        '<div class="bar-label">'
        f'<span>{html.escape(label)}</span><strong>{html.escape(str(value if value is not None else 0))}</strong>'
        '</div>'
        for label, value in items
    )


def _source_name(value: Any) -> str:
    text = _text(value)
    return text.replace("\\", "/").rsplit("/", 1)[-1] if text else "-"


def _history_value(item: dict[str, Any], field: str) -> str:
    aliases = {
        "smartroomId": ("smartroomId", "smartroom_id"),
        "switchIp": ("switchIp", "switch_ip"),
        "switchPort": ("switchPort", "switch_port"),
    }
    return next((_text(item.get(key)) for key in aliases.get(field, (field,)) if _text(item.get(key))), "")


def _snapshot_device_with_history(
    device: dict[str, Any],
    snapshot: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fill persistence gaps from the history row belonging to this final export."""
    result = dict(device)
    snapshot_source = _source_name(snapshot.get("source") or device.get("source"))
    snapshot_date = _text(snapshot.get("createdAt") or snapshot.get("created_at"))

    def score(item: dict[str, Any]) -> tuple[int, float]:
        source_match = _source_name(item.get("source") or item.get("source_file")) == snapshot_source
        recorded = _text(item.get("recorded_at") or item.get("recordedAt"))
        distance = float("inf")
        try:
            left = datetime.fromisoformat(snapshot_date.replace("Z", "+00:00"))
            right = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
            distance = abs((left - right).total_seconds())
        except (ValueError, TypeError):
            pass
        return (0 if source_match else 1, distance)

    candidates = [item for item in history if isinstance(item, dict)]
    if not candidates:
        return result
    evidence = min(candidates, key=score)
    evidence_score = score(evidence)
    if evidence_score[0] and evidence_score[1] > 300:
        return result
    for field in ("vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort"):
        if not _text(result.get(field)):
            value = _history_value(evidence, field)
            if value:
                result[field] = value
    return result


def device_fields_html(device: dict[str, Any], model_prefixes: list[dict[str, Any]]) -> str:
    fields = [
        "vendor", "vendorSource", "vendorConfidence", "model", "modelSource", "modelConfidence",
        "ip", "address", "room", "smartroomId", "switchIp", "switchPort", "source",
    ]
    rows = "".join(
        '<div class="device-field">'
        f'<span>{html.escape(DEVICE_FIELD_LABELS.get(field, field))}</span>'
        f'<strong>{html.escape(_text(device.get(field), "-"))}</strong>'
        '</div>'
        for field in fields
    )
    if model_prefixes:
        rows += (
            '<div class="device-field"><span>Префиксы модели</span>'
            f'<strong>{html.escape(", ".join(_text(item.get("prefix")) for item in model_prefixes if _text(item.get("prefix"))))}</strong></div>'
        )
    return rows


def device_detailed_report(mac: str, device: dict[str, Any]) -> str:
    """Port of SingleDeviceAnalyticsDialog.generate_report."""
    def value(default: str, *keys: str) -> str:
        for key in keys:
            if key in device:
                return _text(device.get(key), default)
        return default

    mac_value = value(format_mac(mac), "macFormatted", "mac_formatted", "mac")
    return "\n".join([
        "=== ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ОБ УСТРОЙСТВЕ ===",
        "",
        f"MAC-адрес: {mac_value}",
        f"Производитель: {value('Unknown', 'vendor')}",
        f"Модель: {value('Не указана', 'model')}",
        f"IP-адрес: {value('Не указан', 'ip')}",
        f"Физический адрес: {value('Не указан', 'address')}",
        f"Помещение: {value('Не указано', 'room')}",
        f"Smartroom ID: {value('Не указан', 'smartroomId', 'smartroom_id')}",
        f"Коммутатор: {value('Не указан', 'switchIp', 'switch_ip')}",
        f"Порт: {value('Не указан', 'switchPort', 'switch_port')}",
        "",
        "Источники данных:",
        f"  Производитель: {value('Неизвестен', 'vendorSource', 'vendor_source')}",
        f"  Модель: {value('Неизвестен', 'modelSource', 'model_source')}",
        "",
        f"Примечания: {value('Нет', 'matchDetails', 'match_details')}",
    ])


def build_device_analytics(
    mac: str,
    devices: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    history: list[dict[str, Any]] | None = None,
    movements: list[dict[str, Any]] | None = None,
    model_mappings: dict[str, str] | None = None,
) -> dict[str, Any]:
    normalized = normalize_mac(mac)
    history = history or []
    movements = movements or []
    model_mappings = model_mappings or {}
    current = next((device for device in devices if normalize_mac(device.get("mac") or device.get("macFormatted")) == normalized), {})
    appearances = []
    for snapshot in snapshots:
        snapshot_devices = snapshot.get("devices", [])
        if not isinstance(snapshot_devices, list):
            continue
        matches = [device for device in snapshot_devices if normalize_mac(device.get("mac") or device.get("macFormatted")) == normalized]
        for match in matches:
            historical_device = _snapshot_device_with_history(match, snapshot, history)
            appearances.append({
                "snapshotId": snapshot.get("id", ""),
                "snapshotName": snapshot.get("name", ""),
                "source": snapshot.get("source") or historical_device.get("source", ""),
                "createdAt": snapshot.get("createdAt") or snapshot.get("created_at", ""),
                "device": historical_device,
            })
    sources = sorted({_text(item.get("source")) for item in appearances if _text(item.get("source"))})
    rooms = sorted({_text((item.get("device") or {}).get("room")) for item in appearances if _text((item.get("device") or {}).get("room"))})
    switches = sorted({_text((item.get("device") or {}).get("switchIp") or (item.get("device") or {}).get("switch_ip")) for item in appearances if _text((item.get("device") or {}).get("switchIp") or (item.get("device") or {}).get("switch_ip"))})

    model = _text(current.get("model"))
    matching_prefixes = [
        {"prefix": prefix, "model": value, "matchesDevice": bool(normalized and normalized.startswith(prefix))}
        for prefix, value in sorted(model_mappings.items(), key=lambda item: (-len(item[0]), item[0]))
        if not model or value == model or (normalized and normalized.startswith(prefix))
    ]
    recent_history = sorted(history, key=lambda item: _text(item.get("recorded_at")), reverse=True)[:20]
    recent_movements = sorted(movements, key=lambda item: _text(item.get("changed_at")), reverse=True)[:20]
    history_records_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(_display_datetime(item.get('recorded_at')))}</td>"
        f"<td>{html.escape(_source_name(item.get('source') or item.get('source_file')))}</td>"
        f"<td>{html.escape(_text(item.get('vendor'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('model'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('ip'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('address'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('room'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('smartroomId') or item.get('smartroom_id'), '-'))}</td>"
        "</tr>"
        for item in recent_history
    )

    def movement_ddio_badge(item: dict[str, Any]) -> str:
        candidate_ip = _text(item.get("ddio_candidate_ip"))
        if not candidate_ip:
            return ""
        match_label = "резервация" if _text(item.get("ddio_match")) == "reservation" else "аренда"
        title = (
            f"DDIO: возможный новый IP устройства {candidate_ip} ({match_label}). "
            "Подсказка показана из-за смены IP коммутатора; основные данные не изменены."
        )
        safe_title = html.escape(title, quote=True)
        return f' <span class="ddio-history-warning" title="{safe_title}" aria-label="{safe_title}">?</span>'

    movement_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(_display_datetime(item.get('changed_at')))}</td>"
        f"<td>{html.escape(_text(item.get('field_name'), '-'))}{movement_ddio_badge(item)}</td>"
        f"<td>{html.escape(_text(item.get('from_value'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('to_value'), '-'))}</td>"
        f"<td>{html.escape(_source_name(item.get('source') or item.get('source_file')))}</td>"
        "</tr>"
        for item in recent_movements
    )
    timeline_rows = sorted(
        [
            {
                "type": "movement",
                "event": "Изменение поля",
                "date": item.get("changed_at", ""),
                "field": item.get("field_name", ""),
                "before": item.get("from_value", ""),
                "after": item.get("to_value", ""),
                "source": item.get("source") or "SQLite",
            }
            for item in recent_movements
        ]
        + [
            {
                "type": "history",
                "event": "Запись истории",
                "date": item.get("recorded_at", ""),
                "field": "history",
                "before": "",
                "after": " / ".join(filter(None, [item.get("vendor"), item.get("model"), item.get("ip"), item.get("address")])) or item.get("source") or "",
                "source": item.get("source") or "SQLite",
            }
            for item in recent_history
        ]
        + [
            {
                "type": "snapshot",
                "event": "Появление в снимке",
                "date": item.get("createdAt", ""),
                "field": "snapshot",
                "before": "",
                "after": item.get("source") or "",
                "source": item.get("snapshotName") or item.get("source") or "snapshot",
            }
            for item in appearances
        ],
        key=lambda item: _text(item.get("date")),
        reverse=True,
    )
    history_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(_display_datetime(item.get('date')))}</td>"
        f"<td>{html.escape(_text(item.get('field')))}</td>"
        f"<td>{html.escape(_text(item.get('before'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('after'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('source'), '-'))}</td>"
        "</tr>"
        for item in timeline_rows
    )
    chronology_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(_display_datetime(item.get('date')))}</td>"
        f"<td>{html.escape(_text(item.get('event')))}</td>"
        f"<td>{html.escape(_text(item.get('field')))}</td>"
        f"<td>{html.escape(_text(item.get('before'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('after'), '-'))}</td>"
        f"<td>{html.escape(_text(item.get('source'), '-'))}</td>"
        "</tr>"
        for item in timeline_rows
    )
    metrics = {
        "appearances": len(appearances),
        "sources": len(sources),
        "historyRecords": len(history),
        "movements": len(movements),
        "rooms": len(rooms),
        "switches": len(switches),
        "modelPrefixes": len(matching_prefixes),
        "chronologyEvents": len(timeline_rows),
    }
    history_dates = sorted(_text(item.get("recorded_at")) for item in history if _text(item.get("recorded_at")))
    history_sources = {
        _text(item.get("source") or item.get("source_file"))
        for item in history
        if _text(item.get("source") or item.get("source_file"))
    }
    history_stats = {
        "totalAppearances": len(history),
        "firstSeen": history_dates[0] if history_dates else "",
        "lastSeen": history_dates[-1] if history_dates else "",
        "uniqueFiles": len(history_sources),
        "totalMovements": len(movements),
    }
    return {
        "mac": normalized,
        "macFormatted": _text(current.get("macFormatted") or current.get("mac") or normalized),
        "current": current,
        "metrics": metrics,
        "metricsHtml": device_metrics_html(metrics),
        "fieldsHtml": device_fields_html(current, matching_prefixes),
        "detailedReportText": device_detailed_report(normalized, current),
        "appearances": appearances,
        "sources": sources,
        "rooms": rooms,
        "switches": switches,
        "history": recent_history,
        "movements": recent_movements,
        "timelineRows": timeline_rows,
        "chronology": timeline_rows,
        "chronologyRowsHtml": chronology_rows_html,
        "chronologySummaryHtml": chronology_summary_html(metrics),
        "historyRowsHtml": history_rows_html,
        "emptyHistoryRowsHtml": '<tr><td colspan="5" class="empty-state">История устройства пока пуста.</td></tr>',
        "historyStats": history_stats,
        "macHistoryStatsHtml": mac_history_stats_html(history_stats),
        "historyRecordsRowsHtml": history_records_rows_html,
        "emptyHistoryRecordsRowsHtml": '<tr><td colspan="7" class="empty-state">История появлений MAC пока пуста.</td></tr>',
        "movementRowsHtml": movement_rows_html,
        "emptyMovementRowsHtml": '<tr><td colspan="5" class="empty-state">Изменения параметров MAC пока отсутствуют.</td></tr>',
        "emptyChronologyRowsHtml": '<tr><td colspan="6" class="empty-state">MAC chronology is empty.</td></tr>',
        "modelPrefixes": matching_prefixes,
    }


def _format_model_prefix(prefix: Any) -> str:
    normalized = normalize_mac(prefix)
    return ":".join(normalized[index:index + 2] for index in range(0, len(normalized), 2))


def _model_source_label(source: Any) -> str:
    value = _text(source).lower()
    return {
        "builtin": "Встроенная база",
        "custom": "Пользовательское правило",
        "learned": "Обучение по истории",
        "history": "История обогащений",
        "legacy": "Импорт Python-базы",
    }.get(value, _text(source) or "SQLite")


def build_model_analytics(
    model: str,
    model_mappings: dict[str, str],
    devices: list[dict[str, Any]] | None = None,
    model_sources: dict[str, str] | None = None,
) -> dict[str, Any]:
    model_name = _text(model)
    query = model_name.casefold()
    model_sources = model_sources or {}
    prefixes = [
        {
            "prefix": prefix,
            "formattedPrefix": _format_model_prefix(prefix),
            "model": value,
            "source": _text(model_sources.get(prefix)) or "SQLite",
            "sourceLabel": _model_source_label(model_sources.get(prefix)),
            "sampleMac": (prefix + "0" * 12)[:12],
        }
        for prefix, value in sorted(model_mappings.items(), key=lambda item: (item[1], item[0]))
        if query and (value.casefold() == query or query in value.casefold())
    ]
    matched_devices = []
    for device in devices or []:
        mac = normalize_mac(device.get("mac") or device.get("macFormatted"))
        if device.get("model") == model_name or any(mac.startswith(item["prefix"]) for item in prefixes):
            matched_devices.append(device)
    prefix_rows_html = "".join(
        '<div class="mapping-row">'
        f"<strong>{html.escape(_text(item.get('prefix')))}</strong>"
        f"<span>{html.escape(format_mac(item.get('sampleMac')))}</span>"
        "</div>"
        for item in prefixes
    )
    if not prefix_rows_html:
        prefix_rows_html = '<p class="muted">Префиксы модели не найдены.</p>'
    table_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(_text(item.get('formattedPrefix')))}</td>"
        f"<td>{html.escape(_text(item.get('model')))}</td>"
        f"<td>{html.escape(_text(item.get('sourceLabel')))}</td>"
        "</tr>"
        for item in prefixes
    )
    if not table_rows_html:
        table_rows_html = '<tr><td>Нет данных</td><td></td><td></td></tr>'
    summary_row_html = (
        '<div class="mapping-row"><span><strong>Устройств</strong>'
        f"<small>{len(matched_devices)} найдено в текущем наборе</small></span></div>"
    )
    return {
        "model": model_name,
        "prefixes": prefixes,
        "metrics": {
            "prefixes": len(prefixes),
            "matchedDevices": len(matched_devices),
            "vendors": len({_text(device.get("vendor")) for device in matched_devices if _text(device.get("vendor"))}),
        },
        "prefixRowsHtml": prefix_rows_html,
        "tableRowsHtml": table_rows_html,
        "summaryRowHtml": summary_row_html,
        "dialogRowsHtml": prefix_rows_html + summary_row_html,
        "devices": matched_devices[:100],
    }


def export_device_analytics_html(payload: dict[str, Any]) -> dict[str, str]:
    metrics = payload.get("metrics", {})
    metric_html = "".join(f"<li>{html.escape(str(key))}: {html.escape(str(value))}</li>" for key, value in metrics.items())
    movement_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('changed_at', '')))}</td>"
        f"<td>{html.escape(str(item.get('field_name', '')))}</td>"
        f"<td>{html.escape(str(item.get('from_value', '')))}</td>"
        f"<td>{html.escape(str(item.get('to_value', '')))}</td>"
        "</tr>"
        for item in payload.get("movements", [])
    )
    chronology_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('date', '')))}</td>"
        f"<td>{html.escape(str(item.get('event', '')))}</td>"
        f"<td>{html.escape(str(item.get('field', '')))}</td>"
        f"<td>{html.escape(str(item.get('before', '')))}</td>"
        f"<td>{html.escape(str(item.get('after', '')))}</td>"
        f"<td>{html.escape(str(item.get('source', '')))}</td>"
        "</tr>"
        for item in payload.get("chronology", payload.get("timelineRows", []))
    )
    content = (
        '<!doctype html><html><head><meta charset="utf-8"><title>MAC Device Analytics</title>'
        "<style>body{font:14px Arial;margin:32px}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #bbb;padding:7px;text-align:left}th{background:#eee}</style></head><body>"
        f"<h1>{html.escape(str(payload.get('macFormatted') or payload.get('mac')))}</h1>"
        f"<p>Created: {html.escape(datetime.utcnow().isoformat(timespec='seconds'))}Z</p>"
        f"<h2>Detailed device report</h2><pre>{html.escape(_text(payload.get('detailedReportText'), 'Нет данных'))}</pre>"
        f"<h2>Metrics</h2><ul>{metric_html}</ul>"
        f"<h2>MAC chronology</h2><table><thead><tr><th>Date</th><th>Event</th><th>Field</th><th>Before</th><th>After</th><th>Source</th></tr></thead><tbody>{chronology_rows}</tbody></table>"
        f"<h2>Movements</h2><table><thead><tr><th>Date</th><th>Field</th><th>Before</th><th>After</th></tr></thead><tbody>{movement_rows}</tbody></table>"
        "</body></html>"
    )
    return {"filename": "mac-device-analytics.html", "mimeType": "text/html", "content": content}

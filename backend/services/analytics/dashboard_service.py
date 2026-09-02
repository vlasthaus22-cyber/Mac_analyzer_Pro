import html
import base64
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from backend.services.identity.device_identity_service import identity_key, pair_device_sets

from .chart_service import build_chart_payload


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_dashboard_settings(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = settings or {}
    status = _text(settings.get("status")).lower()
    if status not in {"all", "changed", "missing", "unchanged"}:
        status = "all"
    card_settings = settings.get("visibleCards") if isinstance(settings.get("visibleCards"), dict) else {}
    chart_settings = settings.get("visibleCharts") if isinstance(settings.get("visibleCharts"), dict) else {}
    try:
        refresh_interval = int(settings.get("refreshInterval") or 60)
    except (TypeError, ValueError):
        refresh_interval = 60
    change_mode = _text(settings.get("changeMode")).lower()
    if change_mode not in {"period", "snapshots"}:
        change_mode = "snapshots"
    return {
        "query": _text(settings.get("query")),
        "vendor": _text(settings.get("vendor")),
        "room": _text(settings.get("room")),
        "status": status,
        "chartLimit": max(1, min(int(settings.get("chartLimit") or 8), 25)),
        "showUnknown": bool(settings.get("showUnknown", True)),
        "visibleCards": {
            key: bool(card_settings.get(key, True))
            for key in ("total", "changed", "missing", "unchanged", "vendors", "rooms", "changedRooms")
        },
        "visibleCharts": {
            key: bool(chart_settings.get(key, True))
            for key in ("dynamics", "vendors", "fields", "missing")
        },
        "autoRefresh": bool(settings.get("autoRefresh", True)),
        "refreshInterval": max(10, min(refresh_interval, 300)),
        "changeMode": change_mode,
        "changeDateFrom": _text(settings.get("changeDateFrom")),
        "changeDateTo": _text(settings.get("changeDateTo")),
        "baselineSnapshotId": _text(settings.get("baselineSnapshotId")),
        "comparisonSnapshotId": _text(settings.get("comparisonSnapshotId")),
    }


CHANGE_FIELDS = ("mac", "vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort", "hostname", "serialNumber", "deviceId", "deviceName")
CHANGE_FIELD_LABELS = {
    "vendor": "Производитель", "model": "Модель", "ip": "IP-адрес", "address": "Адрес",
    "room": "Помещение", "smartroomId": "Smartroom ID", "switchIp": "IP коммутатора", "switchPort": "Порт", "device": "Устройство",
    "mac": "MAC / физический адрес", "hostname": "Hostname", "serialNumber": "Серийный номер",
    "deviceId": "ID устройства", "deviceName": "Название устройства", "identityConflict": "Конфликт идентификации",
}
CHANGE_FIELD_ALIASES = {
    **{key.casefold(): key for key in CHANGE_FIELD_LABELS},
    **{label.casefold(): key for key, label in CHANGE_FIELD_LABELS.items()},
    "switch_ip": "switchIp", "switch_port": "switchPort", "smartroom_id": "smartroomId",
    "ip": "ip", "ip адрес": "ip", "ip-адрес": "ip", "коммутатор": "switchIp",
    "-": "device",
}
CHANGE_TYPE_ALIASES = {
    "added": "added", "добавлено": "added",
    "removed": "removed", "удалено": "removed", "отсутствует": "removed",
    "modified": "modified", "изменено": "modified",
}


def _normalize_change_field(value: Any) -> str:
    field = _text(value) or "device"
    return CHANGE_FIELD_ALIASES.get(field.casefold(), field)


def _parse_date(value: Any, *, end_of_day: bool = False) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        if len(text) == 10 and end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed
    except ValueError:
        return None


def _snapshot_id(snapshot: dict[str, Any], index: int) -> str:
    return _text(snapshot.get("id") or snapshot.get("snapshotId") or snapshot.get("name") or f"snapshot-{index + 1}")


def dashboard_snapshot_options(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    options = []
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            continue
        snapshot_id = _snapshot_id(snapshot, index)
        date = _text(snapshot.get("fileCreatedAt") or snapshot.get("createdAt") or snapshot.get("created_at") or snapshot.get("savedAt"))
        options.append({
            "id": snapshot_id,
            "name": _text(snapshot.get("name") or snapshot_id),
            "date": date,
            "order": snapshot.get("snapshotOrder") or snapshot.get("snapshot_order") or 0,
        })
    options.sort(key=lambda item: (int(item.get("order") or 0), item.get("date", ""), item["id"]))
    return options


def dashboard_upload_fleet(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    unique_macs: set[str] = set()
    series: list[dict[str, Any]] = []
    usable = [
        snapshot for snapshot in snapshots
        if isinstance(snapshot, dict)
        and (
            _text(snapshot.get("kind")).lower() == "analysis"
            or _text(snapshot.get("name")).lower().startswith("анализ:")
        )
    ]
    selected = usable if usable else [snapshot for snapshot in snapshots if isinstance(snapshot, dict)]
    for index, snapshot in enumerate(selected):
        current = {
            _mac(device) for device in snapshot.get("devices", [])
            if isinstance(device, dict) and _mac(device)
        }
        unique_macs.update(current)
        count = int(snapshot.get("deviceCount") or len(current))
        series.append({
            "id": _snapshot_id(snapshot, index),
            "name": _text(snapshot.get("name") or f"Выгрузка {index + 1}"),
            "date": _text(snapshot.get("fileCreatedAt") or snapshot.get("createdAt") or snapshot.get("created_at")),
            "count": count,
            "delta": count - int(series[-1]["count"]) if series else 0,
        })
    latest_count = int(series[-1]["count"]) if series else 0
    return {
        "uniqueAcrossUploads": max(len(unique_macs), latest_count),
        "latestCount": latest_count,
        "series": series,
    }


def _change_severity(
    change_type: str,
    field: str,
    before_device: dict[str, Any] | None = None,
    after_device: dict[str, Any] | None = None,
    before_value: Any = "",
    after_value: Any = "",
) -> str:
    previous = _device_context(before_device)
    current = _device_context(after_device)
    old_value = _text((previous or {}).get(field) if previous and field in previous else before_value)
    new_value = _text((current or {}).get(field) if current and field in current else after_value)
    if field in {"switchIp", "ip"} and old_value and new_value and old_value != new_value:
        return "critical"
    if field in {"mac", "identityConflict"}:
        return "critical"
    if field in {"ip", "address", "room"}:
        return "high"
    if field in {"vendor", "model", "smartroomId", "switchIp", "switchPort"}:
        return "medium"
    if change_type == "removed":
        return "high"
    return "low"


def _device_context(device: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(device, dict):
        return None
    return {
        "mac": _mac(device),
        "vendor": _text(device.get("vendor")),
        "model": _text(device.get("model")),
        "ip": _text(device.get("ip")),
        "address": _text(device.get("address")),
        "room": _text(device.get("room")),
        "smartroomId": _text(device.get("smartroomId") or device.get("smartroom_id")),
        "switchIp": _text(device.get("switchIp") or device.get("switch_ip")),
        "switchPort": _text(device.get("switchPort") or device.get("switch_port")),
        "hostname": _text(device.get("hostname") or device.get("host_name")),
        "serialNumber": _text(device.get("serialNumber") or device.get("serial_number") or device.get("serial")),
        "deviceId": _text(device.get("deviceId") or device.get("device_id")),
        "deviceName": _text(device.get("deviceName") or device.get("device_name") or device.get("name")),
        "source": _text(device.get("source")),
        "ipSource": _text(device.get("ipSource") or (device.get("fieldSources") or {}).get("ip")),
        "possibleIps": list(device.get("possibleIps") or []),
        "hasConflict": bool(device.get("hasConflict")),
        "conflicts": list(device.get("conflicts") or []),
    }


def _device_identity(device: dict[str, Any] | None, mac: str = "") -> str:
    return identity_key(device or {}) or ("mac:" + (_mac(device or {}) or mac) if (_mac(device or {}) or mac) else "")


def _change_row(
    *, mac: str, changed_at: str, change_type: str, field: str = "device",
    before: Any = "", after: Any = "", source: str = "history",
    before_device: dict[str, Any] | None = None, after_device: dict[str, Any] | None = None,
) -> dict[str, Any]:
    labels = {"added": "Добавлено", "removed": "Удалено", "modified": "Изменено"}
    normalized_field = _normalize_change_field(field)
    previous = _device_context(before_device)
    current = _device_context(after_device)
    result = {
        "mac": mac, "macFormatted": ":".join(mac[index:index + 2] for index in range(0, 12, 2)) if len(mac) == 12 else mac,
        "identity": _device_identity(current or previous, mac),
        "date": changed_at, "type": change_type, "typeLabel": labels.get(change_type, "Изменено"),
        "field": normalized_field, "fieldLabel": CHANGE_FIELD_LABELS.get(normalized_field, normalized_field),
        "before": _text(before) or "-", "after": _text(after) or "-", "source": source,
        "severity": _change_severity(change_type, normalized_field, previous, current, before, after),
        "beforeDevice": previous, "afterDevice": current,
    }
    if normalized_field == "switchIp" and current:
        possible_ips = list(current.get("possibleIps") or [])
        device_ip = _text(current.get("ip"))
        if device_ip and device_ip not in possible_ips:
            possible_ips.append(device_ip)
        if possible_ips:
            result["ddioCandidateIp"] = possible_ips[0]
            result["possibleDdioIps"] = possible_ips
            result["ddioMatch"] = "device"
            result["valueSource"] = _text(current.get("ipSource") or "DDIO")
    return result


def analyze_dashboard_changes(
    snapshots: list[dict[str, Any]], movements: list[dict[str, Any]], settings: dict[str, Any],
    snapshot_options: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized = normalize_dashboard_settings(settings)
    options = dashboard_snapshot_options(snapshot_options if snapshot_options is not None else snapshots)
    changes: list[dict[str, Any]] = []
    selected_from = normalized["changeDateFrom"]
    selected_to = normalized["changeDateTo"]
    baseline_id = normalized["baselineSnapshotId"]
    comparison_id = normalized["comparisonSnapshotId"]
    baseline_date = ""
    comparison_date = ""
    skipped_invalid_dates = 0

    if len(snapshots) >= 2:
        baseline_id = baseline_id or options[-2]["id"]
        comparison_id = comparison_id or options[-1]["id"]
        indexed = {_snapshot_id(snapshot, index): snapshot for index, snapshot in enumerate(snapshots) if isinstance(snapshot, dict)}
        baseline = indexed.get(baseline_id) or indexed.get(options[-2]["id"]) or snapshots[-2]
        comparison = indexed.get(comparison_id) or indexed.get(options[-1]["id"]) or snapshots[-1]
        baseline_date = _text(baseline.get("fileCreatedAt") or baseline.get("createdAt") or baseline.get("created_at") or baseline.get("savedAt"))
        comparison_date = _text(comparison.get("fileCreatedAt") or comparison.get("createdAt") or comparison.get("created_at") or comparison.get("savedAt"))
        if normalized["changeMode"] == "period":
            selected_from = selected_from or (_parse_date(baseline_date) or datetime.now()).date().isoformat()
            selected_to = selected_to or (_parse_date(comparison_date) or datetime.now()).date().isoformat()
        baseline_devices = [device for device in baseline.get("devices", []) if isinstance(device, dict)]
        comparison_devices = [device for device in comparison.get("devices", []) if isinstance(device, dict)]
        pairs, added_devices, removed_devices = pair_device_sets(baseline_devices, comparison_devices)
        changed_at = _text(comparison.get("fileCreatedAt") or comparison.get("createdAt") or comparison.get("created_at"))
        for device in added_devices:
            mac = _mac(device)
            changes.append(_change_row(
                mac=mac, changed_at=changed_at, change_type="added",
                after=device.get("source") or "Устройство", source="snapshot",
                after_device=device,
            ))
        for device in removed_devices:
            mac = _mac(device)
            changes.append(_change_row(
                mac=mac, changed_at=changed_at, change_type="removed",
                before=device.get("source") or "Устройство", source="snapshot",
                before_device=device,
            ))
        for before_device, after_device in pairs:
            mac = _mac(after_device) or _mac(before_device)
            for field in CHANGE_FIELDS:
                before = _mac(before_device) if field == "mac" else before_device.get(field)
                after = _mac(after_device) if field == "mac" else after_device.get(field)
                if _text(before) and not _text(after):
                    continue
                if _text(before) != _text(after):
                    changes.append(_change_row(
                        mac=mac, changed_at=changed_at, change_type="modified", field=field,
                        before=before, after=after, source="snapshot",
                        before_device=before_device, after_device=after_device,
                    ))
            if after_device.get("hasConflict"):
                conflicts = after_device.get("conflicts") if isinstance(after_device.get("conflicts"), list) else []
                changes.append(_change_row(
                    mac=mac, changed_at=changed_at, change_type="modified", field="identityConflict",
                    before="-", after="; ".join(_text(item.get("field")) for item in conflicts if isinstance(item, dict)) or "Обнаружен конфликт",
                    source="snapshot", before_device=before_device, after_device=after_device,
                ))
    else:
        movement_dates = [
            _parse_date(_movement_value(item, "changedAt", "changed_at") or _text(item.get("date_str")))
            for item in movements
            if isinstance(item, dict)
        ]
        latest_movement = max((value for value in movement_dates if value is not None), default=None)
        # A stored dashboard must stay reproducible: an omitted period is relative
        # to the newest supplied event, not to the wall clock at viewing time.
        date_to = _parse_date(selected_to, end_of_day=True) or latest_movement or datetime.now()
        date_from = _parse_date(selected_from) or (date_to - timedelta(days=30))
        if date_from > date_to:
            date_from, date_to = date_to.replace(hour=0, minute=0, second=0, microsecond=0), date_from.replace(hour=23, minute=59, second=59, microsecond=999999)
        selected_from = selected_from or date_from.date().isoformat()
        selected_to = selected_to or date_to.date().isoformat()
        if selected_from > selected_to:
            selected_from, selected_to = selected_to, selected_from
        for movement in movements:
            if not isinstance(movement, dict) or not _mac(movement):
                continue
            changed_at = _movement_value(movement, "changedAt", "changed_at") or _text(movement.get("date_str"))
            parsed = _parse_date(changed_at)
            if parsed is None:
                skipped_invalid_dates += 1
                continue
            if not date_from <= parsed <= date_to:
                continue
            field = _movement_value(movement, "field", "field_name") or "device"
            before = movement.get("before", movement.get("from_value", movement.get("old_value", "")))
            after = movement.get("after", movement.get("to_value", movement.get("new_value", "")))
            change_type = CHANGE_TYPE_ALIASES.get(
                _text(movement.get("type") or movement.get("change_type") or "modified").casefold(),
                "modified",
            )
            if change_type == "modified" and _text(before) and not _text(after):
                # A temporarily absent value is not proof of a real change.
                continue
            context = _movement_device_context(movement)
            before_device = {**context, _normalize_change_field(field): before} if context else None
            after_device = {**context, _normalize_change_field(field): after} if context else None
            changes.append(_change_row(
                mac=_mac(movement), changed_at=changed_at, change_type=change_type, field=field,
                before=before, after=after,
                source=_text(movement.get("source") or movement.get("file_name") or "history"),
                before_device=before_device, after_device=after_device,
            ))

    period_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in changes:
        period_groups.setdefault((item.get("identity") or item["mac"], item["date"], item["source"]), []).append(item)
    for grouped_changes in period_groups.values():
        fields = {item["field"] for item in grouped_changes}
        inferred_critical = "switchIp" in fields and not ({"ip", "room"} & fields)
        if inferred_critical and not any(item.get("beforeDevice") or item.get("afterDevice") for item in grouped_changes):
            for item in grouped_changes:
                if item["field"] == "switchIp":
                    item["severity"] = "critical"

    changes.sort(key=lambda item: item.get("date", ""), reverse=True)
    summary = {
        key: len({item.get("identity") or item["mac"] for item in changes if item["type"] == key})
        for key in ("added", "removed", "modified")
    }
    summary["critical"] = len({item.get("identity") or item["mac"] for item in changes if item["severity"] == "critical"})
    summary["total"] = len({item.get("identity") or item["mac"] for item in changes})
    changed_rooms = {
        _text((item.get("afterDevice") or item.get("beforeDevice") or {}).get("room"))
        for item in changes
        if _text((item.get("afterDevice") or item.get("beforeDevice") or {}).get("room"))
    }
    summary["changedRooms"] = len(changed_rooms)
    summary["changedRoomValues"] = sorted(changed_rooms)
    field_counts = Counter(item["fieldLabel"] for item in changes)
    baseline_time = _parse_date(baseline_date)
    comparison_time = _parse_date(comparison_date)
    if normalized["changeMode"] == "period":
        baseline_time = _parse_date(selected_from)
        comparison_time = _parse_date(selected_to, end_of_day=True)
    duration_ms = max(0, int((comparison_time - baseline_time).total_seconds() * 1000)) if baseline_time and comparison_time else 0
    return {
        "mode": normalized["changeMode"], "dateFrom": selected_from, "dateTo": selected_to,
        "baselineSnapshotId": baseline_id, "comparisonSnapshotId": comparison_id,
        "baselineDate": baseline_date, "comparisonDate": comparison_date,
        "durationMs": duration_ms, "durationSeconds": duration_ms // 1000,
        "snapshotOptions": options, "summary": summary, "changes": changes,
        "fieldChanges": len(changes),
        "skippedInvalidDates": skipped_invalid_dates,
        "fieldCounts": [{"label": label, "value": value} for label, value in field_counts.most_common(12)],
    }


def filter_dashboard_devices(devices: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = normalize_dashboard_settings(settings)
    result = []
    query = normalized["query"].casefold()
    for device in devices:
        if not isinstance(device, dict):
            continue
        vendor = _text(device.get("vendor"))
        room = _text(device.get("room"))
        if normalized["vendor"] and vendor != normalized["vendor"]:
            continue
        if normalized["room"] and room != normalized["room"]:
            continue
        if not normalized["showUnknown"] and (not vendor or vendor == "Unknown"):
            continue
        if query:
            searchable = " ".join(_text(device.get(key)) for key in (
                "mac", "macFormatted", "mac_formatted", "vendor", "model", "ip", "address",
                "room", "smartroomId", "smartroom_id", "switchIp", "switch_ip", "switchPort",
                "switch_port", "source",
            )).casefold()
            normalized_query_mac = re.sub(r"[^0-9A-F]", "", normalized["query"].upper())
            normalized_device_mac = _mac(device)
            if query not in searchable and (not normalized_query_mac or normalized_query_mac not in normalized_device_mac):
                continue
        result.append(device)
    return result


def _mac(device_or_value: Any) -> str:
    if isinstance(device_or_value, dict):
        device_or_value = device_or_value.get("mac") or device_or_value.get("macFormatted") or device_or_value.get("mac_formatted")
    return re.sub(r"[^0-9A-F]", "", _text(device_or_value).upper())


def _movement_value(record: dict[str, Any], camel: str, snake: str) -> str:
    return _text(record.get(camel) if record.get(camel) is not None else record.get(snake))


def _movement_device_context(record: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "vendor": ("history_vendor", "vendor"),
        "model": ("history_model", "model"),
        "ip": ("history_ip", "ip"),
        "address": ("history_address", "address"),
        "room": ("history_room", "room"),
        "smartroomId": ("history_smartroom_id", "smartroomId", "smartroom_id"),
        "switchIp": ("history_switch_ip", "switchIp", "switch_ip"),
        "switchPort": ("history_switch_port", "switchPort", "switch_port"),
        "hostname": ("history_hostname", "hostname", "host_name"),
        "serialNumber": ("history_serial_number", "serialNumber", "serial_number", "serial"),
        "deviceId": ("history_device_id", "deviceId", "device_id"),
        "deviceName": ("history_device_name", "deviceName", "device_name"),
    }
    result = {"mac": _mac(record)}
    for field, keys in aliases.items():
        value = next((_text(record.get(key)) for key in keys if _text(record.get(key))), "")
        if value:
            result[field] = value
    return result if len(result) > 1 else {}


def _latest_history_devices(
    snapshots: list[dict[str, Any]],
    history_devices: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for device in history_devices:
        if isinstance(device, dict) and _mac(device):
            latest.setdefault(_mac(device), device)
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            continue
        for device in snapshot.get("devices") or []:
            if isinstance(device, dict) and _mac(device):
                latest.setdefault(_mac(device), device)
    return latest


def classify_dashboard_devices(
    devices: list[dict[str, Any]],
    snapshots: list[dict[str, Any]] | None = None,
    movements: list[dict[str, Any]] | None = None,
    history_devices: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Reproduce DashboardWidget's changed/missing/unchanged classification."""
    current = {_mac(device): device for device in devices if isinstance(device, dict) and _mac(device)}
    movement_rows = [row for row in (movements or []) if isinstance(row, dict) and _mac(row)]
    if not current:
        return {"all": [], "changed": [], "missing": [], "unchanged": [], "movements": []}
    changed_macs = {_mac(row) for row in movement_rows if _mac(row) in current}
    latest_history = _latest_history_devices(snapshots or [], history_devices or [])
    history_macs = set(latest_history) | {_mac(row) for row in movement_rows if _mac(row)}
    missing_macs = history_macs - set(current)
    missing_devices = []
    for mac in sorted(missing_macs):
        previous = dict(latest_history.get(mac) or {})
        previous.setdefault("mac", mac)
        previous.setdefault("macFormatted", previous.get("mac_formatted") or mac)
        previous["dashboardStatus"] = "missing"
        missing_devices.append(previous)
    changed_devices = []
    unchanged_devices = []
    for mac, device in current.items():
        row = dict(device)
        if mac in changed_macs:
            row["dashboardStatus"] = "changed"
            changed_devices.append(row)
        else:
            row["dashboardStatus"] = "unchanged"
            unchanged_devices.append(row)
    return {
        "all": [*changed_devices, *unchanged_devices],
        "changed": changed_devices,
        "missing": missing_devices,
        "unchanged": unchanged_devices,
        "movements": movement_rows,
    }


def _status_charts(
    classified: dict[str, Any],
    displayed: list[dict[str, Any]],
    limit: int,
) -> dict[str, list[dict[str, Any]]]:
    daily: Counter[str] = Counter()
    fields: Counter[str] = Counter()
    field_labels = {
        "vendor": "Производитель", "model": "Модель", "ip": "IP-адрес",
        "address": "Адрес", "room": "Помещение", "switch_ip": "Коммутатор",
        "switchIp": "Коммутатор", "switch_port": "Порт", "switchPort": "Порт",
    }
    for row in classified["movements"]:
        date = _movement_value(row, "changedAt", "changed_at") or _text(row.get("date_str"))
        if date:
            daily[date[:10]] += 1
        field = _movement_value(row, "field", "field_name")
        if field:
            fields[field_labels.get(field, field)] += 1
    vendors = Counter(_text(device.get("vendor")) or "Unknown" for device in displayed)
    missing_vendors = Counter(_text(device.get("vendor")) or "Unknown" for device in classified["missing"])

    def rows(counter: Counter[str], *, chronological: bool = False) -> list[dict[str, Any]]:
        values = sorted(counter.items())[-limit:] if chronological else counter.most_common(limit)
        return [{"label": label, "value": value} for label, value in values]

    return {
        "dynamics": rows(daily, chronological=True),
        "vendors": rows(vendors),
        "fields": rows(fields),
        "missing": rows(missing_vendors),
    }


def dashboard_filter_options_html(values: list[str], selected: str, empty_label: str) -> str:
    options = [f'<option value="">{html.escape(empty_label)}</option>']
    for value in values:
        selected_attr = " selected" if value == selected else ""
        safe_value = html.escape(value, quote=True)
        options.append(f'<option value="{safe_value}"{selected_attr}>{html.escape(value)}</option>')
    return "".join(options)


def build_dashboard_payload(
    devices: list[dict[str, Any]],
    snapshots: list[dict[str, Any]] | None = None,
    settings: dict[str, Any] | None = None,
    movements: list[dict[str, Any]] | None = None,
    history_devices: list[dict[str, Any]] | None = None,
    change_snapshots: list[dict[str, Any]] | None = None,
    snapshot_options: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized = normalize_dashboard_settings(settings)
    comparison_snapshots = change_snapshots if change_snapshots is not None else (snapshots or [])
    change_analysis = analyze_dashboard_changes(
        comparison_snapshots,
        movements or [],
        normalized,
        snapshot_options=snapshot_options,
    )
    comparison_movements = [
        {
            "mac": item.get("mac"),
            "type": item.get("type"),
            "field": item.get("field"),
            "before": item.get("before"),
            "after": item.get("after"),
            "changedAt": item.get("date"),
            "source": item.get("source"),
            "beforeDevice": item.get("beforeDevice"),
            "afterDevice": item.get("afterDevice"),
        }
        for item in change_analysis.get("changes", [])
    ]
    use_snapshot_comparison = normalized["changeMode"] == "snapshots" and len(comparison_snapshots) >= 2
    classified = classify_dashboard_devices(
        devices,
        comparison_snapshots if use_snapshot_comparison else snapshots,
        comparison_movements if use_snapshot_comparison else movements,
        history_devices,
    )
    if use_snapshot_comparison:
        current_by_mac = {_mac(device): device for device in devices if isinstance(device, dict) and _mac(device)}
        modified_macs = {
            item["mac"] for item in change_analysis.get("changes", [])
            if item.get("type") == "modified"
        }
        added_macs = {
            item["mac"] for item in change_analysis.get("changes", [])
            if item.get("type") == "added"
        }
        classified["changed"] = [current_by_mac[mac] for mac in sorted(modified_macs) if mac in current_by_mac]
        classified["unchanged"] = [
            device for mac, device in current_by_mac.items()
            if mac not in modified_macs and mac not in added_macs
        ]
    elif normalized["changeMode"] == "period":
        current_by_identity = {
            _device_identity(device): device
            for device in devices
            if isinstance(device, dict) and _device_identity(device)
        }
        modified_identities = {
            item.get("identity") for item in change_analysis.get("changes", [])
            if item.get("type") == "modified" and item.get("identity")
        }
        added_identities = {
            item.get("identity") for item in change_analysis.get("changes", [])
            if item.get("type") == "added" and item.get("identity")
        }
        missing_by_identity: dict[str, dict[str, Any]] = {}
        latest_history = _latest_history_devices(snapshots or [], history_devices or [])
        for item in change_analysis.get("changes", []):
            if item.get("type") != "removed" or not item.get("identity"):
                continue
            previous = dict(item.get("beforeDevice") or latest_history.get(item.get("mac")) or {"mac": item.get("mac")})
            previous["dashboardStatus"] = "missing"
            missing_by_identity.setdefault(item["identity"], previous)
        classified = {
            "all": [dict(device) for device in current_by_identity.values()],
            "changed": [
                {**current_by_identity[identity], "dashboardStatus": "changed"}
                for identity in sorted(modified_identities)
                if identity in current_by_identity
            ],
            "missing": list(missing_by_identity.values()),
            "unchanged": [
                {**device, "dashboardStatus": "unchanged"}
                for identity, device in current_by_identity.items()
                if identity not in modified_identities and identity not in added_identities
            ],
            "movements": comparison_movements,
        }
    current_scope = filter_dashboard_devices(classified["all"], normalized)
    changed_scope = filter_dashboard_devices(classified["changed"], normalized)
    missing_scope = filter_dashboard_devices(classified["missing"], normalized)
    unchanged_scope = filter_dashboard_devices(classified["unchanged"], normalized)
    status_devices = {
        "all": current_scope,
        "changed": changed_scope,
        "missing": missing_scope,
        "unchanged": unchanged_scope,
    }
    filtered = status_devices[normalized["status"]]
    chart_payload = build_chart_payload(filtered, snapshots or [])
    fleet = dashboard_upload_fleet(snapshots or [])
    status_charts = _status_charts({**classified, "missing": missing_scope}, filtered, normalized["chartLimit"])
    # The dashboard panel is explicitly the fleet-size timeline.  Movement
    # events belong to the changes table/field chart and must not be displayed
    # as if they were device totals.
    status_charts["dynamics"] = [
        {
            "label": _text(item.get("name") or item.get("date") or item.get("id"))[:28],
            "value": int(item.get("count") or 0),
        }
        for item in (fleet.get("series") or [])[-20:]
    ]
    vendors = sorted({_text(device.get("vendor")) for device in devices if _text(device.get("vendor"))})
    rooms = sorted({_text(device.get("room")) for device in devices if _text(device.get("room"))})
    return {
        "settings": normalized,
        "filters": {"vendors": vendors, "rooms": rooms},
        "filterOptionsHtml": {
            "vendors": dashboard_filter_options_html(vendors, normalized["vendor"], "Все производители"),
            "rooms": dashboard_filter_options_html(rooms, normalized["room"], "Все помещения"),
        },
        "devices": filtered,
        "metrics": {
            "devices": len(filtered),
            "total": len(current_scope),
            "totalAcross": max(int(fleet["uniqueAcrossUploads"] or 0), len(current_scope)),
            "changed": len(changed_scope),
            "missing": len(missing_scope),
            "unchanged": len(unchanged_scope),
            "uniqueMacs": len({_text(device.get("mac") or device.get("macFormatted")) for device in filtered if _text(device.get("mac") or device.get("macFormatted"))}),
            "vendors": len({_text(device.get("vendor")) for device in current_scope if _text(device.get("vendor")) and _text(device.get("vendor")) != "Unknown"}),
            "rooms": len({
                _text(device.get("smartroomId") or device.get("smartroom_id") or device.get("room"))
                for device in current_scope
                if _text(device.get("smartroomId") or device.get("smartroom_id") or device.get("room")) not in {"", "Unknown"}
            }),
            "switches": len({_text(device.get("switchIp") or device.get("switch_ip")) for device in filtered if _text(device.get("switchIp") or device.get("switch_ip"))}),
        },
        "statusCounts": {key: len(value) for key, value in status_devices.items()},
        "uploadFleet": fleet,
        "changeAnalysis": change_analysis,
        "statusCharts": status_charts,
        "charts": [
            {**chart, "items": (chart.get("items") or [])[:normalized["chartLimit"]]}
            for chart in chart_payload["charts"]
        ],
    }


def build_dashboard_metrics_payload(
    devices: list[dict[str, Any]],
    invalid: list[Any] | None = None,
    snapshots: list[dict[str, Any]] | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_dashboard_payload(devices, snapshots or [], settings or {})
    filtered = payload.get("devices", [])
    unknown_labels = {"", "unknown", "неизвестный вендор", "unknown vendor", "не определено"}
    unknown_vendor = sum(1 for device in filtered if _text(device.get("vendor")).lower() in unknown_labels)
    total = int(payload.get("metrics", {}).get("devices") or 0)
    known = max(0, total - unknown_vendor)
    def value(device: dict[str, Any], *keys: str) -> str:
        for key in keys:
            current = _text(device.get(key))
            if current:
                return current
        return ""

    def ranked(values: list[str], limit: int = 20) -> list[dict[str, Any]]:
        return [{"label": label, "value": count} for label, count in Counter(item for item in values if item).most_common(limit)]

    normalized_macs = [_mac(device) for device in filtered]
    vendors = [value(device, "vendor") or "Unknown" for device in filtered]
    models = [value(device, "model") for device in filtered]
    rooms = [value(device, "room") for device in filtered]
    room_identities = [value(device, "smartroomId", "smartroom_id", "room") for device in filtered]
    switches = [value(device, "switchIp", "switch_ip") for device in filtered]
    oui3 = [mac[:6] for mac in normalized_macs if len(mac) >= 6]
    oui4 = [mac[:8] for mac in normalized_macs if len(mac) >= 8]
    oui5 = [mac[:10] for mac in normalized_macs if len(mac) >= 10]
    with_model = sum(bool(item) for item in models)
    with_address = sum(bool(value(device, "address")) for device in filtered)
    with_room = sum(bool(item) for item in rooms)
    with_ip = sum(bool(value(device, "ip")) for device in filtered)
    with_switch = sum(bool(item) for item in switches)
    auto_vendors = sum(
        value(device, "vendor").lower() not in unknown_labels
        and (device.get("vendorMatchedPrefix") or not device.get("vendorSource") or device.get("vendorSource") not in {"file", "history"})
        for device in filtered
    )
    auto_models = sum(
        bool(value(device, "model"))
        and (device.get("modelMatchedPrefix") or not device.get("modelSource") or device.get("modelSource") not in {"file", "history"})
        for device in filtered
    )
    return {
        "metrics": {
            "devices": total,
            "vendors": len({item for item in vendors if item.lower() not in unknown_labels}),
            "models": len({item for item in models if item}),
            "rooms": len({item for item in room_identities if item}),
            "switches": len({item for item in switches if item}),
            "knownDevices": known,
            "unknownVendor": unknown_vendor,
            "knownPercent": round(known / total * 100) if total else 0,
            "invalid": len(invalid or []),
            "withAddress": with_address,
            "withRoom": with_room,
            "withIp": with_ip,
            "withSwitch": with_switch,
            "withModel": with_model,
            "autoVendors": auto_vendors,
            "autoModels": auto_models,
            "uniqueOui3": len(set(oui3)),
            "uniqueOui4": len(set(oui4)),
            "uniqueOui5": len(set(oui5)),
        },
        "distributions": {
            "vendors": ranked(vendors),
            "models": ranked(models),
            "rooms": ranked(rooms),
            "switches": ranked(switches),
            "oui3": ranked(oui3),
            "oui4": ranked(oui4),
            "oui5": ranked(oui5),
        },
        "filters": payload.get("filters", {}),
        "settings": payload.get("settings", {}),
    }


def export_dashboard_html(payload: dict[str, Any]) -> dict[str, str]:
    metrics = payload.get("metrics", {})
    charts = payload.get("charts", [])
    metric_items = "".join(
        f"<li>{html.escape(str(key))}: {html.escape(str(value))}</li>"
        for key, value in metrics.items()
    )
    chart_sections = []
    for chart in charts:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(str(item.get('label', '')))}</td>"
            f"<td>{html.escape(str(item.get('value', 0)))}</td>"
            "</tr>"
            for item in chart.get("items", [])
        )
        chart_sections.append(
            f"<h2>{html.escape(str(chart.get('title', 'Chart')))}</h2>"
            "<table><thead><tr><th>Label</th><th>Value</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    content = (
        '<!doctype html><html><head><meta charset="utf-8"><title>MAC Analyzer Dashboard</title>'
        "<style>body{font:14px Arial;margin:32px}table{border-collapse:collapse;margin:12px 0 24px;width:100%}"
        "td,th{border:1px solid #bbb;padding:7px;text-align:left}th{background:#eee}</style></head><body>"
        f"<h1>MAC Analyzer Dashboard</h1><p>Created: {html.escape(datetime.utcnow().isoformat(timespec='seconds'))}Z</p>"
        f"<h2>Metrics</h2><ul>{metric_items}</ul>{''.join(chart_sections)}</body></html>"
    )
    return {"filename": "mac-dashboard.html", "mimeType": "text/html", "content": content}


def export_dashboard_png(payload: dict[str, Any]) -> dict[str, Any]:
    """Render the PyQt dashboard's six KPI cards and four chart areas to PNG."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 2000, 1200
    background, surface, border = "#f4f7fb", "#ffffff", "#d7dee8"
    text_color, muted, accent = "#172033", "#667085", "#2563eb"
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)

    def font(size: int, bold: bool = False):
        names = ["seguisb.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
        roots = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")]
        for root in roots:
            for name in names + (["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"]):
                candidate = root / name
                if candidate.exists():
                    return ImageFont.truetype(str(candidate), size)
        return ImageFont.load_default()

    title_font, subtitle_font = font(34, True), font(17)
    card_label_font, card_value_font = font(16), font(31, True)
    panel_title_font, row_font = font(21, True), font(15)
    draw.text((40, 28), "MAC Analyzer Dashboard", fill=text_color, font=title_font)
    draw.text((40, 75), f"Создано: {datetime.now().isoformat(timespec='seconds')}", fill=muted, font=subtitle_font)

    metrics = payload.get("metrics") or {}
    metric_rows = [
        ("Всего устройств", metrics.get("total", 0)),
        ("Изменённые", metrics.get("changed", 0)),
        ("Отсутствовавшие", metrics.get("missing", 0)),
        ("Без изменений", metrics.get("unchanged", 0)),
        ("Производителей", metrics.get("vendors", 0)),
        ("Помещений", metrics.get("rooms", 0)),
    ]
    gap, card_y, card_h = 14, 112, 112
    card_w = (width - 80 - gap * 5) // 6
    for index, (label, value) in enumerate(metric_rows):
        x = 40 + index * (card_w + gap)
        draw.rounded_rectangle((x, card_y, x + card_w, card_y + card_h), radius=8, fill=surface, outline=border, width=2)
        draw.text((x + 18, card_y + 17), label, fill=muted, font=card_label_font)
        draw.text((x + 18, card_y + 50), str(value), fill=text_color, font=card_value_font)

    charts = payload.get("statusCharts") or {}
    chart_specs = [
        ("Динамика общего числа устройств", charts.get("dynamics") or []),
        ("Топ производителей", charts.get("vendors") or []),
        ("Изменения по полям", charts.get("fields") or []),
        ("Отсутствовавшие устройства", charts.get("missing") or []),
    ]
    panel_gap, panel_x, panel_y = 20, 40, 250
    panel_w = (width - 80 - panel_gap) // 2
    panel_h = (height - panel_y - 40 - panel_gap) // 2
    palette = ["#2563eb", "#0f9f6e", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#be185d", "#4b5563"]
    for index, (title, items) in enumerate(chart_specs):
        column, row = index % 2, index // 2
        x = panel_x + column * (panel_w + panel_gap)
        y = panel_y + row * (panel_h + panel_gap)
        draw.rounded_rectangle((x, y, x + panel_w, y + panel_h), radius=8, fill=surface, outline=border, width=2)
        draw.text((x + 22, y + 18), title, fill=text_color, font=panel_title_font)
        rows = [item for item in items[:8] if isinstance(item, dict)]
        if not rows:
            draw.text((x + 22, y + 78), "Нет данных", fill=muted, font=row_font)
            continue
        max_value = max([int(item.get("value") or 0) for item in rows] + [1])
        bar_left, bar_width, row_y = x + 245, panel_w - 320, y + 67
        row_height = max(37, min(48, (panel_h - 85) // max(1, len(rows))))
        for row_index, item in enumerate(rows):
            label = _text(item.get("label"))
            if len(label) > 25:
                label = label[:24] + "…"
            value = int(item.get("value") or 0)
            current_y = row_y + row_index * row_height
            draw.text((x + 22, current_y + 5), label, fill=text_color, font=row_font)
            draw.rounded_rectangle((bar_left, current_y + 4, bar_left + bar_width, current_y + 24), radius=4, fill="#e8edf5")
            filled = max(2, int(bar_width * value / max_value)) if value else 0
            if filled:
                draw.rounded_rectangle((bar_left, current_y + 4, bar_left + filled, current_y + 24), radius=4, fill=palette[row_index % len(palette)])
            draw.text((bar_left + bar_width + 12, current_y + 5), str(value), fill=text_color, font=row_font)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return {
        "filename": f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        "mimeType": "image/png",
        "binary": True,
        "content": base64.b64encode(buffer.getvalue()).decode("ascii"),
        "width": width,
        "height": height,
    }

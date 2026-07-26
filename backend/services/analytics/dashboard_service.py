import html
import base64
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

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
        "vendor": _text(settings.get("vendor")),
        "room": _text(settings.get("room")),
        "status": status,
        "chartLimit": max(1, min(int(settings.get("chartLimit") or 8), 25)),
        "showUnknown": bool(settings.get("showUnknown", True)),
        "visibleCards": {
            key: bool(card_settings.get(key, True))
            for key in ("total", "changed", "missing", "unchanged", "vendors", "rooms")
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


CHANGE_FIELDS = ("vendor", "model", "ip", "address", "room", "switchIp", "switchPort")
CHANGE_FIELD_LABELS = {
    "vendor": "Производитель", "model": "Модель", "ip": "IP-адрес", "address": "Адрес",
    "room": "Помещение", "switchIp": "Коммутатор", "switchPort": "Порт", "device": "Устройство",
}


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
        date = _text(snapshot.get("fileCreatedAt") or snapshot.get("createdAt") or snapshot.get("created_at"))
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
) -> str:
    if field == "switchIp" and before_device and after_device:
        if (
            _text(before_device.get("ip")) == _text(after_device.get("ip"))
            and _text(before_device.get("room")) == _text(after_device.get("room"))
        ):
            return "critical"
    if field in {"ip", "address", "room"}:
        return "high"
    if field in {"vendor", "model", "switchIp", "switchPort"}:
        return "medium"
    if change_type == "removed":
        return "high"
    return "low"


def _device_context(device: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(device, dict):
        return None
    return {
        "mac": _mac(device),
        "vendor": _text(device.get("vendor")),
        "model": _text(device.get("model")),
        "ip": _text(device.get("ip")),
        "address": _text(device.get("address")),
        "room": _text(device.get("room")),
        "switchIp": _text(device.get("switchIp") or device.get("switch_ip")),
        "switchPort": _text(device.get("switchPort") or device.get("switch_port")),
    }


def _change_row(
    *, mac: str, changed_at: str, change_type: str, field: str = "device",
    before: Any = "", after: Any = "", source: str = "history",
    before_device: dict[str, Any] | None = None, after_device: dict[str, Any] | None = None,
) -> dict[str, Any]:
    labels = {"added": "Добавлено", "removed": "Удалено", "modified": "Изменено"}
    normalized_field = {"switch_ip": "switchIp", "switch_port": "switchPort"}.get(field, field or "device")
    previous = _device_context(before_device)
    current = _device_context(after_device)
    return {
        "mac": mac, "macFormatted": ":".join(mac[index:index + 2] for index in range(0, 12, 2)) if len(mac) == 12 else mac,
        "date": changed_at, "type": change_type, "typeLabel": labels.get(change_type, "Изменено"),
        "field": normalized_field, "fieldLabel": CHANGE_FIELD_LABELS.get(normalized_field, normalized_field),
        "before": _text(before) or "-", "after": _text(after) or "-", "source": source,
        "severity": _change_severity(change_type, normalized_field, previous, current),
        "beforeDevice": previous, "afterDevice": current,
    }


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

    if normalized["changeMode"] == "snapshots" and len(snapshots) >= 2:
        baseline_id = baseline_id or options[-2]["id"]
        comparison_id = comparison_id or options[-1]["id"]
        indexed = {_snapshot_id(snapshot, index): snapshot for index, snapshot in enumerate(snapshots) if isinstance(snapshot, dict)}
        baseline = indexed.get(baseline_id) or indexed.get(options[-2]["id"]) or snapshots[-2]
        comparison = indexed.get(comparison_id) or indexed.get(options[-1]["id"]) or snapshots[-1]
        before_devices = {_mac(device): device for device in baseline.get("devices", []) if isinstance(device, dict) and _mac(device)}
        after_devices = {_mac(device): device for device in comparison.get("devices", []) if isinstance(device, dict) and _mac(device)}
        changed_at = _text(comparison.get("fileCreatedAt") or comparison.get("createdAt") or comparison.get("created_at"))
        for mac in sorted(set(after_devices) - set(before_devices)):
            changes.append(_change_row(
                mac=mac, changed_at=changed_at, change_type="added",
                after=after_devices[mac].get("source") or "Устройство", source="snapshot",
                after_device=after_devices[mac],
            ))
        for mac in sorted(set(before_devices) - set(after_devices)):
            changes.append(_change_row(
                mac=mac, changed_at=changed_at, change_type="removed",
                before=before_devices[mac].get("source") or "Устройство", source="snapshot",
                before_device=before_devices[mac],
            ))
        for mac in sorted(set(before_devices) & set(after_devices)):
            for field in CHANGE_FIELDS:
                before = before_devices[mac].get(field)
                after = after_devices[mac].get(field)
                if _text(before) != _text(after):
                    changes.append(_change_row(
                        mac=mac, changed_at=changed_at, change_type="modified", field=field,
                        before=before, after=after, source="snapshot",
                        before_device=before_devices[mac], after_device=after_devices[mac],
                    ))
    else:
        date_to = _parse_date(selected_to, end_of_day=True) or datetime.now()
        date_from = _parse_date(selected_from) or (date_to - timedelta(days=30))
        selected_from = selected_from or date_from.date().isoformat()
        selected_to = selected_to or date_to.date().isoformat()
        for movement in movements:
            if not isinstance(movement, dict) or not _mac(movement):
                continue
            changed_at = _movement_value(movement, "changedAt", "changed_at") or _text(movement.get("date_str"))
            parsed = _parse_date(changed_at)
            if parsed and not date_from <= parsed <= date_to:
                continue
            field = _movement_value(movement, "field", "field_name") or "device"
            before = movement.get("before", movement.get("from_value", movement.get("old_value", "")))
            after = movement.get("after", movement.get("to_value", movement.get("new_value", "")))
            change_type = _text(movement.get("type") or movement.get("change_type") or "modified").lower()
            if change_type not in {"added", "removed", "modified"}:
                change_type = "modified"
            changes.append(_change_row(mac=_mac(movement), changed_at=changed_at, change_type=change_type, field=field, before=before, after=after, source=_text(movement.get("source") or movement.get("file_name") or "history")))

    period_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in changes:
        period_groups.setdefault((item["mac"], item["date"], item["source"]), []).append(item)
    for grouped_changes in period_groups.values():
        fields = {item["field"] for item in grouped_changes}
        inferred_critical = "switchIp" in fields and not ({"ip", "room"} & fields)
        if inferred_critical and not any(item.get("beforeDevice") or item.get("afterDevice") for item in grouped_changes):
            for item in grouped_changes:
                if item["field"] == "switchIp":
                    item["severity"] = "critical"

    changes.sort(key=lambda item: item.get("date", ""), reverse=True)
    summary = {
        key: len({item["mac"] for item in changes if item["type"] == key})
        for key in ("added", "removed", "modified")
    }
    summary["critical"] = len({item["mac"] for item in changes if item["severity"] == "critical"})
    summary["total"] = len({item["mac"] for item in changes})
    field_counts = Counter(item["fieldLabel"] for item in changes)
    return {
        "mode": normalized["changeMode"], "dateFrom": selected_from, "dateTo": selected_to,
        "baselineSnapshotId": baseline_id, "comparisonSnapshotId": comparison_id,
        "snapshotOptions": options, "summary": summary, "changes": changes,
        "fieldChanges": len(changes),
        "fieldCounts": [{"label": label, "value": value} for label, value in field_counts.most_common(12)],
    }


def filter_dashboard_devices(devices: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = normalize_dashboard_settings(settings)
    result = []
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
        result.append(device)
    return result


def _mac(device_or_value: Any) -> str:
    if isinstance(device_or_value, dict):
        device_or_value = device_or_value.get("mac") or device_or_value.get("macFormatted") or device_or_value.get("mac_formatted")
    return re.sub(r"[^0-9A-F]", "", _text(device_or_value).upper())


def _movement_value(record: dict[str, Any], camel: str, snake: str) -> str:
    return _text(record.get(camel) if record.get(camel) is not None else record.get(snake))


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
            "rooms": len({_text(device.get("room")) for device in current_scope if _text(device.get("room")) and _text(device.get("room")) != "Unknown"}),
            "switches": len({_text(device.get("switchIp") or device.get("switch_ip")) for device in filtered if _text(device.get("switchIp") or device.get("switch_ip"))}),
        },
        "statusCounts": {key: len(value) for key, value in status_devices.items()},
        "uploadFleet": fleet,
        "changeAnalysis": change_analysis,
        "statusCharts": _status_charts({**classified, "missing": missing_scope}, filtered, normalized["chartLimit"]),
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
    return {
        "metrics": {
            "devices": total,
            "vendors": len({_text(device.get("vendor")) for device in filtered if _text(device.get("vendor"))}),
            "knownDevices": known,
            "unknownVendor": unknown_vendor,
            "knownPercent": round(known / total * 100) if total else 0,
            "invalid": len(invalid or []),
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
        ("Динамика изменений по дням", charts.get("dynamics") or []),
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

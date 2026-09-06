import csv
import html
import io
import json
import re
from datetime import datetime
from typing import Any

from backend.services.identity.device_identity_service import pair_device_sets


DEFAULT_FIELDS = ["mac", "vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort", "hostname", "serialNumber", "deviceId", "deviceName"]
FIELD_TITLES = {
    "vendor": "Производитель",
    "model": "Модель",
    "ip": "IP",
    "address": "Адрес",
    "room": "Помещение",
    "smartroomId": "Smartroom ID",
    "switchIp": "Коммутатор",
    "switchPort": "Порт",
    "source": "Источник",
    "mac": "MAC / физический адрес",
    "hostname": "Hostname",
    "serialNumber": "Серийный номер",
    "deviceId": "ID устройства",
    "deviceName": "Название устройства",
    "identityConflict": "Конфликт идентификации",
}
STATUS_TITLES = {
    "added": "Добавлено",
    "removed": "Удалено",
    "modified": "Изменено",
}
EXPORT_MIME_TYPES = {
    "csv": "text/csv",
    "txt": "text/plain",
    "html": "text/html",
    "json": "application/json",
    "excel": "application/vnd.ms-excel",
    "xlsx": "application/vnd.ms-excel",
    "xml": "application/vnd.ms-excel",
}


def normalize_mac(value: Any) -> str:
    return re.sub(r"[^0-9A-F]", "", str(value or "").upper())


def format_mac(value: Any) -> str:
    clean = normalize_mac(value)
    if len(clean) == 12:
        return ":".join(clean[index:index + 2] for index in range(0, 12, 2))
    return str(value or "")


def _device_mac(device: dict[str, Any]) -> str:
    return normalize_mac(device.get("mac") or device.get("macFormatted") or device.get("MAC"))


def _device_label(device: dict[str, Any], mac: str) -> str:
    return str(device.get("macFormatted") or format_mac(mac) or mac)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _indexed_devices(devices: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for device in devices:
        if isinstance(device, dict):
            mac = _device_mac(device)
            if mac:
                indexed[mac] = device
    return indexed


def comparison_rows_html(changes: list[dict[str, Any]]) -> str:
    return "".join(
        "<tr>"
        f"<td>{html.escape(_text(change.get('macFormatted') or format_mac(change.get('mac'))))}</td>"
        f"<td>{html.escape(_text(change.get('statusTitle') or change.get('status')))}</td>"
        f"<td>{html.escape(_text(change.get('fieldTitle') or change.get('field') or '-'))}</td>"
        f"<td>{html.escape(_text(change.get('before') or '-'))}</td>"
        f"<td>{html.escape(_text(change.get('after') or '-'))}</td>"
        "</tr>"
        for change in changes
    )


def comparison_summary_html(summary: dict[str, Any], title: str = "Результат сравнения", sets: list[dict[str, Any]] | None = None) -> str:
    if sets:
        details = "<br>".join(
            f"{html.escape(_text(item.get('name')))}: +{int((item.get('summary') or {}).get('added') or 0)} / "
            f"-{int((item.get('summary') or {}).get('removed') or 0)} / "
            f"изменено {int((item.get('summary') or {}).get('modified') or 0)}"
            for item in sets
        )
    else:
        details = (
            f"Добавлено: {int(summary.get('added') or 0)} · "
            f"Удалено: {int(summary.get('removed') or 0)} · "
            f"Изменено: {int(summary.get('modified') or 0)}"
        )
    return (
        f"<h2>{html.escape(title)}</h2>"
        f'<span class="summary-number">{int(summary.get("total") or 0)}</span>'
        f'<p class="muted">{details}</p>'
    )


def decorate_comparison_result(result: dict[str, Any], title: str = "Результат сравнения", sets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    changes = result.get("changes", [])
    if not isinstance(changes, list):
        changes = []
    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    result["changesRowsHtml"] = comparison_rows_html(changes)
    result["emptyRowsHtml"] = '<tr><td colspan="5" class="empty-state">Изменений не найдено.</td></tr>'
    result["summaryHtml"] = comparison_summary_html(summary, title, sets)
    return result


def compare_devices(
    baseline_devices: list[dict[str, Any]],
    current_devices: list[dict[str, Any]],
    fields: list[str] | None = None,
) -> dict[str, Any]:
    selected_fields = [field for field in (fields or DEFAULT_FIELDS) if field]
    changes: list[dict[str, str]] = []

    pairs, added_devices, removed_devices = pair_device_sets(baseline_devices, current_devices)
    for current_device in added_devices:
        mac = _device_mac(current_device)
        changes.append({
                "mac": mac,
                "macFormatted": _device_label(current_device, mac),
                "status": "added",
                "statusTitle": STATUS_TITLES["added"],
                "field": "",
                "fieldTitle": "-",
                "before": "-",
                "after": _text(current_device.get("source") or current_device.get("vendor") or "-") or "-",
            })
    for baseline_device, current_device in pairs:
        mac = _device_mac(current_device) or _device_mac(baseline_device)
        for field in selected_fields:
            before = _text(_device_mac(baseline_device) if field == "mac" else baseline_device.get(field))
            after = _text(_device_mac(current_device) if field == "mac" else current_device.get(field))
            if before and not after:
                continue
            if before != after:
                changes.append({
                    "mac": mac,
                    "macFormatted": _device_label(current_device, mac),
                    "status": "modified",
                    "statusTitle": STATUS_TITLES["modified"],
                    "field": field,
                    "fieldTitle": FIELD_TITLES.get(field, field),
                    "before": before or "-",
                    "after": after or "-",
                })
    for baseline_device in removed_devices:
        mac = _device_mac(baseline_device)
        changes.append({
            "mac": mac,
            "macFormatted": _device_label(baseline_device, mac),
            "status": "removed",
            "statusTitle": STATUS_TITLES["removed"],
            "field": "",
            "fieldTitle": "-",
            "before": _text(baseline_device.get("source") or baseline_device.get("vendor") or "-") or "-",
            "after": "-",
        })

    summary = {
        "added": sum(1 for change in changes if change["status"] == "added"),
        "removed": sum(1 for change in changes if change["status"] == "removed"),
        "modified": sum(1 for change in changes if change["status"] == "modified"),
    }
    summary["total"] = len(changes)
    return decorate_comparison_result({"summary": summary, "changes": changes})


def compare_many_devices(
    baseline_devices: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    fields: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    if len(comparisons) > limit:
        raise ValueError(f"Too many files for multi comparison: maximum is {limit}")

    result_sets: list[dict[str, Any]] = []
    flat_changes: list[dict[str, Any]] = []
    total = {"added": 0, "removed": 0, "modified": 0, "total": 0}

    for index, item in enumerate(comparisons, start=1):
        if not isinstance(item, dict):
            continue
        devices = item.get("devices", [])
        if not isinstance(devices, list):
            devices = []
        comparison = compare_devices(baseline_devices, devices, fields)
        comparison_id = str(item.get("id") or f"comparison-{index}")
        comparison_name = str(item.get("name") or comparison_id)
        mapping = item.get("mapping") if isinstance(item.get("mapping"), dict) else {}

        enriched_changes = []
        for change in comparison["changes"]:
            enriched = {
                **change,
                "comparisonId": comparison_id,
                "comparisonName": comparison_name,
                "mapping": mapping,
            }
            enriched_changes.append(enriched)
            flat_changes.append(enriched)

        for key in total:
            total[key] += int(comparison["summary"].get(key, 0))
        result_sets.append({
            "id": comparison_id,
            "name": comparison_name,
            "mapping": mapping,
            "summary": comparison["summary"],
            "changes": enriched_changes,
        })

    return decorate_comparison_result(
        {"summary": total, "sets": result_sets, "changes": flat_changes, "limit": limit},
        "Массовое сравнение",
        result_sets,
    )


def _snapshot_by_id(snapshots: list[dict[str, Any]], snapshot_id: Any) -> dict[str, Any] | None:
    target = str(snapshot_id or "")
    return next((item for item in snapshots if isinstance(item, dict) and str(item.get("id") or "") == target), None)


def compare_snapshots(
    snapshots: list[dict[str, Any]],
    baseline_id: Any,
    current_id: Any,
    fields: list[str] | None = None,
    export_format: str = "",
) -> dict[str, Any]:
    if not isinstance(snapshots, list):
        raise ValueError("snapshots must be an array")
    baseline = _snapshot_by_id(snapshots, baseline_id)
    current = _snapshot_by_id(snapshots, current_id)
    if not baseline or not current:
        raise ValueError("Select two existing snapshots")
    if str(baseline.get("id")) == str(current.get("id")):
        raise ValueError("Select two different snapshots")
    baseline_devices = baseline.get("devices", [])
    current_devices = current.get("devices", [])
    if not isinstance(baseline_devices, list) or not isinstance(current_devices, list):
        raise ValueError("snapshot devices must be arrays")
    result = compare_devices(baseline_devices, current_devices, fields)
    result["baseline"] = {
        "id": baseline.get("id", ""),
        "name": baseline.get("name", ""),
        "source": baseline.get("source", ""),
        "deviceCount": len(baseline_devices),
    }
    result["current"] = {
        "id": current.get("id", ""),
        "name": current.get("name", ""),
        "source": current.get("source", ""),
        "deviceCount": len(current_devices),
    }
    requested_export = str(export_format or "").strip()
    if requested_export:
        result["export"] = export_comparison(result["changes"], requested_export)
    return result


def compare_many_snapshots(
    snapshots: list[dict[str, Any]],
    baseline_id: Any,
    comparison_ids: list[Any],
    fields: list[str] | None = None,
    export_format: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    if not isinstance(snapshots, list):
        raise ValueError("snapshots must be an array")
    if not isinstance(comparison_ids, list):
        raise ValueError("comparisonIds must be an array")
    baseline = _snapshot_by_id(snapshots, baseline_id)
    if not baseline:
        raise ValueError("Select an existing baseline snapshot")
    selected_ids = [str(item) for item in comparison_ids if str(item or "") and str(item) != str(baseline.get("id"))][:limit]
    if not selected_ids:
        raise ValueError("Select at least one comparison snapshot")
    baseline_devices = baseline.get("devices", [])
    if not isinstance(baseline_devices, list):
        raise ValueError("snapshot devices must be arrays")

    comparisons = []
    for snapshot_id in selected_ids:
        snapshot = _snapshot_by_id(snapshots, snapshot_id)
        if not snapshot:
            continue
        devices = snapshot.get("devices", [])
        comparisons.append({
            "id": snapshot.get("id") or snapshot_id,
            "name": snapshot.get("name") or snapshot_id,
            "mapping": snapshot.get("mapping") if isinstance(snapshot.get("mapping"), dict) else snapshot.get("columnMapping") if isinstance(snapshot.get("columnMapping"), dict) else {},
            "devices": devices if isinstance(devices, list) else [],
        })
    if not comparisons:
        raise ValueError("Select at least one existing comparison snapshot")

    result = compare_many_devices(baseline_devices, comparisons, fields, limit)
    result["baseline"] = {
        "id": baseline.get("id", ""),
        "name": baseline.get("name", ""),
        "source": baseline.get("source", ""),
        "deviceCount": len(baseline_devices),
    }
    requested_export = str(export_format or "").strip()
    if requested_export:
        result["export"] = export_comparison(result["changes"], requested_export)
    return result


def _rows(changes: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [
            _text(change.get("macFormatted") or format_mac(change.get("mac"))),
            _text(change.get("statusTitle") or STATUS_TITLES.get(_text(change.get("status")), change.get("status"))),
            _text(change.get("fieldTitle") or change.get("field") or "-"),
            _text(change.get("before") or "-"),
            _text(change.get("after") or "-"),
        ]
        for change in changes
    ]


def export_comparison(changes: list[dict[str, Any]], export_format: str) -> dict[str, str]:
    requested_format = str(export_format or "").lower().strip()
    if requested_format not in EXPORT_MIME_TYPES:
        raise ValueError("Unsupported comparison export format")

    headers = ["MAC", "Тип изменения", "Поле", "Было", "Стало"]
    rows = _rows(changes)
    output_format = requested_format
    if requested_format == "json":
        content = json.dumps(changes, ensure_ascii=False, indent=2)
    elif requested_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        content = output.getvalue()
    elif requested_format == "txt":
        content = "\n\n".join(
            "\n".join(f"{header}: {value}" for header, value in zip(headers, row))
            for row in rows
        )
    elif requested_format == "html":
        head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
            for row in rows
        )
        content = (
            '<!doctype html><html><head><meta charset="utf-8"><title>MAC Analyzer Compare</title>'
            "<style>body{font:14px Arial;margin:24px}table{border-collapse:collapse;width:100%}"
            "td,th{border:1px solid #bbb;padding:6px;text-align:left}th{background:#eee}</style></head><body>"
            f"<h1>MAC Analyzer Compare</h1><p>Created: {html.escape(datetime.utcnow().isoformat(timespec='seconds'))}Z</p>"
            f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></body></html>"
        )
    else:
        row_xml = "".join(
            "<Row>" + "".join(
                f'<Cell><Data ss:Type="String">{html.escape(value)}</Data></Cell>' for value in row
            ) + "</Row>"
            for row in rows
        )
        header_xml = "".join(
            f'<Cell><Data ss:Type="String">{html.escape(header)}</Data></Cell>' for header in headers
        )
        content = (
            '<?xml version="1.0"?>'
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
            'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
            f"<Worksheet ss:Name=\"Compare\"><Table><Row>{header_xml}</Row>{row_xml}</Table></Worksheet></Workbook>"
        )
        output_format = "xml"

    return {
        "filename": f"mac-comparison.{output_format}",
        "mimeType": EXPORT_MIME_TYPES[requested_format],
        "content": content,
    }

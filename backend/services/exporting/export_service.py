import csv
import html
import io
import json
from datetime import datetime
from typing import Any


MIME_TYPES = {
    "csv": "text/csv",
    "txt": "text/plain",
    "html": "text/html",
    "json": "application/json",
    "yaml": "text/yaml",
}


def normalize_columns(columns: list[Any]) -> list[tuple[str, str]]:
    normalized: list[tuple[str, str]] = []
    for item in columns:
        if isinstance(item, dict):
            key = str(item.get("key") or "").strip()
            title = str(item.get("title") or key).strip()
        else:
            key = str(item or "").strip()
            title = key
        if key and key not in {column_key for column_key, _ in normalized}:
            normalized.append((key, title or key))
    return normalized


def _value(device: dict[str, Any], key: str) -> str:
    value = device.get(key, "")
    if value is None:
        return ""
    return str(value)


def _yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def export_text(devices: list[dict[str, Any]], columns: list[Any], export_format: str) -> dict[str, str]:
    fmt = export_format.lower().strip()
    if fmt not in MIME_TYPES:
        raise ValueError("Unsupported export format")
    normalized_columns = normalize_columns(columns)
    if not normalized_columns:
        raise ValueError("At least one column is required")

    if fmt == "json":
        content = json.dumps(devices, ensure_ascii=False, indent=2)
    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([title for _, title in normalized_columns])
        for device in devices:
            writer.writerow([_value(device, key) for key, _ in normalized_columns])
        content = output.getvalue()
    elif fmt == "txt":
        blocks = []
        for index, device in enumerate(devices, start=1):
            lines = [f"Device {index}"]
            lines.extend(f"{title}: {_value(device, key) or '-'}" for key, title in normalized_columns)
            blocks.append("\n".join(lines))
        content = "\n\n".join(blocks)
    elif fmt == "yaml":
        content = "\n".join(
            "-\n" + "\n".join(f"  {key}: {_yaml_quote(_value(device, key))}" for key, _ in normalized_columns)
            for device in devices
        )
    else:
        header = "".join(f"<th>{html.escape(title)}</th>" for _, title in normalized_columns)
        rows = "".join(
            "<tr>" + "".join(f"<td>{html.escape(_value(device, key))}</td>" for key, _ in normalized_columns) + "</tr>"
            for device in devices
        )
        content = (
            '<!doctype html><html><head><meta charset="utf-8"><title>MAC Analyzer Export</title>'
            "<style>body{font:14px Arial;margin:24px}table{border-collapse:collapse;width:100%}"
            "td,th{border:1px solid #bbb;padding:6px;text-align:left}th{background:#eee}</style></head><body>"
            f"<h1>MAC Analyzer Export</h1><p>Created: {html.escape(datetime.utcnow().isoformat(timespec='seconds'))}Z</p>"
            f"<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></body></html>"
        )

    return {
        "filename": f"mac-analysis.{fmt}",
        "mimeType": MIME_TYPES[fmt],
        "content": content,
    }

import base64
import html
from datetime import datetime
from typing import Any

from .export_service import export_text, normalize_columns
from backend.services.detection.oui_service import format_oui_for_devices
from .pdf_service import export_pdf
from backend.services.workspace.xlsx_service import export_xlsx


SUPPORTED_FORMATS = {
    "csv": {"label": "CSV", "binary": False, "mimeType": "text/csv", "extension": "csv"},
    "txt": {"label": "Text", "binary": False, "mimeType": "text/plain", "extension": "txt"},
    "html": {"label": "HTML", "binary": False, "mimeType": "text/html", "extension": "html"},
    "json": {"label": "JSON", "binary": False, "mimeType": "application/json", "extension": "json"},
    "yaml": {"label": "YAML", "binary": False, "mimeType": "text/yaml", "extension": "yaml"},
    "xlsx": {
        "label": "Excel XLSX",
        "binary": True,
        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "extension": "xlsx",
    },
    "pdf": {"label": "PDF", "binary": True, "mimeType": "application/pdf", "extension": "pdf"},
    "spreadsheetml": {"label": "Excel XML", "binary": False, "mimeType": "application/vnd.ms-excel", "extension": "xml"},
}

FORMAT_ALIASES = {
    "excel": "xlsx",
    "xls": "spreadsheetml",
    "xml": "spreadsheetml",
    "excel-xml": "spreadsheetml",
}


def supported_export_formats() -> dict[str, Any]:
    return {
        "formats": [
            {"format": key, **value}
            for key, value in SUPPORTED_FORMATS.items()
        ],
        "aliases": FORMAT_ALIASES,
    }


def normalize_export_format(export_format: str) -> str:
    fmt = str(export_format or "").strip().lower()
    fmt = FORMAT_ALIASES.get(fmt, fmt)
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError("Unsupported export format")
    return fmt


def _spreadsheetml(devices: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    def xml_escape(value: Any) -> str:
        return html.escape(str(value if value is not None else ""), quote=True)

    rows = []
    rows.append("<Row>" + "".join(f'<Cell><Data ss:Type="String">{xml_escape(title)}</Data></Cell>' for _, title in columns) + "</Row>")
    for device in devices:
        rows.append(
            "<Row>"
            + "".join(f'<Cell><Data ss:Type="String">{xml_escape(device.get(key, ""))}</Data></Cell>' for key, _ in columns)
            + "</Row>"
        )
    return (
        '<?xml version="1.0"?>'
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
        'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
        '<Worksheet ss:Name="MAC Analyzer"><Table>'
        + "".join(rows)
        + "</Table></Worksheet></Workbook>"
    )


def export_managed(
    devices: list[dict[str, Any]],
    columns: list[Any],
    export_format: str,
    filename_prefix: str = "mac-analysis",
    oui_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(devices, list):
        raise ValueError("devices must be an array")
    if not isinstance(columns, list):
        raise ValueError("columns must be an array")

    fmt = normalize_export_format(export_format)
    normalized_columns = normalize_columns(columns)
    if not normalized_columns:
        raise ValueError("At least one column is required")
    oui_settings = oui_settings or {}
    try:
        oui_length = int(oui_settings.get("length") or 3)
    except (TypeError, ValueError):
        oui_length = 3
    oui_style = str(oui_settings.get("style") or "plain")
    formatted_ouis = format_oui_for_devices(devices, oui_length, oui_style)
    export_devices = [
        {**device, "oui": formatted.get("oui", device.get("oui", ""))}
        for device, formatted in zip(devices, formatted_ouis)
    ]

    metadata = SUPPORTED_FORMATS[fmt]
    filename = f"{filename_prefix}.{metadata['extension']}"
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    if fmt in {"csv", "txt", "html", "json", "yaml"}:
        result = export_text(export_devices, [{"key": key, "title": title} for key, title in normalized_columns], fmt)
        return {
            **result,
            "format": fmt,
            "binary": False,
            "encoding": "utf-8",
            "size": len(result["content"].encode("utf-8")),
            "createdAt": created_at,
        }

    if fmt == "spreadsheetml":
        content = _spreadsheetml(export_devices, normalized_columns)
        return {
            "filename": filename,
            "mimeType": metadata["mimeType"],
            "content": content,
            "format": fmt,
            "binary": False,
            "encoding": "utf-8",
            "size": len(content.encode("utf-8")),
            "createdAt": created_at,
        }

    payload = export_xlsx(export_devices, normalized_columns) if fmt == "xlsx" else export_pdf(export_devices, normalized_columns)
    return {
        "filename": filename,
        "mimeType": metadata["mimeType"],
        "content": base64.b64encode(payload).decode("ascii"),
        "format": fmt,
        "binary": True,
        "encoding": "base64",
        "size": len(payload),
        "createdAt": created_at,
    }

from __future__ import annotations

import re
from typing import Any


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def is_empty_row(row: Any) -> bool:
    """Return True only for a source row that contains no meaningful cell."""
    return not isinstance(row, (list, tuple)) or not any(text(value) for value in row)


def invalid_identity_record(
    *,
    row: list[Any],
    row_number: int,
    source: str,
    source_role: str,
    raw_mac: Any,
    mac_column: int | None,
) -> dict[str, Any]:
    raw_mac_text = text(raw_mac)
    compact_mac = re.sub(r"[^0-9A-Fa-f]", "", raw_mac_text).upper()
    if raw_mac_text:
        error_code = "INVALID_MAC"
        explanation = (
            f"Значение MAC «{raw_mac_text}» после удаления разделителей содержит "
            f"{len(compact_mac)} из 12 шестнадцатеричных символов; серийный номер и Device ID отсутствуют."
        )
        suggestion = "Исправьте MAC либо укажите серийный номер или Device ID в сопоставленных колонках."
    else:
        error_code = "MISSING_IDENTITY"
        explanation = "В сопоставленных колонках не заполнены MAC, серийный номер и Device ID."
        suggestion = "Проверьте сопоставление колонок и заполненность исходной строки."
    raw_preview = " | ".join(text(value) for value in row).strip(" |")[:500]
    return {
        "invalid": True,
        "valid": False,
        "errorCode": error_code,
        "row": row_number,
        "source": source,
        "sourceRole": source_role,
        "raw": raw_preview,
        "rawMac": raw_mac_text,
        "macHexLength": len(compact_mac),
        "expectedMacHexLength": 12,
        "macColumn": mac_column,
        "error": "Некорректный MAC" if raw_mac_text else "Отсутствует идентификатор устройства",
        "explanation": explanation,
        "suggestion": suggestion,
    }

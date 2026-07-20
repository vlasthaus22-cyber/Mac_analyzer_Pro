"""Unified tabular file import for the web backend."""

import csv
import io
import json
from pathlib import Path

from .xlsx_service import read_xls, read_xlsx


def decode_text_table(content: bytes) -> str:
    if not content:
        raise ValueError("Файл пустой")
    candidates: list[tuple[int, str]] = []
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1251", "latin-1"):
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        text = text.replace("\x00", "")
        if not text.strip():
            continue
        readable = sum(1 for char in text if char.isalnum() or char.isspace() or char in ",;\t|:.#_-")
        controls = sum(1 for char in text if ord(char) < 32 and char not in "\r\n\t")
        cyrillic = sum(1 for char in text if "А" <= char <= "я" or char == "ё" or char == "Ё")
        delimiters = sum(text.count(delimiter) for delimiter in (",", ";", "\t", "|"))
        candidates.append((readable + cyrillic * 4 + delimiters * 8 - controls * 20, text))
    if not candidates:
        raise ValueError("Не удалось определить кодировку файла")
    return max(candidates, key=lambda item: item[0])[1]


def detect_delimiter(text: str, suffix: str) -> str:
    if suffix == ".tsv":
        return "\t"
    sample = "\n".join(line for line in text.splitlines()[:20] if line.strip())
    if not sample:
        raise ValueError("Файл не содержит строк")
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        candidates = [(",", sample.count(",")), (";", sample.count(";")), ("\t", sample.count("\t")), ("|", sample.count("|"))]
        delimiter, count = max(candidates, key=lambda item: item[1])
        return delimiter if count else ","


def normalize_rows(rows: list[list[str]]) -> dict:
    stripped = [[str(cell).strip() for cell in row] for row in rows]
    if stripped and not any(stripped[0]):
        raise ValueError("Первая строка файла не содержит заголовков")
    cleaned = [row for row in stripped if any(row)]
    if not cleaned:
        raise ValueError("Файл не содержит строк")
    headers = cleaned[0]
    if not any(headers):
        raise ValueError("Первая строка файла не содержит заголовков")
    width = len(headers)
    normalized_rows = [(row + [""] * width)[:width] for row in cleaned[1:]]
    return {"headers": headers, "rows": normalized_rows}


def read_table(filename: str, content: bytes, sheet: str | None = None) -> dict:
    suffix = Path(filename).suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return read_xlsx(content, sheet)
    if suffix == ".xls":
        return read_xls(content, sheet)
    text = decode_text_table(content)
    if suffix == ".json":
        items = json.loads(text)
        if isinstance(items, dict):
            items = items.get("devices") or items.get("rows") or items.get("data") or []
        if not isinstance(items, list):
            raise ValueError("JSON должен содержать массив или объект с devices/rows/data")
        if not items:
            raise ValueError("JSON не содержит записей")
        if not all(isinstance(item, dict) for item in items):
            raise ValueError("JSON-записи должны быть объектами")
        headers = list(dict.fromkeys(key for item in items for key in item))
        return {"headers": headers, "rows": [[item.get(key, "") for key in headers] for item in items]}
    delimiter = detect_delimiter(text, suffix)
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    return normalize_rows(rows)

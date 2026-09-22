"""Safe metadata-only scanning for three-folder batch enrichment."""

from __future__ import annotations

import os
import re
import threading
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


SUPPORTED_SUFFIXES = {".csv", ".tsv", ".txt", ".json", ".xlsx", ".xlsm", ".xls"}
VALID_ROLES = {"primary", "smartroom", "ddio"}


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")


def _valid_date(year: str, month: str, day: str, hour: str = "", minute: str = "", second: str = "") -> str:
    try:
        value = datetime(
            int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0), tzinfo=timezone.utc,
        )
    except ValueError:
        return ""
    return value.isoformat().replace("+00:00", "Z")


def date_from_filename(filename: str) -> str:
    name = str(filename or "")
    patterns = (
        (r"(?:^|\D)(20\d{2})[-_. ](0?[1-9]|1[0-2])[-_. ](0?[1-9]|[12]\d|3[01])(?:[T _-](\d{1,2})[-_.:](\d{2})(?:[-_.:](\d{2}))?)?(?:\D|$)", (1, 2, 3, 4, 5, 6)),
        (r"(?:^|\D)(0?[1-9]|[12]\d|3[01])[-_. ](0?[1-9]|1[0-2])[-_. ](20\d{2})(?:[T _-](\d{1,2})[-_.:](\d{2})(?:[-_.:](\d{2}))?)?(?:\D|$)", (3, 2, 1, 4, 5, 6)),
        (r"(?:^|\D)(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?:[_-]?(\d{2})(\d{2})(\d{2})?)?(?:\D|$)", (1, 2, 3, 4, 5, 6)),
        (r"(?:^|\D)(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])(20\d{2})(?:[_-]?(\d{2})(\d{2})(\d{2})?)?(?:\D|$)", (3, 2, 1, 4, 5, 6)),
    )
    for pattern, order in patterns:
        match = re.search(pattern, name)
        if not match:
            continue
        values = [match.group(index) or "" for index in order]
        parsed = _valid_date(*values)
        if parsed:
            return parsed
    return ""


def xlsx_creation_date(path: Path) -> str:
    if path.suffix.lower() not in {".xlsx", ".xlsm"}:
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("docProps/core.xml"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, ElementTree.ParseError):
        return ""
    for local_name in ("created", "modified"):
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1].lower() != local_name or not (node.text or "").strip():
                continue
            try:
                parsed = datetime.fromisoformat(node.text.strip().replace("Z", "+00:00"))
            except ValueError:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return ""


def observation_date(path: Path) -> dict[str, str]:
    filename_date = date_from_filename(path.name)
    if filename_date:
        return {"date": filename_date, "source": "filename"}
    workbook_date = xlsx_creation_date(path)
    if workbook_date:
        return {"date": workbook_date, "source": "xlsx.created"}
    stat = path.stat()
    # On Windows st_ctime is the creation time. Other platforms have no
    # portable creation timestamp, so mtime is the least surprising fallback.
    use_creation_time = os.name == "nt" and hasattr(stat, "st_ctime")
    observed = stat.st_ctime if use_creation_time else stat.st_mtime
    return {"date": _iso(observed), "source": "filesystem.created" if use_creation_time else "filesystem.modified"}


class BatchFolderRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._files: dict[str, Path] = {}

    def register(self, path: Path) -> str:
        token = str(uuid.uuid4())
        with self._lock:
            self._files[token] = path.resolve()
        return token

    def resolve(self, token: Any) -> Path:
        with self._lock:
            path = self._files.get(str(token or ""))
        if path is None or not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError("Файл массового обогащения не найден; повторно просканируйте папки")
        return path

    def clear(self) -> None:
        with self._lock:
            self._files.clear()


def scan_batch_folders(paths: dict[str, Any], registry: BatchFolderRegistry) -> dict[str, Any]:
    descriptors: list[dict[str, Any]] = []
    folders: dict[str, dict[str, Any]] = {}
    for role in ("primary", "smartroom", "ddio"):
        raw_path = str(paths.get(role) or "").strip()
        if not raw_path:
            folders[role] = {"path": "", "files": 0}
            continue
        root = Path(raw_path).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Папка {role} не найдена: {raw_path}")
        files = sorted(
            (item for item in root.rglob("*") if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES),
            key=lambda item: str(item.relative_to(root)).casefold(),
        )
        folders[role] = {"path": str(root), "files": len(files)}

        def describe(entry: tuple[int, Path]) -> dict[str, Any]:
            index, path = entry
            date_info = observation_date(path)
            return {
                "id": f"backend:{role}:{index}:{path.name}",
                "backendToken": registry.register(path),
                "role": role,
                "name": path.name,
                "relativePath": str(path.relative_to(root)),
                "size": path.stat().st_size,
                "date": date_info["date"],
                "dateSource": date_info["source"],
            }

        if files:
            with ThreadPoolExecutor(max_workers=min(8, len(files)), thread_name_prefix="batch-metadata") as executor:
                descriptors.extend(executor.map(describe, enumerate(files)))
    if not any(item["role"] == "primary" for item in descriptors):
        raise ValueError("В папке основных файлов нет поддерживаемых CSV/XLSX/JSON")
    return {"folders": folders, "files": descriptors, "supportedExtensions": sorted(SUPPORTED_SUFFIXES)}

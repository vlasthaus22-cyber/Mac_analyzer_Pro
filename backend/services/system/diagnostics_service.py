"""Read-only operational diagnostics for the web application."""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any, Callable

from .parity_service import build_parity_status


REQUIRED_TABLES = {
    "app_settings",
    "app_autosaves",
    "vendor_mappings",
    "model_mappings",
    "mac_history",
    "mac_movements",
    "vendor_model_history",
    "snapshots",
    "scheduled_tasks",
    "ip_address_mappings",
    "column_preferences",
    "app_logs",
    "performance_metrics",
    "data_quality_reports",
}

REQUIRED_API_MARKERS = (
    "/api/health",
    "/api/files/import-binary",
    "/api/single-file/analyze",
    "/api/enrichment/run",
    "/api/results/filter",
    "/api/history",
    "/api/snapshots",
    "/api/dashboard",
    "/api/export",
    "/api/parity/status",
    "/api/reference/oui/status",
)


def _check(group: str, name: str, passed: bool, detail: str, *, warning: bool = False) -> dict[str, Any]:
    status = "warning" if warning else ("passed" if passed else "failed")
    return {"group": group, "name": name, "status": status, "passed": bool(passed), "detail": detail}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _database_checks(db_connection: Callable[[], Any]) -> list[dict[str, Any]]:
    try:
        with db_connection() as connection:
            quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            table_rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tables = {str(row[0]) for row in table_rows}
        missing = sorted(REQUIRED_TABLES - tables)
        return [
            _check("SQLite", "Целостность базы", quick_check.lower() == "ok", f"PRAGMA quick_check: {quick_check}"),
            _check(
                "SQLite",
                "Обязательные таблицы",
                not missing,
                f"Найдено {len(REQUIRED_TABLES)}/{len(REQUIRED_TABLES)} таблиц" if not missing else "Отсутствуют: " + ", ".join(missing),
            ),
        ]
    except Exception as error:  # pragma: no cover - exercised through failure injection
        return [_check("SQLite", "Подключение к базе", False, str(error))]


def _diagnostics_html(checks: list[dict[str, Any]]) -> str:
    labels = {"passed": "OK", "warning": "Внимание", "failed": "Ошибка"}
    return "".join(
        '<div class="diagnostic-row diagnostic-{status}">'
        '<span><strong>{name}</strong><small>{group} · {detail}</small></span>'
        '<b>{label}</b></div>'.format(
            status=html.escape(str(item["status"])),
            name=html.escape(str(item["name"])),
            group=html.escape(str(item["group"])),
            detail=html.escape(str(item["detail"])),
            label=labels.get(str(item["status"]), str(item["status"])),
        )
        for item in checks
    )


def build_system_diagnostics(root: Path, storage: Any, db_connection: Callable[[], Any]) -> dict[str, Any]:
    """Check the installed application without modifying its data."""
    root = Path(root).resolve()
    checks: list[dict[str, Any]] = []

    required_files = (
        "index.html",
        "app.js",
        "styles.css",
        "server.py",
        "START_MAC_ANALYZER.cmd",
        "STOP_MAC_ANALYZER.cmd",
        "scripts/portable_start.ps1",
        "scripts/portable_stop.ps1",
        "frontend/memory-guard.js",
        "frontend/file-readers.js",
        "frontend/state-persistence.js",
        "frontend/browser-snapshot-store.js",
        "frontend/guide.js",
        "backend/services/detection/reference_data_service.py",
    )
    missing_files = [name for name in required_files if not (root / name).is_file()]
    checks.append(_check(
        "Структура",
        "Файлы web-приложения",
        not missing_files,
        f"Найдено {len(required_files)}/{len(required_files)}" if not missing_files else "Отсутствуют: " + ", ".join(missing_files),
    ))

    directories = list(storage.directories())
    missing_directories = [path.name for path in directories if not path.is_dir()]
    checks.append(_check(
        "Структура",
        "Каталоги данных",
        not missing_directories,
        f"Доступно {len(directories)}/{len(directories)}" if not missing_directories else "Отсутствуют: " + ", ".join(missing_directories),
    ))
    unwritable = [path.name for path in directories if path.exists() and not os.access(path, os.W_OK)]
    checks.append(_check(
        "Структура",
        "Запись рабочих данных",
        not unwritable,
        "Каталоги доступны для записи" if not unwritable else "Нет доступа: " + ", ".join(unwritable),
    ))

    checks.extend(_database_checks(db_connection))

    server_text = _read(root / "server.py")
    missing_routes = [route for route in REQUIRED_API_MARKERS if route not in server_text]
    checks.append(_check(
        "API",
        "Ключевые маршруты",
        not missing_routes,
        f"Найдено {len(REQUIRED_API_MARKERS)}/{len(REQUIRED_API_MARKERS)}" if not missing_routes else "Отсутствуют: " + ", ".join(missing_routes),
    ))

    memory_guard = _read(root / "frontend" / "memory-guard.js")
    file_readers = _read(root / "frontend" / "file-readers.js")
    app_text = _read(root / "app.js")
    snapshot_store = _read(root / "frontend" / "browser-snapshot-store.js")
    standalone_text = _read(root / "mac_analyzer_standalone.html")
    memory_markers = (
        ("browserRows: 150_000", memory_guard),
        ("browserCells: 1_500_000", memory_guard),
        ("browserEnrichmentRows: 220_000", memory_guard),
        ("browserEnrichmentTextBytes", memory_guard),
        ("assertHeapHeadroom", memory_guard),
        ("assertEnrichmentCapacity", memory_guard),
        ("assertImportCapacity", memory_guard),
        ("assertZipDirectoryCapacity", memory_guard),
        ("BROWSER_MEMORY_LIMIT", memory_guard),
        ("collectPage", memory_guard),
        ("xlsxWorksheetRows", file_readers),
        ("memoryGuard.assertZipDirectoryCapacity(entries)", file_readers),
        ('fileToken,sheet:', app_text),
        ("compactResult:true,resultPageSize", app_text),
        ("MemoryGuard.yieldToMainThread", app_text),
        ("snapshotPreviewRows: 500", memory_guard),
        ("localExportRows: 20_000", memory_guard),
        ("assertLocalExportCapacity", memory_guard),
        ("BrowserSnapshots.save", app_text),
        ("resultBrowserSnapshotId", app_text),
        ("createLocalComparisonIndex", app_text),
        ("state:autosaveState", app_text),
        ("currentDevicePayload({compactResult:true,resultPageSize})", app_text),
        ('const snapshotStore = "snapshots"', snapshot_store),
        ("compactStandaloneState", standalone_text),
        ("standaloneMemoryLimits", standalone_text),
        ("zipExpandedBytes", standalone_text),
    )
    missing_memory = [marker for marker, content in memory_markers if marker not in content]
    checks.append(_check(
        "Большие файлы",
        "Защита от Out of Memory",
        not missing_memory,
        "Потоковый XLSX, лимиты, paging, компактный autosave и отдельные снимки IndexedDB активны" if not missing_memory else "Не найдены: " + ", ".join(missing_memory),
    ))

    parity = build_parity_status(root)
    parity_total = int(parity["summary"]["pyqtBlocks"] or 0)
    parity_complete = int(parity["summary"]["webComplete"] or 0)
    registry_total = int(parity["registry"]["total"] or 0)
    registry_checked = int(parity["registry"]["checked"] or 0)
    parity_ready = parity["status"] == "complete"
    checks.append(_check(
        "Перенос",
        "Функциональные блоки PyQt",
        parity_ready,
        f"Web-эквиваленты {parity_complete}/{parity_total}; реестр {registry_checked}/{registry_total}",
    ))

    failed = sum(1 for item in checks if item["status"] == "failed")
    warnings = sum(1 for item in checks if item["status"] == "warning")
    passed = sum(1 for item in checks if item["status"] == "passed")
    total = len(checks)
    readiness_percent = round((passed / total) * 100) if total else 0
    parity_percent = round((parity_complete / parity_total) * 100) if parity_total else 0
    status = "healthy" if not failed and not warnings else ("degraded" if not failed else "error")
    summary = {
        "status": status,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "total": total,
        "readinessPercent": readiness_percent,
        "parityPercent": parity_percent,
        "pyqtBlocks": parity_total,
        "webComplete": parity_complete,
        "registryChecked": registry_checked,
        "registryTotal": registry_total,
    }
    summary_html = (
        f'<div class="bar-label"><span>Готовность</span><strong>{readiness_percent}%</strong></div>'
        f'<div class="bar-label"><span>Перенос PyQt</span><strong>{parity_complete}/{parity_total}</strong></div>'
        f'<div class="bar-label"><span>Проверки</span><strong>{passed}/{total}</strong></div>'
        f'<div class="bar-label"><span>Ошибки</span><strong>{failed}</strong></div>'
    )
    return {
        "status": status,
        "summary": summary,
        "checks": checks,
        "summaryHtml": summary_html,
        "detailsHtml": _diagnostics_html(checks),
    }

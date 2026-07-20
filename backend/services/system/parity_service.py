"""Parity status checks for the PyQt-to-web migration."""

from __future__ import annotations

import json
import html
from pathlib import Path
from typing import Any


PYQT_SOURCE = "MAC_ANALYZER финальная.py"


PYQT_WEB_EQUIVALENTS: list[dict[str, Any]] = [
    {"name": "Database management", "pyqt": "class DatabaseManagementDialog", "web": [("server.py", "/api/database/summary"), ("server.py", "/api/database/maintenance"), ("index.html", "databaseMaintenanceButton"), ("index.html", "legacyImportButton")]},
    {"name": "Enhanced MAC history", "pyqt": "class EnhancedHistoryDialog", "web": [("server.py", "/api/history/search"), ("server.py", "/api/history/statistics"), ("index.html", "sqliteHistoryBody")]},
    {"name": "MAC history dialog", "pyqt": "class MACHistoryDialog", "web": [("server.py", "/api/history"), ("app.js", "showDevice"), ("index.html", "deviceHistoryBody")]},
    {"name": "Column conflict review", "pyqt": "class ColumnConflictDialog", "web": [("server.py", "/api/columns/detect"), ("app.js", "columnDetection"), ("index.html", "columnDetectionSummary")]},
    {"name": "Vendor detector settings", "pyqt": "class VendorDetectorSettingsDialog", "web": [("backend/services/detection/vendor_detector_service.py", "def detect_vendor"), ("server.py", "/api/oui/settings"), ("index.html", "ouiLengthSelect")]},
    {"name": "History enrichment settings", "pyqt": "class HistoryEnrichmentSettingsDialog", "web": [("server.py", "/api/vendor-model-history/learn"), ("index.html", "learnVendorModelButton"), ("app.js", "renderVendorModelHistory")]},
    {"name": "Vendor/model history", "pyqt": "class VendorModelHistoryDialog", "web": [("server.py", "/api/vendor-model-history"), ("server.py", "/api/vendor-model-history/uploads"), ("index.html", "vendorModelHistoryBody")]},
    {"name": "IP address mapping", "pyqt": "class IPAddressMappingDialog", "web": [("server.py", "/api/ip-mappings"), ("server.py", "/api/ip-mappings/import"), ("index.html", "ipMappingList")]},
    {"name": "Column mapping", "pyqt": "class ColumnMappingDialog", "web": [("server.py", "/api/mapping/summary"), ("index.html", "mappingGrid"), ("app.js", "detectColumnsWithBackend")]},
    {"name": "Column manager", "pyqt": "class ColumnManagerDialog", "web": [("server.py", "/api/columns/preferences"), ("index.html", "columnPreferenceList"), ("app.js", "renderColumnPreferences")]},
    {"name": "OUI format selection", "pyqt": "class OUIFormatSelectionDialog", "web": [("server.py", "/api/oui/format"), ("index.html", "ouiStyleSelect"), ("app.js", "ouiSettings")]},
    {"name": "Comparison file mapping", "pyqt": "class ComparisonFileMappingDialog", "web": [("server.py", "/api/compare"), ("index.html", "baselineSelect"), ("index.html", "comparisonSelect")]},
    {"name": "Multi-file comparison", "pyqt": "class MultiFileComparisonDialog", "web": [("server.py", "/api/compare/many"), ("index.html", "multiCompareButton"), ("app.js", "multiCompare")]},
    {"name": "Comparison fields", "pyqt": "class FieldsSelectionDialog", "web": [("server.py", "/api/compare"), ("index.html", "comparisonFilters"), ("index.html", "compareButton")]},
    {"name": "File comparison", "pyqt": "class FileComparisonDialog", "web": [("server.py", "/api/compare"), ("server.py", "export_comparison"), ("index.html", "comparisonBody")]},
    {"name": "Time statistics", "pyqt": "class TimeStatsDialog", "web": [("server.py", "/api/statistics/temporal"), ("index.html", "temporalStatisticsChart"), ("app.js", "renderTemporalStatistics")]},
    {"name": "Notifications", "pyqt": "class NotificationSettingsDialog", "web": [("server.py", "/api/notifications"), ("server.py", "/api/notifications/event"), ("index.html", "notificationChannel")]},
    {"name": "Scheduler", "pyqt": "class SchedulerDialog", "web": [("server.py", "/api/tasks"), ("server.py", "/api/tasks/queue"), ("index.html", "taskList")]},
    {"name": "API enrichment", "pyqt": "class APIEnrichmentDialog", "web": [("server.py", "/api/external-enrichment/run"), ("server.py", "/api/external-enrichment/test"), ("index.html", "apiEnrichButton")]},
    {"name": "Clustering", "pyqt": "class ClusteringDialog", "web": [("server.py", "/api/clusters"), ("index.html", "clusterChart"), ("app.js", "renderBackendClusters")]},
    {"name": "Single file analysis", "pyqt": "class SingleFileAnalysisDialog", "web": [("server.py", "/api/single-file/analyze"), ("index.html", "singleFileAnalyzeButton"), ("app.js", "renderSingleReport")]},
    {"name": "Export dialog", "pyqt": "class ExportDialog", "web": [("server.py", "/api/export"), ("server.py", "/api/xlsx/export"), ("server.py", "/api/pdf/export"), ("index.html", "exportCsvButton")]},
    {"name": "Analytics dialog", "pyqt": "class AnalyticsDialog", "web": [("server.py", "/api/dashboard"), ("server.py", "/api/charts"), ("index.html", "analyticsView")]},
    {"name": "Single device analytics", "pyqt": "class SingleDeviceAnalyticsDialog", "web": [("server.py", "/api/device/analytics"), ("app.js", "exportDeviceAnalytics"), ("index.html", "deviceDialog")]},
    {"name": "Model prefixes", "pyqt": "class ModelPrefixesDialog", "web": [("server.py", "/api/model/analytics"), ("app.js", "showModelAnalytics"), ("index.html", "modelDialog")]},
    {"name": "Theme selection", "pyqt": "class ThemeSelectionDialog", "web": [("server.py", "/api/theme"), ("index.html", "themeButton"), ("app.js", "saveThemePreference")]},
    {"name": "API settings", "pyqt": "class APISettingsDialog", "web": [("server.py", "/api/external-enrichment/settings"), ("index.html", "externalProviderSelect"), ("app.js", "externalApiSettings")]},
    {"name": "Dashboard settings", "pyqt": "class DashboardSettingsDialog", "web": [("server.py", "/api/dashboard/settings"), ("index.html", "saveDashboardSettingsButton"), ("app.js", "saveDashboardSettings")]},
    {"name": "Topology", "pyqt": "show_topology", "web": [("server.py", "/api/topology"), ("index.html", "topologyGraph"), ("app.js", "renderBackendTopology")]},
    {"name": "Data quality analysis", "pyqt": "def analyze_data_quality", "web": [("server.py", "/api/quality/analyze"), ("index.html", "qualityAnalysisButton"), ("backend/services/analytics/data_quality_service.py", "def analyze_data_quality")]},
    {"name": "Legacy SQLite migration", "pyqt": "mac_history.db", "web": [("server.py", "/api/legacy/import"), ("backend/services/system/legacy_migration_service.py", "def migrate_legacy_sqlite"), ("index.html", "legacyImportButton")]},
]


def _read(root: Path, filename: str) -> str:
    path = root / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_registry(root: Path) -> dict[str, Any]:
    lines = _read(root, "PARITY_REGISTRY.md").splitlines()
    items = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("- ["):
            checked = stripped.startswith("- [x]") or stripped.startswith("- [X]")
            items.append({
                "line": line_number,
                "checked": checked,
                "text": stripped[6:].strip(),
            })
    return {
        "items": items,
        "checked": sum(1 for item in items if item["checked"]),
        "total": len(items),
        "unchecked": [item for item in items if not item["checked"]],
    }


def parity_summary_html(status: str, summary: dict[str, Any], registry: dict[str, Any]) -> str:
    return (
        f'<div class="bar-label"><span>Status</span><strong>{html.escape(str(status or "unknown"))}</strong></div>'
        f'<div class="bar-label"><span>PyQt blocks</span><strong>{int(summary.get("webComplete") or 0)}/{int(summary.get("pyqtBlocks") or 0)}</strong></div>'
        f'<div class="bar-label"><span>Missing equivalents</span><strong>{int(summary.get("missingEquivalents") or 0)}</strong></div>'
        f'<div class="bar-label"><span>Registry unchecked</span><strong>{int(summary.get("registryUnchecked") or 0)}</strong></div>'
        f'<div class="bar-label"><span>Registry checked</span><strong>{int(registry.get("checked") or 0)}/{int(registry.get("total") or 0)}</strong></div>'
    )


def parity_details_html(equivalents: list[dict[str, Any]]) -> str:
    return "".join(
        '<div class="mapping-row"><span>'
        f'<strong>{html.escape(str(item.get("name") or ""))}</strong>'
        f'<small>{html.escape(str(item.get("pyqtMarker") or ""))} · {"complete" if item.get("webComplete") else "missing"} · '
        f'markers {len(item.get("presentMarkers") or [])}</small>'
        f'</span><span class="muted">{"OK" if item.get("webComplete") else "TODO"}</span></div>'
        for item in equivalents
    )


def build_parity_status(root: Path) -> dict[str, Any]:
    pyqt_text = _read(root, PYQT_SOURCE)
    file_cache: dict[str, str] = {}
    equivalents = []
    for requirement in PYQT_WEB_EQUIVALENTS:
        pyqt_present = requirement["pyqt"] in pyqt_text
        missing_markers = []
        present_markers = []
        for filename, marker in requirement["web"]:
            content = file_cache.setdefault(filename, _read(root, filename))
            marker_present = marker in content
            entry = {"file": filename, "marker": marker}
            if marker_present:
                present_markers.append(entry)
            else:
                missing_markers.append(entry)
        equivalents.append({
            "name": requirement["name"],
            "pyqtMarker": requirement["pyqt"],
            "pyqtPresent": pyqt_present,
            "webComplete": pyqt_present and not missing_markers,
            "presentMarkers": present_markers,
            "missingMarkers": missing_markers,
        })
    registry = parse_registry(root)
    missing_equivalents = [
        item for item in equivalents
        if item["pyqtPresent"] and not item["webComplete"]
    ]
    status_value = "complete" if not registry["unchecked"] and not missing_equivalents else "incomplete"
    summary = {
        "pyqtBlocks": len(equivalents),
        "webComplete": sum(1 for item in equivalents if item["webComplete"]),
        "missingEquivalents": len(missing_equivalents),
        "registryUnchecked": len(registry["unchecked"]),
    }
    return {
        "status": status_value,
        "registry": registry,
        "equivalents": equivalents,
        "summary": summary,
        "missingEquivalents": missing_equivalents,
        "summaryHtml": parity_summary_html(status_value, summary, registry),
        "detailsHtml": parity_details_html(equivalents),
        "emptyDetailsHtml": '<p class="muted">Нет данных parity.</p>',
    }


def build_parity_report(root: Path) -> dict[str, str]:
    status = build_parity_status(root)
    content = json.dumps(status, ensure_ascii=False, indent=2)
    return {
        "filename": "mac-analyzer-parity-report.json",
        "mimeType": "application/json",
        "content": content,
    }


def write_parity_status_file(root: Path, filename: str = "PARITY_STATUS.json") -> Path:
    output_path = root / filename
    output_path.write_text(build_parity_report(root)["content"] + "\n", encoding="utf-8")
    return output_path

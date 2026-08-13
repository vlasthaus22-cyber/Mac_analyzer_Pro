from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def assert_markers(source: str, markers: tuple[str, ...]) -> None:
    missing = [marker for marker in markers if marker not in source]
    assert not missing, "Missing markers:\n" + "\n".join(missing)


def test_user_requested_frontend_parity_blocks_are_present():
    html = read_text("index.html")
    app = read_text("frontend/memory-guard.js") + "\n" + read_text("frontend/file-readers.js") + "\n" + read_text("app.js")

    assert_markers(
        html,
        (
            'data-view="workspace"',
            'data-view="single"',
            'data-view="compare"',
            'data-view="analytics"',
            'data-view="history"',
            'data-view="data"',
            'data-view="automation"',
            'data-view="settings"',
            'id="fileInput" type="file" accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm,.xls"',
            'id="enrichFileInput" type="file" accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm,.xls"',
            'id="mappingFileSelect"',
            'id="mappingDisplayMode"',
            'id="columnConflictDialog"',
            'id="columnConflictBody"',
            'id="applyConflictColumnsButton"',
            'id="copyMappingToAllButton"',
            'id="analysisDashboardPanel"',
            'id="analysisVendorChart"',
            'id="analysisModelChart"',
            'id="analysisOuiChart"',
            'id="metricModels"',
            'id="metricOuiCoverage"',
            'id="metricAutoDetected"',
            'id="historyBody"',
            'id="localMovementBody"',
            'id="movementTypeFilter"',
            'id="movementFieldFilter"',
            'id="exportMovementHistoryButton"',
            'id="deleteShownMovementsButton"',
            'id="movementColumnControls"',
            'id="deviceChronologySummary"',
            'id="deviceChronologyBody"',
            'id="ipMappingImportInput"',
            'id="timeStatsSummary"',
            'id="timeStatsBody"',
            'id="learnVendorModelButton"',
            'id="vendorModelLearnMinCount"',
            'id="vendorModelLearnSource"',
            'id="vendorDetectorEnabled"',
            'id="vendorDetectorOui3"',
            'id="vendorDetectorMac5"',
            'id="vendorDetectorText"',
            'id="vendorDetectorInference"',
            'id="saveVendorDetectorSettingsButton"',
            'id="historyEnrichmentEnabled"',
            'id="historyEnrichmentPriority"',
            'id="historyEnrichmentMac5"',
            'id="historyEnrichmentOui"',
            'id="saveHistoryEnrichmentSettingsButton"',
            'id="themeButton"',
            'id="engineeringLoginButton"',
            'id="copyResultsTableButton"',
            'id="copyHistoryTableButton"',
            'id="tableContextMenu"',
            'id="optimizeColumnWidthsButton"',
            'id="resetColumnWidthsButton"',
            'id="saveColumnWidthsButton"',
            'id="loadColumnWidthsButton"',
            'id="databaseHistoryBody"',
            'id="deleteSelectedDatabaseHistoryButton"',
            'id="deleteFilteredDatabaseHistoryButton"',
            '<kbd>F9</kbd>',
            "async function parseXlsxFile(file)",
            "function renderFallbackTopMetrics()",
            "function renderFallbackAnalysisDashboard()",
            "function fallbackVendorFromText(...values)",
            "function fallbackCompatibleRuleValue(mac, rules)",
            "function fallbackNormalizeVendorDetectorSettings(settings = {})",
            "function fallbackNormalizeHistoryEnrichmentSettings(settings = {})",
            "function fallbackVendorModelLearnSettings()",
            "function learnFallbackVendorModelMappings()",
        ),
    )

    assert_markers(
        app,
        (
            "function activateView(name,{updateHash=true,render=true}={})",
            'history.pushState(null,"","#"+name)',
            'api("/files/import-binary",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name),"X-Sheet-Name":"","X-Preview-Rows":"100"},body:file})',
            "function fileInfoDate(file)",
            "function primaryFileCreatedAt()",
            "const fileCreatedAt=fileInfoDate(pendingSingleFile);",
            "mapping:singleManualMapping(),createdAt:fileCreatedAt,saveHistory:true,saveSnapshot:true",
            "async function clientXlsxTable(file, onProgress = () => {}, options = {})",
            "async function xlsxWorksheetRows(directory, sheetPath, sharedStrings, onProgress = () => {}, options = {})",
            "function assertTableCapacity(rowCount, cellCount)",
            "function selectedMappingFile()",
            "function showColumnConflictReview(file,result)",
            "function applyColumnConflictSelection()",
            "function renderMappingControls()",
            "state.files.forEach((item)=>{item.mapping={...file.mapping};localMappingSummary(item);});",
            "function sourceFilesPayload(compact=true)",
            'files:sourceFilesPayload(true)',
            "async function refreshWorkspaceFileCache(onProgress=()=>{})",
            "function renderAnalysisDashboard()",
            "function analysisHeaderMetrics(devices=state.devices)",
            "function renderAnalysisHeaderMetrics(devices=state.devices)",
            "function localVendorFromText(...values)",
            "function localCompatibleRuleValue(mac,rules)",
            "function normalizeVendorDetectorSettings(settings={})",
            'api("/vendor-detector/settings"',
            "function normalizeHistoryEnrichmentSettings(settings={})",
            'api("/history-enrichment/settings"',
            "function vendorModelLearnSettings()",
            "function localRuleValue(mac,rules)",
            "[6,8,10].includes(prefix.length)",
            'api("/vendor-model-history/learn",{method:"POST",body:JSON.stringify(settings)})',
            "applyLocalVendorModelMappings(state.devices);save();renderResults();renderAnalytics();renderHistory();",
            'api("/ip-mappings/import",{method:"POST",body:JSON.stringify({filename:file.name,contentBase64:await fileToBase64(file)})})',
            'api("/ip-mappings/autodetect",{method:"POST",body:JSON.stringify(currentDevicePayload())})',
            'api("/ip-mappings/apply",{method:"POST",body:JSON.stringify(currentDevicePayload({compactResult:Boolean(state.resultSnapshotId),resultPageSize}))})',
            'api("/detection/apply",{method:"POST",body:JSON.stringify(currentDevicePayload({compactResult:true,resultPageSize}))})',
            'api("/history/panel?"+historyQueryParams(query,from,to,limit).toString())',
            "function restoreBootstrapAutosave(autosave)",
            "function localMacChronology(mac)",
            "async function renderMovementHistory()",
            "async function exportMovementHistory()",
            "async function deleteShownMovementHistory()",
            'MacChronology.renderTimeline(events,{formatDate:formatDisplayDateTime})',
            'analytics?.historyRecordsRowsHtml',
            'analytics?.movementRowsHtml',
            '$("#macHistoryStats")',
            'analytics?.detailedReportText',
            'function localDeviceDetailedReport(device={},mac="")',
            "function renderLocalTimeStats()",
            "function showTableContextMenu(event,row)",
            "function handleAppShortcut(event)",
            "function applyResultColumnWidths()",
            "async function saveResultColumnWidths(",
            "async function loadDatabaseHistoryManagement()",
            "async function deleteDatabaseHistoryEntries(ids=[],filters={})",
            'api("/database/history/delete",{method:"POST"',
            'html.timeStatsSummaryHtml',
            'html.timeStatsRowsHtml',
            'persistAutosave("enrichment-analysis").catch(()=>{})',
            'persistAutosave("external-api-enrichment").catch(()=>{})',
            'api("/engineering/login",{method:"POST",body:JSON.stringify({password,ttlMinutes})})',
            'api("/theme",{method:"POST",body:JSON.stringify({theme})})',
            "window.MacAnalyzerAppReady=true",
        ),
    )

    assert "Excel/XLSX требует запущенный backend" not in html
    assert "Excel/XLSX читается через backend" not in app


def test_user_requested_backend_parity_blocks_are_present():
    server = read_text("server.py")
    detector = read_text("backend/services/detection/vendor_detector_service.py")
    device_analytics = read_text("backend/services/analytics/device_analytics_service.py")

    assert_markers(
        server,
        (
            'elif parsed.path == "/api/files/import":',
            "def column_conflict_review_payload",
            'elif parsed.path == "/api/vendor-detector/settings":',
            'elif parsed.path == "/api/history-enrichment/settings":',
            "def import_workspace_table(",
            "table = read_table(filename, content, sheet or None)",
            "file_token = WORKSPACE_FILE_CACHE.put(filename, table)",
            'elif parsed.path == "/api/enrichment/run":',
            'source_created_at = as_text(payload.get("createdAt"))',
            "save_history(valid, source, source_created_at)",
            'elif parsed.path == "/api/vendor-model-history/learn":',
            "for prefix_length in (6, 8, 10):",
            "INSERT INTO vendor_mappings (oui, vendor, source, updated_at) VALUES (?, ?, 'learned', ?)",
            "INSERT INTO model_mappings (prefix, model, source, updated_at) VALUES (?, ?, 'learned', ?)",
            'text_values = [device.get(field) for field in ("model", "description", "name", "hostname", "device_name")]',
            'detector_settings = batch.get("detectorSettings") or normalize_detector_settings({})',
            'history_settings = batch.get("historySettings") or normalize_history_enrichment_settings({})',
            "def build_enrichment_context",
            "def normalize_history_enrichment_settings",
            'elif parsed.path == "/api/history/panel":',
            '"autosave": load_autosave_state("main", hydrate=False)',
            "if new_value != old_value and (new_value or old_value):",
            'elif parsed.path == "/api/ip-mappings/import":',
            'elif parsed.path == "/api/ip-mappings/autodetect":',
            'elif parsed.path == "/api/dashboard":',
            'elif parsed.path == "/api/dashboard/metrics":',
            'elif parsed.path == "/api/engineering/login":',
            'elif parsed.path == "/api/theme":',
            '"timeStatsSummaryHtml": time_summary_rows',
            '"timeStatsRowsHtml": time_history_rows',
            "DEFAULT_RESULT_COLUMN_WIDTHS = {",
            'data-column-width="{escaped_field}"',
            "def database_history_records",
            "def enhanced_movement_history",
            "def export_enhanced_movement_history",
            "def delete_enhanced_movement_history",
            "def save_enhanced_history_column_settings",
            'elif parsed.path == "/api/history/movements":',
            "def delete_database_history_records",
            'elif parsed.path == "/api/database/history/records":',
            'elif parsed.path == "/api/database/history/delete":',
        ),
    )
    assert_markers(
        device_analytics,
        (
            "def chronology_summary_html",
            '"chronology": timeline_rows',
            '"chronologyRowsHtml": chronology_rows_html',
            '"chronologySummaryHtml": chronology_summary_html(metrics)',
            "MAC chronology",
        ),
    )
    assert_markers(
        detector,
        (
            "VENDOR_KEYWORDS = {",
            "def normalize_detector_settings",
            "def detector_rule_allowed",
            "def detect_vendor_from_text",
            "def compatible_mac5_model",
            "text_vendor = detect_vendor_from_text(text_values or [])",
            'return {"value": compatible_rule["model"], "source": "prefix_compatible"',
        ),
    )


def test_user_requested_runtime_tests_cover_the_critical_paths():
    frontend_tests = read_text("tests/test_frontend_event_bindings.py")
    smoke_tests = read_text("tests/test_web_api_ui_smoke.py")

    assert_markers(
        frontend_tests,
        (
            "test_excel_files_are_selectable_in_main_import",
            "test_html_has_startup_fallback_for_tabs_and_file_choice",
            "test_two_file_manual_mapping_supports_name_or_letter_mode",
            "test_local_html_mode_keeps_theme_engineering_and_analytics_working",
            "test_analysis_tab_dashboard_and_mapping_learning_refresh_results",
            "test_html_fallback_supports_local_ip_mapping_without_backend",
            "test_html_fallback_supports_vendor_model_rules_without_backend",
            "test_device_dialog_shows_mac_chronology",
            "test_pyqt_mac_history_dialog_keeps_separate_history_and_movement_tables",
            "test_pyqt_single_device_analytics_text_report_is_rendered_locally_and_from_api",
            "restoreBootstrapAutosave",
            "persistAutosave(\"enrichment-analysis\")",
            "renderLocalTimeStats",
            "test_clipboard_context_menu_and_pyqt_shortcuts_are_available",
            "test_database_history_manager_has_structured_filters_and_scoped_delete",
            "test_enhanced_history_dialog_is_grouped_filterable_exportable_and_persistent",
            "test_ai_column_conflict_dialog_requires_explicit_review_and_mac_mapping",
        ),
    )
    assert_markers(
        smoke_tests,
        (
            "/api/files/import",
            "/api/enrichment/run",
            "/api/dashboard",
            "/api/history/panel",
            "/api/vendor-model-history/learn",
            "/api/history-enrichment/settings",
            "chronologyRowsHtml",
            "bootstrap_with_autosave",
            "LEARN_VENDOR_PREFIX_3BYTE",
            "LEARN_VENDOR_PREFIX_4BYTE",
            "LEARN_VENDOR_PREFIX_5BYTE",
            "timeStatsRowsHtml",
        ),
    )


if __name__ == "__main__":
    test_user_requested_frontend_parity_blocks_are_present()
    test_user_requested_backend_parity_blocks_are_present()
    test_user_requested_runtime_tests_cover_the_critical_paths()
    print("user requested parity audit passed")

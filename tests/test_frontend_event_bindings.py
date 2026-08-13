from pathlib import Path


def read_app_js():
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path("frontend/memory-guard.js"), Path("frontend/file-readers.js"), Path("frontend/state-persistence.js"), Path("frontend/guide.js"), Path("app.js"))
    )


def test_ddio_third_export_is_display_only_and_bound_in_primary_frontend():
    html = read_index_html()
    app = read_app_js()
    ddio = Path("frontend/ddio-overlay.js").read_text(encoding="utf-8")
    assert 'id="ddioFileInput"' in html
    assert 'id="browseDdioFileButton"' in html
    assert 'id="ddioMappingGrid"' in html
    assert '<script src="frontend/ddio-overlay.js?v=20260813.1"></script>' in html
    assert 'loadDdioFile(e.target.files,e.target)' in app
    assert all(field in ddio for field in ('reservationMac', 'reservationIp', 'leaseMac', 'leaseIp'))
    assert '[["deviceId","Device ID"],["reservationMac","MAC резервации"],["reservationIp","IP резервации"],["leaseMac","MAC аренды"],["leaseIp","IP аренды"],["possibleIps","Возможные IP"]]' in app
    assert 'mappingOptionLabel(header,"letter")' in app
    assert 'headers = Array.from({ length: columnCount }' in Path("frontend/file-readers.js").read_text(encoding="utf-8")
    assert 'applyDdioOverlayToResults(body,columns)' in app
    assert 'ddioFile:ddioFilePayload(true)' in app
    assert 'state.ddioOverlay=serverResult.ddioOverlay||{}' in app


def read_index_html():
    return Path("index.html").read_text(encoding="utf-8")


def read_styles_css():
    return Path("styles.css").read_text(encoding="utf-8")


def test_global_process_progress_covers_file_analysis_compare_and_export():
    html = read_index_html()
    app = read_app_js()
    styles = read_styles_css()

    for marker in (
        'id="processProgressPanel"',
        'id="processProgressTitle"',
        'id="processProgressPercent"',
        'id="processProgressBar" max="100" value="0"',
        'id="processProgressDetail"',
    ):
        assert marker in html
    for marker in (
        "function beginProcess(",
        "function updateProcess(",
        "function finishProcess(",
        "function failProcess(",
        'beginProcess("Загрузка файлов"',
        'beginProcess("Обогащение MAC-адресов"',
        'beginProcess("Анализ одного файла"',
        'beginProcess("Сравнение снимков"',
        'beginProcess("Экспорт данных"',
        "async function clientZipEntries(buffer, onProgress = () => {})",
        'onProgress(78, `Чтение строк листа ${',
        'finishProcess(processId,"Обогащение завершено: "+currentDeviceCount()+" устройств")',
    ):
        assert marker in app
    for marker in (
        "function fallbackBeginProcess(",
        "function fallbackUpdateProcess(",
        "function fallbackFinishProcess(",
        "async function runFallbackAnalysis()",
        'fallbackBeginProcess("Загрузка файлов"',
        'fallbackUpdateProcess(processId, 72, "Определение производителей, моделей и адресов")',
    ):
        assert marker in html
    for marker in (
        ".process-progress {",
        ".process-progress.complete",
        ".process-progress.warning",
        ".process-progress.error",
        ".process-progress progress::-webkit-progress-value",
    ):
        assert marker in styles


def test_navigation_tabs_are_hash_routable_and_safe():
    html = read_index_html()
    app = read_app_js()

    assert 'role="tablist"' in html
    assert 'data-view="workspace" role="tab" aria-controls="workspaceView" aria-selected="true"' in html
    assert 'data-view="history" role="tab" aria-controls="historyView" aria-selected="false"' in html
    assert 'id="workspaceView" role="tabpanel"' in html
    assert 'id="automationView" role="tabpanel"' in html

    assert "const viewConfig=" in app
    assert "function normalizeViewName(name)" in app
    assert 'if(name==="iphistory")return"analytics";' in app
    assert 'return Object.prototype.hasOwnProperty.call(viewConfig,name)?name:"workspace";' in app
    assert "function viewFromHash()" in app
    assert 'replace(/^#/,"")' in app
    assert "function renderViewContent(name)" in app
    assert 'if(name==="history")renderHistory();' in app
    assert 'if(name==="analytics")renderAnalytics();' in app
    assert 'if(name==="data"){renderServices();loadDatabaseHistoryManagement();}else if(name==="automation")renderServices();' in app
    assert "function activateView(name,{updateHash=true,render=true}={})" in app
    assert 'b.setAttribute("aria-selected",active?"true":"false")' in app
    assert "panel.hidden=!active" in app
    assert 'history.pushState(null,"","#"+name)' in app
    assert '$$(".nav-item").forEach((b)=>b.setAttribute("aria-controls",b.dataset.view+"View"));' in app
    assert 'event.target.closest?.(".nav-item[data-view]")' in app
    assert 'window.addEventListener("hashchange",()=>view(viewFromHash(),{updateHash:true}));' in app
    assert 'view(viewFromHash(),{updateHash:true,render:false});renderEngineeringState();renderAll();' in app


def test_portable_two_file_import_is_local_first_and_race_safe():
    app = read_app_js()
    html = read_index_html()

    assert 'id="fileInput" type="file" accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm,.xls"' in html
    assert 'id="enrichFileInput" type="file" accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm,.xls"' in html
    assert '<script src="frontend/memory-guard.js?v=20260722.9"></script>' in html
    assert '<script src="frontend/file-readers.js?v=20260722.8"></script>' in html
    assert '<meta name="application-build" content="2026.08.12.2">' in html
    assert 'document.documentElement.dataset.memoryGuard = "ready";' in app
    assert 'document.documentElement.dataset.fileReaders = "ready";' in app
    assert 'document.documentElement.dataset.macAnalyzerApp="ready";' in app
    assert 'async function clientXlsxTable(file, onProgress = () => {}, options = {})' in app
    assert 'async function clientFileRecord(file,fileCreatedAt,onProgress=()=>{})' in app
    assert 'if(backendAvailable)try{fileRecord=await backendFileRecord(file,fileCreatedAt,fileProgress);}' in app
    assert 'if(!fileRecord)fileRecord=await clientFileRecord(file,fileCreatedAt,fileProgress);' in app
    assert 'insertImportedFile(fileRecord,requestedRole,fileIndex);' in app
    assert 'renderFiles();\n        renderMapping();' in app
    assert 'let fileRenderVersion = 0;' in app
    assert 'if(renderVersion!==fileRenderVersion)return;' in app
    assert 'paintLocalFileList(root);\n    if(pendingFileImports.length||!backendAvailable)return;' in app
    assert 'Автономный HTML-режим · XLSX/CSV обрабатываются в браузере' in app


def test_large_second_xlsx_uses_indexeddb_without_blocking_render():
    app = read_app_js()
    html = read_index_html()
    styles = Path("styles.css").read_text(encoding="utf-8")

    assert 'const browserStateDbName = "mac-analyzer-browser-storage-v1";' in app
    assert 'if(!("indexedDB" in window))return reject' in app
    assert 'function compactBrowserState(source)' in app
    assert 'StatePersistence.compactLocalState(source)' in app
    assert 'StatePersistence.compactIndexedState(state)' in app
    assert 'serverBackedResult ? [] : list(source.devices)' in app
    assert 'preserveBrowserRows && !file.fileToken ? list(file.rows).slice(0, workspacePreviewRows) : []' in app
    assert 'localStorage.setItem(key,JSON.stringify(compactBrowserState(state)))' in app
    assert 'scheduleBrowserStateSave(savedAt,options.immediate?0:250);' in app
    assert 'async function flushBrowserStateSave()' in app
    assert 'async function restoreBrowserStateFromIndexedDb()' in app
    assert 'restoreBrowserStateFromIndexedDb().then((restored)' in app
    assert 'let pendingFileImports = [];' in app
    assert 'Чтение Excel в браузере...' in app
    assert 'if(pendingFileImports.length||!backendAvailable)return;' in app
    import_success = app.index('insertImportedFile(fileRecord,requestedRole,fileIndex);')
    immediate_render = app.index('renderFiles();', import_success)
    persistent_save = app.index('save();', import_success)
    assert immediate_render < persistent_save

    assert 'const fallbackBrowserDbName = "mac-analyzer-browser-storage-v1";' in html
    assert 'function fallbackScheduleBrowserSave(payload)' in html
    assert 'function fallbackCompactState()' in html
    assert 'async function fallbackLoadIndexedState()' in html
    assert 'fallbackLoadIndexedState().then((restored)' in html
    assert '.file-row-pending' in styles


def test_cross_browser_restore_prefers_compact_sqlite_workspace():
    app = read_app_js()
    server = Path("server.py").read_text(encoding="utf-8")

    assert 'if(fileRecord.fileToken&&!fileRecord.clientImported)return true;' in app
    assert 'const data=await api("/autosave?slot=main&compact=1")' in app
    assert 'state.backendAutosaveUpdatedAt=result.updatedAt||state.backendAutosaveUpdatedAt||"";' in app
    assert 'function shouldRestoreBootstrapAutosave(autosave)' in app
    assert 'if(!merged.resultSnapshotId&&merged.activeSnapshotId)' in app
    assert 'async function restoreInitialState()' in app
    assert 'const backendSynced=browserOnlyMode?false:await syncFromBackend();' in app
    assert 'const restored=await restoreBrowserStateFromIndexedDb();' in app
    assert 'const folderRestored=await restoreLocalFolderHandle({preferBrowserState:restored});' in app
    assert 'if(!backendSynced){' in app
    assert 'if(!folderRestored&&!restored)await restorePortableDatabaseHandle();' in app
    assert '"autosave": load_autosave_state("main", hydrate=False)' in server
    assert 'state = load_autosave_state(query.get("slot", ["main"])[0], hydrate=not compact)' in server
    assert 'state["devices"] = []' in server
    assert '{**item, "rows": []}' in server


def test_migrated_controls_have_single_backend_binding():
    app = read_app_js()

    assert app.count('$("#multiCompareButton").addEventListener') == 1
    assert app.count('$("#exportDashboardButton").addEventListener') == 1
    assert app.count('$("#exportExcelButton").addEventListener') == 1
    assert app.count('$("#exportHistoryButton").addEventListener') == 1
    assert app.count('$("#exportPdfButton").addEventListener') == 1
    assert '["#engineeringLoginButton","#appModeButton","#brandModeButton","#modeContextAction"]' in app
    assert app.count('$("#saveColumnsButton").addEventListener') == 1
    assert app.count('$("#resetColumnsButton").addEventListener') == 1
    assert app.count('$("#addCustomColumnButton").addEventListener') == 1
    assert app.count('$("#columnPreferenceList").addEventListener') == 3
    assert app.count("function compare()") == 1

    assert 'multiCompareButton").addEventListener("click",multiCompare,true)' in app
    assert 'exportDashboardButton").addEventListener("click",(event)=>' in app
    assert 'exportExcelButton").addEventListener("click",()=>exportData("spreadsheetml"))' in app
    assert 'exportHistoryButton").addEventListener("click",async()=>{try{await exportHistory();}' in app
    assert 'exportPdfButton").addEventListener("click",async()=>{try{await exportManagedBinary("pdf");}' in app
    assert 'api("/engineering/login"' in app
    assert 'api("/engineering/logout"' in app
    assert 'api("/engineering/verify"' not in app
    assert 'ss:Name="MAC Analyzer"' in app
    assert "'<tr><th>Дата</th><th>Снимок</th><th>Устройств</th><th>Источник</th></tr>'" not in app

def test_full_xlsx_export_includes_analytics_changes_and_mac_history():
    app = read_app_js()
    html = read_index_html()
    report = Path("frontend/full-xlsx-report.js").read_text(encoding="utf-8")

    assert 'id="exportFullXlsxButton"' in html
    assert "Скачать всё XLSX" in html
    assert '<script src="frontend/full-xlsx-report.js?v=20260729.1"></script>' in html
    assert "async function exportFullWorkbook()" in app
    assert "const FullXlsxReport = window.MacAnalyzerFullXlsxReport;" in app
    assert "FullXlsxReport.buildReport({" in app
    assert "streamFullReportSnapshotRows" in app
    assert "streamFullReportInvalidRows" in app
    assert 'deliverDownload(`mac-analyzer-full-${date}.xlsx`,result.blob)' in app
    assert app.count('$("#exportFullXlsxButton").addEventListener') == 1
    assert "function fullExportDeviceColumns()" not in app
    assert "function fullExportHistoryGroups(" not in app
    for sheet in ("Сводка", "Устройства", "Аналитика", "Выгрузки", "Изменения", "Ошибки", "Исходные файлы", "Справочники", "Настройки", "История MAC"):
        assert f'sheetName: "{sheet}"' in report or f'? "{sheet}"' in report
    assert "async function buildReport(options = {})" in report
    assert "function historyGroups(" in report
    assert "window.MacAnalyzerFullXlsxReport" in report


def test_single_snapshot_compare_uses_backend_snapshot_resolver():
    app = read_app_js()

    assert 'function comparisonPayload(exportFormat="")' in app
    assert 'return {snapshots:finalDashboardSnapshots(),baselineId:$("#baselineSelect").value,currentId:$("#comparisonSelect").value,fields,exportFormat};' in app
    assert 'api("/compare/snapshots",{method:"POST",body:JSON.stringify(payload)})' in app
    assert 'api("/compare",{method:"POST",body:JSON.stringify(payload.body)})' not in app
    assert 'baselineDevices:baseline.devices||[],currentDevices:current.devices||[]' not in app
    assert 'const current=state.snapshots.find((item)=>item.id===$("#comparisonSelect").value)' not in app


def test_multi_snapshot_compare_uses_backend_snapshot_resolver():
    app = read_app_js()

    assert 'async function multiCompare(event)' in app
    assert 'const baselineId=$("#baselineSelect").value;' in app
    assert 'const comparisonIds=Array.from($("#multiComparisonSelect").selectedOptions).map((option)=>option.value).filter((id)=>id!==baselineId).slice(0,10);' in app
    assert 'api("/compare/snapshots/many",{method:"POST",body:JSON.stringify({snapshots:state.snapshots,baselineId,comparisonIds,fields})})' in app
    assert 'api("/compare/many",{method:"POST",body:JSON.stringify({baselineDevices:baseline.devices||[],comparisons,fields})})' not in app
    assert 'const baseline=state.snapshots.find((item)=>item.id===$("#baselineSelect").value)' not in app
    assert 'const comparisons=selectedIds.map((id)=>' not in app
    assert 'const snapshot=state.snapshots.find((item)=>item.id===id)' not in app


def test_comparison_result_uses_backend_html_payload():
    app = read_app_js()

    assert 'function renderComparisonResult(result)' in app
    assert '$("#comparisonBody").innerHTML=result.changesRowsHtml||result.emptyRowsHtml||' in app
    assert '$("#comparisonSummary").innerHTML=result.summaryHtml||' in app
    assert 'function localSnapshotById(id)' in app
    assert 'const paired=DeviceIdentity.pairSets(baseline.devices||[],current.devices||[])' in app
    assert 'function localComparisonPayload(payload=comparisonPayload())' in app
    assert 'async function storedLocalComparisonPayload(payload=comparisonPayload())' in app
    assert 'function localComparisonExport(result,format)' in app
    assert 'renderComparisonResult(await storedLocalComparisonPayload(payload));' in app
    assert 'const exported=localComparisonExport(await storedLocalComparisonPayload(payload),format);' in app
    assert 'renderLocalSnapshotOptions();' in app
    assert 'rows.map((change)=>"<tr>"+[' not in app
    assert '(result.sets||[]).map((item)=>esc(item.name)' not in app
    assert '$("#comparisonSummary").innerHTML="<h2>Массовое сравнение</h2>' not in app


def test_backend_export_paths_are_still_wired():
    app = read_app_js()

    for marker in (
        'api("/bootstrap")',
        'api("/export",{method:"POST",body:JSON.stringify(currentDevicePayload({format:type,columns,ouiSettings}))})',
        'files:sourceFilesPayload(true)',
        'if(cacheError.status!==409)throw cacheError;',
        'await refreshWorkspaceFileCache((value,detail)=>updateProcess(processId,38+Math.round(value*0.12),detail));',
        'api("/columns/detect",{method:"POST",body:JSON.stringify({headers:file.headers.map((h)=>h.name),rows:file.rows.slice(1,101),ai,mode})})',
        'api("/mapping/summary",{method:"POST",body:JSON.stringify({headers:file.headers.map((h)=>h.name),mapping:file.mapping||{},fields})})',
        'api("/quality/reports?limit=5")',
        'api("/quality/panel",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload({invalid:state.invalid,source:"current-browser-dataset",save:true}):{devices:dashboardDevices(),invalid:state.invalid,source:"current-browser-dataset",save:true})})',
        'api("/device/analytics",{method:"POST",body:JSON.stringify(currentDevicePayload({mac:normalized,snapshots:state.snapshots}))})',
        'api("/model/analytics",{method:"POST",body:JSON.stringify(currentDevicePayload({model}))})',
        'api("/analytics/panel",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload({snapshots}):{devices,snapshots})})',
        'api("/topology",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload():{devices})})',
        'api("/charts",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload({snapshots:state.snapshots,exportFormat:"svg"}):{devices:dashboardDevices(),snapshots:state.snapshots,exportFormat:"svg"})})',
        'exportData("spreadsheetml")',
        'api("/statistics/snapshots/export?"+params.toString())',
        'api("/database/snapshots/delete",{method:"POST",body:JSON.stringify({})})',
        'api("/compare/snapshots",{method:"POST",body:JSON.stringify(payload)})',
        'api("/compare/snapshots/many",{method:"POST",body:JSON.stringify({snapshots:state.snapshots,baselineId,comparisonIds,fields})})',
        'api("/mappings/vendors",{method:"POST",body:JSON.stringify({key:oui,value:name})})',
        'api("/mappings/models",{method:"POST",body:JSON.stringify({key:p,value:name})})',
        'api("/mappings/"+(v?"vendors/":"models/")+encodeURIComponent(v||m),{method:"DELETE"})',
        'api("/columns/preferences/results",{method:"POST",body:JSON.stringify({order,visible:columns,custom,widths:state.columnWidths})})',
        'api("/columns/preferences/results",{method:"DELETE"})',
        'api("/columns/preferences/results",{method:"POST",body:JSON.stringify({action:"move",column:field,direction})})',
        'api("/theme",{method:"POST",body:JSON.stringify({theme})})',
        'api("/oui/settings",{method:"POST",body:JSON.stringify({settings})})',
        'api("/dashboard/settings")',
        'api("/dashboard",{method:"POST",body:JSON.stringify(currentDevicePayload({snapshots:state.snapshots,movements:state.movementHistory,settings:state.dashboardSettings,saveSettings:true,compactResult:Boolean(state.resultSnapshotId),resultPageSize:500}))})',
        'api("/autosave?slot=main",{method:"DELETE"})',
        'api("/backup/export",{method:"POST",body:JSON.stringify({state:compactAnalysisAutosaveState()})})',
        'api("/backup/restore",{method:"POST",body:JSON.stringify({filename:file.name,contentBase64:await fileToBase64(file)})})',
        'api("/external-enrichment/settings",{method:"POST",body:JSON.stringify({settings})})',
        'api("/external-enrichment/run",{method:"POST",body:JSON.stringify(currentDevicePayload({createdAt:sourceCreatedAt,saveHistory:true,compactResult:true,resultPageSize:resultPageSize}))})',
        'api("/external-enrichment/test",{method:"POST",body:JSON.stringify({mac})})',
        'exportManagedBinary("xlsx")',
        'exportManagedBinary("pdf")',
        'exportDashboard();',
        'exportComparison("excel")',
        'exportComparison("csv")',
        'exportComparison("txt")',
    ):
        assert marker in app


def test_workspace_navigation_renders_compact_results():
    app = read_app_js()

    assert 'function renderViewContent(name){if(name==="workspace"){renderFiles();renderMapping();renderMetrics();renderResults();return Promise.resolve();}' in app
    assert 'UiFeedback?.start("Открытие вкладки…")' in app
    assert 'function activateView(name,{updateHash=true,render=true}={})' in app
    assert 'if(render)scheduleViewContent(name);return name;' in app
    assert 'function scheduleViewContent(name)' in app


def test_excel_files_are_selectable_in_main_import():
    html = Path("index.html").read_text(encoding="utf-8")
    app = read_app_js()

    assert 'id="fileInput" type="file" accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm,.xls"' in html
    assert 'id="enrichFileInput" type="file" accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm,.xls"' in html
    assert 'id="singleFileInput" type="file" accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm,.xls"' in html
    assert 'id="browseFilesButton" type="button"' in html
    assert 'id="browseEnrichmentFilesButton" type="button"' in html
    assert 'id="singleBrowseFileButton" type="button"' in html
    assert 'id="fileImportStatus"' in html
    assert "CSV, TSV, JSON, Excel" in html
    assert 'title="CSV, TSV, TXT, JSON, XLSX, XLSM, XLS"' in html
    assert "Поддерживаются CSV, TSV, TXT, JSON, XLSX, XLSM и XLS." in html
    assert '<details class="advanced" open>' in html
    assert '$("#dropZone").addEventListener("drop"' in app
    assert 'loadFiles(e.dataTransfer.files,null,"auto")' in app
    assert 'loadFiles(e.target.files,e.target,"primary")' in app
    assert '$("#browseFilesButton")?.addEventListener("click",()=>$("#fileInput")?.click())' in app
    assert '$("#browseEnrichmentFilesButton")?.addEventListener("click",()=>$("#enrichFileInput")?.click())' in app
    assert '$("#enrichFileInput")?.addEventListener("change",(e)=>loadFiles(e.target.files,e.target,"smartroom"))' in app
    assert '$("#singleBrowseFileButton")?.addEventListener("click",()=>$("#singleFileInput")?.click())' in app
    assert 'const importStatus=$("#fileImportStatus");' in app


def test_html_has_startup_fallback_for_tabs_and_file_choice():
    html = Path("index.html").read_text(encoding="utf-8")
    app = read_app_js()

    assert "window.MacAnalyzerAppReady=true" in app
    assert "window.MacAnalyzerFallbackReady = true" in html
    assert 'if (window.MacAnalyzerAppBootstrapped || window.MacAnalyzerAppReady) return;' in html
    assert '$$(".nav-item").forEach((button) => button.addEventListener("click", () => fallbackView(button.dataset.view)))' in html
    assert '$("#browseFilesButton")?.addEventListener("click", () => $("#fileInput")?.click());' in html
    assert '$("#browseEnrichmentFilesButton")?.addEventListener("click", () => $("#enrichFileInput")?.click());' in html
    assert '$("#singleBrowseFileButton")?.addEventListener("click", () => $("#singleFileInput")?.click());' in html
    assert '$("#fileImportStatus").textContent = "Чтение файлов: " + files.map((file) => file.name).join(", ");' in html
    assert '$("#fileInput")?.addEventListener("change", (event) => loadFallbackFiles(event.target.files, event.target, "primary"))' in html
    assert '$("#enrichFileInput")?.addEventListener("change", (event) => loadFallbackFiles(event.target.files, event.target, "smartroom"))' in html
    assert "fallbackState.files = []" not in html
    assert "const beforeCount = fallbackState.files.length;" in html
    assert "Всего файлов: ${fallbackState.files.length}, добавлено: ${fallbackState.files.length - beforeCount}" in html
    assert "async function parseFallbackFile(file)" in html
    assert "const fileCreatedAt = file && Number(file.lastModified || 0) > 0 ? new Date(Number(file.lastModified)).toISOString() : new Date().toISOString();" in html
    assert "createdAt: fileCreatedAt" in html
    assert "async function parseXlsxFile(file)" in html
    assert "async function zipEntries(buffer)" in html
    assert 'rows = await parseXlsxFile(file);' in html
    assert "Excel/XLSX требует запущенный backend" not in html
    assert "Файл обработан в браузере без backend." in html


def test_html_fallback_preserves_snapshots_and_movement_history():
    html = Path("index.html").read_text(encoding="utf-8")

    for marker in (
        "snapshots: []",
        "movementHistory: []",
        'if (viewName === "history") renderFallbackHistory();',
        "function fallbackPushSnapshot(name, source, devices, createdAt = new Date().toISOString())",
        "function fallbackCompareDevices(before = [], after = [])",
        "function fallbackPreserveBeforeAnalysis(source)",
        "function fallbackRecordMovements(beforeDevices, afterDevices, source, changedAt)",
        "function renderFallbackHistory()",
        "const createdAt = fallbackState.files[0]?.createdAt || new Date().toISOString();",
        'data-fallback-snapshot="${esc(snapshot.id)}"',
        "fallbackPreserveBeforeAnalysis(source);",
        "fallbackRecordMovements(previousDevices, fallbackState.devices, source, createdAt);",
        'fallbackPushSnapshot("Analysis: " + source, source, fallbackState.devices, createdAt);',
        '$("#historyBody")?.addEventListener("click", (event) => {',
    ):
        assert marker in html


def test_html_fallback_supports_local_ip_mapping_without_backend():
    html = Path("index.html").read_text(encoding="utf-8")

    for marker in (
        "ipMappings: []",
        'if (viewName === "data") renderFallbackIpMappings();',
        "function normalizeIp(value)",
        "function fallbackIpMappingRows()",
        "function renderFallbackIpMappings()",
        "function upsertFallbackIpMapping(switchIp, address, source = \"manual\")",
        "async function importFallbackIpMappings(file)",
        "function applyFallbackIpMappings()",
        "function inferFallbackSwitchAddressMappings(devices = fallbackState.devices, source = \"analysis\")",
        "function exportFallbackIpMappings()",
        "inferFallbackSwitchAddressMappings(fallbackState.devices, source);",
        '$("#addIpMappingButton")?.addEventListener("click", () => {',
        '$("#ipMappingImportInput")?.addEventListener("change", async (event) => {',
        '$("#autoDetectIpMappingsButton")?.addEventListener("click", () => {',
        '$("#applyIpMappingsButton")?.addEventListener("click", () => {',
        '$("#exportIpMappingsButton")?.addEventListener("click", () => {',
        'data-remove-fallback-ip="${esc(item.switchIp)}"',
    ):
        assert marker in html


def test_html_fallback_supports_vendor_model_rules_without_backend():
    html = Path("index.html").read_text(encoding="utf-8")

    for marker in (
        "localVendorMappings: {}",
        "localModelMappings: {}",
        "function fallbackRuleValue(mac, rules)",
        'id="vendorDetectorEnabled"',
        'id="vendorDetectorOui3"',
        'id="vendorDetectorMac5"',
        'id="vendorDetectorText"',
        'id="vendorDetectorInference"',
        'id="vendorDetectorThreshold"',
        'id="saveVendorDetectorSettingsButton"',
        'id="historyEnrichmentEnabled"',
        'id="historyEnrichmentPriority"',
        'id="historyEnrichmentMac5"',
        'id="historyEnrichmentOui"',
        'id="saveHistoryEnrichmentSettingsButton"',
        "function fallbackNormalizeVendorDetectorSettings(settings = {})",
        "function fallbackVendorDetectorSettingsFromUi()",
        "function fallbackApplyVendorDetectorSettings(settings = fallbackState.vendorDetectorSettings)",
        "function fallbackNormalizeHistoryEnrichmentSettings(settings = {})",
        "function fallbackHistoryEnrichmentSettingsFromUi()",
        "function fallbackApplyHistoryEnrichmentSettings(settings = fallbackState.historyEnrichmentSettings)",
        "function fallbackCompatibleRuleValue(mac, rules)",
        "const fallbackVendorKeywords =",
        "function fallbackVendorFromText(...values)",
        "function fallbackVendor(mac)",
        "function fallbackModel(mac)",
        "fallbackVendorFromText(model, rowValue(file, row, \"name\"), row.join(\" \"))",
        "function applyFallbackVendorModelMappings(devices = fallbackState.devices)",
        "function renderFallbackMappings()",
        "function learnFallbackVendorModelMappings()",
        "applyFallbackVendorModelMappings(fallbackState.devices);",
        'data-remove-fallback-vendor',
        'data-remove-fallback-model',
        'id="vendorModelLearnMinCount"',
        'id="vendorModelLearnSource"',
        "function fallbackVendorModelLearnSettings()",
        "function learnFallbackVendorModelMappings(settings = fallbackVendorModelLearnSettings())",
        "const prefixes = [6, 8, 10];",
        "total < minCount || target[prefix]",
        '$("#learnVendorModelButton")?.addEventListener("click", () => {',
        "const settings = fallbackVendorModelLearnSettings();",
        "const result = learnFallbackVendorModelMappings(settings);",
        '$("#addVendorButton")?.addEventListener("click", () => {',
        '$("#addModelButton")?.addEventListener("click", () => {',
        '$("#settingsView")?.addEventListener("click", (event) => {',
        "delete fallbackState.localVendorMappings[vendor];",
        "delete fallbackState.localModelMappings[model];",
    ):
        assert marker in html


def test_html_fallback_persists_state_and_backup_without_backend():
    html = Path("index.html").read_text(encoding="utf-8")

    for marker in (
        'const fallbackStorageKey = "mac-analyzer-html-fallback-state-v1";',
        'function fallbackPersist(reason = "autosave")',
        "localStorage.setItem(fallbackStorageKey, JSON.stringify(payload));",
        "function fallbackLoadPersistedState()",
        "function fallbackRestoreStatePayload(payload)",
        "function renderFallbackAll()",
        "fallbackLoadPersistedState();",
        'window.addEventListener("beforeunload", () => fallbackPersist("beforeunload"));',
        'setInterval(() => fallbackPersist("interval"), 60000);',
        'fallbackPersist("analysis");',
        'fallbackPersist("files-import");',
        'fallbackPersist("mapping-change");',
        'fallbackPersist("ip-mapping-import");',
        'fallbackPersist("vendor-model-learn");',
        '$("#saveBackupButton")?.addEventListener("click", () => {',
        'fallbackDownload("mac-analyzer-html-backup.json", JSON.stringify(payload, null, 2), "application/json");',
        '$("#saveAutosaveButton")?.addEventListener("click", () => {',
        '$("#restoreAutosaveButton")?.addEventListener("click", () => {',
        '$("#deleteAutosaveButton")?.addEventListener("click", () => {',
        '$("#restoreBackupInput")?.addEventListener("change", async (event) => {',
    ):
        assert marker in html


def test_frontend_exports_do_not_duplicate_backend_generators():
    app = read_app_js()

    for legacy_marker in (
        'JSON.stringify(exportDevices,null,2)',
        'exportDevices=state.devices.map((item)=>({...item,oui:formatOui(item)}))',
        'const formatOui = (device)',
        'Backend экспорт недоступен, использован локальный экспорт',
        'mac-analysis-"+date+".yaml',
        'mac-analysis-"+date+".txt',
        'mac-analysis-"+date+".html',
        'old=new Map(a.devices.map',
        'fresh=new Map(b.devices.map',
        'function makeDevice(',
        'function detectFromSamples(',
        'detectFromSamples(state.files[0])',
        'function detect(headers)',
        'mapping:detect(headers)',
        'mapping=detect(state.files[0].headers)',
        'Backend недоступен, использован локальный детектор',
        'byMac=new Map',
        'локальный fallback',
        'результат сохранён локально',
    ):
        assert legacy_marker not in app


def test_mapping_rules_are_backend_first():
    app = read_app_js()

    for marker in (
        'await api("/mappings/vendors",{method:"POST",body:JSON.stringify({key:oui,value:name})})',
        'await api("/mappings/models",{method:"POST",body:JSON.stringify({key:p,value:name})})',
        'await api("/mappings/"+(v?"vendors/":"models/")+encodeURIComponent(v||m),{method:"DELETE"})',
        'async function renderMappings()',
        'const data=await api("/mappings/panel");',
        '$("#vendorMappingList").innerHTML=data.vendorRowsHtml||',
        '$("#modelMappingList").innerHTML=data.modelRowsHtml||',
        "await syncFromBackend();await renderMappings();",
    ):
        assert marker in app

    for legacy_marker in (
        "const vendorsBuiltIn =",
        "const modelsBuiltIn =",
        "const modelFor =",
        "vendors:{...vendorsBuiltIn}",
        "models:{...modelsBuiltIn}",
        "state.vendors =",
        "state.models =",
        "function renderMappings(){const draw=(root,data,kind)=>$(root).innerHTML=Object.entries(data)",
        'draw("#vendorMappingList",state.vendors,"vendor")',
        'draw("#modelMappingList",state.models,"model")',
        'const draw=(root,rules,kind)=>',
        '(rules||[]).slice(0,100).map((item)=>',
        'data.vendorRules||[]',
        'data.modelRules||[]',
        "state.vendors[oui]=name",
        "state.models[p]=name",
        "delete state.vendors",
        "delete state.models",
        'Promise.all([api("/mappings/vendors"),api("/mappings/models")])',
        "Правило сохранено только локально",
        "Правило удалено только локально",
    ):
        assert legacy_marker not in app


def test_snapshot_history_delete_uses_bulk_backend_endpoint():
    app = read_app_js()
    html = read_index_html()

    assert app.count('$("#clearHistoryButton").addEventListener') == 1
    assert 'api("/database/snapshots/delete",{method:"POST",body:JSON.stringify({})})' in app
    assert 'api("/database/snapshots/delete",{method:"POST",body:JSON.stringify({ids})})' in app
    assert "async function deleteSelectedSnapshots()" in app
    assert "BrowserSnapshots?.removeSnapshot?.(id)" in app
    assert 'id="deleteSelectedSnapshotsButton"' in html
    assert 'id="selectAllSnapshots"' in html
    assert 'data-snapshot-select' in app

    for legacy_marker in (
        'snapshots.map((item)=>api("/snapshots/"+encodeURIComponent(item.id),{method:"DELETE"}))',
        "Promise.allSettled(snapshots.map",
    ):
        assert legacy_marker not in app


def test_column_preferences_are_backend_first():
    app = read_app_js()

    for marker in (
        "async function renderColumnPreferences()",
        'api("/columns/preferences/results/render",{method:"POST",body:JSON.stringify({preferences:columnPreferencesPayload(),labels})})',
        "root.innerHTML=data.listHtml||data.emptyListHtml",
        "function applyColumnPreferences(preferences)",
        "function columnPreferencesPayload(overrides={})",
        "applyColumnPreferences(result.preferences);toast(",
        'api("/columns/preferences/results",{method:"POST",body:JSON.stringify({order,visible:columns,custom,widths:state.columnWidths})})',
        'api("/columns/preferences/results",{method:"DELETE"})',
        'api("/columns/preferences/results",{method:"POST",body:JSON.stringify({action:"move",column:field,direction})})',
        'JSON.stringify(columnPreferencesPayload({order:nextOrder,visible:nextVisible,customKeys:nextCustom,customColumnMappings:nextMappings,labels:nextLabels}))',
        "function applyResultColumnWidths()",
        "function resizeResultColumn(event)",
        "function optimizedResultColumnWidths()",
        "function resultColumnWidthsFromInputs()",
        "async function saveResultColumnWidths(",
        "async function loadResultColumnWidths()",
        'window.addEventListener("pointermove",resizeResultColumn)',
        '$("#optimizeColumnWidthsButton").addEventListener("click",optimizeResultColumnWidths)',
        '$("#resetColumnWidthsButton").addEventListener("click",resetResultColumnWidths)',
    ):
        assert marker in app

    for legacy_marker in (
        "Колонки сохранены локально",
        "Column order saved locally",
        "state.visibleColumns=columns;state.columnOrder=order;save();renderResults();",
        "state.visibleColumns=empty().visibleColumns;state.columnOrder=empty().columnOrder;",
        "state.customColumns.push(key)",
        "delete state.customColumnMappings[field]",
        "state.visibleColumns.push(key)",
        "state.customColumns=state.customColumns.filter",
        '$("#columnPreferenceList").innerHTML=fields.map((field,index)=>',
        'data-move-column="\'+field',
        'data-remove-custom-column="\'+field',
    ):
        assert legacy_marker not in app


def test_theme_and_oui_preferences_are_backend_first():
    app = read_app_js()
    html = read_index_html()

    for marker in (
        'async function saveThemePreference(theme){try{const result=await api("/theme"',
        'function syncThemeControls(theme)',
        'function showThemeSelection()',
        '$("#themeButton").addEventListener("click",showThemeSelection)',
        '$("#themeDialog").addEventListener("click",(e)=>',
        'function applyOuiPreference(settings)',
        'async function saveOuiPreference(settings){try{const result=await api("/oui/settings"',
        'saveOuiPreference({length:Number(e.target.value),style:state.ouiStyle});',
        'saveOuiPreference({length:state.ouiLength,style:e.target.value});',
    ):
        assert marker in app

    for legacy_marker in (
        "Theme saved locally",
        "state.ouiLength=Number(e.target.value);save();renderResults();saveOuiPreference();",
        "state.ouiStyle=e.target.value;save();renderResults();saveOuiPreference();",
        'toast("Тема изменена.")',
    ):
        assert legacy_marker not in app

    for marker in (
        'id="themeDialog"',
        'data-theme-dialog-choice="dark"',
        'data-theme-dialog-choice="light"',
        '<strong>Темная</strong>',
        '<strong>Светлая</strong>',
        'id="themeDialogCloseButton"',
    ):
        assert marker in html


def test_local_html_mode_keeps_theme_engineering_and_analytics_working():
    app = read_app_js()
    html = Path("index.html").read_text(encoding="utf-8")

    for marker in (
        'catch(error){applyTheme(theme);toast("Тема переключена локально.");}',
        'String(state.engineeringToken||"").startsWith("local-")',
        'state.engineeringToken="local-"+crypto.randomUUID()',
        'function localTally(items,key,limit=8)',
        'function renderLocalAnalytics(devices=dashboardDevices())',
        'function applyLocalDashboard(settings=dashboardSettings())',
        'function analyzeLocalQuality()',
    ):
        assert marker in app

    for marker in (
        'function applyFallbackTheme(theme)',
        'function renderFallbackEngineering()',
        'function renderFallbackAnalytics()',
        'function fallbackDownload(filename, content, type = "text/plain")',
        'function showFallbackThemeSelection()',
        '$("#themeButton")?.addEventListener("click", showFallbackThemeSelection)',
        '$("#themeDialog")?.addEventListener("click", (event) => {',
        'const theme = event.target.dataset.themeChoice;',
        '["#engineeringLoginButton", "#appModeButton", "#brandModeButton", "#modeContextAction"]',
        '$("#dashboardVendorFilter")?.addEventListener("change", renderFallbackAnalytics)',
        '$("#dashboardRoomFilter")?.addEventListener("change", renderFallbackAnalytics)',
        '$("#qualityAnalysisButton")?.addEventListener("click", () => {',
        'renderFallbackAnalytics();',
    ):
        assert marker in html


def test_external_api_runtime_uses_persisted_backend_settings():
    app = read_app_js()

    assert 'saveExternalApiSettingsButton").addEventListener("click",saveExternalApiSettings)' in app
    assert 'api("/external-enrichment/run",{method:"POST",body:JSON.stringify(currentDevicePayload({createdAt:sourceCreatedAt,saveHistory:true,compactResult:true,resultPageSize:resultPageSize}))})' in app
    assert 'if(!state.resultSnapshotId&&!backendAvailable&&state.devices.length>(MemoryGuard.limits.inlineComparisonRows||20000))' in app
    assert 'settings:externalApiSettings(),saveHistory:true' not in app
    assert 'body:JSON.stringify({mac,settings:externalApiSettings()})' not in app
    assert 'unknown=state.devices.filter((item)=>item.vendor==="Unknown"||!item.vendor)' not in app
    assert 'macs:unknown.map((item)=>item.mac)' not in app


def test_pyqt_api_settings_dialog_is_available_with_local_html_fallback():
    app = read_app_js()
    html = read_index_html()

    for marker in (
        'id="openApiSettingsDialogButton"',
        'id="apiSettingsDialog"',
        'id="apiSettingsServiceSelect"',
        '<option value="mac2vendor">mac2vendor - mac2vendor.com</option>',
        'id="apiSettingsTestMacInput"',
        'id="apiSettingsTestButton"',
        'id="apiSettingsTestResult"',
        'id="apiSettingsSaveButton"',
        'function showFallbackApiSettingsDialog()',
        'function testFallbackApiSettings()',
        'function saveFallbackApiSettingsDialog()',
    ):
        assert marker in html

    for marker in (
        'function applyExternalApiSettings(settings={},providers=[])',
        'function showApiSettingsDialog()',
        'async function testApiSettingsDialog()',
        'async function saveApiSettingsDialog()',
        'JSON.stringify({mac,settings})',
        'if(!normalized){resultNode.textContent="Введите корректный MAC-адрес из 12 шестнадцатеричных символов."',
        '"Найден производитель: "+vendor+" (встроенная HTML-база)"',
        '$("#openApiSettingsDialogButton").addEventListener("click",showApiSettingsDialog)',
    ):
        assert marker in app


def test_bootstrap_sync_uses_backend_payload():
    app = read_app_js()

    assert 'const data = await api("/bootstrap");' in app
    assert 'const restoredFromAutosave=restoreBootstrapAutosave(data.autosave);' in app
    assert 'const snapshotMap=new Map(restoredSnapshots.map((item)=>[item.id,item]));' in app
    assert 'data.snapshots.forEach((item)=>snapshotMap.set(item.id,item));' in app
    assert 'state.snapshots=[...snapshotMap.values()];' in app
    assert 'state.customColumns = data.customColumns || [];' in app
    assert 'state.customColumnMappings = data.customColumnMappings || {};' in app
    assert 'Object.assign(labels, data.customLabels || {});' in app
    assert 'Promise.all([' not in app.split("async function syncFromBackend()", 1)[1].split("const esc =", 1)[0]
    assert 'state.snapshots = snapshotData.snapshots.map' not in app
    assert 'Object.fromEntries((columnData.preferences.custom || []).map((item)=>[item.key,item.sourceIndex]))' not in app


def test_dashboard_settings_are_loaded_from_backend():
    app = read_app_js()

    assert 'dashboardSettings:{query:"",vendor:"",room:"",status:"all",chartLimit:8,showUnknown:true,visibleCards:' in app
    assert 'async function loadDashboardSettings(){try{const result=await api("/dashboard/settings")' in app
    assert 'if(!browserOnlyMode){loadThemePreference();' in app
    assert 'loadDashboardSettings();' in app
    assert 'loadEngineeringSession();' in app
    assert 'let dashboardFilteredDevices = null;' in app
    assert 'function dashboardDevices(){return dashboardFilteredDevices||state.devices;}' in app
    assert 'async function loadDashboardPayload(settings=dashboardSettings())' in app
    assert 'dashboardFilteredDevices=data.devices||state.devices;' in app
    assert 'renderDashboardFilterOptions(data.filters||{},data.settings||settings,data.filterOptionsHtml||{});' in app
    assert 'renderDashboardStatus(data);' in app
    assert 'function dashboardStatusContext()' in app
    assert 'function dashboardMovementCharts(displayed,missing,limit=8)' in app
    assert 'id="dashboardStatusFilter"' in Path("index.html").read_text(encoding="utf-8")
    assert 'function normalizeDashboardSettings(settings={})' in app
    assert 'function configureDashboardAutoRefresh(settings=state.dashboardSettings)' in app
    assert 'function applyDashboardVisibility(settings=state.dashboardSettings)' in app
    assert 'function showDashboardSettingsDialog()' in app
    assert 'saveDashboardSettings(dashboardDialogSettings())' in app
    assert 'function exportLocalDashboardPng()' in app
    assert 'exportFormat:"png"' in app
    assert 'downloadBase64(data.export.filename||"mac-dashboard.png"' in app
    assert 'await exportLocalDashboardPng()' in app
    html = Path("index.html").read_text(encoding="utf-8")
    for marker in (
        'id="dashboardSettingsDialog"',
        'data-dashboard-card-toggle="total"',
        'data-dashboard-card-toggle="rooms"',
        'data-dashboard-chart-toggle="dynamics"',
        'data-dashboard-chart-toggle="missing"',
        'id="dashboardAutoRefresh"',
        'id="dashboardRefreshInterval" type="number" min="10" max="300"',
        'id="resetDashboardSettingsButton"',
        'id="applyDashboardSettingsButton"',
        'id="exportDashboardButton">PNG dashboard</button>',
    ):
        assert marker in html
    assert 'function exportFallbackDashboardPng()' in html
    assert 'exportFallbackDashboardPng();' in html
    assert 'filterOptionsHtml.vendors||' in app
    assert 'filterOptionsHtml.rooms||' in app
    assert '(filters.vendors||[]).map' not in app
    assert '(filters.rooms||[]).map' not in app
    assert 'Array.from(new Set(state.devices.map((d)=>d.vendor))).sort()' not in app
    assert 'Array.from(new Set(state.devices.map((d)=>d.room).filter(Boolean))).sort()' not in app


def test_autosave_delete_is_exposed_in_web_ui():
    app = read_app_js()

    assert 'async function deleteAutosave()' in app
    assert 'api("/autosave?slot=main",{method:"DELETE"})' in app
    assert 'if(status)status.textContent=result.statusText||"Autosave slot updated.";' in app
    assert 'if(status)status.textContent=result.statusText||"Autosaved.";' in app
    assert 'if(status)status.textContent=data.autosave.statusText||"Autosave restored.";' in app
    assert 'function currentWorkspaceIsEmpty()' in app
    assert 'function normalizeRestoredState(restored={})' in app
    assert 'function restoreBootstrapAutosave(autosave)' in app
    assert 'const restoredFromAutosave=restoreBootstrapAutosave(data.autosave);' in app
    assert 'persistAutosave("single-file-analysis").catch(()=>{})' in app
    assert 'persistAutosave("enrichment-analysis").catch(()=>{})' in app
    assert 'persistAutosave("external-api-enrichment").catch(()=>{})' in app
    assert 'deleteAutosaveButton").addEventListener("click",async()=>{try{await deleteAutosave();' in app
    assert 'new Date(result.updatedAt).toLocaleString("ru-RU")' not in app
    assert 'new Date(data.autosave.updatedAt).toLocaleString("ru-RU")' not in app


def test_device_dialog_shows_mac_chronology():
    app = read_app_js()
    html = read_index_html()
    chronology = Path("frontend/mac-chronology.js").read_text(encoding="utf-8")

    for marker in (
        'id="deviceChronologySummary"',
        'id="deviceChronologyBody"',
        "Хронология MAC-адреса",
    ):
        assert marker in html

    for marker in (
        'async function collectLocalMacContext(mac)',
        'MacChronology.collectAppearances',
        'BrowserSnapshots.findDevice(snapshot.id,targetMac)',
        'MacChronology.renderSummary(events,appearances)',
        'MacChronology.renderTimeline(events,{formatDate:formatDisplayDateTime})',
        'function localMacChronology(mac)',
    ):
        assert marker in app
    for marker in ("function buildEvents(options = {})", "function renderTimeline(events, options = {})", "mac-timeline-item"):
        assert marker in chronology


def test_backup_export_restore_use_backend_service():
    app = read_app_js()

    assert 'api("/backup/export",{method:"POST",body:JSON.stringify({state:compactAnalysisAutosaveState()})})' in app
    assert 'api("/backup/export",{method:"POST",body:JSON.stringify({state})})' not in app
    assert 'api("/backup/restore",{method:"POST",body:JSON.stringify({filename:file.name,contentBase64:await fileToBase64(file)})})' in app
    assert 'download("mac-analyzer-backup.json",JSON.stringify(state,null,2),"application/json")' not in app
    assert 'JSON.parse(await e.target.files[0].text())' not in app
    assert 'contentBase64:await fileToBase64(file)' in app


def test_notification_config_json_is_parsed_by_backend():
    app = read_app_js()

    assert 'api("/notifications",{method:"POST",body:JSON.stringify({channel:$("#notificationChannel").value,configText:$("#notificationConfig").value,enabled:$("#notificationEnabled").checked})})' in app
    assert 'api("/notifications/test",{method:"POST",body:JSON.stringify({channel,configText:$("#notificationConfig").value})})' in app
    assert 'JSON.parse($("#notificationConfig").value||"{}")' not in app
    assert 'body:JSON.stringify({...config,channel})' not in app


def test_column_auto_mapping_uses_backend_detector():
    app = read_app_js()

    assert 'function defaultColumnMapping()' in app
    assert 'detectColumnsWithBackend(fileRecord,{mode:"auto",ai:false})' in app
    assert 'autoMapColumnsButton").addEventListener("click",async()=>{const file=selectedMappingFile();if(!file)' in app
    assert 'detectColumnsWithBackend(file,{mode:"auto",ai:false})' in app
    assert 'sampleMapColumnsButton").addEventListener("click",async()=>{const file=selectedMappingFile();if(!file)' in app


def test_main_file_import_uses_backend_service():
    app = read_app_js()

    assert "importErrors:[]" in app
    assert "const networkUnavailable = (error)" in app
    assert "[404,405,501].includes(Number(error?.status||0))" in app
    assert 'apiError.status=response.status;throw apiError;' in app
    assert "async function readClientTextFile(file)" in app
    assert "async function clientReadTable(file, onProgress = () => {}, options = {})" in app
    assert "function clientJsonTable(text)" in app
    assert "function localAutoMapping(headers)" in app
    assert 'async function loadFiles(input, sourceInput=null, requestedRole="auto")' in app
    assert 'api("/files/import-binary",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name),"X-Sheet-Name":"","X-Preview-Rows":"100"},body:file})' in app
    assert 'rowCount:Number(data.rowCount??data.rows?.length??0),rowsComplete:data.compactResult!==true' in app
    assert 'await rememberSourceFile(fileRecord,file)' in app
    assert app.index('await rememberSourceFile(fileRecord,file)') < app.index('insertImportedFile(fileRecord,requestedRole,fileIndex)')
    assert 'await rememberSourceFile(state.files[0],pendingSingleFile);' in app
    assert 'const sourceFile=await restoreSourceFile(fileRecord);' in app
    assert 'async function refreshWorkspaceFileCache(onProgress=()=>{})' in app
    assert 'async function ensureWorkspaceFileCache(onProgress=()=>{})' in app
    assert 'await ensureWorkspaceFileCache((value,detail)=>updateProcess(processId,32+Math.round(value*0.08),detail));' in app
    assert 'const keyName=String(event.key||"").toLowerCase()' in app
    assert 'files:sourceFilesPayload(false),refreshFileCache:true' not in app
    assert "function fileInfoDate(file)" in app
    assert "function primaryFileCreatedAt()" in app
    assert "const fileCreatedAt=fileInfoDate(pendingSingleFile);" in app
    assert "mapping:singleManualMapping(),createdAt:fileCreatedAt,saveHistory:true,saveSnapshot:true" in app
    assert "state.lastAnalysis=fileCreatedAt;" in app
    assert "if(networkUnavailable(error))" in app
    assert "const data=await clientReadTable(file,onProgress,{maxRows:workspacePreviewDataRows}),rows=[data.headers||[],...(data.rows||[])];" in app
    assert "const rowCount=Math.max(0,Number(data.rowCount??rows.length-1)||0),previewRows=rows.slice(0,workspacePreviewDataRows+1);" in app
    assert "rows:previewRows" in app
    assert "rowsComplete:data.truncated!==true&&rowCount<=workspacePreviewDataRows" in app
    assert "async function clientXlsxTable(file, onProgress = () => {}, options = {})" in app
    assert "async function clientZipEntries(buffer, onProgress = () => {})" in app
    assert 'if (/\\.(xlsx|xlsm)$/i.test(file.name)) return clientXlsxTable(file, onProgress, options);' in app
    assert "Excel/XLSX читается через backend" not in app
    assert 'const rows=[data.headers||[],...(data.rows||[])];' in app
    assert 'state.importErrors.push({filename:file.name,message})' in app
    assert 'if(sourceInput)sourceInput.value=""' in app
    assert "Загружено файлов: " in app
    assert "Файл не загружен" in app
    assert "chunkSize=0x8000" in app
    assert "bytes.subarray(offset,offset+chunkSize)" in app
    assert 'class="import-error"' in app
    assert 'sheet:data.sheet||""' in app
    assert 'function parseDelimited(' not in app
    assert 'rows=parseDelimited(text,delimiter)' not in app
    assert 'const text=await file.text(); let rows;' not in app


def test_browser_mode_enrichment_keeps_basic_workflow_alive():
    app = read_app_js()

    assert "async function localAnalyzeFiles(fields,strategy,onProgress=()=>{})" in app
    assert "function mergeAnalysisDevice(previous,incoming,{preferExisting=false}={})" in app
    assert "accumulateResolvedDevice(resolvedDevices,identityIndex,result.device,fileIndex>0)" in app
    assert "const resolution=DeviceIdentity.resolve(incoming,index)" in app
    assert "BrowserSnapshots.mergeEnrichmentRows(jobId,devices,{allowNew,preferExisting})" in app
    assert "async function visitLocalRowsForAnalysis(file,fileIndex,fileCount,onProgress,onRow)" in app
    assert "const sourceFile=await restoreSourceFile(file);" in app
    assert "const data=await clientReadTable(sourceFile,progress,{collectRows:false,onRow});" in app
    assert "await releaseTransientAnalysisMemory();" in app
    assert "function localDeviceFromRow(file,row,rowIndex,fields)" in app
    assert "function localResultsTable()" in app
    assert "function localMappingGrid(file)" in app
    assert "local=await localAnalyzeFiles(enrich,strategy," in app
    assert "function browserEnrichmentFallbackAllowed()" in app
    assert "return totalRows<=(MemoryGuard.limits.browserEnrichmentRows||220000)&&totalBytes<=(MemoryGuard.limits.browserInputBatchBytes||96*1024*1024);" in app
    assert "if(!browserEnrichmentFallbackAllowed())" in app
    assert app.index("if(!browserEnrichmentFallbackAllowed())") < app.index("local=await localAnalyzeFiles(enrich,strategy,")
    assert 'if(fileRecord.clientImported)await rememberSourceFile(fileRecord,file);' in app
    assert 'else{sourceFilesById.delete(fileRecord.id);fileRecord.sourceStorageId="";}' in app
    assert "async function hydrateWorkspaceFilesForBrowser(onProgress=()=>{})" not in app
    assert "await hydrateWorkspaceFilesForBrowser(" not in app
    assert "const items=filtered.slice((resultPage-1)*resultPageSize,resultPage*resultPageSize);" in app
    assert "function localSearchText(item)" in app
    assert "file.rows.slice(1).forEach" not in app
    assert "Автономная локальная база" in app
    assert 'await storeLocalSnapshot("Анализ: "+source,source,state.devices,state.invalid,sourceCreatedAt,"analysis")' in app
    assert "async function replaceConsumedEnrichmentFiles(requestedRole)" in app
    assert "WorkspaceFileLifecycle.selectForNextImport(state.files,requestedRole)" in app
    assert "sourceFilesById.delete(file.id)" in app
    assert 'api("/workspace/cache/discard",{method:"POST",body:JSON.stringify({tokens})})' in app
    assert "const replacedEnrichmentFiles=await replaceConsumedEnrichmentFiles(requestedRole);" in app
    assert "function markEnrichmentFilesConsumed(consumedAt=new Date().toISOString())" in app
    assert "WorkspaceFileLifecycle.markConsumed(state.files,consumedAt)" in app
    assert "markEnrichmentFilesConsumed();" in app
    assert '<script src="frontend/workspace-file-lifecycle.js?v=20260722.7"></script>' in read_index_html()
    assert 'previousComparisonIndex=createLocalComparisonIndex(previousDevices)' in app
    assert 'previousDevices=[];' in app
    assert 'state.devices=[];' in app
    assert 'await MemoryGuard.yieldToMainThread();' in app
    assert "body.innerHTML=localResultsTable();" in app
    assert "Колонки определены в браузере." in app
    assert "Полный результат сохранён порциями в IndexedDB; в памяти оставлена только текущая страница." in app
    assert "Автономная локальная база IndexedDB · результат хранится постранично" in app
    assert 'file.name.toLowerCase().endsWith(".json")' not in app
    assert 'file.name.toLowerCase().endsWith(".xlsx")' not in app


def test_browser_snapshots_are_stored_outside_live_workspace_memory():
    html = Path("index.html").read_text(encoding="utf-8")
    app = read_app_js()
    snapshot_store = Path("frontend/browser-snapshot-store.js").read_text(encoding="utf-8")
    memory_guard = Path("frontend/memory-guard.js").read_text(encoding="utf-8")

    assert '<script src="frontend/browser-snapshot-store.js?v=20260813.1"></script>' in html
    assert '<script src="frontend/xlsx-exporter.js?v=20260727.5"></script>' in html
    assert '<script src="frontend/full-xlsx-report.js?v=20260729.1"></script>' in html
    assert 'const browserStateRecordId = "main-v2";' in app
    assert 'async function storeLocalSnapshot(' in app
    assert 'devices:rows.slice(0,previewLimit)' in app
    assert 'const rowBudget=MemoryGuard.limits.browserSnapshotRows||1000000,keepIds=[];' in app
    assert 'let remainingRows=Math.max(0,rowBudget-rows.length);' in app
    assert 'await BrowserSnapshots.prune(keepIds);' in app
    assert app.index('await BrowserSnapshots.prune(keepIds);') < app.index('await BrowserSnapshots.save(record,(percent)=>')
    assert 'browserSnapshotRows: 1_000_000' in memory_guard
    assert 'const snapshotStore = "snapshots";' in snapshot_store
    assert 'const databaseVersion = 10;' in snapshot_store
    smartroom_store = Path("frontend/smartroom-store.js").read_text(encoding="utf-8")
    smartroom_ui = Path("frontend/smartroom-ui.js").read_text(encoding="utf-8")
    assert 'const databaseVersion = 10;' in smartroom_store
    assert 'const knownModelsStore = "KnownModels";' in smartroom_store
    assert '["by_smartroom", "smartroom_id"]' in smartroom_store
    assert '["by_mac", "mac"]' in smartroom_store
    assert '["by_switch", "ip_switch"]' in smartroom_store
    assert '["by_timestamp", "timestamp"]' in smartroom_store
    assert 'class="possible-ip-dropdown ddio-history-warning"' in app
    assert "IP устройства из DDIO" in app
    assert 'const enrichmentRowStore = "enrichmentRows";' in snapshot_store
    assert 'const deviceHistoryStore = "deviceHistory";' in snapshot_store
    assert 'async function enrichDevicesFromHistory(rows)' in snapshot_store
    assert 'async function enrichEnrichmentRowsFromHistory(jobId)' in snapshot_store
    assert 'async function mergeDeviceHistoryRows(rows, source = "browser-history")' in snapshot_store
    assert 'async function backfillDeviceHistory(snapshotIds = [])' in snapshot_store
    assert 'await BrowserSnapshots.enrichDevicesFromHistory(devices);' in app
    assert 'await BrowserSnapshots.enrichEnrichmentRowsFromHistory(jobId);' in app
    assert 'await BrowserSnapshots?.backfillDeviceHistory?.(historicalSnapshots).catch(()=>0);' in app
    assert 'function applyFallbackDeviceHistory(devices = fallbackState.devices)' in html
    assert 'async function mergeEnrichmentRows(jobId, devices, options = {})' in snapshot_store
    assert 'async function pruneEnrichmentRows(maxAgeMs = 12 * 60 * 60 * 1000)' in snapshot_store
    assert 'updatedAt: Date.now()' in snapshot_store
    assert 'await BrowserSnapshots?.pruneEnrichmentRows?.().catch(()=>0);' in app
    assert 'async function saveEnrichmentSnapshot(jobId, snapshot, invalid = [], onProgress = () => {})' in snapshot_store
    assert 'async function aggregate(id, options = {})' in snapshot_store
    assert 'async function aggregateSeries(snapshots, options = {})' in snapshot_store
    assert 'async function compareSnapshots(baselineId, comparisonId, options = {})' in snapshot_store
    assert 'const criticalMove = Boolean(previous.switchIp && device.switchIp && previous.switchIp !== device.switchIp);' in snapshot_store
    assert 'if (criticalMove || device.hasConflict) result.critical += 1;' in snapshot_store
    assert 'critical: result.critical,' in snapshot_store
    assert 'async function localAnalyzeFilesToSnapshot(fields,strategy,source,createdAt,onProgress=()=>{})' in app
    assert 'local=await localAnalyzeFilesToSnapshot(enrich,strategy,source,sourceCreatedAt' in app
    assert 'const snapshotChunkStore = "snapshotChunks";' in snapshot_store
    assert 'const snapshotChunkRows = 1_000;' in snapshot_store
    assert 'function* chunkRows(rows, size = snapshotChunkRows)' in snapshot_store
    assert 'await transaction(snapshotChunkStore, "readwrite"' in snapshot_store
    assert 'await new Promise((resolve) => setTimeout(resolve, 0));' in snapshot_store
    assert 'const sourceFileStore = "sourceFiles";' in snapshot_store
    assert 'function saveSourceFile(id, file)' in snapshot_store
    assert 'async function loadSourceFile(id)' in snapshot_store
    assert 'async function pruneSourceFiles(keepIds = [])' in snapshot_store
    assert 'saveSourceFile,' in snapshot_store
    assert 'loadSourceFile,' in snapshot_store
    assert 'await BrowserSnapshots?.saveSourceFile?.(fileRecord.sourceStorageId,file)' in app
    assert 'BrowserSnapshots.page?.(state.resultBrowserSnapshotId,{offset:0,limit:resultPageSize})' in app
    assert 'if(state.resultBrowserSnapshotId&&BrowserSnapshots)' in app
    assert 'if(state.resultBrowserSnapshotId&&!state.devices.length&&BrowserSnapshots)' not in app
    assert 'BrowserSnapshots.page(state.resultBrowserSnapshotId,{query:' in app
    assert 'state.devices.length=0;state.invalid.length=0;state.devices=firstPage;state.invalid=invalidPreview;' in app
    assert 'Полный результат сохранён порциями в IndexedDB; в памяти оставлена только текущая страница.' in app
    assert 'function createPageCollector(options = {})' in snapshot_store
    assert 'async function page(id, options = {})' in snapshot_store


def test_xlsx_reader_uses_file_backed_zip_slices():
    readers = Path("frontend/file-readers.js").read_text(encoding="utf-8")
    app = read_app_js()
    memory_guard = Path("frontend/memory-guard.js").read_text(encoding="utf-8")
    xlsx_reader = readers.split("async function clientXlsxTable", 1)[1].split("async function clientReadTable", 1)[0]

    assert "async function clientZipFileDirectory(file)" in readers
    assert 'file.slice(tailOffset, fileSize).arrayBuffer()' in readers
    assert 'file.slice(centralOffset, centralOffset + centralSize).arrayBuffer()' in readers
    assert '? directory.file.slice(entry.start, entry.start + entry.size)' in readers
    assert "const directory = await clientZipFileDirectory(file);" in xlsx_reader
    assert "file.arrayBuffer()" not in xlsx_reader
    assert 'await restoreWorkspaceSourceFiles();' in app
    assert 'let previousDevices=state.devices||[];' in app
    assert 'snapshotPreviewRows: 500' in memory_guard
    assert 'localExportRows: 20_000' in memory_guard
    assert 'localExportCells: 250_000' in memory_guard
    assert 'MemoryGuard.assertLocalExportCapacity(state.devices.length,state.devices.length*exportColumns().length)' in app
    assert 'const autosaveState=compactAnalysisAutosaveState();fetch("/api/autosave"' in app
    assert 'reason==="enrichment-analysis"||reason==="single-file-analysis"' not in app


def test_room_occupancy_analytics_is_wired_in_browser_and_backend_views():
    html = Path("index.html").read_text(encoding="utf-8")
    app = read_app_js()

    assert 'id="roomOccupancyStatus"' in html
    assert 'id="roomOccupancyChart"' in html
    assert 'const allRoomCounts=new Map()' in app
    assert 'roomOccupancy={assignedDevices:room,unassignedDevices:total-room' in app
    assert '=== ЗАПОЛНЕННОСТЬ ПОМЕЩЕНИЙ ===' in app


def test_two_file_manual_mapping_supports_name_or_letter_mode():
    html = Path("index.html").read_text(encoding="utf-8")
    app = read_app_js()
    server = Path("server.py").read_text(encoding="utf-8")

    for marker in (
        'id="mappingFileSelect"',
        'id="mappingDisplayMode"',
        '<option value="letter">Буква колонки</option>',
        'id="copyMappingToAllButton"',
    ):
        assert marker in html

    for marker in (
        "activeMappingFileId",
        "mappingDisplayMode",
        "function columnLetter(index)",
        "function selectedMappingFile()",
        "function renderMappingControls()",
        "const root=$(\"#mappingGrid\"),file=selectedMappingFile()||state.files[0];",
        'file.mappingDisplayMode=state.mappingDisplayMode||"name";',
        'data-file-id="${esc(file.id)}"',
        'root.querySelectorAll("[data-file-id]").forEach((row)=>row.classList.toggle("active-file",row.dataset.fileId===state.activeMappingFileId));',
        '$("#fileList").addEventListener("click",(e)=>{const id=e.target.dataset.removeFile,row=e.target.closest("[data-file-id]");',
        "state.activeMappingFileId=row.dataset.fileId;save();renderFiles();renderMapping();",
        '$("#mappingFileSelect").addEventListener("change"',
        '$("#mappingDisplayMode").addEventListener("change"',
        '$("#copyMappingToAllButton").addEventListener("click"',
        "state.files.forEach((item)=>{item.mapping={...file.mapping};localMappingSummary(item);});",
    ):
        assert marker in app

    assert 'display_mode = as_text(file_item.get("mappingDisplayMode")) or "name"' in server
    assert 'data-file-id="{html_lib.escape(as_text(file_item.get("id")), quote=True)}"' in server
    assert 'def column_letter(index: int) -> str:' in server
    assert 'return f"{letter} · {name}" if display_mode == "letter" else name' in server

    assert 'data-file-id="${esc(item.id)}"' in html
    assert 'data-remove-fallback-file="${esc(item.id)}"' in html
    assert '$("#fileList")?.addEventListener("click", (event) => {' in html
    assert "const removeId = event.target.dataset.removeFallbackFile;" in html
    assert "fallbackState.files = fallbackState.files.filter((item) => item.id !== removeId);" in html
    assert 'fallbackState.activeMappingFileId = fallbackState.files[0]?.id || "";' in html
    assert 'fallbackState.devices = [];' in html
    assert "fallbackState.activeMappingFileId = row.dataset.fileId;" in html


def test_main_tabs_are_clickable_and_hash_addressable():
    html = Path("index.html").read_text(encoding="utf-8")
    app = read_app_js()

    for view in ("workspace", "single", "compare", "analytics", "history", "data", "automation", "settings"):
        assert f'data-view="{view}"' in html
        assert f'id="{view}View"' in html
        assert f"{view}:[" in app

    assert 'function normalizeViewName(name)' in app
    assert 'function viewFromHash()' in app
    assert 'function activateView(name,{updateHash=true,render=true}={})' in app
    assert 'document.addEventListener("click",(event)=>{const button=event.target.closest?.(".nav-item[data-view]")' in app
    assert 'window.addEventListener("hashchange",()=>view(viewFromHash(),{updateHash:true}))' in app
    assert 'panel.hidden=!active' in app
    assert 'history.pushState(null,"","#"+name)' in app


def test_browser_export_fallback_when_backend_is_unavailable():
    app = read_app_js()

    for marker in (
        "function exportColumns()",
        "function exportCell(device,key,index)",
        "function localExportTable()",
        "function localCsvLine(row,separator=\",\")",
        "function localYamlScalar(value)",
        "function localSpreadsheetXml(table)",
        "function localHtmlExport(table)",
        "function localExportData(type)",
        'localExportData("spreadsheetml")',
        'localExportData("html")',
        'if(localExportData(type))finishProcess(processId,"Экспорт завершён в браузере: "+type,"warning")',
        'toast("Экспорт выполнен в браузере без backend.")',
        'Потоковый XLSX:',
        'BrowserSnapshots.streamSnapshot(state.resultBrowserSnapshotId',
        'deliverDownload(`mac-analysis-${date}.xlsx`,result.blob)',
        'document.body.appendChild(link);link.click()',
        'setTimeout(()=>{URL.revokeObjectURL(url);link.remove();},15_000)',
        'result.rows!==totalRows',
        'XLSX полностью сформирован в браузере',
        'Backend недоступен: скачан HTML-отчёт для печати/PDF.',
        'filename=name+".csv"',
        'filename=name+".txt"',
        'filename=name+".json"',
        'filename=name+".yaml"',
        'filename=name+".html"',
        'filename=name+".xls"',
        'application/vnd.ms-excel',
        'export_date:new Date().toISOString()',
    ):
        assert marker in app


def test_enrichment_progress_uses_backend_html_payload():
    app = read_app_js()

    assert 'api("/enrichment/progress",{method:"POST",body:JSON.stringify({status:"starting"})})' in app
    assert 'progress.innerHTML=startProgress.progressHtml' in app
    assert 'progress.innerHTML=serverResult.progressHtml' in app
    assert "const p=serverResult.progress||{};" not in app
    assert "progress.innerHTML='<div class=\"bar-item\"><div class=\"bar-label\"><span>Обогащение</span>" not in app
    assert "progress.innerHTML='<div class=\"bar-item\"><div class=\"bar-label\"><span>Файлов: '" not in app


def test_scheduler_queue_uses_backend_file_packer():
    app = read_app_js()

    assert 'api("/tasks/queue",{method:"POST",body:JSON.stringify({taskId:task.id,files:sourceFilesPayload(true)})})' in app
    assert 'function queuedFilesFromState()' not in app
    assert 'function textToBase64(' not in app
    assert 'textToBase64(rows)' not in app
    assert 'api("/tasks/queue",{method:"POST",body:JSON.stringify({taskId:task.id,files:state.files})})' not in app


def test_ip_mapping_import_uses_backend_base64_payload():
    app = read_app_js()
    html = Path("index.html").read_text(encoding="utf-8")

    assert 'api("/ip-mappings/import",{method:"POST",body:JSON.stringify({filename:file.name,contentBase64:await fileToBase64(file)})})' in app
    assert 'async function importLocalIpMappings(file)' in app
    assert 'const result=await importLocalIpMappings(file);' in app
    assert 'async function applyLocalIpMappings()' in app
    assert 'async function updateCurrentBrowserSnapshot(' in app
    assert 'BrowserSnapshots.updateSnapshotWithTransform(sourceId,transform' in app
    assert 'await updateCurrentBrowserSnapshot("Обогащение: IP-маппинг"' in app
    assert 'state.snapshots.unshift(metadata)' not in app[app.index('async function updateCurrentBrowserSnapshot('):app.index('function createLocalComparisonIndex')]
    assert 'function isFinalDashboardSnapshot(snapshot={})' in app
    assert '["ip-mapping-apply","local-ip-mapping","local-vendor-model-rules"].includes(source)' in app
    assert 'const result=await applyLocalIpMappings();' in app
    assert 'function exportLocalIpMappings()' in app
    assert 'function autodetectLocalIpMappings()' in app
    assert 'function inferSwitchAddressMappings(devices=state.devices, source="analysis")' in app
    assert 'if(count>=2&&upsertLocalIpMapping(ip,address,"inferred-consensus"))imported++;' in app
    assert 'if(address&&!device.address){device.address=address;device.addressSource="switch-address-mapping";}' in app
    assert 'inferSwitchAddressMappings(state.devices,source);' in app
    assert 'ipMappings:[]' in app
    assert 'accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm"' in html
    assert 'content:await file.text()' not in app


def test_mapping_summary_uses_backend_service():
    app = read_app_js()

    assert 'async function refreshMappingSummary(file)' in app
    assert '$$("[data-field]").map((input)=>[input.dataset.field,input.checked])' in app
    assert 'api("/mapping/summary",{method:"POST",body:JSON.stringify({headers:file.headers.map((h)=>h.name),mapping:file.mapping||{},fields})})' in app
    assert 'refreshMappingSummary(file).catch(()=>localMappingSummary(file));save();' in app
    assert 'await refreshMappingSummary(file);toast("Колонки определены backend-детектором.")' in app
    assert 'root.innerHTML=(summary?.summaryHtml||"")+(result?.detectorHtml||"");' in app
    assert 'const ai=(result.ai?.suggestions||[]).slice(0,8).map' not in app
    assert 'Object.entries(result.mapping||{}).map' not in app
    assert 'Mapping summary' not in app


def test_single_file_report_uses_backend_html_payload():
    app = read_app_js()

    assert 'function renderSingleReport(result)' in app
    assert 'root.innerHTML=result?.summaryHtml||"";' in app
    assert 'detected.innerHTML=result?.detectedColumnsHtml' in app
    assert '$("#singlePreviewHead").innerHTML=result.previewHeadHtml;' in app
    assert '$("#singlePreviewBody").innerHTML=result.previewBodyHtml;' in app
    assert 'const cards=[["Строк"' not in app
    assert 'summary.detectedColumns||[]' not in app
    assert 'columns.map((item)=>' not in app


def test_single_file_preview_uses_backend_html_payload():
    app = read_app_js()

    assert 'async function renderSinglePreview(headers=[],rows=[],invalid=[])' in app
    assert 'api("/single-file/preview",{method:"POST",body:JSON.stringify({headers,rows,invalid})})' in app
    assert 'head.innerHTML=data.previewHeadHtml||"";' in app
    assert 'body.innerHTML=data.previewBodyHtml||"";' in app
    assert 'count.textContent=data.previewCountText||"";' in app
    assert 'safeHeaders.slice(0,12).map((header)=>"<th>"+esc(header)+"</th>")' not in app
    assert 'allRows.map((row)=>"<tr>"+safeHeaders.slice(0,12).map' not in app


def test_single_file_uses_binary_token_and_compact_result():
    app = Path("app.js").read_text(encoding="utf-8")
    file_readers = Path("frontend/file-readers.js").read_text(encoding="utf-8")
    memory_guard = Path("frontend/memory-guard.js").read_text(encoding="utf-8")

    assert app.count('MemoryGuard.assertImportCapacity(pendingSingleFile);') == 2
    assert 'MemoryGuard.assertImportCapacity(file,state.files);' in app
    assert 'memoryGuard.assertImportCapacity' not in app
    assert 'const memoryGuard' not in app
    assert 'const memoryGuard' not in file_readers
    assert 'memoryGuard.' not in file_readers
    assert 'MemoryGuard.assertImportCapacity(file);' in file_readers
    assert 'window.memoryGuard = publicApi;' in memory_guard
    assert 'state.importErrors=[];' in app
    assert 'merged.importErrors=[];' in app
    assert '"/files/import-binary"' in app
    assert 'fileToken,sheet:' in app
    assert 'compactResult:true,resultPageSize' in app
    assert 'sourceBytes:pendingSingleFile.size||0,fileToken,rowCount:' in app


def test_full_runner_isolates_sqlite_from_working_database():
    runner = Path("scripts/run_tests.ps1").read_text(encoding="utf-8")

    assert '$env:MAC_ANALYZER_DATA_DIR = $testDataDirectory' in runner
    assert '$env:MAC_ANALYZER_DATABASE_PATH = Join-Path $testDataDirectory "databases\\mac_analyzer_web.db"' in runner
    assert '$resolvedTestData.StartsWith($resolvedTestRoot, [StringComparison]::OrdinalIgnoreCase)' in runner


def test_bootstrap_clears_deleted_server_snapshot_reference():
    app = read_app_js()

    assert 'if(state.resultSnapshotId){' in app
    assert 'const staleId=state.resultSnapshotId;' in app
    assert 'if(error.status!==404)throw error;' in app
    assert 'state.snapshots=(state.snapshots||[]).filter((item)=>item.id!==staleId);' in app
    assert 'clearResultReference();' in app


def test_workspace_file_list_uses_backend_html_payload():
    app = read_app_js()

    assert 'async function renderFiles()' in app
    assert 'api("/workspace/files",{method:"POST",body:JSON.stringify({files:state.files.map(workspaceFileSummary)})})' in app
    assert 'function workspaceFileSummary(file)' in app
    assert 'const errors=(state.importErrors||[]).map' in app
    assert "root.innerHTML=(data.fileRowsHtml||data.emptyFilesHtml" in app
    assert 'state.files.map((f,i)=>' not in app
    assert 'data-remove-file="\'+f.id' not in app


def test_workspace_mapping_grid_uses_backend_html_payload():
    app = read_app_js()

    assert 'async function renderMapping()' in app
    assert 'api("/workspace/mapping-grid",{method:"POST",body:JSON.stringify({file:workspaceMappingPayload(file)})})' in app
    assert 'function workspaceMappingPayload(file)' in app
    assert 'root.innerHTML=data.mappingGridHtml' in app
    assert '$("#customColumnSource").innerHTML=data.customColumnOptionsHtml' in app
    assert 'fieldList.map(([field,title])=>\'<label>\'+title+\'<select data-map="' not in app
    assert 'file.headers.map((h)=>\'<option value="\'+h.index' not in app


def test_single_file_mapping_grid_uses_backend_html_payload():
    app = read_app_js()

    assert 'async function renderSingleMappingGrid()' in app
    assert 'api("/workspace/single-mapping-grid",{method:"POST",body:JSON.stringify({headers})})' in app
    assert 'root.innerHTML=data.singleMappingGridHtml' in app
    assert 'fieldList.map(([field,title])=>\'<label>\'+title+\'<select data-single-map="' not in app
    assert 'headers.map((name,index)=>\'<option value="\'+index' not in app


def test_quality_reports_are_backend_first():
    app = read_app_js()

    assert 'async function renderQualityReportsHistory()' in app
    assert 'api("/quality/reports?limit=5")' in app
    assert 'api("/quality/panel",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload({invalid:state.invalid,source:"current-browser-dataset",save:true}):{devices:dashboardDevices(),invalid:state.invalid,source:"current-browser-dataset",save:true})})' in app
    assert '$("#qualityInsights").innerHTML=panel.insightsHtml' in app
    assert 'root.innerHTML=data.reportsHtml||data.emptyReportsHtml' in app
    assert 'panel.issueRows||[]' not in app
    assert 'issue.percent||0' not in app
    assert 'reports.map((report)=>' not in app
    assert 'panel.summaryText||"0 devices' not in app
    assert 'await renderQualityReportsHistory();' in app
    assert 'renderQualityReportsHistory();refreshAnalyticsReport();' in app
    assert 'bars("#qualityInsights",insights)' not in app
    assert 'const duplicateCount=state.devices.length-new Set(state.devices.map((item)=>item.mac)).size' not in app
    assert 'Math.min(100,Math.max(5,issue.count/Math.max(1,summary.devices||1)*100))' not in app


def test_device_dialog_uses_backend_analytics():
    app = read_app_js()

    assert 'async function showDevice(mac)' in app
    assert 'api("/device/analytics",{method:"POST",body:JSON.stringify(currentDevicePayload({mac:normalized,snapshots:state.snapshots}))})' in app
    assert 'async function showLocalDevice(mac)' in app
    assert 'function localMacHistoryRows(mac,loadedAppearances=null,loadedMovements=null)' in app
    assert 'Promise.allSettled([' in app
    assert 'Локальная история MAC удалена.' in app
    assert 'const appearances=MacChronology.mergeAppearances(analytics?.appearances||[],local?.appearances||[]);' in app
    assert 'const events=MacChronology.buildEvents({appearances,history,movements});' in app
    assert 'dialog.dataset.mac=normalized||requestedMac;' in app
    assert '$("#deviceMetrics").innerHTML=analytics?.metricsHtml||' in app
    assert '$("#deviceFields").innerHTML=analytics?.fieldsHtml||localFields' in app
    assert 'analytics.metrics.historyRecords' not in app
    assert 'fields.map((field)=>' not in app
    assert 'analytics.modelPrefixes?.length' not in app
    assert 'MacChronology.appearancesRowsHtml(appearances,{formatDate:formatDisplayDateTime})' in app
    assert '$("#deviceHistoryBody").innerHTML=analytics?.movementRowsHtml||localMovements.html;' in app
    assert 'await api("/history?mac="+encodeURIComponent(mac),{method:"DELETE"});await showDevice(mac);' in app
    assert "'<tr><td colspan=\"5\" class=\"empty-state\">История удалена.</td></tr>'" not in app
    assert 'const rows=analytics.timelineRows||[];' not in app
    assert 'new Date(item.date).toLocaleString("ru-RU")' not in app
    assert 'analytics?.appearances||[]' in app
    assert 'analytics?.movements||[]' in app
    assert 'const movementRows=' not in app
    assert 'const historyRows=' not in app
    assert 'const appearanceRows=' not in app
    assert '[...movementRows,...historyRows,...appearanceRows]' not in app
    assert 'const device=state.devices.find((item)=>item.mac===mac)' not in app
    assert 'const appearances=state.snapshots.reduce' not in app
    assert 'let changes=[]' not in app
    assert 'api("/history?mac="+encodeURIComponent(mac));if(data.timeline?.length)' not in app


def test_model_prefix_dialog_uses_backend_analytics():
    app = read_app_js()
    html = read_index_html()

    assert 'async function showModelAnalytics(model)' in app
    assert 'api("/model/analytics",{method:"POST",body:JSON.stringify(currentDevicePayload({model}))})' in app
    assert 'function localModelAnalytics(model)' in app
    assert 'function renderModelAnalyticsDialog(data,model)' in app
    assert '$("#modelPrefixBody").innerHTML=data.tableRowsHtml||' in app
    assert 'renderModelAnalyticsDialog(localModelAnalytics(model),model)' in app
    assert 'showModelAnalytics(model);}},true)' in app
    assert 'if(model)return;if(lv||lm)' in app
    assert 'if(v||m){try{await api("/mappings/"+(v?"vendors/":"models/")+encodeURIComponent(v||m),{method:"DELETE"})' in app
    assert 'const builtinVendorMappings=' in app
    assert 'const builtinModelMappings=' in app
    assert '"00231420":"Lenovo Yoga 9i"' in app
    assert '"001E58":"Sony Corporation"' in app
    assert 'id="modelPrefixTable"' in html
    assert 'id="modelPrefixBody"' in html
    assert '<th>Префикс (5 байт)</th><th>Модель</th><th>Источник</th>' in html
    assert 'const fallbackBuiltinModels =' in html
    assert 'function showFallbackModelPrefixes(model)' in html


def test_clusters_topology_statistics_and_exports_have_local_fallbacks():
    app = read_app_js()
    html = read_index_html()
    local_analytics = Path("frontend/local-analytics.js").read_text(encoding="utf-8")

    assert 'async function renderBackendClusters(devices=state.devices)' in app
    assert 'async function renderBackendTopology(devices=state.devices)' in app
    assert 'root.innerHTML=data.clusterRowsHtml||data.emptyClusterRowsHtml' in app
    assert 'root.innerHTML=data.topologyHtml||data.emptyTopologyHtml' in app
    assert '<script src="frontend/local-analytics.js?v=20260729.3"></script>' in html
    assert 'const LocalAnalytics = window.MacAnalyzerLocalAnalytics;' in app
    assert 'async function collectLocalAnalytics(' in app
    assert 'vendor:settings.vendor||"",room:settings.room||"",showUnknown:settings.showUnknown!==false' in app
    assert 'LocalAnalytics.renderClusters(await collectLocalAnalytics(devices))' in app
    assert 'LocalAnalytics.renderTopology(await collectLocalAnalytics(devices))' in app
    assert 'LocalAnalytics.renderStatistics(finalDashboardSnapshots()' in app
    assert 'LocalAnalytics.renderTemporal(finalDashboardSnapshots())' in app
    assert 'LocalAnalytics.clustersCsv(payload)' in app
    assert 'LocalAnalytics.topologyDocument(payload)' in app
    assert 'LocalAnalytics.chartsSvg(payload)' in app
    assert 'Cluster backend unavailable:' not in app
    assert 'Topology backend unavailable:' not in app
    assert 'SQLite statistics unavailable:' not in app
    assert 'Temporal statistics unavailable:' not in app
    assert 'function createCollector(options = {})' in local_analytics
    assert 'window.MacAnalyzerLocalAnalytics = Object.freeze({' in local_analytics
    assert 'if (vendorFilter && vendor !== vendorFilter) continue;' in local_analytics
    assert 'if (roomFilter && room !== roomFilter) continue;' in local_analytics
    assert 'if (!showUnknown && unknownVendors.has(vendor.toLowerCase())) continue;' in local_analytics
    assert '$("#clusterChart").innerHTML=LocalAnalytics.renderClusters(details);' in app
    assert '$("#topologyGraph").innerHTML=LocalAnalytics.renderTopology(details);' in app


def test_primary_analytics_charts_use_backend_payload():
    app = read_app_js()

    assert 'function loadAnalyticsPanel(devices=dashboardDevices())' in app
    assert 'analyticsPanelPromise=loadAnalyticsPanel(devices);' in app
    assert 'async function renderPrimaryCharts()' in app
    assert 'const data=await(analyticsPanelPromise||loadAnalyticsPanel()),charts=data.primaryChartsHtml||{};' in app
    assert '$("#vendorChart").innerHTML=charts.vendors' in app
    assert '$("#modelChart").innerHTML=charts.models' in app
    assert '$("#qualityChart").innerHTML=charts.quality' in app
    assert '$("#timelineChart").innerHTML=charts.timeline' in app
    assert 'const data=await(analyticsPanelPromise||loadAnalyticsPanel());' in app
    assert 'const data=await(analyticsPanelPromise||loadAnalyticsPanel(devices));' in app
    assert 'renderPrimaryCharts();renderBackendStatistics();' in app
    assert 'function renderChartBarsFromItems' not in app
    assert 'function bars(' not in app
    assert 'function tally(' not in app
    assert "items.slice(0,8).map(([name,count])=>'<div class=\"bar-item\"" not in app
    assert 'Object.fromEntries((data.charts||[]).map((chart)=>[chart.id,chart]))' not in app
    assert 'api("/charts",{method:"POST",body:JSON.stringify({devices:dashboardDevices(),snapshots:state.snapshots})})' not in app
    assert 'Math.round((cluster.count||0)/max*100)' not in app
    assert 'function renderTimeline(' not in app
    assert 'renderTimeline();' not in app
    assert 'bars("#vendorChart",tally(devices.map((d)=>d.vendor)))' not in app
    assert 'bars("#qualityChart",[["Определён вендор"' not in app


def test_dashboard_metrics_use_backend_payload():
    app = read_app_js()

    assert 'async function renderMetrics()' in app
    assert 'api("/dashboard/metrics",{method:"POST",body:JSON.stringify(currentDevicePayload({invalid:state.invalid,snapshots:state.snapshots,settings:{vendor:"",room:"",chartLimit:8,showUnknown:true}}))})' in app
    assert '$("#metricKnown").textContent=(metrics.knownPercent||0)+"%";' in app
    assert '$("#metricInvalid").textContent=metrics.invalid||0;' in app
    assert '$("#snapshotMetric").textContent=finalDashboardSnapshots().length||0;' in app
    assert '$("#uniqueMacMetric").textContent=data.metrics.uniqueMacs||0;' in app
    assert 'quality=(data.charts||[]).find((chart)=>chart.id==="quality")' not in app
    assert 'Object.fromEntries((quality?.items||[]).map((item)=>[item.label,item.value]))' not in app
    assert 'Math.max(0,devices-unknown)' not in app
    assert 'state.devices.filter((d)=>d.vendor!=="Unknown").length' not in app
    assert 'new Set(state.devices.map((d)=>d.vendor).filter((v)=>v!=="Unknown")).size' not in app
    assert 'state.snapshots.flatMap((s)=>s.devices)' not in app
    assert 'new Set(all.map((d)=>d.mac)).size' not in app


def test_history_screen_uses_backend_statistics():
    app = read_app_js()
    html = Path("index.html").read_text(encoding="utf-8")

    assert 'function loadHistoryPanel(query="", from="", to="", limit="500")' in app
    assert 'historyPanelPromise=loadHistoryPanel(query, from, to);' in app
    assert 'function devicesSignature(devices=[])' in app
    assert 'async function preserveCurrentBeforeAnalysis(source)' in app
    assert 'movementHistory:[]' in app
    assert 'function localComparisonBetweenDevices(beforeDevices=[], afterDevices=[]' in app
    assert 'function recordLocalMovements(beforeDevices=[], afterDevices=[]' in app
    assert 'recordLocalMovements(previousDevices,state.devices,source,state.lastAnalysis);' in app
    assert 'await preserveCurrentBeforeAnalysis(source);' in app
    assert 'await storeLocalSnapshot("До анализа: "+(source||"текущие данные")' in app
    assert 'function localMovementItems(query="", from="", to="")' in app
    assert 'function localMovementTableRows(items)' in app
    assert 'async function renderMovementHistory()' in app
    assert 'renderMovementHistory(query, from, to);' in app
    assert 'api("/history/movements?"+movementHistoryParams(filters).toString())' in app
    assert 'id="localMovementBody"' in html
    assert 'async function renderSnapshotHistory(query="", from="", to="")' in app
    assert 'async function renderBackendHistorySummaries(query="", from="", to="")' in app
    assert 'function localHistoryItems(query="", from="", to="")' in app
    assert 'function localSnapshotHistoryRows(query="", from="", to="")' in app
    assert 'function renderLocalSqliteHistory(query="", from="", to="")' in app
    assert 'function renderLocalVendorModelHistory(query="", from="", to="")' in app
    assert 'root.innerHTML=localSnapshotHistoryRowsFrom(await localHistoryItemsAsync(query,from,to));' in app
    assert 'renderLocalHistorySummaries(query,from,to);' in app
    assert 'renderLocalSqliteHistory(query,from,to);' in app
    assert 'renderLocalVendorModelHistory(query,from,to);' in app
    assert 'const panel=await(historyPanelPromise||loadHistoryPanel(query,from,to));' in app
    assert 'vendorBody.innerHTML=summary.vendorRowsHtml||summary.emptyRowsHtml' in app
    assert 'modelBody.innerHTML=summary.modelRowsHtml||summary.emptyRowsHtml' in app
    assert 'vendors.map(row).join("")' not in app
    assert 'models.map(row).join("")' not in app
    assert 'panel.historySearch||{}' in app
    assert 'panel.vendorModelHistory||{}' in app
    assert 'summary.innerHTML=data.summaryHtml' in app
    assert "const data=panel.historySearch||{},statsData=panel.historyStats||{};" not in app
    assert "const data=panel.vendorModelHistory||{},statsData=panel.vendorModelStats||{},uploadData=panel.vendorModelUploads||{};" not in app
    assert "'<div class=\"bar-label\"><span>Records</span><strong>'+(totals.records" not in app
    assert "'<div class=\"bar-label\"><span>Uploads</span><strong>'+(uploads.uploads" not in app
    assert "body.innerHTML=data.tableRowsHtml||data.emptyTableRowsHtml||'<tr><td colspan=\"7\" class=\"empty-state\">SQLite history is empty.</td></tr>';" in app
    assert "body.innerHTML=data.tableRowsHtml||data.emptyTableRowsHtml||'<tr><td colspan=\"7\" class=\"empty-state\">Vendor/model history is empty.</td></tr>';" in app
    assert "(data.history||[]).map((item)=>'<tr data-mac='" not in app
    assert 'new Date(item.recorded_at).toLocaleString("ru-RU")' not in app
    assert "(data.history||[]).map((item)=>'<tr><td>'+esc(formatMac(item.mac||\"\"))" not in app
    assert 'new Date(item.observed_at).toLocaleString("ru-RU")' not in app
    assert 'api("/statistics/snapshots?"+historyQueryParams(query,from,to,"500").toString())' in app
    assert "root.innerHTML=data.tableRowsHtml||data.emptyTableRowsHtml||'<tr><td colspan=\"5\" class=\"empty-state\">Backend snapshot history is empty.</td></tr>';" in app
    assert "(data.snapshots||[]).map((s)=>" not in app
    assert 'new Date(s.createdAt).toLocaleString("ru-RU")' not in app
    assert 'api("/snapshots/open",{method:"POST",body:JSON.stringify({id,snapshots:state.snapshots,compactResult:true,resultPageSize})})' in app
    assert 'state.resultSnapshotId=String(reference.snapshotId||id);' in app
    assert 'const openedItems=opened.resultPage?.items||opened.devices||[];' in app
    assert 'state.devices=openedItems.filter((item)=>item?.valid!==false&&!item?.invalid);' in app
    assert 's=await api("/snapshots/"+encodeURIComponent(id))' not in app
    assert 'let s=state.snapshots.find((x)=>x.id===id)' not in app
    assert 'structuredClone(s.devices||[])' not in app
    assert 'renderVendorModelHistory(query, from, to);' in app
    assert 'Promise.all([api("/history/statistics?"+params),api("/vendor-model-history/statistics?"+params)])' not in app
    assert 'Promise.all([api("/history/search?"+params.toString()),api("/history/statistics?"+params.toString())])' not in app
    assert 'Promise.all([api("/vendor-model-history?"+params.toString()),api("/vendor-model-history/statistics?"+params.toString()),api("/vendor-model-history/uploads?"+params.toString())])' not in app
    assert 'const snapshots=state.snapshots.filter' not in app
    assert 'const aggregate=(field)=>' not in app
    assert 'state.snapshots.forEach((snapshot)=>' not in app
    assert 'renderVendorModelHistory(($("#historySearchInput")?.value||"").trim().toLowerCase())' not in app


def test_snapshot_select_options_use_backend_payload():
    app = read_app_js()

    assert 'async function renderSnapshots()' in app
    assert 'api("/snapshots/options",{method:"POST",body:JSON.stringify({snapshots:finalSnapshots})})' in app
    assert 'data.optionsHtml||""' in app
    assert 'data.comparisonSelectedIndex||0' in app
    assert 'state.snapshots.map((s)=>' not in app
    assert 'const options=state.snapshots.map((s)=>' not in app


def test_statistics_panels_use_backend_panel_payload():
    app = read_app_js()

    assert 'const data=await api("/statistics/panel");' in app
    assert 'root.innerHTML=data.statisticsHtml' in app
    assert 'root.innerHTML=data.temporalHtml' in app
    assert 'root.innerHTML=data.backendChartsHtml' in app
    assert 'data.trendRows||[]' not in app
    assert 'data.temporalRows||[]' not in app
    assert 'data.backendCharts||[]' not in app
    assert 'charts.map((chart)=>' not in app
    assert 'api("/statistics"),api("/statistics/snapshots?limit=25"),api("/statistics/performance?limit=200")' not in app
    assert 'api("/statistics/temporal?period=day&limit=365")' not in app
    assert 'Math.round((item.maxDevices||item.deviceTotal||0)/max*100)' not in app


def test_services_panel_uses_backend_aggregator():
    app = read_app_js()

    assert 'const serviceData=await api("/services/panel")' in app
    assert 'html=serviceData.html||{}' in app
    assert '$("#ipMappingList").innerHTML=html.ipRowsHtml' in app
    assert '$("#taskList").innerHTML=html.taskRowsHtml' in app
    assert '$("#appLogList").innerHTML=html.logRowsHtml' in app
    assert '$("#metricList").innerHTML=html.metricRowsHtml' in app
    assert '$("#timeStatsSummary").innerHTML=html.timeStatsSummaryHtml' in app
    assert '$("#timeStatsBody").innerHTML=html.timeStatsRowsHtml' in app
    assert '$("#databaseSummary").innerHTML=html.databaseSummaryHtml' in app
    assert '$("#legacyImportSummary").innerHTML=html.legacySummaryHtml' in app
    assert '} catch { renderLocalIpMappings(); renderLocalTimeStats(); }' in app
    assert 'function renderLocalIpMappings()' in app
    assert 'function renderLocalTimeStats()' in app
    assert 'Local snapshots' in app
    assert 'upsertLocalIpMapping(switchIp,address,"manual")' in app
    assert 'const result=await applyLocalIpMappings();' in app
    assert 'applyLocalVendorModelMappingsToCurrentResult' in app
    assert 'let snapshotMutationPromise=Promise.resolve();' in app
    assert 'const operation=snapshotMutationPromise.then(()=>applyLocalIpMappingsNow());' in app
    assert 'await snapshotMutationPromise;' in app
    assert 'await BrowserSnapshots?.prune?.([]).catch(()=>0);' in app
    assert 'state.snapshots=[];state.movementHistory=[];state.devices=[];state.invalid=[];clearResultReference();' in app
    assert 'ipData=serviceData.ip||{}' not in app
    assert 'legacyData=serviceData.legacy||{}' not in app
    assert 'ipData.mappings.map' not in app
    assert 'taskData.tasks.map' not in app
    assert 'logData.logs.length?logData.logs.slice' not in app
    assert 'metricData.metrics.length?metricData.metrics.slice' not in app
    assert 'Object.entries(databaseData.summary).map' not in app
    assert 'legacySources.map' not in app
    assert 'Promise.all([api("/ip-mappings"),api("/tasks"),api("/notifications"),api("/logs"),api("/metrics"),api("/database/summary"),api("/autosaves"),api("/signals/status"),api("/legacy/import/status")])' not in app


def test_local_vendor_model_rules_and_result_headers_work_without_backend():
    app = read_app_js()
    html = read_index_html()
    styles = read_styles_css()

    for marker in (
        'localVendorMappings:{}',
        'localModelMappings:{}',
        'function localRuleValue(mac,rules)',
        'function localCompatibleRuleValue(mac,rules)',
        'function normalizeVendorDetectorSettings(settings={})',
        'function vendorDetectorSettingsFromUi()',
        'function applyVendorDetectorSettings(settings={})',
        'async function loadVendorDetectorSettings()',
        'async function saveVendorDetectorSettings()',
        'function normalizeHistoryEnrichmentSettings(settings={})',
        'function historyEnrichmentSettingsFromUi()',
        'function applyHistoryEnrichmentSettings(settings={})',
        'async function loadHistoryEnrichmentSettings()',
        'async function saveHistoryEnrichmentSettings()',
        'api("/vendor-detector/settings"',
        'api("/history-enrichment/settings"',
        'loadVendorDetectorSettings();',
        'loadHistoryEnrichmentSettings();',
        '$("#saveVendorDetectorSettingsButton")?.addEventListener("click",saveVendorDetectorSettings)',
        '$("#saveHistoryEnrichmentSettingsButton")?.addEventListener("click",saveHistoryEnrichmentSettings)',
        'const localVendorKeywords=',
        'function localVendorFromText(...values)',
        'function localVendor(mac)',
        'function localModel(mac)',
        'localVendorFromText(model,pick("name"),row.join(" "))',
        'function applyLocalVendorModelMappings(devices=state.devices)',
        'function renderLocalResultsHeader()',
        'renderLocalResultsHeader();',
        'function resultHeaderHtml(columns)',
        'renderLocalMappings();',
        'function vendorModelLearnSettings()',
        'function learnLocalVendorModelMappings(settings=vendorModelLearnSettings())',
        'state.localVendorMappings[oui]=name;',
        'state.localModelMappings[p]=name;',
        'async function exportModelPrefixes()',
        'download("mac-model-hex-prefixes.csv"',
        '$("#exportModelPrefixesButton").addEventListener("click",exportModelPrefixes)',
        'async function applyBackendDetectionToCurrentResult()',
        'api("/detection/apply"',
        'delete state.localVendorMappings[lv];',
        'delete state.localModelMappings[lm];',
    ):
        assert marker in app


def test_oui_prefix_lengths_and_dashboard_render_locally():
    app = read_app_js()
    html = Path("index.html").read_text(encoding="utf-8")

    for marker in (
        "function normalizePrefix(value)",
        "function formatOuiValue(mac,length=state.ouiLength,style=state.ouiStyle)",
        "function compileLocalRuleIndex(rules)",
        "byPrefix.set(prefix,value)",
        "for(const length of index.lengths)",
        "localRuleValue(mac,rules)",
        "oui:formatOuiValue(mac)",
        'column==="oui"?formatOuiValue(item.mac||item.macFormatted||item.oui)',
        'if(key==="oui")return formatOuiValue(device.mac||device.macFormatted||device.oui);',
        "state.devices.forEach((device)=>{device.oui=formatOuiValue(device.mac||device.macFormatted||device.oui);});",
        "async function renderAnalytics(){",
        "loadBrowserDashboardCache(dashboardSettings())",
    ):
        assert marker in app

    for marker in (
        "ouiLength: 3",
        "ouiStyle: \"plain\"",
        "function fallbackFormatOui(mac, length = fallbackState.ouiLength, style = fallbackState.ouiStyle)",
        "filter(([prefix, value]) => value && [6, 8, 10].includes(prefix.length) && normalized.startsWith(prefix))",
        "fallbackRuleValue(mac, rules)",
        "oui: fallbackFormatOui(mac)",
        "fallbackTally(fallbackState.devices, \"room\", 200)",
        "device.room === settings.room",
        "fallbackTally(devices, \"room\")",
        '$("#ouiLengthSelect")?.addEventListener("change", (event) => {',
        '$("#ouiStyleSelect")?.addEventListener("change", (event) => {',
    ):
        assert marker in html


def test_analysis_tab_dashboard_and_mapping_learning_refresh_results():
    app = read_app_js()
    html = Path("index.html").read_text(encoding="utf-8")
    styles = Path("styles.css").read_text(encoding="utf-8")
    snapshot_store = Path("frontend/browser-snapshot-store.js").read_text(encoding="utf-8")

    for marker in (
        'id="analysisDashboardPanel"',
        'id="analysisMetricDevices"',
        'id="analysisMetricKnown"',
        'id="analysisMetricRooms"',
        'id="analysisMetricSwitches"',
        'id="analysisMetricInvalid"',
        'id="analysisVendorChart"',
        'id="analysisModelChart"',
        'id="analysisRoomChart"',
        'id="analysisSwitchChart"',
        'id="analysisOuiChart"',
        'id="analysisOui3Chart"',
        'id="analysisOui4Chart"',
        'id="analysisOui5Chart"',
        'id="analysisCoverageChart"',
        'id="analysisQualityChart"',
        'id="metricModels"',
        'id="metricOuiCoverage"',
        'id="metricAutoDetected"',
        "function renderFallbackAnalysisDashboard()",
        "function renderFallbackTopMetrics()",
        'if ($("#metricModels")) $("#metricModels").textContent = models.size;',
        'if ($("#metricOuiCoverage")) $("#metricOuiCoverage").textContent = `${oui3.size} / ${oui4.size} / ${oui5.size}`;',
        'if ($("#metricAutoDetected")) $("#metricAutoDetected").textContent = `${knownVendors} / ${models.size}`;',
        "renderFallbackAnalysisDashboard();",
    ):
        assert marker in html

    for marker in (
        "function analysisHeaderMetrics(devices=state.devices)",
        "function renderAnalysisHeaderMetrics(devices=state.devices)",
        '$("#metricModels").textContent=header.models;',
        '$("#metricOuiCoverage").textContent=header.oui3+" / "+header.oui4+" / "+header.oui5;',
        '$("#metricAutoDetected").textContent=header.autoVendors+" / "+header.autoModels;',
        "function vendorModelLearnSettings()",
        "function learnLocalRulesFromDevices(rows=[],minCount=2)",
        "function learnLocalVendorModelMappings(settings=vendorModelLearnSettings())",
        'body:JSON.stringify(settings)',
        "learned=learnLocalRulesFromDevices(rows,settings.minCount)",
        'if(model)count(modelCounts,mac.slice(0,10),model);',
        "function renderAnalysisDashboard()",
        "function analysisDashboardLocalPayload(devices=state.devices,summary=state.resultSummary)",
        "function analysisDashboardAggregatePayload(aggregate={})",
        "function renderAnalysisDashboardPayload(payload={},statusText=\"\")",
        "async function refreshAnalysisDashboard(key)",
        "BrowserSnapshots.aggregate(state.resultBrowserSnapshotId,{limit:20})",
        'api("/dashboard/metrics"',
        'set("#analysisMetricDevices",total)',
        'chart("#analysisRoomChart",distributions.rooms',
        'chart("#analysisSwitchChart",distributions.switches',
        'chart("#analysisOui3Chart",distributions.oui3',
        'chart("#analysisCoverageChart",coverage',
        "renderAnalysisDashboard();",
        "state.localVendorMappings=data.vendors||state.localVendorMappings||{};",
        "state.localModelMappings=data.models||state.localModelMappings||{};",
        "applyLocalVendorModelMappings(state.devices);save();renderResults();renderAnalytics();renderHistory();",
        "state.localVendorMappings[oui]=name;",
        "state.localModelMappings[p]=name;",
    ):
        assert marker in app
    assert 'id="exportModelPrefixesButton"' in html
    assert 'публичный IEEE-реестр содержит производителей, но не модели устройств' in html
    assert '.analytics-panel-actions .icon-button:hover' in styles
    assert '.active-filter span,.active-filter small,.active-filter strong' in styles
    for marker in (
        "const oui3Rows = new Map();",
        "const oui4Rows = new Map();",
        "const oui5Rows = new Map();",
        "tallyRowsBounded(switchRows, switchIp)",
        "uniqueOui3: oui3Rows.size",
        "switches: rankedRows(switchRows, limit)",
    ):
        assert marker in snapshot_store
    assert ".analysis-dashboard-metrics" in styles


def test_database_device_open_uses_backend_lookup_fallback():
    app = read_app_js()

    assert 'const result=await api("/database/device?mac="+encodeURIComponent(mac));' in app
    assert 'catch{result=await api("/lookup?mac="+encodeURIComponent(mac));}' not in app
    assert 'let result;try{result=await api("/database/device?mac="+encodeURIComponent(mac));}' not in app


def test_database_search_uses_backend_html_payload():
    app = read_app_js()

    assert 'const data=await api("/database/search?query="+encodeURIComponent(query)+"&limit=100");' in app
    assert 'root.innerHTML=data.resultsHtml||data.emptyResultsHtml' in app
    assert '(data.results||[]).map((item)=>' not in app
    assert 'data-db-type="\'+esc(item.type' not in app


def test_database_history_manager_has_structured_filters_and_scoped_delete():
    html = read_index_html()
    app = read_app_js()

    for marker in (
        'id="dbHistoryMacFilter"',
        'id="dbHistorySourceFilter"',
        'id="dbHistoryVendorFilter"',
        'id="dbHistoryModelFilter"',
        'id="dbHistoryRoomFilter"',
        'id="dbHistoryDateFrom"',
        'id="dbHistoryDateTo"',
        'id="selectAllDatabaseHistory"',
        'id="deleteSelectedDatabaseHistoryButton"',
        'id="deleteFilteredDatabaseHistoryButton"',
        'id="databaseHistoryBody"',
    ):
        assert marker in html

    for marker in (
        "function databaseHistoryFilters()",
        "async function loadDatabaseHistoryManagement()",
        'api("/database/history/records?"+databaseHistoryParams().toString())',
        "function selectedDatabaseHistoryIds()",
        "async function deleteDatabaseHistoryEntries(ids=[],filters={})",
        'api("/database/history/delete",{method:"POST",body:JSON.stringify({ids:selected,filters:activeFilters})})',
        'if(!selected.length&&!Object.keys(activeFilters).length)',
        'if(name==="data"){renderServices();loadDatabaseHistoryManagement();}',
    ):
        assert marker in app


def test_parity_status_uses_backend_html_payload():
    app = read_app_js()

    assert 'const data=await api("/parity/status");' in app
    assert 'root.innerHTML=data.summaryHtml' in app
    assert 'details.innerHTML=data.detailsHtml||data.emptyDetailsHtml' in app
    assert '(data.equivalents||[]).map((item)=>' not in app
    assert 'registry=data.registry||{}' not in app
    assert '<span>PyQt blocks</span><strong>' not in app


def test_result_table_filters_use_backend_service():
    app = read_app_js()

    assert 'async function loadFilteredResults(signal=null)' in app
    assert 'ouiLength:state.ouiLength,ouiStyle:state.ouiStyle' in app
    assert 'const labelMap=Object.fromEntries(columns.map((column)=>[column,labels[column]||column]));' in app
    assert 'renderLocalResultsHeader();' in app
    assert 'offset:(resultPage-1)*resultPageSize,limit:resultPageSize' in app
    assert 'api("/results/filter",{method:"POST",signal,body:JSON.stringify(currentDevicePayload({invalid:state.invalid,filters,columns,labels:labelMap}))})' in app
    assert '$("#resultsHeader").innerHTML=data.headerHtml||resultHeaderHtml(columns);' in app
    assert 'body.innerHTML=data.tableRowsHtml||data.emptyTableRowsHtml' in app
    assert '$("#vendorFilter").innerHTML=data.vendorOptionsHtml' in app
    assert '$("#resultCount").textContent=data.summaryText||"0 записей";' in app
    assert 'data.summary?.total??(data.items||[]).length' not in app
    assert 'columns.map((column)=>"<th>"+esc(labels[column]||column)+"</th>").join("")' not in app
    assert 'const cell=(device,column)=>device[column]||"—";' not in app
    assert 'function filterDevices()' not in app
    assert 'const cell=(device,column)=>column==="oui"?formatOui(device):device[column]||"—";' not in app
    assert 'Object.values(d).join(" ").toLowerCase().includes(search)' not in app
    assert 'const vendors=Array.from(new Set(state.devices.map((d)=>d.vendor))).sort();$("#vendorFilter")' not in app


def test_clipboard_context_menu_and_pyqt_shortcuts_are_available():
    html = Path("index.html").read_text(encoding="utf-8")
    styles = Path("styles.css").read_text(encoding="utf-8")
    app = read_app_js()

    for marker in (
        'id="copyResultsTableButton"',
        'id="copyResultsMacButton"',
        'id="copyHistoryTableButton"',
        'id="copyHistoryMacButton"',
        'id="tableContextMenu"',
        'data-context-action="copy-mac"',
        'data-context-action="copy-row"',
        'data-context-action="show-history"',
        '<kbd>Ctrl+O</kbd>',
        '<kbd>F9</kbd>',
        '<kbd>Esc</kbd>',
    ):
        assert marker in html

    for marker in (
        "function clipboardSafeCell(value)",
        "function tableRowsToTsv(rows)",
        "async function copyTextToClipboard(value,label=\"данные\")",
        "navigator.clipboard?.writeText",
        'document.execCommand("copy")',
        "function showTableContextMenu(event,row)",
        "function bindSelectableMacTable(body)",
        'bindSelectableMacTable($("#resultsBody"))',
        'bindSelectableMacTable($("#sqliteHistoryBody"))',
        "function handleAppShortcut(event)",
        'if(keyName==="f1")',
        'if(ctrl&&keyName==="s")',
        'if(ctrl&&keyName==="a")',
        'if(ctrl&&keyName==="h")',
        'if(keyName==="f5")',
        'if(keyName==="f9")',
        'document.addEventListener("keydown",handleAppShortcut)',
        '"001122":"Cisco Systems"',
    ):
        assert marker in app

    assert ".table-context-menu" in styles
    assert "tr.selected-row td" in styles


def test_enhanced_history_dialog_is_grouped_filterable_exportable_and_persistent():
    html = read_index_html()
    app = read_app_js()
    styles = Path("styles.css").read_text(encoding="utf-8")

    for marker in (
        'id="movementDateFrom" type="datetime-local"',
        'id="movementDateTo" type="datetime-local"',
        'id="movementTypeFilter"',
        'id="movementFieldFilter"',
        'id="movementSearchInput"',
        'id="exportMovementHistoryButton"',
        'id="deleteShownMovementsButton"',
        'id="expandMovementGroupsButton"',
        'id="collapseMovementGroupsButton"',
        'id="movementColumnControls"',
        'id="enhancedMovementTable"',
        'data-movement-resize="before"',
    ):
        assert marker in html

    for marker in (
        "function movementHistoryFilters()",
        "async function renderMovementHistory()",
        'api("/history/movements?"+movementHistoryParams(filters).toString())',
        "function setMovementGroupsExpanded(expanded)",
        "async function exportMovementHistory()",
        'api("/history/movements/export?"+params.toString())',
        "async function deleteShownMovementHistory()",
        'api("/history/movements/delete",{method:"POST"',
        "function applyMovementColumnSettings(settings=movementColumnSettings)",
        "async function saveMovementColumnSettings(",
        'api("/history/movements/columns",{method:"POST"',
        "function startMovementColumnResize(event)",
    ):
        assert marker in app

    assert ".movement-group-row td" in styles
    assert ".movement-child-row.movement-added" in styles
    assert "#movementColumnControls" in styles


def test_ai_column_conflict_dialog_requires_explicit_review_and_mac_mapping():
    html = read_index_html()
    app = read_app_js()
    styles = Path("styles.css").read_text(encoding="utf-8")

    for marker in (
        'id="columnConflictDialog"',
        'id="columnConflictBody"',
        'id="columnConflictStatus"',
        'id="autoSelectConflictColumnsButton"',
        'id="clearConflictColumnsButton"',
        'id="cancelConflictColumnsButton"',
        'id="applyConflictColumnsButton"',
        '<th>Рекомендация AI</th>',
        '<th>Примеры данных</th>',
    ):
        assert marker in html

    for marker in (
        "let columnConflictContext = null;",
        "function columnConflictMapping()",
        "function resolveColumnConflict(mapping)",
        "function showColumnConflictReview(file,result)",
        "function autoSelectConflictColumns()",
        "function applyColumnConflictSelection()",
        "if(mapping.mac===undefined)",
        "const reviewed=await showColumnConflictReview(file,result);",
        'if(!reviewed){renderColumnDetectionSummary(file);toast("Выбор колонок отменён.");return;}',
        '$("#columnConflictDialog").addEventListener("cancel"',
    ):
        assert marker in app

    assert ".column-conflict-dialog" in styles
    assert ".column-conflict-table-wrap" in styles
    assert ".dialog-actions" in styles


def test_pyqt_analytics_dialog_report_is_available_in_web_ui():
    html = read_index_html()
    app = read_app_js()
    styles = Path("styles.css").read_text(encoding="utf-8")

    for marker in (
        'id="analyticsReportStatus"',
        'id="analyticsReportPreview"',
        'id="refreshAnalyticsReportButton"',
        'id="exportAnalyticsReportButton"',
    ):
        assert marker in html

    for marker in (
        "function buildLocalAnalyticsReport(devices=state.devices)",
        "function renderAnalyticsReport(report,source=\"local\")",
        "async function refreshAnalyticsReport()",
        "async function exportAnalyticsReport()",
        'api("/analytics/report"',
        'exportFormat:"txt"',
        '$("#refreshAnalyticsReportButton").addEventListener("click",refreshAnalyticsReport)',
        '$("#exportAnalyticsReportButton").addEventListener("click",exportAnalyticsReport)',
    ):
        assert marker in app

    assert ".analytics-report-panel" in styles
    assert ".analytics-report-preview" in styles


def test_pyqt_mac_history_dialog_keeps_separate_history_and_movement_tables():
    html = read_index_html()
    app = read_app_js()

    for marker in (
        'id="macHistoryStats"',
        'id="deviceHistoryRecordsBody"',
        '<th>Файл</th><th>Производитель</th><th>Модель</th><th>IP</th><th>Адрес</th><th>Помещение</th>',
        '<h3>Изменения параметров</h3>',
    ):
        assert marker in html

    for marker in (
        'MacChronology.renderSummary(events,appearances)',
        'analytics?.historyRecordsRowsHtml||localHistory.html',
        'analytics?.movementRowsHtml||localMovements.html',
        'function localMacMovementRows(mac,loadedRows=null)',
        'MacChronology.appearancesRowsHtml(rows,{formatDate:formatDisplayDateTime})',
        'await showDevice(mac);renderHistory();toast("История MAC удалена.")',
    ):
        assert marker in app


def test_dashboard_change_period_snapshot_drilldown_is_wired_backend_and_local():
    html = read_index_html()
    app = read_app_js()
    styles = Path("styles.css").read_text(encoding="utf-8")

    for marker in (
        'id="dashboardChangeMode"', 'id="dashboardChangeDateFrom"', 'id="dashboardChangeDateTo"',
        'id="dashboardBaselineSnapshot"', 'id="dashboardComparisonSnapshot"',
        'id="dashboardChangesDialog"', 'id="dashboardCriticalCount"', 'id="dashboardChangesBody"',
        'id="dashboardChangeTypeFilter"', 'id="dashboardDynamicsDialog"', 'data-dashboard-change-type="added"',
        'role="tablist" aria-label="Категории изменений"', 'id="dashboardChangesPanel" role="tabpanel"',
        'frontend/dashboard-change-tabs.js?v=',
    ):
        assert marker in html
    for marker in (
        "function localDashboardChangeAnalysis", "function renderDashboardChanges", "function showDashboardChangesDialog",
        "payload.changeAnalysis", "dashboardChangeSeverity", "applyDashboardChangeRangeButton",
        "function finalDashboardSnapshots", "function selectLatestDashboardPair", "function loadBrowserDashboardCache",
        "BrowserSnapshots.compareSnapshots", "BrowserSnapshots.aggregateSeries", 'changeMode:"snapshots"',
        "function groupDashboardChanges", "function showDashboardDynamicsDialog",
        "function selectDashboardChangeTab", "function syncDashboardChangeTabState",
        "function handleDashboardChangeTabKeydown", "DashboardChangeTabs.filtersForTab",
    ):
        assert marker in app
    for marker in (
        "function selectFallbackDashboardChangeTab", "function syncFallbackDashboardChangeTabState",
        "dashboardChangeTypeFilter\")?.addEventListener", "dashboardChangeMacSearch\")?.addEventListener",
    ):
        assert marker in html
    assert "function buildFallbackChangeAnalysis" in html
    assert ".severity-critical" in styles
    assert '.dashboard-change-metrics .metric[aria-selected="true"]' in styles
    assert ".dashboard-changes-dialog[open] { display:flex; flex-direction:column; }" in styles
    assert "resize:both;" in styles
    assert ".dashboard-changes-table { flex:1 1 260px;" in styles


def test_search_dashboard_smartroom_and_unified_exports_are_wired():
    html = read_index_html()
    app = read_app_js()
    snapshots = Path("frontend/browser-snapshot-store.js").read_text(encoding="utf-8")
    chronology = Path("frontend/mac-chronology.js").read_text(encoding="utf-8")
    full_json = Path("frontend/full-json-report.js").read_text(encoding="utf-8")

    for marker in (
        'id="globalSearchForm"', 'id="globalSearchInput"', 'id="exportMenu"',
        'id="exportFullJsonButton"', 'id="dashboardChangeMacSearch"',
        'id="dashboardSearchInput"', 'id="databaseImportButton"', 'id="databaseImportInput"',
        'id="dashboardChangedRoomMetric"', 'data-field="smartroomId"',
        'data-dashboard-card-toggle="changedRooms"',
    ):
        assert marker in html
    for marker in (
        "async function runGlobalSearch()", "function dashboardSnapshotPair(",
        "current.vendor=vendor.value", "current.room=room.value",
        "BrowserSnapshots.aggregate(currentId,{limit:200,vendor:settings.vendor,room:settings.room",
        "async function exportFullJson()", "FullJsonReport.createReport({",
        "function initializeAnalyticsExpanders()",
        "function normalizedRoomName(", "function synchronizeSmartroomIdentity(",
        "function inferSmartroomRoomMappings(", "function mergeDdioOverlayMovements(",
        'api("/database/import"',
    ):
        assert marker in app
    assert "const vendorFilter = String(options.vendor || \"\").trim();" in snapshots
    assert "const roomFilter = String(options.room || \"\").trim();" in snapshots
    assert "smartroomId: String(device?.smartroomId || device?.smartroom_id || \"\")" in snapshots
    assert "function appearanceChanges(appearances)" in chronology
    assert "window.MacAnalyzerFullJsonReport" in full_json


def test_pyqt_single_device_analytics_text_report_is_rendered_locally_and_from_api():
    html = read_index_html()
    app = read_app_js()
    styles = Path("styles.css").read_text(encoding="utf-8")

    assert 'id="deviceDetailedReport"' in html
    assert '<h3>Детальная информация об устройстве</h3>' in html
    assert 'analytics?.detailedReportText||localDeviceDetailedReport' in app
    assert 'function localDeviceDetailedReport(device={},mac="")' in app
    for marker in (
        "=== ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ОБ УСТРОЙСТВЕ ===",
        "Источники данных:",
        "vendorSource","vendor_source","modelSource","model_source",
        "matchDetails","match_details",
    ):
        assert marker in app
    assert ".device-detailed-report" in styles


def test_primary_and_enrichment_files_are_grouped_in_browser_only_html():
    html = read_index_html()
    app = read_app_js()
    styles = Path("styles.css").read_text(encoding="utf-8")

    for marker in (
        'id="primaryFileSummary"',
        'id="enrichmentFileSummary"',
        'id="backendStatusDot"',
        'id="reconnectBackendButton"',
    ):
        assert marker in html
    for marker in (
        'const browserOnlyMode = location.protocol === "file:";',
        'const autonomousHtmlMode = browserOnlyMode;',
        'const backendCandidates = browserOnlyMode ? [] : [location.origin + "/api"];',
        'function normalizeFileRoles(files=[])',
        'function insertImportedFile(fileRecord,requestedRole="auto",batchIndex=0)',
        'loadFiles(e.target.files,e.target,"primary")',
        'loadFiles(e.target.files,e.target,"smartroom")',
        'data-file-group="${role}"',
        'data-file-role="${role}"',
        'Сначала добавьте файл №1 — основной, затем выберите файл №2 — SmartRoom.',
    ):
        assert marker in app
    assert 'loadFallbackFiles(event.target.files, event.target, "smartroom")' in html
    assert 'function normalizeFallbackFileRoles()' in html
    assert 'const file=state.files[fileIndex],allowNew=true;' in app
    assert 'if(fileIndex&&strategy==="primary")return' not in app
    assert '.file-group-head' in styles
    assert '.backend-reconnect' in styles


def test_user_and_engineering_modes_match_pyqt_access_split():
    html = read_index_html()
    app = read_app_js()
    styles = Path("styles.css").read_text(encoding="utf-8")

    for marker in (
        'id="appModeButton"',
        'id="modeContext"',
        'id="engineeringDialog"',
        'id="engineeringLoginForm"',
        'id="engineeringPasswordInput"',
        'id="engineeringTtlInput"',
        'data-engineering-permission="delete:history"',
        'data-engineering-permission="write:migration"',
        'data-engineering-permission="delete:api-cache"',
    ):
        assert marker in html
    assert html.count('data-engineering-only role="tab"') == 5
    for marker in (
        'const engineeringOnlyViews=new Set(["single","compare","data","automation","settings"])',
        'if(!engineeringSessionActive()&&engineeringOnlyViews.has(name))name="history"',
        'function engineeringHasPermission(permission="")',
        'function renderEngineeringState({redirect=true}={})',
        'function openEngineeringDialog()',
        'async function loginEngineering(password,ttlMinutes=480)',
        'async function logoutEngineering()',
        'if(!networkUnavailable(error))throw error',
        'if(password!=="admin123")throw new Error("Неверный пароль инженерного режима.")',
        'view("workspace");toast("Инженерный режим включён.")',
        'view("workspace");toast("Включён пользовательский режим.")',
    ):
        assert marker in app
    assert 'const password=prompt("Пароль инженерного режима:")' not in app
    assert 'body[data-mode="engineering"] .sidebar' in styles
    assert '.mode-badge.engineering-mode' in styles
    assert '[hidden] { display: none !important; }' in styles


def test_role_aware_guide_is_a_separate_working_view():
    html = read_index_html()
    app = read_app_js()
    styles = read_styles_css()

    for marker in (
        'data-view="guide" role="tab" aria-controls="guideView"',
        'id="guideView" role="tabpanel"',
        'id="guideCurrentMode"',
        'data-guide-tab="overview"',
        'data-guide-tab="user"',
        'data-guide-tab="engineer"',
        'data-guide-tab="large-files"',
        'data-guide-requires-engineering',
        'id="openGuideFromHelpButton"',
        '<script src="frontend/guide.js?v=20260722.7"></script>',
    ):
        assert marker in html
    for text in (
        "Единая картина устройств, адресов и изменений сети",
        "Пользовательский режим",
        "Инженерный режим",
        "Как обрабатывать большие XLSX без Out of Memory",
        "постраничный вывод",
    ):
        assert text in html
    for marker in (
        "const Guide = window.MacAnalyzerGuide;",
        'Guide.syncMode(active,state.engineeringExpiresAt,document);',
        'guide:["Руководство","Назначение программы и рабочие сценарии для пользователя и инженера."]',
        'if(name==="guide"){Guide.syncMode(engineeringSessionActive(),state.engineeringExpiresAt,document);',
        'if(!$("#systemDiagnosticsSummary")?.dataset.loaded)runSystemDiagnostics();',
        'Guide.activateTab(tab.dataset.guideTab,document);',
        'view("guide")',
        'document.documentElement.dataset.guideModule = "ready";',
    ):
        assert marker in app
    for marker in (
        ".guide-mode-strip {",
        ".guide-tabs {",
        ".guide-step-list {",
        ".guide-safety-grid {",
        ".guide-view button:disabled",
    ):
        assert marker in styles


def test_full_system_diagnostics_is_visible_and_has_offline_fallback():
    html = read_index_html()
    app = read_app_js()
    styles = read_styles_css()
    server = Path("server.py").read_text(encoding="utf-8")

    for marker in (
        'id="runSystemDiagnosticsButton"',
        'id="systemDiagnosticsSummary"',
        'id="systemDiagnosticsDetails"',
        "Проверяет web-файлы, SQLite, каталоги данных, API, перенос PyQt и защиту больших XLSX.",
        "function fallbackRunSystemDiagnostics()",
    ):
        assert marker in html
    for marker in (
        "function localSystemDiagnostics()",
        "function paintSystemDiagnostics(data)",
        "async function runSystemDiagnostics()",
        'const data=await api("/system/diagnostics")',
        '$("#runSystemDiagnosticsButton")?.addEventListener("click",runSystemDiagnostics);',
    ):
        assert marker in app
    assert 'elif parsed.path == "/api/system/diagnostics":' in server
    assert "build_system_diagnostics(ROOT, STORAGE, db_connection)" in server
    for marker in (".guide-diagnostics {", ".diagnostic-row {", ".diagnostic-row.diagnostic-failed"):
        assert marker in styles


def test_oui_reference_import_and_safe_autodetection_are_wired_end_to_end():
    html = read_index_html()
    app = read_app_js()
    server = Path("server.py").read_text(encoding="utf-8")
    memory_guard = Path("frontend/memory-guard.js").read_text(encoding="utf-8")
    snapshot_store = Path("frontend/browser-snapshot-store.js").read_text(encoding="utf-8")

    for marker in (
        'id="ouiReferenceFileInput"',
        'id="importOuiReferenceButton"',
        'id="ouiReferenceStatus"',
        'accept=".txt,.csv,text/plain,text/csv"',
    ):
        assert marker in html
    for marker in (
        "async function importOuiReference()",
        "async function parseLocalOuiReference(file)",
        'api("/reference/oui/import"',
        '$("#importOuiReferenceButton")?.addEventListener("click",importOuiReference);',
        "function learnLocalRulesFromDevices(rows=[],minCount=2)",
        "if(model)count(modelCounts,mac.slice(0,10),model);",
    ):
        assert marker in app
    for marker in (
        'parsed.path == "/api/reference/oui/status"',
        'parsed.path == "/api/reference/oui/import"',
        'rows.append((mac, mac[:6], mac[:10]',
        "class ManagedSQLiteConnection(sqlite3.Connection)",
        '"vendorModelAggregates": len(vendor_model_rows)',
    ):
        assert marker in server
    assert "browserRows: 150_000" in memory_guard
    assert "browserCells: 1_500_000" in memory_guard
    assert "browserEnrichmentRows: 220_000" in memory_guard
    assert "browserEnrichmentCells: 2_200_000" in memory_guard
    assert "function assertEnrichmentCapacity(files, memoryInfo" in memory_guard
    assert "browserEnrichmentTextBytes: 64 * 1024 * 1024" in memory_guard
    assert "function assertHeapHeadroom(size, memoryInfo" in memory_guard
    assert "resultBrowserSnapshotId" in app
    assert "MemoryGuard.assertStreamingEnrichmentCapacity(state.files,strategy);" in app
    assert "async function copySnapshotWithTransform(" in snapshot_store
    assert "async function updateSnapshotWithTransform(" in snapshot_store
    assert "async function transformChunkRows(" in snapshot_store
    assert "copySnapshotWithTransform," in snapshot_store
    assert "updateSnapshotWithTransform," in snapshot_store
    assert "window.MacAnalyzerMemoryGuard?.assertEnrichmentCapacity(fallbackState.files);" in html


def test_primary_app_bootstrap_disables_duplicate_inline_fallback():
    app = Path("app.js").read_text(encoding="utf-8")
    html = Path("index.html").read_text(encoding="utf-8")
    assert "window.MacAnalyzerAppBootstrapped = true;" in app
    assert "if (window.MacAnalyzerAppBootstrapped || window.MacAnalyzerAppReady) return;" in html


def test_autonomous_file_database_is_streamed_and_connected_to_workspace_saves():
    html = Path("index.html").read_text(encoding="utf-8")
    app = Path("app.js").read_text(encoding="utf-8")
    database = Path("frontend/portable-database.js").read_text(encoding="utf-8")
    for marker in (
        'id="portableDatabaseButton"',
        'id="portableDatabaseDialog"',
        'id="openPortableDatabaseButton"',
        'id="createPortableDatabaseButton"',
        'id="portableDatabaseInput"',
        'id="portableFolderInput"',
        '<script src="frontend/portable-database.js?v=20260810.1"></script>',
    ):
        assert marker in html
    assert 'if(theme){saveThemePreference(theme);$("#themeDialog").close();}' in app
    assert '$("#themeDialog")?.close();' in html
    for marker in (
        "function portableDatabasePayload()",
        "async function persistPortableDatabase()",
        "async function restorePortableDatabaseHandle()",
        "await flushPortableDatabaseSave().catch(()=>{})",
        'if(!autonomousHtmlMode&&backendAvailable)',
    ):
        assert marker in app
    for marker in (
        "const writeBatchRows = 250;",
        "file.stream().getReader()",
        'type: "snapshot-current"',
        "maximumDatabaseBytes = 1024 * 1024 * 1024",
        'const retainRows = options.retainRows !== false;',
        'await options.onSnapshotChunk(context.metadata, kind, rows, context[indexKey]);',
    ):
        assert marker in database
    assert "JSON.stringify(payload)" not in database


def test_browser_only_mode_uses_a_structured_local_folder():
    html = Path("index.html").read_text(encoding="utf-8")
    app = Path("app.js").read_text(encoding="utf-8")
    folder_store = Path("frontend/local-folder-store.js").read_text(encoding="utf-8")
    for marker in (
        'id="chooseLocalFolderButton"',
        'id="importPortableFolderButton"',
        'id="localFolderStatus"',
        '<script src="frontend/local-folder-store.js?v=20260728.1"></script>',
        "Подключить папку данных",
    ):
        assert marker in html
    for marker in (
        'const browserOnlyMode = location.protocol === "file:";',
        'const backendCandidates = browserOnlyMode ? [] : [location.origin + "/api"];',
        "async function attachLocalFolder(",
        "async function restoreLocalFolderHandle({preferBrowserState=false}={})",
        "LocalFolderStore?.copyImport?.(",
        'setBackendStatus(false,"Локальная файловая база подключена · backend не используется")',
        'const localFolderSavedAtKey = key+"-folder-saved-at";',
        'const header=await PortableDatabase.readHeader(structure.databaseHandle);',
        'if(preferBrowserState&&browserHasRestorableData&&knownSavedAt>=fileSavedAt)',
        "async function importPortableFolderFiles(files)",
        "portableDatabaseRestoreOptions(importedSnapshotIds)",
    ):
        assert marker in app
    assert 'setInterval(()=>{if(browserOnlyMode){if(portableDatabaseHandle)schedulePortableDatabaseSave(0);}' not in app
    for marker in (
        'const folderNames = Object.freeze(["database", "imports", "exports", "settings", "logs", "backups"]);',
        'const databaseFileName = "mac-analyzer-data.madb";',
        "showDirectoryPicker",
        "function findDatabaseFile(files = [])",
        "function inspectFolderFiles(files = [])",
        "async function copyImport(",
    ):
        assert marker in folder_store


def test_ddio_switch_ip_hint_is_persisted_and_rendered_in_local_history():
    app = Path("app.js").read_text(encoding="utf-8")
    styles = Path("styles.css").read_text(encoding="utf-8")
    assert "function attachDdioHistoryHint(item)" in app
    assert "item.ddioCandidateIp=hint.ip" in app
    assert "ddioHistoryBadge(item)" in app
    assert 'class="possible-ip-dropdown ddio-history-warning"' in app
    assert ".ddio-history-warning" in styles


if __name__ == "__main__":
    test_ddio_switch_ip_hint_is_persisted_and_rendered_in_local_history()
    test_ddio_third_export_is_display_only_and_bound_in_primary_frontend()
    test_autonomous_file_database_is_streamed_and_connected_to_workspace_saves()
    test_primary_app_bootstrap_disables_duplicate_inline_fallback()
    test_portable_two_file_import_is_local_first_and_race_safe()
    test_single_file_uses_binary_token_and_compact_result()
    test_full_runner_isolates_sqlite_from_working_database()
    test_global_process_progress_covers_file_analysis_compare_and_export()
    test_navigation_tabs_are_hash_routable_and_safe()
    test_cross_browser_restore_prefers_compact_sqlite_workspace()
    test_migrated_controls_have_single_backend_binding()
    test_full_xlsx_export_includes_analytics_changes_and_mac_history()
    test_single_snapshot_compare_uses_backend_snapshot_resolver()
    test_multi_snapshot_compare_uses_backend_snapshot_resolver()
    test_comparison_result_uses_backend_html_payload()
    test_backend_export_paths_are_still_wired()
    test_workspace_navigation_renders_compact_results()
    test_excel_files_are_selectable_in_main_import()
    test_html_has_startup_fallback_for_tabs_and_file_choice()
    test_html_fallback_preserves_snapshots_and_movement_history()
    test_html_fallback_supports_local_ip_mapping_without_backend()
    test_html_fallback_supports_vendor_model_rules_without_backend()
    test_html_fallback_persists_state_and_backup_without_backend()
    test_frontend_exports_do_not_duplicate_backend_generators()
    test_mapping_rules_are_backend_first()
    test_snapshot_history_delete_uses_bulk_backend_endpoint()
    test_column_preferences_are_backend_first()
    test_theme_and_oui_preferences_are_backend_first()
    test_local_html_mode_keeps_theme_engineering_and_analytics_working()
    test_external_api_runtime_uses_persisted_backend_settings()
    test_pyqt_api_settings_dialog_is_available_with_local_html_fallback()
    test_bootstrap_sync_uses_backend_payload()
    test_dashboard_settings_are_loaded_from_backend()
    test_autosave_delete_is_exposed_in_web_ui()
    test_device_dialog_shows_mac_chronology()
    test_backup_export_restore_use_backend_service()
    test_notification_config_json_is_parsed_by_backend()
    test_column_auto_mapping_uses_backend_detector()
    test_main_file_import_uses_backend_service()
    test_browser_mode_enrichment_keeps_basic_workflow_alive()
    test_browser_snapshots_are_stored_outside_live_workspace_memory()
    test_room_occupancy_analytics_is_wired_in_browser_and_backend_views()
    test_two_file_manual_mapping_supports_name_or_letter_mode()
    test_enrichment_progress_uses_backend_html_payload()
    test_scheduler_queue_uses_backend_file_packer()
    test_ip_mapping_import_uses_backend_base64_payload()
    test_mapping_summary_uses_backend_service()
    test_single_file_report_uses_backend_html_payload()
    test_single_file_preview_uses_backend_html_payload()
    test_workspace_file_list_uses_backend_html_payload()
    test_workspace_mapping_grid_uses_backend_html_payload()
    test_single_file_mapping_grid_uses_backend_html_payload()
    test_quality_reports_are_backend_first()
    test_device_dialog_uses_backend_analytics()
    test_model_prefix_dialog_uses_backend_analytics()
    test_clusters_topology_statistics_and_exports_have_local_fallbacks()
    test_primary_analytics_charts_use_backend_payload()
    test_dashboard_metrics_use_backend_payload()
    test_history_screen_uses_backend_statistics()
    test_snapshot_select_options_use_backend_payload()
    test_statistics_panels_use_backend_panel_payload()
    test_services_panel_uses_backend_aggregator()
    test_local_vendor_model_rules_and_result_headers_work_without_backend()
    test_oui_prefix_lengths_and_dashboard_render_locally()
    test_analysis_tab_dashboard_and_mapping_learning_refresh_results()
    test_database_device_open_uses_backend_lookup_fallback()
    test_database_search_uses_backend_html_payload()
    test_parity_status_uses_backend_html_payload()
    test_result_table_filters_use_backend_service()
    test_clipboard_context_menu_and_pyqt_shortcuts_are_available()
    test_pyqt_analytics_dialog_report_is_available_in_web_ui()
    test_pyqt_mac_history_dialog_keeps_separate_history_and_movement_tables()
    test_dashboard_change_period_snapshot_drilldown_is_wired_backend_and_local()
    test_search_dashboard_smartroom_and_unified_exports_are_wired()
    test_pyqt_single_device_analytics_text_report_is_rendered_locally_and_from_api()
    test_primary_and_enrichment_files_are_grouped_in_browser_only_html()
    test_user_and_engineering_modes_match_pyqt_access_split()
    test_role_aware_guide_is_a_separate_working_view()
    test_full_system_diagnostics_is_visible_and_has_offline_fallback()
    test_oui_reference_import_and_safe_autodetection_are_wired_end_to_end()
    print("frontend event bindings test passed")

from pathlib import Path


def read_standalone():
    return Path("mac_analyzer_standalone.html").read_text(encoding="utf-8")


def test_standalone_keeps_xlsx_import_support():
    html = read_standalone()

    assert 'accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm,.xls"' in html
    assert "async function parseXlsx(file)" in html
    assert "DecompressionStream" in html
    assert '["xlsx","xlsm","xls"].includes(ext)' in html
    assert "const standaloneMemoryLimits=Object.freeze" in html
    assert "function assertStandaloneEnrichmentCapacity(files=state.files,memoryInfo=" in html
    assert "enrichmentTextBytes:64*1024*1024" in html
    assert "heapReserveBytes:64*1024*1024" in html
    assert "if(buf.byteLength>standaloneMemoryLimits.workbookBytes)" in html
    assert "declaredSize>standaloneMemoryLimits.zipEntryBytes" in html
    assert "expandedBytes>standaloneMemoryLimits.zipExpandedBytes" in html
    assert "shared.length>standaloneMemoryLimits.sharedStrings" in html
    assert "assertStandaloneEnrichmentCapacity([...state.files,rec])" in html
    assert "assertStandaloneEnrichmentCapacity();state.devices=[];state.invalid=[];const byMac=new Map()" in html
    assert "byMac.clear();state.invalid=invalid" in html
    assert '"DCA632":"Raspberry Pi"' in html
    assert '"DC A632".replace' not in html
    assert '$("#helpPermissionMode").textContent=engineeringSessionActive()?"engineering":"user"' in html
    assert "isEngineeringActive()" not in html


def test_standalone_two_file_enrichment_mapping_controls():
    html = read_standalone()

    assert 'id="fileInput"' in html
    assert 'id="enrichFileInput"' in html
    assert 'id="browseFilesButton"' in html
    assert 'id="browseEnrichmentFilesButton"' in html
    assert 'id="mappingFileSelect"' in html
    assert 'id="mappingDisplayMode"' in html
    assert '<option value="name">Имя колонки</option>' in html
    assert '<option value="letter">Буква колонки</option>' in html
    assert 'id="copyMappingToAllButton"' in html
    assert 'activeMappingFileId:""' in html
    assert 'mappingDisplayMode:"name"' in html
    assert "function columnLetter(index)" in html
    assert "function mappingLabel(header,index)" in html
    assert "function selectedMappingFile()" in html
    assert "function ensureMappingSelection()" in html
    assert "function renderMappingControls()" in html
    assert 'state.activeMappingFileId=rec.id' in html
    assert 'data-file-id="${esc(f.id)}"' in html
    assert 'Основной":"Файл обогащения' in html
    assert '$("#browseFilesButton").onclick=()=>$("#fileInput").click()' in html
    assert '$("#browseEnrichmentFilesButton").onclick=()=>$("#enrichFileInput").click()' in html
    assert '$("#fileInput").onchange=e=>{loadFiles(e.target.files);e.target.value=""}' in html
    assert '$("#enrichFileInput").onchange=e=>{loadFiles(e.target.files);e.target.value=""}' in html
    assert '$("#mappingFileSelect").onchange=e=>{state.activeMappingFileId=e.target.value;save();renderMapping();renderFiles()}' in html
    assert '$("#mappingDisplayMode").onchange=e=>{state.mappingDisplayMode=e.target.value==="letter"?"letter":"name";save();renderMapping()}' in html
    assert '$("#copyMappingToAllButton").onclick=()=>{const f=selectedMappingFile()' in html
    assert "state.files.forEach(file=>{file.mapping={...f.mapping}})" in html


def test_standalone_ip_mapping_parity_block():
    html = read_standalone()

    assert 'id="ipMappingsInput"' in html
    assert 'id="ipMappingImport"' in html
    assert 'id="autoDetectIpMappings"' in html
    assert 'id="exportIpMappings"' in html
    assert "ipMappings:{}" in html
    assert "function normalizeIp(v)" in html
    assert "function validIp(v)" in html
    assert "function parseIpMappings(text)" in html
    assert "async function importIpMappingsFile(file)" in html
    assert "function exportIpMappingsCsv()" in html
    assert "function autoDetectIpMappings()" in html
    assert "function fillAddressBySwitchIp(device,overwrite=false)" in html
    assert 'device.addressSource="ip_mapping"' in html
    assert "fillAddressBySwitchIp(d);return d" in html
    assert 'id="applyIpMappings"' in html
    assert '$("#ipMappingImport").onchange' in html
    assert '$("#applyIpMappings").onclick=applyIpMappings' in html
    assert '$("#autoDetectIpMappings").onclick=autoDetectIpMappings' in html
    assert '$("#exportIpMappings").onclick=exportIpMappingsCsv' in html
    assert 'state.ipMappings=parseIpMappings($("#ipMappingsInput").value)' in html


def test_standalone_column_manager_parity_block():
    html = read_standalone()

    assert 'id="columnSettings"' in html
    assert 'id="saveColumns"' in html
    assert 'id="resetColumns"' in html
    assert 'id="customColumnName"' in html
    assert 'id="addCustomColumn"' in html
    assert 'id="customColumnSelect"' in html
    assert 'id="removeCustomColumn"' in html
    assert 'id="customColumnList"' in html
    assert 'id="optimizeColumnWidths"' in html
    assert 'id="resetColumnWidths"' in html
    assert 'id="saveColumnWidths"' in html
    assert 'id="loadColumnWidths"' in html
    assert "const defaultVisible=" in html
    assert "columns:[...defaultVisible]" in html
    assert "visible:[...defaultVisible]" in html
    assert "customColumns:[]" in html
    assert "columnWidths:{}" in html
    assert "savedColumnWidths:{}" in html
    assert "function resultColumns()" in html
    assert "function customColumnKey(name)" in html
    assert "function customColumnNameFromKey(key)" in html
    assert "function normalizedCustomColumns()" in html
    assert "function allResultColumns()" in html
    assert "function isCustomColumn(column)" in html
    assert "function columnTitle(column)" in html
    assert "function deviceColumnValue(device,column,index=0)" in html
    assert "fields=device.customFields||device.custom_fields||{}" in html
    assert "function defaultColumnWidth(column)" in html
    assert "function columnWidthFor(column)" in html
    assert "function columnWidthStyle(column)" in html
    assert "function resultColumnWidthProfile()" in html
    assert "function optimizeResultColumnWidths()" in html
    assert "function resetResultColumnWidths()" in html
    assert "function saveResultColumnWidths()" in html
    assert "function loadResultColumnWidths()" in html
    assert 'state.savedColumnWidths=resultColumnWidthProfile()' in html
    assert 'state.columnWidths={...state.savedColumnWidths}' in html
    assert '${columnWidthStyle(c)}' in html
    assert "function renderColumnSettings()" in html
    assert "function renderCustomColumns()" in html
    assert "function addCustomColumn()" in html
    assert "function removeCustomColumn()" in html
    assert "function saveColumnSettings()" in html
    assert "function resetColumnSettings()" in html
    assert "function moveColumn(field,direction)" in html
    assert 'data-column-visible="${esc(c)}"' in html
    assert 'data-move-column="${esc(c)}"' in html
    assert "[Пользовательская] " in html
    assert "return[...defaultVisible,...normalizedCustomColumns()]" in html
    assert "function buildStandaloneExport(type,rows=filtered(),cols=resultColumns())" in html
    assert "cols.map(columnTitle)" in html
    assert "deviceColumnValue(d,c,i)" in html
    assert "Object.fromEntries(cols.map(c=>[columnTitle(c),deviceColumnValue(d,c,i)]))" in html
    assert '$("#addCustomColumn").onclick=addCustomColumn' in html
    assert '$("#customColumnName").onkeydown' in html
    assert '$("#removeCustomColumn").onclick=removeCustomColumn' in html
    assert '$("#optimizeColumnWidths").onclick=optimizeResultColumnWidths' in html
    assert '$("#resetColumnWidths").onclick=resetResultColumnWidths' in html
    assert '$("#saveColumnWidths").onclick=saveResultColumnWidths' in html
    assert '$("#loadColumnWidths").onclick=loadResultColumnWidths' in html
    assert '$("#saveColumns").onclick=saveColumnSettings' in html
    assert '$("#resetColumns").onclick=resetColumnSettings' in html
    assert '$("#columnSettings").onclick' in html


def test_standalone_oui_settings_parity_block():
    html = read_standalone()

    assert 'id="ouiLengthSelect"' in html
    assert 'id="ouiStyleSelect"' in html
    assert 'ouiLength:3' in html
    assert 'ouiStyle:"plain"' in html
    assert "function normalizeOuiSettings()" in html
    assert "function formatOuiPrefix(value)" in html
    assert "function refreshOuiDisplay()" in html
    assert "state.ouiLength*2" in html
    assert 'state.ouiStyle==="colon"' in html
    assert 'state.ouiStyle==="dash"' in html
    assert 'state.ouiStyle==="dot"||state.ouiStyle==="cisco-dot"' in html
    assert "oui:formatOuiPrefix(mac)" in html
    assert 'state.ouiLength=Number($("#ouiLengthSelect").value)' in html
    assert 'state.ouiStyle=$("#ouiStyleSelect").value' in html
    assert "refreshOuiDisplay();save();renderAll()" in html


def test_standalone_theme_settings_parity_block():
    html = read_standalone()

    assert '<meta name="theme-color" content="#0f766e">' in html
    assert "body.dark" in html
    assert 'id="themeButton"' in html
    assert 'id="themeSelect"' in html
    assert 'theme:"light"' in html
    assert "function applyTheme(theme)" in html
    assert "function saveThemePreference(theme)" in html
    assert 'document.body.classList.toggle("dark",state.theme==="dark")' in html
    assert 'meta.content=state.theme==="dark"?"#101817":"#0f766e"' in html
    assert '$("#themeButton").onclick=()=>saveThemePreference' in html
    assert '$("#themeSelect").onchange=e=>saveThemePreference(e.target.value)' in html
    assert "applyTheme(state.theme);renderAll();" in html


def test_standalone_backup_restore_parity_block():
    html = read_standalone()

    assert 'id="exportBackup"' in html
    assert 'id="restoreBackupInput"' in html
    assert 'id="backupStatus"' in html
    assert "function exportStandaloneBackup()" in html
    assert "async function restoreStandaloneBackup(file)" in html
    assert 'app:"MAC Analyzer Pro Standalone"' in html
    assert "version:1" in html
    assert "exportedAt:new Date().toISOString()" in html
    assert 'download("mac-analyzer-standalone-backup.json"' in html
    assert "const parsed=JSON.parse(await file.text())" in html
    assert "state={...emptyState(),...next}" in html
    assert "save();applyTheme(state.theme);renderAll()" in html
    assert '$("#exportBackup").onclick=exportStandaloneBackup' in html
    assert '$("#restoreBackupInput").onchange' in html


def test_standalone_topology_parity_block():
    html = read_standalone()

    assert 'data-view="topology"' in html
    assert 'id="topology"' in html
    assert 'id="topologyGraph"' in html
    assert 'id="exportTopology"' in html
    assert 'id="topoSwitches"' in html
    assert 'id="topoPorts"' in html
    assert 'id="topoLinked"' in html
    assert 'id="topoUnassigned"' in html
    assert "function buildTopology(devices=state.devices)" in html
    assert "const switches={},unassigned=[]" in html
    assert "portCount:ports.length" in html
    assert "summary:{switches:nodes.length" in html
    assert "function renderTopology()" in html
    assert "function exportTopologyHtml()" in html
    assert 'download("mac-topology.html"' in html
    assert "renderAnalytics();renderTimeStatistics();renderClusters();renderQuality();renderTopology();renderInvalid()" in html
    assert '$("#exportTopology").onclick=exportTopologyHtml' in html


def test_standalone_clusters_parity_block():
    html = read_standalone()

    assert 'data-view="clusters"' in html
    assert 'id="clusters"' in html
    assert 'id="clusterChart"' in html
    assert 'id="exportClusters"' in html
    assert 'id="clusterMinSize"' in html
    assert 'data-cluster-field="vendor"' in html
    assert 'data-cluster-field="room"' in html
    assert 'data-cluster-field="switchIp"' in html
    assert "const clusterFieldTitles=" in html
    assert "function clusterFieldValue(device,field)" in html
    assert "function selectedClusterFields()" in html
    assert "function buildClusters(devices=state.devices" in html
    assert "uniqueMacs:new Set()" in html
    assert "largestCluster:clusters[0]?.count||0" in html
    assert "function renderClusters()" in html
    assert "function exportClustersCsv()" in html
    assert 'download("mac-clusters.csv"' in html
    assert "renderAnalytics();renderTimeStatistics();renderClusters();renderQuality();renderTopology()" in html
    assert '$("#exportClusters").onclick=exportClustersCsv' in html
    assert '$("#clusterMinSize").oninput=renderClusters' in html


def test_standalone_chart_export_parity_block():
    html = read_standalone()

    assert 'data-view="analytics"' in html
    assert 'id="analytics"' in html
    assert 'id="exportChartsSvg"' in html
    assert 'id="exportChartsJson"' in html
    assert 'id="vendorChart"' in html
    assert 'id="modelChart"' in html
    assert 'id="roomChart"' in html
    assert 'id="analyticsQualityChart"' in html
    assert 'id="analyticsTimelineChart"' in html
    assert "function chartItemsFromTally(items)" in html
    assert "function snapshotTimelineItems(snapshots=state.snapshots)" in html
    assert "function standaloneChartPayload(devices=state.devices,snapshots=state.snapshots)" in html
    assert "function renderChartItems(root,items)" in html
    assert "function standaloneChartsSvg(payload=standaloneChartPayload())" in html
    assert "function exportChartsSvgStandalone()" in html
    assert "function exportChartsJsonStandalone()" in html
    assert 'id:"timeline",title:"Динамика снимков",type:"line"' in html
    assert 'download("mac-charts.svg",standaloneChartsSvg(),"image/svg+xml")' in html
    assert 'download("mac-charts.json",JSON.stringify(standaloneChartPayload(),null,2),"application/json")' in html
    assert '$("#exportChartsSvg").onclick=exportChartsSvgStandalone' in html
    assert '$("#exportChartsJson").onclick=exportChartsJsonStandalone' in html


def test_standalone_quality_parity_block():
    html = read_standalone()

    assert 'data-view="quality"' in html
    assert 'id="quality"' in html
    assert 'id="runQuality"' in html
    assert 'id="exportQuality"' in html
    assert 'id="qualityScore"' in html
    assert 'id="qualityGrade"' in html
    assert 'id="qualityCompleteness"' in html
    assert 'id="qualityIssuesCount"' in html
    assert 'id="qualityInsights"' in html
    assert 'id="qualityRecommendations"' in html
    assert "function isUnknownVendor(v)" in html
    assert "function validOptionalIp(v)" in html
    assert "function qualityIssue(id,title,count,severity,recommendation)" in html
    assert "function analyzeDataQuality(devices=state.devices,invalid=state.invalid)" in html
    assert 'qualityIssue("invalid_rows","Invalid source rows"' in html
    assert 'qualityIssue("duplicate_macs","Duplicate MAC addresses"' in html
    assert 'qualityIssue("unknown_vendors","Unknown vendors"' in html
    assert "const score=total?" in html
    assert 'grade=score>=90?"A":score>=75?"B":score>=60?"C":"D"' in html
    assert "function renderQuality()" in html
    assert "function exportQualityJson()" in html
    assert 'download("mac-quality-report.json"' in html
    assert "renderClusters();renderQuality();renderTopology()" in html
    assert '$("#runQuality").onclick=()=>{renderQuality();toast("Анализ качества данных завершён")}' in html
    assert '$("#exportQuality").onclick=exportQualityJson' in html


def test_standalone_device_analytics_parity_block():
    html = read_standalone()

    assert 'data-view="device"' in html
    assert 'id="device"' in html
    assert 'id="deviceSelect"' in html
    assert 'id="refreshDeviceAnalytics"' in html
    assert 'id="exportDeviceAnalytics"' in html
    assert 'id="deviceAppearances"' in html
    assert 'id="deviceSources"' in html
    assert 'id="deviceRooms"' in html
    assert 'id="deviceSwitches"' in html
    assert 'id="deviceFields"' in html
    assert 'id="deviceTimelineBody"' in html
    assert 'data-mac="${esc(d.mac||d.macFormatted||"")}"' in html
    assert "function deviceAnalytics(macValue)" in html
    assert "function renderDeviceOptions()" in html
    assert "function renderDeviceAnalytics()" in html
    assert "function exportDeviceAnalyticsHtml()" in html
    assert 'download("mac-device-analytics.html"' in html
    assert "renderResults();renderExportManager();renderDeviceAnalytics();renderModelAnalytics();renderAnalytics()" in html
    assert '$("#resultBody").ondblclick' in html
    assert '$("#deviceSelect").onchange=renderDeviceAnalytics' in html
    assert '$("#exportDeviceAnalytics").onclick=exportDeviceAnalyticsHtml' in html


def test_standalone_model_analytics_parity_block():
    html = read_standalone()

    assert 'data-view="model"' in html
    assert 'id="model"' in html
    assert 'id="modelSelect"' in html
    assert 'id="refreshModelAnalytics"' in html
    assert 'id="exportModelAnalytics"' in html
    assert 'id="modelDevices"' in html
    assert 'id="modelPrefixes"' in html
    assert 'id="modelVendors"' in html
    assert 'id="modelSources"' in html
    assert 'id="modelPrefixList"' in html
    assert 'id="modelDeviceBody"' in html
    assert "function modelAnalytics(modelName)" in html
    assert "function renderModelOptions()" in html
    assert "function renderModelAnalytics()" in html
    assert "function exportModelAnalyticsHtml()" in html
    assert "prefixCounts={}" in html
    assert "sampleMac:formatMac" in html
    assert 'download("mac-model-analytics.html"' in html
    assert "renderDeviceAnalytics();renderModelAnalytics();renderAnalytics()" in html
    assert '$("#modelSelect").onchange=renderModelAnalytics' in html
    assert '$("#exportModelAnalytics").onclick=exportModelAnalyticsHtml' in html


def test_standalone_notifications_parity_block():
    html = read_standalone()

    assert 'data-view="notifications"' in html
    assert 'id="notifications"' in html
    assert 'id="saveNotificationSettings"' in html
    assert 'id="testNotification"' in html
    assert 'id="clearNotifications"' in html
    assert 'id="notificationLog"' in html
    assert 'id="notifyEmailEnabled"' in html
    assert 'id="notifyTelegramEnabled"' in html
    assert 'id="notifySlackEnabled"' in html
    assert 'id="notificationEventAnalysis"' in html
    assert 'id="notificationEventQuality"' in html
    assert 'id="notificationEventBackup"' in html
    assert "function defaultNotificationSettings()" in html
    assert "notificationSettings:defaultNotificationSettings()" in html
    assert "notificationLog:[]" in html
    assert "function notificationSettings()" in html
    assert "function enabledNotificationChannels" in html
    assert "function logNotification(item)" in html
    assert "function notifyEvent(type,title,message" in html
    assert "function renderNotifications()" in html
    assert "function saveNotificationSettings()" in html
    assert "function testStandaloneNotification()" in html
    assert "function clearStandaloneNotifications()" in html
    assert "function runStandaloneQualityCheck()" in html
    assert 'notifyEvent("analysis"' in html
    assert 'notifyEvent("quality"' in html
    assert 'notifyEvent("backup"' in html
    assert "renderColumnSettings();renderNotifications()" in html
    assert '$("#runQuality").onclick=runStandaloneQualityCheck' in html
    assert '$("#saveNotificationSettings").onclick=saveNotificationSettings' in html
    assert '$("#testNotification").onclick=testStandaloneNotification' in html
    assert '$("#clearNotifications").onclick=clearStandaloneNotifications' in html


def test_standalone_scheduler_parity_block():
    html = read_standalone()

    assert 'data-view="scheduler"' in html
    assert 'id="scheduler"' in html
    assert 'id="addLoadedToQueue"' in html
    assert 'id="runQueue"' in html
    assert 'id="clearQueue"' in html
    assert 'id="exportQueueReport"' in html
    assert 'id="queueList"' in html
    assert 'id="queueTotal"' in html
    assert 'id="queuePending"' in html
    assert 'id="queueDone"' in html
    assert 'id="queueErrors"' in html
    assert 'schedulerQueue:[]' in html
    assert "function prepareStandaloneQueueFiles(files=state.files)" in html
    assert 'rows:f.rows||[]' in html
    assert 'rows:structuredClone(f.rows||[])' not in html
    assert "function queueSummary(items=state.schedulerQueue||[])" in html
    assert "function analyzeQueueItem(item)" in html
    assert "function addLoadedFilesToQueue()" in html
    assert "function runStandaloneQueue()" in html
    assert "function renderScheduler()" in html
    assert "function clearStandaloneQueue()" in html
    assert "function exportQueueReport()" in html
    assert "rowToDevice(row,file,ri)" in html
    assert 'standaloneSnapshot("Очередь "+new Date().toLocaleString("ru-RU"),"scheduler",state.devices)' in html
    assert 'download("mac-scheduler-report.json"' in html
    assert "renderNotifications();renderScheduler()" in html
    assert '$("#addLoadedToQueue").onclick=addLoadedFilesToQueue' in html
    assert '$("#runQueue").onclick=runStandaloneQueue' in html
    assert '$("#clearQueue").onclick=clearStandaloneQueue' in html
    assert '$("#exportQueueReport").onclick=exportQueueReport' in html


def test_standalone_external_api_enrichment_parity_block():
    html = read_standalone()

    assert 'data-view="externalApi"' in html
    assert 'id="externalApi"' in html
    assert 'id="externalApiEnabled"' in html
    assert 'id="externalProviderSelect"' in html
    assert 'id="externalEndpointInput"' in html
    assert 'id="externalRateLimitInput"' in html
    assert 'id="externalCacheTtlInput"' in html
    assert 'id="externalApiKeyInput"' in html
    assert 'id="externalOnlyUnknown"' in html
    assert 'id="externalLookupMacInput"' in html
    assert 'id="testExternalApiLookup"' in html
    assert 'id="runExternalApiEnrichment"' in html
    assert 'id="clearExternalApiCache"' in html
    assert 'id="exportExternalApiCache"' in html
    assert 'id="externalSelectedMacs"' in html
    assert 'id="externalApiStatus"' in html
    assert "function defaultExternalApiSettings()" in html
    assert 'externalApiSettings:defaultExternalApiSettings()' in html
    assert 'externalApiCache:{}' in html
    assert 'externalApiSummary:{candidates:0,lookups:0,cached:0,updated:0,skipped:0}' in html
    assert "function normalizeExternalApiSettings" in html
    assert "function externalCacheKey(provider,mac)" in html
    assert "function externalCacheFresh(entry,ttlDays)" in html
    assert "function externalLookupVendor(mac,settings)" in html
    assert "async function testExternalApiLookup()" in html
    assert "async function runExternalApiEnrichment()" in html
    assert "function renderExternalApiPanel()" in html
    assert "function saveExternalApiSettingsStandalone()" in html
    assert "function clearExternalApiCacheStandalone()" in html
    assert "function exportExternalApiCacheStandalone()" in html
    assert 'settings.onlyUnknown&&!isUnknownVendor(device.vendor)' in html
    assert 'summary.lookups<settings.rateLimit' in html
    assert 'device.vendorSource=cached&&vendor===cached.value?"external_cache":"external_api"' in html
    assert 'download("mac-external-api-cache.json"' in html
    assert "renderScheduler();renderExternalApiPanel()" in html
    assert '$("#saveExternalApiSettings").onclick=saveExternalApiSettingsStandalone' in html
    assert '$("#testExternalApiLookup").onclick=testExternalApiLookup' in html
    assert '$("#runExternalApiEnrichment").onclick=runExternalApiEnrichment' in html
    assert '$("#clearExternalApiCache").onclick=clearExternalApiCacheStandalone' in html
    assert '$("#exportExternalApiCache").onclick=exportExternalApiCacheStandalone' in html


def test_standalone_dashboard_parity_block():
    html = read_standalone()

    assert 'data-view="dashboard"' in html
    assert 'id="dashboard"' in html
    assert 'id="dashboardVendorFilter"' in html
    assert 'id="dashboardRoomFilter"' in html
    assert 'id="dashboardShowUnknown"' in html
    assert 'id="dashboardChartLimit"' in html
    assert 'id="saveDashboardSettings"' in html
    assert 'id="exportDashboard"' in html
    assert 'id="dashDevices"' in html
    assert 'id="dashUniqueMacs"' in html
    assert 'id="dashVendors"' in html
    assert 'id="dashRooms"' in html
    assert 'id="dashSwitches"' in html
    assert 'id="dashKnown"' in html
    assert 'id="dashUnknown"' in html
    assert 'id="dashKnownPercent"' in html
    assert 'id="dashboardVendorChart"' in html
    assert 'id="dashboardModelChart"' in html
    assert 'id="dashboardRoomChart"' in html
    assert "function defaultDashboardSettings()" in html
    assert "dashboardSettings:defaultDashboardSettings()" in html
    assert "function normalizeDashboardSettings" in html
    assert "function dashboardSettingsFromForm()" in html
    assert "function dashboardFilterDevices" in html
    assert "function dashboardPayload" in html
    assert "function renderDashboardOptions(payload)" in html
    assert "function renderDashboard()" in html
    assert "function saveDashboardSettingsStandalone()" in html
    assert "function exportDashboardHtml()" in html
    assert "knownPercent:filtered.length?Math.round(known/filtered.length*100):0" in html
    assert 'download("mac-dashboard.html"' in html
    assert "renderExternalApiPanel();renderDashboard()" in html
    assert "function tally(items,key,limit=8)" in html
    assert '$("#dashboardVendorFilter").onchange=renderDashboard' in html
    assert '$("#dashboardRoomFilter").onchange=renderDashboard' in html
    assert '$("#dashboardShowUnknown").onchange=renderDashboard' in html
    assert '$("#dashboardChartLimit").oninput=renderDashboard' in html
    assert '$("#saveDashboardSettings").onclick=saveDashboardSettingsStandalone' in html
    assert '$("#exportDashboard").onclick=exportDashboardHtml' in html


def test_standalone_autosave_parity_block():
    html = read_standalone()

    assert 'data-view="autosave"' in html
    assert 'id="autosave"' in html
    assert 'id="autosaveSlotInput"' in html
    assert 'id="saveAutosave"' in html
    assert 'id="restoreAutosave"' in html
    assert 'id="deleteAutosave"' in html
    assert 'id="autosaveStatus"' in html
    assert 'id="autosaveList"' in html
    assert 'id="autosaveSlotCount"' in html
    assert 'id="autosaveLastSlot"' in html
    assert 'id="autosaveLastReason"' in html
    assert 'id="autosaveLastBytes"' in html
    assert "autosaveSlots:[]" in html
    assert "function autosavePayload()" in html
    assert "function autosaveBytes(payload)" in html
    assert "function autosaveSlotName()" in html
    assert "function listStandaloneAutosaves()" in html
    assert "function saveStandaloneAutosave(slot=autosaveSlotName(),reason=\"manual\")" in html
    assert "function restoreStandaloneAutosave(slot=autosaveSlotName())" in html
    assert "function deleteStandaloneAutosave(slot=autosaveSlotName())" in html
    assert "function renderAutosaves()" in html
    assert "function persistIntervalAutosave()" in html
    assert "function persistBeforeUnloadAutosave()" in html
    assert "delete payload.autosaveSlots" in html
    assert "autosaveSlots:currentSlots" in html
    assert "renderDashboard();renderAutosaves()" in html
    assert '$("#saveAutosave").onclick' in html
    assert '$("#restoreAutosave").onclick=()=>restoreStandaloneAutosave()' in html
    assert '$("#deleteAutosave").onclick=()=>deleteStandaloneAutosave()' in html
    assert '$("#autosaveList").onclick' in html
    assert "setInterval(persistIntervalAutosave,60000)" in html
    assert 'window.addEventListener("beforeunload",persistBeforeUnloadAutosave)' in html
    assert "function autosavePayload(){const payload=compactStandaloneState()" in html


def test_standalone_vendor_model_mappings_parity_block():
    html = read_standalone()

    assert 'data-view="mappings"' in html
    assert 'id="mappings"' in html
    assert 'id="vendorMappingKey"' in html
    assert 'id="vendorMappingValue"' in html
    assert 'id="addVendorMapping"' in html
    assert 'id="vendorMappingList"' in html
    assert 'id="vendorMappingCount"' in html
    assert 'id="modelMappingKey"' in html
    assert 'id="modelMappingValue"' in html
    assert 'id="addModelMapping"' in html
    assert 'id="modelMappingList"' in html
    assert 'id="modelMappingCount"' in html
    assert 'id="learnMappings"' in html
    assert 'id="applyMappings"' in html
    assert 'id="exportMappings"' in html
    assert "vendorMappings:{}" in html
    assert "modelMappings:{}" in html
    assert "function bestMappingMatch(mac,rules)" in html
    assert "function vendorFor(mac,current=\"\")" in html
    assert "function modelFor(mac,current=\"\")" in html
    assert "d.model=modelFor(mac,d.model)" in html
    assert "function normalizeMappingKey" in html
    assert "function mappingRules(kind)" in html
    assert "function renderMappingsPanel()" in html
    assert "function addMappingRule(kind,key,value,source=\"manual\")" in html
    assert "function deleteMappingRule(kind,key)" in html
    assert "function learnMappingsFromResults(minCount=2)" in html
    assert "function applyMappingsToDevices()" in html
    assert "function exportMappingsJson()" in html
    assert "renderAutosaves();renderMappingsPanel();renderVendorModelHistory()" in html
    assert 'download("mac-vendor-model-mappings.json"' in html
    assert '$("#addVendorMapping").onclick' in html
    assert '$("#addModelMapping").onclick' in html
    assert '$("#learnMappings").onclick=()=>learnMappingsFromResults(2)' in html
    assert '$("#applyMappings").onclick=applyMappingsToDevices' in html
    assert '$("#exportMappings").onclick=exportMappingsJson' in html
    assert '$("#mappings").onclick' in html
    assert "state.vendorMappings={...(state.vendorMappings||{}),[key]:v.trim()}" in html


def test_standalone_local_database_search_parity_block():
    html = read_standalone()

    assert 'data-view="database"' in html
    assert 'id="database"' in html
    assert 'id="localDatabaseSearchInput"' in html
    assert 'id="localDatabaseSearchButton"' in html
    assert 'id="refreshLocalDatabase"' in html
    assert 'id="localDatabaseResults"' in html
    assert 'id="localDatabaseDevice"' in html
    assert 'id="localDbDevices"' in html
    assert 'id="localDbSnapshots"' in html
    assert 'id="localDbMappings"' in html
    assert 'id="localDbAutosaves"' in html
    assert "function localDatabaseSummary()" in html
    assert "function localDatabaseHaystack(values)" in html
    assert "function localDatabaseSearch(query=\"\",limit=100)" in html
    assert "function localDatabaseDeviceLookup(macValue)" in html
    assert "function renderLocalDatabase()" in html
    assert "function renderLocalDatabaseSearch()" in html
    assert "function openLocalDatabaseDevice(mac)" in html
    assert 'type:"device"' in html
    assert 'type:"snapshotDevice"' in html
    assert 'type:"ipMapping"' in html
    assert 'type:"vendorMapping"' in html
    assert 'type:"modelMapping"' in html
    assert 'type:"autosave"' in html
    assert "renderMappingsPanel();renderVendorModelHistory();renderLocalDatabase()" in html
    assert '$("#localDatabaseSearchButton").onclick=renderLocalDatabaseSearch' in html
    assert '$("#refreshLocalDatabase").onclick' in html
    assert '$("#localDatabaseSearchInput").onkeydown' in html
    assert '$("#localDatabaseResults").ondblclick' in html
    assert "openLocalDatabaseDevice(mac)" in html


def test_standalone_app_log_performance_metrics_parity_block():
    html = read_standalone()

    assert 'data-view="logs"' in html
    assert 'id="logs"' in html
    assert 'id="metricOperationFilter"' in html
    assert 'id="refreshLogs"' in html
    assert 'id="exportLogs"' in html
    assert 'id="exportLogsCsv"' in html
    assert 'id="exportLogsHtml"' in html
    assert 'id="exportLogsXlsx"' in html
    assert 'id="exportLogsPdf"' in html
    assert 'id="clearLogs"' in html
    assert 'id="logCount"' in html
    assert 'id="metricCount"' in html
    assert 'id="metricAvgMs"' in html
    assert 'id="metricMaxMs"' in html
    assert 'id="appLogList"' in html
    assert 'id="performanceMetricList"' in html
    assert "appLogs:[]" in html
    assert "performanceMetrics:[]" in html
    assert "function logAction(action,details=\"\")" in html
    assert "function savePerformanceMetric(operation,durationMs,details=\"\")" in html
    assert "function performanceStatistics(operation=\"\")" in html
    assert "function renderLogsPanel()" in html
    assert "function clearLogsAndMetrics()" in html
    assert "function logsExportTable()" in html
    assert "function exportLogsJson()" in html
    assert "function exportLogsCsv()" in html
    assert "function exportLogsHtml()" in html
    assert "function exportLogsXlsx()" in html
    assert "function exportLogsPdf()" in html
    assert "function timedOperation(operation,details,fn)" in html
    assert 'download("mac-standalone-logs.json"' in html
    assert 'download("mac-standalone-logs.csv"' in html
    assert 'download("mac-standalone-logs.html"' in html
    assert 'download("mac-standalone-logs.xlsx",buildXlsxFromTable(logsExportTable(),"Logs")' in html
    assert 'download("mac-standalone-logs.pdf",buildSimplePdf("MAC Analyzer Logs"' in html
    assert 'timedOperation("analyze"' in html
    assert 'timedOperation("scheduler_queue"' in html
    assert 'timedOperation("local_database_search"' in html
    assert "renderLocalDatabase();renderLogsPanel()" in html
    assert '$("#refreshLogs").onclick=renderLogsPanel' in html
    assert '$("#exportLogs").onclick=exportLogsJson' in html
    assert '$("#exportLogsCsv").onclick=exportLogsCsv' in html
    assert '$("#exportLogsHtml").onclick=exportLogsHtml' in html
    assert '$("#exportLogsXlsx").onclick=exportLogsXlsx' in html
    assert '$("#exportLogsPdf").onclick=exportLogsPdf' in html
    assert '$("#clearLogs").onclick=clearLogsAndMetrics' in html
    assert '$("#metricOperationFilter").onchange=renderLogsPanel' in html


def test_standalone_single_file_analysis_parity_block():
    html = read_standalone()

    assert 'data-view="single"' in html
    assert 'id="single"' in html
    assert 'id="singleFileInput"' in html
    assert 'accept=".csv,.tsv,.txt,.json,.xlsx,.xlsm,.xls"' in html
    assert 'id="singleFileStatus"' in html
    assert 'id="singleManualMappingToggle"' in html
    assert 'id="singleMappingGrid"' in html
    assert 'id="singleFileAnalyze"' in html
    assert 'id="singleFileMode"' in html
    assert 'id="singleRows"' in html
    assert 'id="singleValid"' in html
    assert 'id="singleInvalid"' in html
    assert 'id="singleUnique"' in html
    assert 'id="singleDetectedColumns"' in html
    assert 'id="singlePreviewHead"' in html
    assert 'id="singlePreviewBody"' in html
    assert 'id="singlePreviewCount"' in html
    assert "singleFile:null" in html
    assert "singleResult:null" in html
    assert "function renderSingleMappingGrid()" in html
    assert "function singleManualMapping()" in html
    assert "function renderSinglePreview(headers=[],rows=[],invalid=[])" in html
    assert "async function inspectSingleFile(file)" in html
    assert "function summarizeSingleFile(filename,headers,rows,mapping,devices,invalid)" in html
    assert "function renderSingleReport(result)" in html
    assert "function analyzeSingleFileStandalone()" in html
    assert 'timedOperation("single_file_analyze"' in html
    assert 'state.snapshots.unshift(standaloneSnapshot("Single file: "+file.name,file.name,devices))' in html
    assert "function compactStandaloneState()" in html
    assert "devices:(state.devices||[]).slice(0,2000)" in html
    assert 'const allRows=filtered(),rows=allRows.slice(0,500)' in html
    assert "state.files=[{...file,mapping}]" in html
    assert "state.devices=devices" in html
    assert "renderLogsPanel();renderEngineeringState();renderHelp();renderSingleMappingGrid()" in html
    assert '$("#singleFileInput").onchange=e=>inspectSingleFile(e.target.files[0])' in html
    assert '$("#singleManualMappingToggle").onchange=renderSingleMappingGrid' in html
    assert '$("#singleMappingGrid").onchange' in html
    assert '$("#singleFileAnalyze").onclick=analyzeSingleFileStandalone' in html


def test_standalone_engineering_security_parity_block():
    html = read_standalone()

    assert 'data-view="engineering"' in html
    assert 'id="engineering"' in html
    assert 'id="engineeringLogin"' in html
    assert 'id="engineeringLogout"' in html
    assert 'id="engineeringStatus"' in html
    assert 'id="engineeringPassword"' in html
    assert 'id="engineeringTtl"' in html
    assert 'id="engineeringRole"' in html
    assert 'id="engineeringPermissionCount"' in html
    assert 'id="engineeringExpires"' in html
    assert 'id="engineeringTokenState"' in html
    assert 'id="engineeringPermissions"' in html
    assert 'const engineeringPermissions=[' in html
    assert '"delete:history"' in html
    assert '"delete:mappings"' in html
    assert '"delete:api-cache"' in html
    assert '"write:settings"' in html
    assert "engineeringSession:null" in html
    assert "async function engineeringTokenHash(token)" in html
    assert "function engineeringSessionActive(permission=\"\")" in html
    assert "function requireEngineering(permission,action)" in html
    assert "async function issueEngineeringSession(ttlMinutes=480)" in html
    assert "async function loginEngineeringStandalone()" in html
    assert "function logoutEngineeringStandalone()" in html
    assert "function renderEngineeringState()" in html
    assert 'password!=="admin123"' in html
    assert "renderLogsPanel();renderEngineeringState()" in html
    assert 'requireEngineering("write:settings","clear all")' in html
    assert 'requireEngineering("delete:tasks","clear queue")' in html
    assert 'requireEngineering("delete:api-cache","clear external api cache")' in html
    assert 'requireEngineering("delete:mappings","delete mapping")' in html
    assert '$("#engineeringLogin").onclick=loginEngineeringStandalone' in html
    assert '$("#engineeringLogout").onclick=logoutEngineeringStandalone' in html
    assert '$("#engineeringPassword").onkeydown' in html


def test_standalone_multi_snapshot_comparison_parity_block():
    html = read_standalone()

    assert 'id="compareManyBtn"' in html
    assert 'id="manySnapSelect"' in html
    assert 'id="exportCompareJson"' in html
    assert 'id="exportCompareCsv"' in html
    assert 'id="exportCompareTxt"' in html
    assert 'id="exportCompareXlsx"' in html
    assert 'id="exportCompareExcel"' in html
    assert 'id="exportComparePdf"' in html
    assert 'id="compareAdded"' in html
    assert 'id="compareRemoved"' in html
    assert 'id="compareModified"' in html
    assert 'id="compareStable"' in html
    assert 'id="compareSummary"' in html
    assert "lastComparison:null" in html
    assert 'const comparisonFields=["vendor","model","ip","address","room","switchIp","switchPort"]' in html
    assert "function deviceMap(devices=[])" in html
    assert "function compareDeviceSets(baselineDevices=[],currentDevices=[],fieldsToCompare=comparisonFields,meta={})" in html
    assert "function renderComparison(result)" in html
    assert "function selectedManySnapshotIds()" in html
    assert "function compareManySnapshots()" in html
    assert "function comparisonTable()" in html
    assert "function exportComparisonJson()" in html
    assert "function exportComparisonCsv()" in html
    assert "function exportComparisonTxt()" in html
    assert "function exportComparisonXlsx()" in html
    assert "function exportComparisonExcelXml()" in html
    assert "function exportComparisonPdf()" in html
    assert 'download("mac-comparison.txt"' in html
    assert 'download("mac-comparison.xlsx",buildXlsxFromTable(comparisonTable(),"Comparison")' in html
    assert 'download("mac-comparison.xls"' in html
    assert 'download("mac-comparison.pdf",buildSimplePdf("MAC Analyzer Comparison"' in html
    assert '$("#manySnapSelect").innerHTML=opts' in html
    assert '$("#compareManyBtn").onclick=compareManySnapshots' in html
    assert '$("#exportCompareJson").onclick=exportComparisonJson' in html
    assert '$("#exportCompareCsv").onclick=exportComparisonCsv' in html
    assert '$("#exportCompareTxt").onclick=exportComparisonTxt' in html
    assert '$("#exportCompareXlsx").onclick=exportComparisonXlsx' in html
    assert '$("#exportCompareExcel").onclick=exportComparisonExcelXml' in html
    assert '$("#exportComparePdf").onclick=exportComparisonPdf' in html


def test_standalone_time_statistics_parity_block():
    html = read_standalone()

    assert 'data-view="timeStats"' in html
    assert 'id="timeStats"' in html
    assert 'id="timeStatsDays"' in html
    assert 'id="refreshTimeStats"' in html
    assert 'id="exportTimeStats"' in html
    assert 'id="timeStatsSnapshots"' in html
    assert 'id="timeStatsDevices"' in html
    assert 'id="timeStatsNew"' in html
    assert 'id="timeStatsMovements"' in html
    assert 'id="timeStatsTrend"' in html
    assert 'id="timeStatsMovementList"' in html
    assert 'id="timeStatsHistoryBody"' in html
    assert "function snapshotTime(snapshot)" in html
    assert "function timeStatsRows(days=30)" in html
    assert "function detectSnapshotMovements(previousDevices=[],currentDevices=[],snapshotName=\"\")" in html
    assert "function buildTimeStatistics(days=30)" in html
    assert "function renderTimeStatistics()" in html
    assert "function exportTimeStatisticsJson()" in html
    assert "compareDeviceSets(prev.devices,devices,comparisonFields" in html
    assert 'download("mac-time-statistics.json"' in html
    assert "renderAnalytics();renderTimeStatistics();renderClusters()" in html
    assert '$("#refreshTimeStats").onclick=renderTimeStatistics' in html
    assert '$("#timeStatsDays").oninput=renderTimeStatistics' in html
    assert '$("#exportTimeStats").onclick=exportTimeStatisticsJson' in html


def test_standalone_export_manager_parity_block():
    html = read_standalone()

    assert 'data-view="export"' in html
    assert 'id="export"' in html
    assert 'id="exportFormatSelect"' in html
    assert '<option value="csv">CSV</option>' in html
    assert '<option value="txt">TXT</option>' in html
    assert '<option value="html">HTML</option>' in html
    assert '<option value="json">JSON</option>' in html
    assert '<option value="yaml">YAML</option>' in html
    assert '<option value="xlsx">Excel XLSX</option>' in html
    assert '<option value="xls">Excel XML</option>' in html
    assert '<option value="pdf">PDF</option>' in html
    assert 'data-export="txt"' in html
    assert 'data-export="yaml"' in html
    assert 'data-export="xlsx"' in html
    assert 'data-export="pdf"' in html
    assert 'id="exportOnlyFiltered"' in html
    assert 'id="runManagedExport"' in html
    assert 'id="refreshExportPreview"' in html
    assert 'id="exportRows"' in html
    assert 'id="exportColumns"' in html
    assert 'id="exportFormatLabel"' in html
    assert 'id="exportFileSize"' in html
    assert 'id="exportColumnList"' in html
    assert 'id="exportPreview"' in html
    assert "function selectedExportColumns()" in html
    assert "function exportTable(rows,cols)" in html
    assert "function csvLine(row,separator=\",\")" in html
    assert "function yamlScalar(value)" in html
    assert "function xmlSafe(value)" in html
    assert "function xlsxColName(index)" in html
    assert "function crc32(bytes)" in html
    assert "function zipStore(files)" in html
    assert "function buildXlsxFromTable(table,sheetName=\"MAC Analyzer\")" in html
    assert "function buildStandaloneXlsx(rows,cols)" in html
    assert "function pdfSafeText(value)" in html
    assert "function buildSimplePdf(title,lines)" in html
    assert "function standalonePdfLines(rows,cols)" in html
    assert "function buildStandaloneExport(type,rows=filtered(),cols=resultColumns())" in html
    assert 'xlsx:["mac-analysis.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]' in html
    assert 'if(fmt==="xlsx")return{filename:metadata.xlsx[0],mimeType:metadata.xlsx[1],content:buildStandaloneXlsx(rows,cols)' in html
    assert 'new Uint8Array([0x50,0x4b,0x03,0x04' in html
    assert 'name:"xl/worksheets/sheet1.xml"' in html
    assert 'pdf:["mac-analysis.pdf","application/pdf"]' in html
    assert 'if(fmt==="pdf")return{filename:metadata.pdf[0],mimeType:metadata.pdf[1],content:buildSimplePdf("MAC Analyzer Export",standalonePdfLines(rows,cols))}' in html
    assert 'let pdf="%PDF-1.4\\n"' in html
    assert "function renderExportManager()" in html
    assert "payload.preview||String(payload.content).slice(0,6000)" in html
    assert "function runManagedExport()" in html
    assert 'download(payload.filename,payload.content,payload.mimeType)' in html
    assert "content instanceof Uint8Array" in html
    assert "renderResults();renderExportManager();renderDeviceAnalytics()" in html
    assert '$("#exportFormatSelect").onchange=renderExportManager' in html
    assert '$("#exportOnlyFiltered").onchange=renderExportManager' in html
    assert '$("#refreshExportPreview").onclick=renderExportManager' in html
    assert '$("#runManagedExport").onclick=runManagedExport' in html
    assert '$("#exportColumnList").onchange=renderExportManager' in html


def test_standalone_mac_history_parity_block():
    html = read_standalone()

    assert 'data-view="history"' in html
    assert 'id="history"' in html
    assert 'id="historyQueryInput"' in html
    assert 'id="runHistorySearch"' in html
    assert 'id="exportHistoryJson"' in html
    assert 'id="exportHistoryCsv"' in html
    assert 'id="exportHistoryHtml"' in html
    assert 'id="exportHistoryXlsx"' in html
    assert 'id="exportHistoryPdf"' in html
    assert 'id="optimizeHistoryWidths"' in html
    assert 'id="resetHistoryWidths"' in html
    assert 'id="saveHistoryWidths"' in html
    assert 'id="loadHistoryWidths"' in html
    assert 'id="clearStandaloneHistory"' in html
    assert 'id="historyRecords"' in html
    assert 'id="historyUniqueMacs"' in html
    assert 'id="historySources"' in html
    assert 'id="historyMovements"' in html
    assert 'id="historyHead"' in html
    assert 'id="historyBody"' in html
    assert 'id="historyTimeline"' in html
    assert 'id="snapshots"' in html
    assert "historyColumnWidths:{}" in html
    assert "savedHistoryColumnWidths:{}" in html
    assert "function historyRecordFromDevice(device,source,recordedAt)" in html
    assert "function standaloneHistoryRecords(query=\"\",limit=500)" in html
    assert "function standaloneHistoryMovements(query=\"\")" in html
    assert "function buildStandaloneHistory(query=\"\")" in html
    assert "const historyColumns=" in html
    assert "function historyColumnValue(record,column)" in html
    assert "function defaultHistoryColumnWidth(column)" in html
    assert "function historyColumnWidthFor(column)" in html
    assert "function historyColumnWidthStyle(column)" in html
    assert "function historyColumnWidthProfile()" in html
    assert "function optimizeHistoryColumnWidths()" in html
    assert "function resetHistoryColumnWidths()" in html
    assert "function saveHistoryColumnWidths()" in html
    assert "function loadHistoryColumnWidths()" in html
    assert 'state.savedHistoryColumnWidths=historyColumnWidthProfile()' in html
    assert 'state.historyColumnWidths={...state.savedHistoryColumnWidths}' in html
    assert 'historyColumns.map(([c,title])=>`<th ${historyColumnWidthStyle(c)}>' in html
    assert 'historyColumns.map(([c])=>`<td ${historyColumnWidthStyle(c)}>' in html
    assert "function renderStandaloneHistorySearch()" in html
    assert "function standaloneHistoryTable(data=buildStandaloneHistory" in html
    assert "function exportStandaloneHistoryJson()" in html
    assert "function exportStandaloneHistoryCsv()" in html
    assert "function exportStandaloneHistoryHtml()" in html
    assert "function exportStandaloneHistoryXlsx()" in html
    assert "function exportStandaloneHistoryPdf()" in html
    assert "function clearStandaloneHistorySnapshots()" in html
    assert "detectSnapshotMovements(snaps[i-1].devices||[],snaps[i].devices||[]" in html
    assert 'download("mac-standalone-history.json"' in html
    assert 'download("mac-standalone-history.csv"' in html
    assert 'download("mac-standalone-history.html"' in html
    assert 'download("mac-standalone-history.xlsx",buildXlsxFromTable(standaloneHistoryTable(),"MAC History")' in html
    assert 'download("mac-standalone-history.pdf",buildSimplePdf("MAC Analyzer History"' in html
    assert 'requireEngineering("delete:history","clear standalone history")' in html
    assert "renderSnapshots();renderStandaloneHistorySearch();renderColumnSettings()" in html
    assert '$("#runHistorySearch").onclick=renderStandaloneHistorySearch' in html
    assert '$("#historyQueryInput").onkeydown' in html
    assert '$("#historyBody").ondblclick' in html
    assert '$("#optimizeHistoryWidths").onclick=optimizeHistoryColumnWidths' in html
    assert '$("#resetHistoryWidths").onclick=resetHistoryColumnWidths' in html
    assert '$("#saveHistoryWidths").onclick=saveHistoryColumnWidths' in html
    assert '$("#loadHistoryWidths").onclick=loadHistoryColumnWidths' in html
    assert '$("#exportHistoryJson").onclick=exportStandaloneHistoryJson' in html
    assert '$("#exportHistoryCsv").onclick=exportStandaloneHistoryCsv' in html
    assert '$("#exportHistoryHtml").onclick=exportStandaloneHistoryHtml' in html
    assert '$("#exportHistoryXlsx").onclick=exportStandaloneHistoryXlsx' in html
    assert '$("#exportHistoryPdf").onclick=exportStandaloneHistoryPdf' in html
    assert '$("#clearStandaloneHistory").onclick=clearStandaloneHistorySnapshots' in html


def test_standalone_snapshot_management_parity_block():
    html = read_standalone()

    assert 'id="selectAllSnapshots"' in html
    assert 'id="exportSnapshotsJson"' in html
    assert 'id="exportSnapshotsCsv"' in html
    assert 'id="exportSnapshotsHtml"' in html
    assert 'id="exportSnapshotsXlsx"' in html
    assert 'id="exportSnapshotsPdf"' in html
    assert 'id="deleteSelectedSnapshots"' in html
    assert 'id="snapshotCount"' in html
    assert 'id="snapshotDeviceTotal"' in html
    assert 'id="snapshotUniqueMacs"' in html
    assert 'id="snapshotSourceCount"' in html
    assert 'data-snapshot-select="${esc(s.id)}"' in html
    assert 'data-export-snapshot="${s.id}"' in html
    assert 'data-delete-snapshot="${s.id}"' in html
    assert "function snapshotSummary(snapshots=state.snapshots||[])" in html
    assert "function selectedSnapshotIds()" in html
    assert "function selectedSnapshots()" in html
    assert "function snapshotExportPayload(snapshots=selectedSnapshots())" in html
    assert "function snapshotExportTable(snapshots=selectedSnapshots())" in html
    assert "function exportSnapshotsJson()" in html
    assert "function exportSnapshotsCsv()" in html
    assert "function exportSnapshotsHtml()" in html
    assert "function exportSnapshotsXlsx()" in html
    assert "function exportSnapshotsPdf()" in html
    assert "function deleteSnapshotById(id)" in html
    assert "function deleteSelectedSnapshots()" in html
    assert 'download("mac-snapshots.json"' in html
    assert 'download("mac-snapshots.csv"' in html
    assert 'download("mac-snapshots.html"' in html
    assert 'download("mac-snapshots.xlsx",buildXlsxFromTable(snapshotExportTable(),"Snapshots")' in html
    assert 'download("mac-snapshots.pdf",buildSimplePdf("MAC Analyzer Snapshots"' in html
    assert 'requireEngineering("delete:snapshots","delete snapshot")' in html
    assert 'requireEngineering("delete:snapshots","delete selected snapshots")' in html
    assert '$("#selectAllSnapshots").onclick' in html
    assert '$("#exportSnapshotsJson").onclick=exportSnapshotsJson' in html
    assert '$("#exportSnapshotsCsv").onclick=exportSnapshotsCsv' in html
    assert '$("#exportSnapshotsHtml").onclick=exportSnapshotsHtml' in html
    assert '$("#exportSnapshotsXlsx").onclick=exportSnapshotsXlsx' in html
    assert '$("#exportSnapshotsPdf").onclick=exportSnapshotsPdf' in html
    assert '$("#deleteSelectedSnapshots").onclick=deleteSelectedSnapshots' in html
    assert 'dataset.exportSnapshot' in html
    assert 'dataset.deleteSnapshot' in html


def test_standalone_vendor_model_history_parity_block():
    html = read_standalone()

    assert 'data-view="vendorHistory"' in html
    assert 'id="vendorHistory"' in html
    assert 'id="vendorHistoryQuery"' in html
    assert 'id="refreshVendorHistory"' in html
    assert 'id="exportVendorHistoryJson"' in html
    assert 'id="exportVendorHistoryCsv"' in html
    assert 'id="exportVendorHistoryHtml"' in html
    assert 'id="exportVendorHistoryXlsx"' in html
    assert 'id="exportVendorHistoryPdf"' in html
    assert 'id="vendorHistoryOuiCount"' in html
    assert 'id="vendorHistoryMac5Count"' in html
    assert 'id="vendorHistoryVendorCount"' in html
    assert 'id="vendorHistoryLoadCount"' in html
    assert 'id="vendorHistoryVendorList"' in html
    assert 'id="vendorHistoryModelList"' in html
    assert 'id="vendorHistoryLoadList"' in html
    assert "function vendorHistoryObservations()" in html
    assert "function incrementHistoryMap(map,key,value,source,observedAt)" in html
    assert "function buildVendorModelHistory(query=\"\")" in html
    assert "function renderVendorModelHistory()" in html
    assert "function vendorModelHistoryTable(data=buildVendorModelHistory" in html
    assert "function exportVendorModelHistoryJson()" in html
    assert "function exportVendorModelHistoryCsv()" in html
    assert "function exportVendorModelHistoryHtml()" in html
    assert "function exportVendorModelHistoryXlsx()" in html
    assert "function exportVendorModelHistoryPdf()" in html
    assert 'source:"manual_vendor_mapping"' in html
    assert 'source:"manual_model_mapping"' in html
    assert 'download("mac-vendor-model-history.json"' in html
    assert 'download("mac-vendor-model-history.csv"' in html
    assert 'download("mac-vendor-model-history.html"' in html
    assert 'download("mac-vendor-model-history.xlsx",buildXlsxFromTable(vendorModelHistoryTable(),"Vendor Model")' in html
    assert 'download("mac-vendor-model-history.pdf",buildSimplePdf("Vendor Model History"' in html
    assert "renderMappingsPanel();renderVendorModelHistory();renderLocalDatabase()" in html
    assert '$("#refreshVendorHistory").onclick=renderVendorModelHistory' in html
    assert '$("#vendorHistoryQuery").oninput=renderVendorModelHistory' in html
    assert '$("#exportVendorHistoryJson").onclick=exportVendorModelHistoryJson' in html
    assert '$("#exportVendorHistoryCsv").onclick=exportVendorModelHistoryCsv' in html
    assert '$("#exportVendorHistoryHtml").onclick=exportVendorModelHistoryHtml' in html
    assert '$("#exportVendorHistoryXlsx").onclick=exportVendorModelHistoryXlsx' in html
    assert '$("#exportVendorHistoryPdf").onclick=exportVendorModelHistoryPdf' in html


def test_standalone_clipboard_context_actions_parity_block():
    html = read_standalone()

    assert 'id="copyResultsTsv"' in html
    assert 'id="copySelectedResultMac"' in html
    assert 'id="copyHistoryTable"' in html
    assert 'id="copyHistoryMac"' in html
    assert 'id="copyLocalDatabaseDevice"' in html
    assert 'selectedResultMac:""' in html
    assert 'selectedHistoryMac:""' in html
    assert 'selectedLocalDatabaseMac:""' in html
    assert ".selected{outline:2px solid var(--brand)" in html

    assert "function clipboardSafeCell(value)" in html
    assert "function tableToTsv(rows)" in html
    assert "async function copyTextToClipboard(text,label=\"data\")" in html
    assert "navigator.clipboard&&navigator.clipboard.writeText" in html
    assert "document.execCommand(\"copy\")" in html
    assert "function filteredResultsClipboardText()" in html
    assert "function selectedResultMacValue()" in html
    assert "function copyFilteredResults()" in html
    assert "function copySelectedResultMac()" in html
    assert "function currentHistoryClipboardText()" in html
    assert "function selectedHistoryMacValue()" in html
    assert "function copyHistoryTable()" in html
    assert "function copyHistoryMac()" in html
    assert "function localDatabaseDeviceClipboardText(mac=state.selectedLocalDatabaseMac)" in html
    assert "function copyLocalDatabaseDevice()" in html

    assert '$("#resultBody").onclick' in html
    assert "state.selectedResultMac=normalizeMac(row.dataset.mac)||\"\"" in html
    assert '$("#copyResultsTsv").onclick=copyFilteredResults' in html
    assert '$("#copySelectedResultMac").onclick=copySelectedResultMac' in html
    assert '$("#historyBody").onclick' in html
    assert "state.selectedHistoryMac=normalizeMac(row.dataset.historyMac)||\"\"" in html
    assert '$("#copyHistoryTable").onclick=copyHistoryTable' in html
    assert '$("#copyHistoryMac").onclick=copyHistoryMac' in html
    assert '$("#localDatabaseResults").onclick' in html
    assert "state.selectedLocalDatabaseMac=normalizeMac(mac)||\"\"" in html
    assert '$("#copyLocalDatabaseDevice").onclick=copyLocalDatabaseDevice' in html


def test_standalone_help_and_shortcuts_parity_block():
    html = read_standalone()

    assert 'data-view="help"' in html
    assert 'id="help"' in html
    assert 'id="refreshHelp"' in html
    assert 'id="exportHelp"' in html
    assert 'id="helpShortcutCount"' in html
    assert 'id="helpPermissionMode"' in html
    assert 'id="helpModeList"' in html
    assert 'id="helpShortcutList"' in html
    assert 'id="helpText"' in html

    assert "function activateView(view)" in html
    assert 'if(view==="help")renderHelp()' in html
    assert "function standaloneHelpText()" in html
    assert "function standaloneShortcutRows()" in html
    assert "function renderHelp()" in html
    assert "function exportHelpTxt()" in html
    assert "function shortcutCombo(event)" in html
    assert "function handleStandaloneShortcut(event)" in html
    assert 'document.addEventListener("keydown",handleStandaloneShortcut)' in html

    for shortcut in [
        "Ctrl+O",
        "Ctrl+S",
        "Ctrl+E",
        "Ctrl+A",
        "Ctrl+H",
        "F5",
        "F6",
        "F7",
        "F8",
        "F9",
        "F1",
        "Ctrl+F",
        "Ctrl+Shift+C",
        "Ctrl+Shift+O",
        "Ctrl+Shift+R",
        "Ctrl+Shift+S",
        "Ctrl+Shift+L",
        "Esc",
    ]:
        assert shortcut in html

    assert '"Ctrl+O":()=>{$("#fileInput").click();activateView("workspace")}' in html
    assert '"Ctrl+S":()=>state.devices.length?exportData("xlsx"):exportStandaloneBackup()' in html
    assert '"Ctrl+E":()=>activateView("export")' in html
    assert '"F5":()=>{activateView("workspace");analyze()}' in html
    assert '"F1":()=>activateView("help")' in html
    assert '"Ctrl+F":()=>{activateView("results");$("#search").focus();$("#search").select()}' in html
    assert '"Ctrl+Shift+O":()=>{activateView("settings");optimizeResultColumnWidths()}' in html
    assert '"Ctrl+Shift+R":()=>resetResultColumnWidths()' in html
    assert '"Ctrl+Shift+S":()=>saveResultColumnWidths()' in html
    assert '"Ctrl+Shift+L":()=>loadResultColumnWidths()' in html
    assert '"Escape":()=>toast("Операция отменена")' in html
    assert "$$(\".nav button\").forEach(b=>b.onclick=()=>activateView(b.dataset.view))" in html
    assert '$("#refreshHelp").onclick=renderHelp' in html
    assert '$("#exportHelp").onclick=exportHelpTxt' in html
    assert 'download("mac-analyzer-help.txt",standaloneHelpText(),"text/plain")' in html
    assert "renderEngineeringState();renderHelp();renderSingleMappingGrid()" in html


if __name__ == "__main__":
    test_standalone_keeps_xlsx_import_support()
    test_standalone_two_file_enrichment_mapping_controls()
    test_standalone_ip_mapping_parity_block()
    test_standalone_column_manager_parity_block()
    test_standalone_oui_settings_parity_block()
    test_standalone_theme_settings_parity_block()
    test_standalone_backup_restore_parity_block()
    test_standalone_topology_parity_block()
    test_standalone_clusters_parity_block()
    test_standalone_chart_export_parity_block()
    test_standalone_quality_parity_block()
    test_standalone_device_analytics_parity_block()
    test_standalone_model_analytics_parity_block()
    test_standalone_notifications_parity_block()
    test_standalone_scheduler_parity_block()
    test_standalone_external_api_enrichment_parity_block()
    test_standalone_dashboard_parity_block()
    test_standalone_autosave_parity_block()
    test_standalone_vendor_model_mappings_parity_block()
    test_standalone_local_database_search_parity_block()
    test_standalone_app_log_performance_metrics_parity_block()
    test_standalone_single_file_analysis_parity_block()
    test_standalone_engineering_security_parity_block()
    test_standalone_multi_snapshot_comparison_parity_block()
    test_standalone_time_statistics_parity_block()
    test_standalone_export_manager_parity_block()
    test_standalone_mac_history_parity_block()
    test_standalone_snapshot_management_parity_block()
    test_standalone_vendor_model_history_parity_block()
    test_standalone_clipboard_context_actions_parity_block()
    test_standalone_help_and_shortcuts_parity_block()
    print("standalone html features test passed")

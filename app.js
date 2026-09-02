(() => {
  "use strict";
  window.MacAnalyzerAppBootstrapped = true;
  const fieldList = [["mac","MAC-адрес"],["vendor","Производитель"],["model","Модель"],["ip","IP"],["address","Адрес"],["room","Помещение"],["smartroomId","Smartroom ID"],["switchIp","IP коммутатора"],["switchPort","Порт"],["hostname","Hostname"],["serialNumber","Серийный номер"],["deviceId","ID устройства"],["deviceName","Название устройства"]];
  const labels = {...Object.fromEntries(fieldList),macFormatted:"MAC",oui:"OUI",smartroomId:"Smartroom ID",switchIp:"IP коммутатора",switchPort:"Порт",source:"Источник",vendorSource:"Источник вендора",vendorConfidence:"Уверенность вендора",vendorMatchedPrefix:"Префикс вендора",modelSource:"Источник модели",modelConfidence:"Уверенность модели",modelMatchedPrefix:"Префикс модели"};
  const builtinVendorMappings={"00037F":"Apple Inc.","001A11":"Apple Inc.","18FE34":"Apple Inc.","001B44":"Intel Corporation","00A0C9":"Intel Corporation","ACDE48":"Samsung Electronics","002590":"Samsung Electronics","001122":"Cisco Systems","00055D":"Cisco Systems","0050B6":"Dell Inc.","00155F":"Hewlett Packard","0050C2":"Microsoft Corp.","005A39":"Google LLC","0025D3":"Huawei Technologies","002128":"Xiaomi Corporation","0022B0":"TP-Link Technologies","001E52":"Netgear Inc.","F832E4":"ASUSTeK Computer","B827EB":"Raspberry Pi Foundation","002314":"Lenovo Group","0022BD":"Acer Inc.","0024B2":"LG Electronics","001E58":"Sony Corporation","000E58":"Cisco-Linksys","001E13":"Nintendo","000C29":"VMware","0050F2":"Microsoft","00107B":"Dell","001EC9":"Huawei","0017C8":"Apple","00236C":"Xiaomi","001AA9":"Samsung"};
  const builtinModelMappings={"00112233":"Cisco Catalyst 2960","00112244":"Cisco Catalyst 3560","00112255":"Cisco Catalyst 3750","00112266":"Cisco Catalyst 4500","00112277":"Cisco Catalyst 6500","00112288":"Cisco ASR 1000","00112299":"Cisco ISR 4000","005055AA":"Cisco Nexus 3000","005055BB":"Cisco Nexus 5000","005055CC":"Cisco Nexus 7000","0010B5AA":"Dell PowerEdge R740","0010B5BB":"Dell PowerEdge R640","0010B5CC":"Dell PowerEdge T340","0010B5DD":"Dell OptiPlex 7070","0010B5EE":"Dell Latitude 5400","0010B5FF":"Dell XPS 15","00215AAB":"HP ProLiant DL380","00215ACC":"HP ProLiant DL360","00215ADD":"HP EliteBook 840","00215AEE":"HP ZBook 15","00215AFF":"HP LaserJet Pro","00215A11":"HP OfficeJet Pro","001A1101":"iPhone 13","001A1102":"iPhone 14","001A1103":"iPhone 15","001A1120":"iPad Pro","001A1121":"iPad Air","001A1130":"MacBook Pro","001A1131":"MacBook Air","001A1140":"iMac 24\"","001A1150":"Mac Studio","00259001":"Samsung Galaxy S23","00259002":"Samsung Galaxy S22","00259010":"Samsung Galaxy Tab","00259020":"Samsung SSD 980 Pro","00259030":"Samsung Smart Monitor","00259040":"Samsung M7","001EC901":"Huawei Mate 50","001EC902":"Huawei P60","001EC910":"Huawei MateBook X","001EC920":"Huawei Watch GT","00236C01":"Xiaomi Mi 11","00236C02":"Xiaomi 12T","00236C10":"Xiaomi Mi Band","00236C20":"Xiaomi Robot Vacuum","0022B001":"TP-Link Archer AX73","0022B002":"TP-Link Deco X60","0022B010":"TP-Link Tapo C200","0022B020":"TP-Link Kasa KP115","001E5201":"Netgear Nighthawk RAX200","001E5202":"Netgear Orbi RBK852","001E5210":"Netgear GS308","001E5220":"Netgear ReadyNAS","F832E401":"ASUS ROG Zephyrus","F832E402":"ASUS TUF Gaming","F832E410":"ASUS RT-AX88U","F832E420":"ASUS ZenBook","00231401":"Lenovo ThinkPad X1","00231402":"Lenovo ThinkPad T14","00231410":"Lenovo Legion 5","00231420":"Lenovo Yoga 9i"};
  const defaultColumnWidths = {macFormatted:180,oui:110,vendor:150,model:150,ip:130,address:200,room:120,smartroomId:140,switchIp:150,switchPort:100,hostname:160,serialNumber:160,deviceId:150,deviceName:180,source:150};
  const key = "mac-analyzer-web-state-v1";
  const browserStateDbName = "mac-analyzer-browser-storage-v1";
  const browserStateStoreName = "workspaces";
  const browserStateRecordId = "main-v2";
  const browserStateSavedAtKey = key+"-saved-at";
  const localFolderSavedAtKey = key+"-folder-saved-at";
  const StatePersistence = window.MacAnalyzerStatePersistence;
  const BrowserSnapshots = window.MacAnalyzerBrowserSnapshots;
  const MacChronology = window.MacAnalyzerMacChronology;
  const XlsxExporter = window.MacAnalyzerXlsxExporter;
  const FullXlsxReport = window.MacAnalyzerFullXlsxReport;
  const FullJsonReport = window.MacAnalyzerFullJsonReport;
  const LocalAnalytics = window.MacAnalyzerLocalAnalytics;
  const MemoryGuard = window.MacAnalyzerMemoryGuard;
  const Guide = window.MacAnalyzerGuide;
  const PortableDatabase = window.MacAnalyzerPortableDatabase;
  const LocalFolderStore = window.MacAnalyzerLocalFolderStore;
  const WorkspaceFileLifecycle = window.MacAnalyzerWorkspaceFileLifecycle;
  const DdioOverlay = window.MacAnalyzerDdioOverlay;
  const IeeeRegistry = window.MacAnalyzerIeeeRegistry;
  const DashboardChangeTabs = window.MacAnalyzerDashboardChangeTabs;
  const LazyTabs = window.MacAnalyzerLazyTabs;
  const VirtualTable = window.MacAnalyzerVirtualTable;
  const SmartroomWorker = window.MacAnalyzerSmartroomWorker;
  const SmartroomStore = window.MacAnalyzerSmartroomStore;
  const SmartroomCharts = window.MacAnalyzerSmartroomCharts;
  const SmartroomUI = window.MacAnalyzerSmartroomUI;
  const RecordValidation = window.MacAnalyzerRecordValidation;
  const DeviceIdentity = window.MacAnalyzerDeviceIdentity;
  const EnrichmentStrategy = window.MacAnalyzerEnrichmentStrategy;
  const UiFeedback = window.MacAnalyzerUiFeedback;
  if(!MemoryGuard)throw new Error("Модуль frontend/memory-guard.js не загружен");
  if(!XlsxExporter)throw new Error("Модуль frontend/xlsx-exporter.js не загружен");
  if(!FullXlsxReport)throw new Error("Модуль frontend/full-xlsx-report.js не загружен");
  if(!FullJsonReport)throw new Error("Модуль frontend/full-json-report.js не загружен");
  if(!LocalAnalytics)throw new Error("Модуль frontend/local-analytics.js не загружен");
  if(!MacChronology)throw new Error("Модуль frontend/mac-chronology.js не загружен");
  if(!WorkspaceFileLifecycle)throw new Error("Модуль frontend/workspace-file-lifecycle.js не загружен");
  if(!DdioOverlay)throw new Error("Модуль frontend/ddio-overlay.js не загружен");
  if(!RecordValidation)throw new Error("Модуль frontend/record-validation.js не загружен");
  if(!DeviceIdentity)throw new Error("Модуль frontend/device-identity.js не загружен");
  if(!EnrichmentStrategy)throw new Error("Модуль frontend/enrichment-strategy.js не загружен");
  if(!IeeeRegistry)throw new Error("Модуль frontend/ieee-vendor-registry.js не загружен");
  if(!DashboardChangeTabs)throw new Error("Модуль frontend/dashboard-change-tabs.js не загружен");
  if(!Guide)throw new Error("Модуль frontend/guide.js не загружен");
  const $ = (s) => document.querySelector(s) || LazyTabs?.querySelector(s) || null;
  const $$ = (s) => [...document.querySelectorAll(s), ...(LazyTabs?.querySelectorAll(s) || [])];
  const debounce=(callback,wait=180)=>{let timer=null;return(...args)=>{clearTimeout(timer);timer=setTimeout(()=>callback(...args),wait);};};
  const networkUnavailable = (error) => error instanceof TypeError || [404,405,501].includes(Number(error?.status||0)) || /Failed to fetch|NetworkError|Load failed|fetch failed/i.test(error?.message||"");
  const browserOnlyMode = location.protocol === "file:";
  const autonomousHtmlMode = browserOnlyMode;
  const backendCandidates = browserOnlyMode ? [] : [location.origin + "/api"];
  let backendBase = backendCandidates[0];
  let backendAvailable = false;
  let resultPage=1,resultPageSize=50,resultRenderRevision=0,resultSortField="",resultSortDirection="asc",resultRequestController=null,resultStateRevision=0;
  const resultResponseCache=new Map(),deviceDialogCache=new Map(),localSearchTextCache=new WeakMap();
  let snapshotMutationPromise=Promise.resolve();
  const engineeringPermissionList=["delete:history","delete:snapshots","delete:mappings","delete:tasks","delete:ip-mappings","delete:api-cache","write:settings","write:migration"];
  const engineeringPermissionLabels={"delete:history":"Удаление истории","delete:snapshots":"Удаление снимков","delete:mappings":"Удаление справочников","delete:tasks":"Управление задачами","delete:ip-mappings":"Удаление IP-маппинга","delete:api-cache":"Очистка API-кэша","write:settings":"Изменение настроек","write:migration":"Миграция Python/SQLite"};
  const engineeringOnlyViews=new Set(["single","compare","data","automation","settings"]);
  const empty = () => ({files:[],ddioFile:null,ddioOverlay:{},ddioSummary:null,devices:[],invalid:[],snapshots:[],movementHistory:[],importErrors:[],ipMappings:[],smartroomMappings:{},localVendorMappings:{},localModelMappings:{},dashboardFleetCache:null,activeMappingFileId:"",mappingDisplayMode:"name",enrichmentStrategy:"NO_EXPANSION",theme:"light",engineeringMode:false,engineeringToken:"",engineeringExpiresAt:"",engineeringPermissions:[],ouiLength:3,ouiStyle:"plain",vendorDetectorSettings:{enabled:true,useOui3:true,useMac5:true,useText:true,useInference:true,confidenceThreshold:0.6},historyEnrichmentSettings:{enabled:true,priorityHistory:true,useOuiMatch:true,useMac5Match:true},externalApiSettings:{enabled:false,provider:"macvendors",endpoint:"",rateLimit:25,cacheTtlDays:30,onlyUnknown:true},dashboardSettings:{query:"",vendor:"",room:"",status:"all",chartLimit:8,showUnknown:true,visibleCards:{total:true,changed:true,missing:true,unchanged:true,vendors:true,rooms:true,changedRooms:true},visibleCharts:{dynamics:true,vendors:true,fields:true,missing:true},autoRefresh:true,refreshInterval:60,changeMode:"snapshots",changeDateFrom:"",changeDateTo:"",baselineSnapshotId:"",comparisonSnapshotId:""},customColumns:[],customColumnMappings:{},columnWidths:{...defaultColumnWidths},visibleColumns:["macFormatted","oui","vendor","model","ip","address","room","smartroomId","switchIp","switchPort","hostname","serialNumber","deviceId","deviceName","source"],columnOrder:["macFormatted","oui","vendor","model","ip","address","room","smartroomId","switchIp","switchPort","hostname","serialNumber","deviceId","deviceName","source"],resultSnapshotId:"",resultBrowserSnapshotId:"",resultBrowserSnapshotDirty:false,resultDeviceCount:0,resultInvalidCount:0,resultSummary:null,lastAnalysis:null});
  let state;
  try { const old = JSON.parse(localStorage.getItem(key)); state = {...empty(),...old}; } catch { state = empty(); }
  state.importErrors=[];
  function normalizeSourceRole(role,index=0){const value=String(role||"").trim().toLowerCase();if(["smartroom","smart-room","sr","enrichment","secondary"].includes(value))return"smartroom";if(value==="ddio")return"ddio";return index===0?"primary":"smartroom";}
  function normalizeFileRoles(files=[]){
    const normalized=(Array.isArray(files)?files:[]).filter((file)=>file&&typeof file==="object").map((file)=>({...file}));
    if(!normalized.length)return normalized;
    let primaryIndex=normalized.findIndex((file)=>file.role==="primary");
    if(primaryIndex<0)primaryIndex=0;
    normalized.forEach((file,index)=>{file.role=index===primaryIndex?"primary":"smartroom";});
    return [normalized[primaryIndex],...normalized.filter((_file,index)=>index!==primaryIndex)];
  }
  state.files=normalizeFileRoles(state.files);
  state.ddioFile=state.ddioFile&&typeof state.ddioFile==="object"?state.ddioFile:null;
  state.ddioOverlay=state.ddioOverlay&&typeof state.ddioOverlay==="object"&&!Array.isArray(state.ddioOverlay)?state.ddioOverlay:{};
  state.movementHistory=Array.isArray(state.movementHistory)?state.movementHistory:[];
  state.ipMappings=Array.isArray(state.ipMappings)?state.ipMappings:[];
  state.smartroomMappings=state.smartroomMappings&&typeof state.smartroomMappings==="object"&&!Array.isArray(state.smartroomMappings)?state.smartroomMappings:{};
  state.localVendorMappings=state.localVendorMappings&&typeof state.localVendorMappings==="object"?state.localVendorMappings:{};
  state.localModelMappings=state.localModelMappings&&typeof state.localModelMappings==="object"?state.localModelMappings:{};
  state.externalApiSettings=state.externalApiSettings&&typeof state.externalApiSettings==="object"?state.externalApiSettings:empty().externalApiSettings;
  state.enrichmentStrategy=EnrichmentStrategy.normalize(state.enrichmentStrategy);
  if($("#strategySelect"))$("#strategySelect").value=state.enrichmentStrategy;
  state.dashboardSettings=normalizeDashboardSettings(state.dashboardSettings);
  state.columnWidths=normalizeColumnWidths(state.columnWidths);
  for(const keyName of ["visibleColumns","columnOrder"]){
    const columns=Array.isArray(state[keyName])?state[keyName]:[];
    if(!columns.includes("smartroomId")){
      const roomIndex=columns.indexOf("room");
      columns.splice(roomIndex>=0?roomIndex+1:columns.length,0,"smartroomId");
    }
    state[keyName]=columns;
  }
  BrowserSnapshots?.removeLegacyWorkspace?.().catch(()=>{});
  let browserStateSaveTimer=null,browserStateSaveRevision=0,browserStateQueuedRevision=0,browserStatePersistedRevision=0,browserStateSavePromise=Promise.resolve(),browserStatePendingSavedAt="";
  let portableDatabaseHandle=null,portableDatabaseSaveTimer=null,portableDatabaseSaveRevision=0,portableDatabaseQueuedRevision=0,portableDatabasePersistedRevision=0,portableDatabaseSavePromise=Promise.resolve();
  let localFolderHandle=null,localFolderStructure=null;
  function openBrowserStateDb(){
    return new Promise((resolve,reject)=>{
      if(!("indexedDB" in window))return reject(new Error("IndexedDB недоступна"));
      const request=indexedDB.open(browserStateDbName,11);
      request.onupgradeneeded=()=>{const db=request.result,tx=request.transaction;if(!db.objectStoreNames.contains(browserStateStoreName))db.createObjectStore(browserStateStoreName,{keyPath:"id"});if(!db.objectStoreNames.contains("snapshots"))db.createObjectStore("snapshots",{keyPath:"id"});if(!db.objectStoreNames.contains("snapshotChunks")){const chunks=db.createObjectStore("snapshotChunks",{keyPath:"key"});chunks.createIndex("snapshotId","snapshotId",{unique:false});}if(!db.objectStoreNames.contains("sourceFiles"))db.createObjectStore("sourceFiles",{keyPath:"id"});const enrichmentRows=db.objectStoreNames.contains("enrichmentRows")?tx.objectStore("enrichmentRows"):db.createObjectStore("enrichmentRows",{keyPath:"key"});if(!enrichmentRows.indexNames.contains("jobId"))enrichmentRows.createIndex("jobId","jobId",{unique:false});if(!enrichmentRows.indexNames.contains("aliases"))enrichmentRows.createIndex("aliases","aliases",{unique:false,multiEntry:true});if(!db.objectStoreNames.contains("deviceHistory"))db.createObjectStore("deviceHistory",{keyPath:"mac"});const inventory=db.objectStoreNames.contains("DeviceInventory")?tx.objectStore("DeviceInventory"):db.createObjectStore("DeviceInventory",{keyPath:"internalDeviceId"});for(const[name,keyPath]of[["by_mac","mac"],["by_serial","serialKey"],["by_device_id","deviceIdKey"],["by_switch","switchIp"],["by_updated_at","updatedAt"]])if(!inventory.indexNames.contains(name))inventory.createIndex(name,keyPath,{unique:false});const equipment=db.objectStoreNames.contains("Equipment")?tx.objectStore("Equipment"):db.createObjectStore("Equipment",{keyPath:"id"});for(const[name,keyPath]of[["smartroom_id","smartroom_id"],["mac","mac"],["ip_switch","ip_switch"],["by_smartroom","smartroom_id"],["by_mac","mac"],["by_switch","ip_switch"]])if(!equipment.indexNames.contains(name))equipment.createIndex(name,keyPath,{unique:false});const history=db.objectStoreNames.contains("History")?tx.objectStore("History"):db.createObjectStore("History",{keyPath:"id",autoIncrement:true});for(const[name,keyPath]of[["entity_type","entity_type"],["timestamp","timestamp"],["by_timestamp","timestamp"],["by_mac","mac"],["by_smartroom","smartroom_id"]])if(!history.indexNames.contains(name))history.createIndex(name,keyPath,{unique:false});if(!db.objectStoreNames.contains("DDIO_Snapshot"))db.createObjectStore("DDIO_Snapshot",{keyPath:"date"});if(!db.objectStoreNames.contains("KnownModels")){const known=db.createObjectStore("KnownModels",{keyPath:"mac"});known.createIndex("by_vendor","vendor",{unique:false});known.createIndex("by_updated_at","updatedAt",{unique:false});}};
      request.onsuccess=()=>resolve(request.result);
      request.onerror=()=>reject(request.error||new Error("Не удалось открыть IndexedDB"));
    });
  }
  async function writeBrowserStateRecord(snapshot,savedAt){
    const db=await openBrowserStateDb();
    return new Promise((resolve,reject)=>{const transaction=db.transaction(browserStateStoreName,"readwrite");transaction.objectStore(browserStateStoreName).put({id:browserStateRecordId,savedAt,state:snapshot});transaction.oncomplete=()=>{db.close();resolve(true);};transaction.onerror=()=>{const error=transaction.error;db.close();reject(error||new Error("Не удалось сохранить IndexedDB"));};});
  }
  async function readBrowserStateRecord(){
    const db=await openBrowserStateDb();
    return new Promise((resolve,reject)=>{const transaction=db.transaction(browserStateStoreName,"readonly"),request=transaction.objectStore(browserStateStoreName).get(browserStateRecordId);request.onsuccess=()=>resolve(request.result||null);request.onerror=()=>reject(request.error||new Error("Не удалось прочитать IndexedDB"));transaction.oncomplete=()=>db.close();});
  }
  function compactBrowserState(source){
    return StatePersistence.compactLocalState(source);
  }
  function browserStateSnapshot(){
    return StatePersistence.compactIndexedState(state);
  }
  function persistLatestBrowserState(){
    if(browserStateSaveTimer){clearTimeout(browserStateSaveTimer);browserStateSaveTimer=null;}
    if(browserStateQueuedRevision>=browserStateSaveRevision)return browserStateSavePromise;
    const revision=browserStateSaveRevision,savedAt=browserStatePendingSavedAt||new Date().toISOString(),snapshot=browserStateSnapshot();
    browserStateQueuedRevision=revision;
    browserStateSavePromise=browserStateSavePromise.catch(()=>{}).then(()=>writeBrowserStateRecord(snapshot,savedAt)).then(()=>{browserStatePersistedRevision=Math.max(browserStatePersistedRevision,revision);if(browserStateSaveRevision>browserStateQueuedRevision)armBrowserStateSave(0);});
    return browserStateSavePromise;
  }
  function armBrowserStateSave(delay){clearTimeout(browserStateSaveTimer);browserStateSaveTimer=setTimeout(()=>{persistLatestBrowserState().catch(()=>{});},Math.max(0,delay));}
  function scheduleBrowserStateSave(savedAt,delay=250){
    browserStateSaveRevision++;
    browserStatePendingSavedAt=savedAt;
    armBrowserStateSave(delay);
  }
  async function flushBrowserStateSave(){
    if(browserStatePersistedRevision>=browserStateSaveRevision&&!browserStateSaveTimer)return true;
    await persistLatestBrowserState();
    return true;
  }
  async function deleteBrowserStateRecord(){
    const db=await openBrowserStateDb();
    return new Promise((resolve,reject)=>{const transaction=db.transaction(browserStateStoreName,"readwrite");transaction.objectStore(browserStateStoreName).delete(browserStateRecordId);transaction.oncomplete=()=>{db.close();resolve(true);};transaction.onerror=()=>{const error=transaction.error;db.close();reject(error||new Error("Не удалось удалить IndexedDB autosave"));};});
  }
  function portableDatabaseStatus(message,status="ready"){
    const target=$("#portableDatabaseStatus");
    if(!target)return;
    target.textContent=message;
    target.dataset.status=status;
  }
  function localFolderStatus(message,status="ready"){
    const target=$("#localFolderStatus");
    if(!target)return;
    target.textContent=message;
    target.dataset.status=status;
  }
  function portableDatabasePayload(){
    const compact=StatePersistence.compactLocalState(state);
    const currentBrowserSnapshotId=String(state.resultBrowserSnapshotId||"");
    const streamCurrentResult=currentBrowserSnapshotId&&BrowserSnapshots?.streamSnapshot
      ?async(onChunk)=>BrowserSnapshots.streamSnapshot(currentBrowserSnapshotId,onChunk)
      :null;
    compact.files=[];
    compact.resultSnapshotId="";
    compact.resultBrowserSnapshotId="";
    compact.resultBrowserSnapshotDirty=false;
    compact.resultDeviceCount=currentBrowserSnapshotId?Number(state.resultDeviceCount||0):(state.devices||[]).length;
    compact.resultInvalidCount=currentBrowserSnapshotId?Number(state.resultInvalidCount||0):(state.invalid||[]).length;
    compact.resultSummary=state.resultSummary||null;
    return{state:compact,devices:streamCurrentResult?[]:state.devices||[],invalid:streamCurrentResult?[]:state.invalid||[],deviceCount:compact.resultDeviceCount,invalidCount:compact.resultInvalidCount,currentResultStreamer:streamCurrentResult,inventoryStreamer:BrowserSnapshots?.streamDeviceHistory?(onChunk)=>BrowserSnapshots.streamDeviceHistory(onChunk):null,movements:state.movementHistory||[],snapshotMetadata:(state.snapshots||[]).filter((item)=>item.browserStored),skipSnapshotId:currentBrowserSnapshotId,snapshotStreamer:BrowserSnapshots?.streamSnapshot?(metadata,onChunk)=>BrowserSnapshots.streamSnapshot(metadata.id,onChunk):null,snapshotLoader:(metadata)=>loadLocalSnapshotRecord(metadata)};
  }
  function portableDatabaseProgress(processId,value,detail){
    portableDatabaseStatus(detail||"Обработка файловой базы...");
    if(processId)updateProcess(processId,Math.max(1,Math.min(100,Number(value)||0)),detail||"");
  }
  async function persistPortableDatabase(){
    if(portableDatabaseSaveTimer){clearTimeout(portableDatabaseSaveTimer);portableDatabaseSaveTimer=null;}
    if(!PortableDatabase||!portableDatabaseHandle||portableDatabaseQueuedRevision>=portableDatabaseSaveRevision)return portableDatabaseSavePromise;
    const revision=portableDatabaseSaveRevision,payload=portableDatabasePayload();
    portableDatabaseQueuedRevision=revision;
    portableDatabaseSavePromise=portableDatabaseSavePromise.catch(()=>{}).then(async()=>{
      const access=await PortableDatabase.permission(portableDatabaseHandle,"readwrite");
      if(access!=="granted"&&access!=="unsupported")throw new Error("Откройте файловую базу кнопкой, чтобы снова разрешить запись");
      const result=await PortableDatabase.write(portableDatabaseHandle,payload,(value,detail)=>portableDatabaseProgress("",value,detail));
      portableDatabasePersistedRevision=Math.max(portableDatabasePersistedRevision,revision);
      try{localStorage.setItem(localFolderSavedAtKey,result.savedAt||"");}catch{}
      portableDatabaseStatus(`Файловая база сохранена: ${new Date(result.savedAt).toLocaleString("ru-RU")} · устройств ${result.counts.devices.toLocaleString("ru-RU")}`);
      if(localFolderStructure?.databaseHandle===portableDatabaseHandle){
        await LocalFolderStore?.writeManifest?.(localFolderStructure,{savedAt:result.savedAt,counts:result.counts}).catch(()=>false);
        localFolderStatus(`Папка подключена: ${localFolderHandle?.name||"MAC Analyzer Data"} · база обновлена ${new Date(result.savedAt).toLocaleString("ru-RU")}`);
      }
      if(portableDatabaseSaveRevision>portableDatabaseQueuedRevision)schedulePortableDatabaseSave(500);
      return result;
    }).catch((error)=>{portableDatabaseStatus(error.message,"error");throw error;});
    return portableDatabaseSavePromise;
  }
  function schedulePortableDatabaseSave(delay=4000){
    if(!portableDatabaseHandle||!PortableDatabase)return;
    portableDatabaseSaveRevision++;
    clearTimeout(portableDatabaseSaveTimer);
    portableDatabaseSaveTimer=setTimeout(()=>{persistPortableDatabase().catch(()=>{});},Math.max(0,delay));
  }
  async function flushPortableDatabaseSave(){
    if(!portableDatabaseHandle||portableDatabasePersistedRevision>=portableDatabaseSaveRevision&&!portableDatabaseSaveTimer)return true;
    await persistPortableDatabase();
    return true;
  }
  async function applyPortableDatabase(data,sourceName="файловая база"){
    state=normalizeRestoredState(data.state||{});
    state.files=[];
    state.devices=Array.isArray(data.devices)?data.devices:[];
    state.invalid=Array.isArray(data.invalid)?data.invalid:[];
    state.movementHistory=Array.isArray(data.movements)?data.movements:[];
    if(Array.isArray(data.snapshots)&&data.snapshots.length){const imported=new Map(data.snapshots.map((item)=>[item.id,item]));state.snapshots=(state.snapshots||[]).map((item)=>imported.get(item.id)||item);}
    const currentReference=(data.snapshots||[]).find((item)=>item.currentReference);
    state.resultSnapshotId="";
    state.resultBrowserSnapshotId=currentReference?.id||"";
    state.resultBrowserSnapshotDirty=false;
    state.resultDeviceCount=Math.max(0,Number(data.deviceCount??data.header?.counts?.devices??state.devices.length)||0);
    state.resultInvalidCount=Math.max(0,Number(data.invalidCount??data.header?.counts?.invalid??state.invalid.length)||0);
    state.lastAnalysis=data.header?.savedAt||state.lastAnalysis||new Date().toISOString();
    try{localStorage.setItem(localFolderSavedAtKey,data.header?.savedAt||"");}catch{}
    save({immediate:true,portable:false});
    await flushBrowserStateSave().catch(()=>{});
    applyTheme(state.theme);
    applyVendorDetectorSettings(state.vendorDetectorSettings||{});
    applyHistoryEnrichmentSettings(state.historyEnrichmentSettings||{});
    renderEngineeringState();renderAll();renderColumnPreferences();
    portableDatabaseStatus(`Подключено: ${sourceName} · ${state.resultDeviceCount.toLocaleString("ru-RU")} устройств · ${new Date(data.header?.savedAt||Date.now()).toLocaleString("ru-RU")}`);
    return true;
  }

  function portableDatabaseRestoreOptions(importedSnapshotIds){
    return{
      retainRows:false,
      previewLimit:resultPageSize,
      batchRows:500,
      onSnapshotStart:async(metadata)=>{
        if(!BrowserSnapshots||!metadata?.id)return;
        await BrowserSnapshots.beginStreamedSnapshot(metadata);
        importedSnapshotIds.push(String(metadata.id));
      },
      onSnapshotChunk:async(metadata,kind,rows,index)=>{
        if(BrowserSnapshots&&metadata?.id)await BrowserSnapshots.appendStreamedSnapshotChunk(metadata.id,kind,index,rows);
      },
      onSnapshotEnd:async(metadata,counts)=>{
        if(BrowserSnapshots&&metadata?.id)await BrowserSnapshots.finishStreamedSnapshot(metadata.id,counts);
      },
      onInventoryChunk:async(rows)=>{
        if(BrowserSnapshots?.mergeDeviceHistoryRows)await BrowserSnapshots.mergeDeviceHistoryRows(rows,"portable-database");
      },
    };
  }

  async function importPortableDatabaseFile(file,sourceName=file?.name||"mac-analyzer-data.madb"){
    if(!(file instanceof Blob))throw new Error("Файл базы не выбран");
    const processId=beginProcess("Файловая база","Потоковое восстановление MADB",5),importedSnapshotIds=[];
    try{
      const data=await PortableDatabase.readFile(file,(value,detail)=>portableDatabaseProgress(processId,value,detail),portableDatabaseRestoreOptions(importedSnapshotIds));
      if(BrowserSnapshots)await BrowserSnapshots.prune(importedSnapshotIds).catch(()=>{});
      portableDatabaseHandle=null;
      await applyPortableDatabase(data,sourceName);
      finishProcess(processId,"Файловая база импортирована");
      return data;
    }catch(error){
      for(const id of importedSnapshotIds)await BrowserSnapshots?.removeSnapshot?.(id).catch(()=>{});
      failProcess(processId,error);
      portableDatabaseStatus(error.message,"error");
      throw error;
    }
  }

  async function importPortableFolderFiles(files){
    if(!LocalFolderStore||!PortableDatabase)throw new Error("Модуль локальной папки не загружен");
    const inspection=LocalFolderStore.inspectFolderFiles(files);
    if(!inspection.database)throw new Error("В выбранной папке не найден database/mac-analyzer-data.madb. Сначала подключите папку в исходном браузере и нажмите «Сохранить сейчас».");
    localFolderHandle=null;
    localFolderStructure=null;
    const source=inspection.database.path||inspection.database.file.name;
    const data=await importPortableDatabaseFile(inspection.database.file,source);
    localFolderStatus(`Папка прочитана: ${inspection.rootName||"выбранная папка"} · ${inspection.fileCount.toLocaleString("ru-RU")} файлов · база ${source}`,"warning");
    portableDatabaseStatus(`Данные восстановлены только для чтения: ${data.deviceCount.toLocaleString("ru-RU")} устройств. Изменения сохраняются в IndexedDB этого браузера; для переноса сохраните новый MADB.`,"warning");
    setBackendStatus(false,"Файловая база импортирована · локальный кэш нового браузера заполнен");
    return true;
  }
  async function readPortableDatabaseHandle(handle,{request=false}={}){
    if(!handle||!PortableDatabase)return false;
    if(request&&!(await PortableDatabase.requestPermission(handle,"readwrite")))throw new Error("Доступ к файловой базе не разрешён");
    const processId=beginProcess("Файловая база","Потоковое чтение MADB",5),importedSnapshotIds=[];
    try{
      const data=await PortableDatabase.read(handle,(value,detail)=>portableDatabaseProgress(processId,value,detail),portableDatabaseRestoreOptions(importedSnapshotIds));
      if(BrowserSnapshots)await BrowserSnapshots.prune(importedSnapshotIds).catch(()=>{});
      portableDatabaseHandle=handle;
      await PortableDatabase.saveHandle(handle).catch(()=>false);
      await applyPortableDatabase(data,handle.name||"mac-analyzer-data.madb");
      portableDatabaseSaveRevision=portableDatabasePersistedRevision=0;
      finishProcess(processId,"Файловая база подключена");
      return true;
    }catch(error){for(const id of importedSnapshotIds)await BrowserSnapshots?.removeSnapshot?.(id).catch(()=>{});failProcess(processId,error);portableDatabaseStatus(error.message,"error");throw error;}
  }
  async function connectPortableDatabase(){
    if(!PortableDatabase)return toast("Модуль файловой базы не загружен.");
    try{
      if(!PortableDatabase.supportsNativePicker()){$("#portableDatabaseInput")?.click();return;}
      const handle=await PortableDatabase.chooseOpenHandle();
      if(handle)await readPortableDatabaseHandle(handle,{request:true});
    }catch(error){if(error?.name!=="AbortError")toast(error.message);}
  }
  async function createPortableDatabase(){
    if(!PortableDatabase)return toast("Модуль файловой базы не загружен.");
    const processId=beginProcess("Файловая база","Создание MADB",5);
    try{
      if(PortableDatabase.supportsNativePicker()){
        const handle=await PortableDatabase.chooseSaveHandle();
        if(!handle){cancelProcess(processId,"Создание отменено");return;}
        portableDatabaseHandle=handle;
        portableDatabaseSaveRevision++;
        const result=await PortableDatabase.write(handle,portableDatabasePayload(),(value,detail)=>portableDatabaseProgress(processId,value,detail));
        portableDatabasePersistedRevision=portableDatabaseQueuedRevision=portableDatabaseSaveRevision;
        portableDatabaseStatus(`Файловая база создана: ${handle.name} · устройств ${result.counts.devices.toLocaleString("ru-RU")}`);
      }else{
        const blob=await PortableDatabase.createBlob(portableDatabasePayload(),(value,detail)=>portableDatabaseProgress(processId,value,detail));
        deliverDownload("mac-analyzer-data.madb",blob);
        portableDatabaseStatus("Файл MADB скачан. В этом браузере автоматическая запись в выбранный файл не поддерживается.","warning");
      }
      finishProcess(processId,"Файловая база сохранена");
    }catch(error){if(error?.name==="AbortError"){cancelProcess(processId,"Создание отменено");return;}failProcess(processId,error);portableDatabaseStatus(error.message,"error");toast(error.message);}
  }
  async function savePortableDatabaseNow(){
    if(!portableDatabaseHandle)return createPortableDatabase();
    const processId=beginProcess("Файловая база","Сохранение текущего состояния",5);
    portableDatabaseSaveRevision++;
    try{await persistPortableDatabase();finishProcess(processId,"Файловая база обновлена");}
    catch(error){failProcess(processId,error);toast(error.message);}
  }
  async function restorePortableDatabaseHandle(){
    if(!PortableDatabase)return false;
    const handle=await PortableDatabase.loadHandle();
    if(!handle)return false;
    const access=await PortableDatabase.permission(handle,"read");
    if(access!=="granted"){
      portableDatabaseHandle=handle;
      portableDatabaseStatus("Файл базы найден. Нажмите «Подключить существующую», чтобы разрешить чтение.","warning");
      return false;
    }
    return readPortableDatabaseHandle(handle).catch(()=>false);
  }
  async function attachLocalFolder(handle,{request=true,preferBrowserState=false}={}){
    if(!LocalFolderStore||!PortableDatabase)throw new Error("Модуль локальной папки не загружен");
    if(request&&!(await LocalFolderStore.requestPermission(handle,"readwrite")))throw new Error("Браузер не разрешил доступ к выбранной папке");
    localFolderStatus("Создание структуры локального хранилища...");
    const structure=await LocalFolderStore.ensureStructure(handle);
    localFolderHandle=handle;
    localFolderStructure=structure;
    portableDatabaseHandle=structure.databaseHandle;
    await LocalFolderStore.saveHandle(handle).catch(()=>false);
    await PortableDatabase.saveHandle(structure.databaseHandle).catch(()=>false);
    const databaseFile=await structure.databaseHandle.getFile();
    if(databaseFile.size>0){
      const header=await PortableDatabase.readHeader(structure.databaseHandle);
      const fileSavedAt=Date.parse(header?.savedAt||"")||0,knownSavedAt=Date.parse(localStorage.getItem(localFolderSavedAtKey)||"")||0;
      const browserHasRestorableData=currentDeviceCount()>0||Boolean(state.resultBrowserSnapshotId)||(state.snapshots||[]).some((item)=>item?.browserStored);
      if(preferBrowserState&&browserHasRestorableData&&knownSavedAt>=fileSavedAt){
        portableDatabaseSaveRevision=portableDatabaseQueuedRevision=portableDatabasePersistedRevision=0;
        portableDatabaseStatus(`Файловая база уже синхронизирована · устройств ${Number(header?.counts?.devices||currentDeviceCount()).toLocaleString("ru-RU")}`);
      }else{
        if(preferBrowserState){if(Array.isArray(state.devices))state.devices.length=0;if(Array.isArray(state.invalid))state.invalid.length=0;await MemoryGuard.yieldToMainThread();}
        await readPortableDatabaseHandle(structure.databaseHandle);
      }
    }else{
      portableDatabaseSaveRevision++;
      await persistPortableDatabase();
    }
    await LocalFolderStore.writeManifest(structure,{connectedAt:new Date().toISOString()}).catch(()=>false);
    await LocalFolderStore.writeLog(structure,"folder-connected",{database:`database/${LocalFolderStore.databaseFileName}`}).catch(()=>false);
    localFolderStatus(`Папка подключена: ${handle.name||"MAC Analyzer Data"} · database, imports, exports, settings, logs, backups`);
    setBackendStatus(false,"Локальная файловая база подключена · backend не используется");
    return true;
  }
  async function connectLocalFolder(){
    if(!LocalFolderStore?.supportsDirectoryPicker?.()){
      localFolderStatus("Прямая запись в папку недоступна. Выберите папку для восстановления MADB только для чтения.","warning");
      $("#portableFolderInput")?.click();
      return false;
    }
    try{
      const handle=await LocalFolderStore.chooseDirectoryHandle();
      if(handle)await attachLocalFolder(handle,{request:true});
    }catch(error){if(error?.name!=="AbortError"){localFolderStatus(error.message,"error");toast(error.message);}}
  }
  async function restoreLocalFolderHandle({preferBrowserState=false}={}){
    if(!LocalFolderStore)return false;
    const handle=await LocalFolderStore.loadHandle();
    if(!handle)return false;
    const access=await LocalFolderStore.permission(handle,"readwrite");
    if(access!=="granted"&&access!=="unsupported"){
      localFolderHandle=handle;
      localFolderStatus(`Найдена папка ${handle.name||"MAC Analyzer Data"}. Нажмите «Выбрать локальную папку», чтобы разрешить доступ.`,"warning");
      return false;
    }
    return attachLocalFolder(handle,{request:false,preferBrowserState}).catch((error)=>{localFolderStatus(error.message,"error");return false;});
  }
  const save = (options={}) => {
    resultStateRevision+=1;
    const savedAt=new Date().toISOString();
    let localCopy=true;
    try{localStorage.setItem(key,JSON.stringify(compactBrowserState(state)));}
    catch{localCopy=false;}
    try{localStorage.setItem(browserStateSavedAtKey,savedAt);}catch{}
    scheduleBrowserStateSave(savedAt,options.immediate?0:250);
    if(options.portable!==false)schedulePortableDatabaseSave(options.immediate?500:4000);
    return localCopy;
  };
  async function restoreBrowserStateFromIndexedDb(){
    try{
      const record=await readBrowserStateRecord();
      if(!record?.state)return false;
      const localSavedAt=Date.parse(localStorage.getItem(browserStateSavedAtKey)||"")||0,indexedSavedAt=Date.parse(record.savedAt||"")||0;
      if(!state.browserStateInIndexedDb&&localSavedAt>indexedSavedAt)return false;
      state=normalizeRestoredState(record.state);
      if(state.resultBrowserSnapshotId&&BrowserSnapshots){
        const stored=await BrowserSnapshots.page?.(state.resultBrowserSnapshotId,{offset:0,limit:resultPageSize}).catch(()=>null);
        if(stored){state.devices=(stored.items||[]).filter((item)=>item?.valid!==false&&!item?.invalid);state.invalid=(stored.items||[]).filter((item)=>item?.valid===false||item?.invalid);state.resultDeviceCount=Number(stored.metadata?.deviceCount||stored.summary?.devices||state.devices.length);state.resultInvalidCount=Number(stored.metadata?.invalidCount||stored.summary?.invalid||state.invalid.length);state.resultSummary=stored.summary||null;state.resultBrowserSnapshotDirty=false;}
        else{const metadata=(state.snapshots||[]).find((item)=>item.id===state.resultBrowserSnapshotId);state.devices=metadata?.devices||[];state.invalid=[];state.resultBrowserSnapshotId="";state.resultBrowserSnapshotDirty=false;state.resultDeviceCount=state.devices.length;state.resultInvalidCount=0;}
      }
      return true;
    }catch{return false;}
  }
  function normalizeColumnWidths(widths={}){const next={...defaultColumnWidths};if(widths&&typeof widths==="object")Object.entries(widths).forEach(([column,value])=>{const width=Number(value);if(column&&Number.isFinite(width))next[column]=Math.max(64,Math.min(600,Math.round(width)));});return next;}
  function syncThemeControls(theme){$$('[data-theme-choice],[data-theme-dialog-choice]').forEach((button)=>{const active=(button.dataset.themeChoice||button.dataset.themeDialogChoice)===theme;button.setAttribute("aria-pressed",String(active));button.classList.toggle("active-theme",active);});}
  function applyTheme(theme){state.theme=theme==="dark"?"dark":"light";document.body.classList.toggle("dark",state.theme==="dark");const meta=document.querySelector('meta[name="theme-color"]');if(meta)meta.content=state.theme==="dark"?"#1e1e1e":"#f5f5f5";syncThemeControls(state.theme);save();}
  function showThemeSelection(){syncThemeControls(state.theme);if(!$("#themeDialog").open)$("#themeDialog").showModal();}
  async function saveThemePreference(theme){try{const result=await api("/theme",{method:"POST",body:JSON.stringify({theme})});applyTheme(result.theme);toast("Theme saved to SQLite.");}catch(error){applyTheme(theme);toast("Тема переключена локально.");}}
  async function loadThemePreference(){try{const result=await api("/theme");applyTheme(result.theme);}catch{applyTheme(state.theme);}}
  async function loadOuiPreference(){try{const result=await api("/oui/settings");applyOuiPreference(result.settings||{});}catch{}}
  function applyOuiPreference(settings){state.ouiLength=settings.length||state.ouiLength;state.ouiStyle=settings.style||state.ouiStyle;$("#ouiLengthSelect").value=String(state.ouiLength||3);$("#ouiStyleSelect").value=state.ouiStyle||"plain";state.devices.forEach((device)=>{device.oui=formatOuiValue(device.mac||device.macFormatted||device.oui);});save();renderResults();if(document.querySelector("#analyticsView.active"))renderAnalytics();}
  async function saveOuiPreference(settings){try{const result=await api("/oui/settings",{method:"POST",body:JSON.stringify({settings})});applyOuiPreference(result.settings);toast("OUI settings saved to SQLite.");}catch(error){applyOuiPreference(settings);toast("OUI settings saved locally.");}}
  function normalizeVendorDetectorSettings(settings={}){return{enabled:settings.enabled!==false,useOui3:settings.useOui3!==false,useMac5:settings.useMac5!==false,useText:settings.useText!==false,useInference:settings.useInference!==false,confidenceThreshold:Math.max(0,Math.min(Number(settings.confidenceThreshold??0.6),1))};}
  function vendorDetectorSettingsFromUi(){return normalizeVendorDetectorSettings({enabled:$("#vendorDetectorEnabled")?.checked,useOui3:$("#vendorDetectorOui3")?.checked,useMac5:$("#vendorDetectorMac5")?.checked,useText:$("#vendorDetectorText")?.checked,useInference:$("#vendorDetectorInference")?.checked,confidenceThreshold:Number($("#vendorDetectorThreshold")?.value||60)/100});}
  function applyVendorDetectorSettings(settings={}){state.vendorDetectorSettings=normalizeVendorDetectorSettings(settings);const s=state.vendorDetectorSettings;if($("#vendorDetectorEnabled"))$("#vendorDetectorEnabled").checked=s.enabled;if($("#vendorDetectorOui3"))$("#vendorDetectorOui3").checked=s.useOui3;if($("#vendorDetectorMac5"))$("#vendorDetectorMac5").checked=s.useMac5;if($("#vendorDetectorText"))$("#vendorDetectorText").checked=s.useText;if($("#vendorDetectorInference"))$("#vendorDetectorInference").checked=s.useInference;if($("#vendorDetectorThreshold"))$("#vendorDetectorThreshold").value=String(Math.round(s.confidenceThreshold*100));if($("#vendorDetectorThresholdLabel"))$("#vendorDetectorThresholdLabel").textContent=Math.round(s.confidenceThreshold*100)+"%";save();}
  async function loadVendorDetectorSettings(){try{const result=await api("/vendor-detector/settings");applyVendorDetectorSettings(result.settings||{});}catch{applyVendorDetectorSettings(state.vendorDetectorSettings||{});}}
  async function saveVendorDetectorSettings(){const settings=vendorDetectorSettingsFromUi();try{const result=await api("/vendor-detector/settings",{method:"POST",body:JSON.stringify({settings})});applyVendorDetectorSettings(result.settings||settings);toast("Настройки автоопределения сохранены в SQLite.");}catch(error){applyVendorDetectorSettings(settings);toast("Настройки автоопределения сохранены локально.");}}
  function normalizeHistoryEnrichmentSettings(settings={}){return{enabled:settings.enabled!==false,priorityHistory:settings.priorityHistory!==false,useOuiMatch:settings.useOuiMatch!==false,useMac5Match:settings.useMac5Match!==false};}
  function historyEnrichmentSettingsFromUi(){return normalizeHistoryEnrichmentSettings({enabled:$("#historyEnrichmentEnabled")?.checked,priorityHistory:$("#historyEnrichmentPriority")?.checked,useOuiMatch:$("#historyEnrichmentOui")?.checked,useMac5Match:$("#historyEnrichmentMac5")?.checked});}
  function applyHistoryEnrichmentSettings(settings={}){state.historyEnrichmentSettings=normalizeHistoryEnrichmentSettings(settings);const s=state.historyEnrichmentSettings;if($("#historyEnrichmentEnabled"))$("#historyEnrichmentEnabled").checked=s.enabled;if($("#historyEnrichmentPriority"))$("#historyEnrichmentPriority").checked=s.priorityHistory;if($("#historyEnrichmentOui"))$("#historyEnrichmentOui").checked=s.useOuiMatch;if($("#historyEnrichmentMac5"))$("#historyEnrichmentMac5").checked=s.useMac5Match;save();}
  async function loadHistoryEnrichmentSettings(){try{const result=await api("/history-enrichment/settings");applyHistoryEnrichmentSettings(result.settings||{});}catch{applyHistoryEnrichmentSettings(state.historyEnrichmentSettings||{});}}
  async function saveHistoryEnrichmentSettings(){const settings=historyEnrichmentSettingsFromUi();try{const result=await api("/history-enrichment/settings",{method:"POST",body:JSON.stringify({settings})});applyHistoryEnrichmentSettings(result.settings||settings);toast("Настройки исторического обогащения сохранены в SQLite.");}catch(error){applyHistoryEnrichmentSettings(settings);toast("Настройки исторического обогащения сохранены локально.");}}
  function engineeringSessionActive(){if(!state.engineeringMode||!state.engineeringToken)return false;const expires=Date.parse(state.engineeringExpiresAt||"");return !Number.isFinite(expires)||expires>Date.now();}
  function engineeringHasPermission(permission=""){return engineeringSessionActive()&&(!permission||(state.engineeringPermissions||[]).includes(permission));}
  function clearEngineeringSession(){state.engineeringMode=false;state.engineeringToken="";state.engineeringExpiresAt="";state.engineeringPermissions=[];}
  function renderEngineeringState({redirect=true}={}){
    if(state.engineeringMode&&!engineeringSessionActive())clearEngineeringSession();
    const active=engineeringSessionActive(),expires=active&&state.engineeringExpiresAt?new Date(state.engineeringExpiresAt).toLocaleString("ru-RU"):"-",permissions=active?(state.engineeringPermissions||[]):[];
    document.body.dataset.mode=active?"engineering":"user";
    document.title="MAC Analyzer Pro Web - "+(active?"Инженерный режим":"Пользовательский режим");
    $$('[data-engineering-only]').forEach((element)=>{element.hidden=!active;element.setAttribute("aria-hidden",active?"false":"true");});
    $$('[data-engineering-permission]').forEach((element)=>{const allowed=engineeringHasPermission(element.dataset.engineeringPermission||"");element.hidden=!allowed;element.disabled=!allowed;});
    const badge=$("#appModeButton");if(badge){badge.classList.toggle("engineering-mode",active);badge.classList.toggle("user-mode",!active);badge.setAttribute("aria-pressed",active?"true":"false");}
    if($("#appModeIcon"))$("#appModeIcon").textContent=active?"ENG":"USER";
    if($("#appModeLabel"))$("#appModeLabel").textContent=active?"Инженерный режим":"Пользовательский режим";
    if($("#appModeHint"))$("#appModeHint").textContent=active?"Полный доступ до "+expires:"Просмотр и поиск";
    const context=$("#modeContext");if(context){context.classList.toggle("engineering-mode",active);context.classList.toggle("user-mode",!active);}
    if($("#modeContextTitle"))$("#modeContextTitle").textContent=active?"Инженерный режим":"Пользовательский режим";
    if($("#modeContextText"))$("#modeContextText").textContent=active?"Доступны загрузка и обогащение файлов, настройки, автоматизация и управление SQLite.":"Доступны универсальный поиск, история и аналитика. Для загрузки файлов и настроек войдите в инженерный режим.";
    if($("#modeContextAction"))$("#modeContextAction").textContent=active?"Выйти":"Войти";
    if($("#engineeringStatus"))$("#engineeringStatus").textContent=active?"Инженерная сессия активна до "+expires:"Пользовательский режим: инженерные операции заблокированы";
    if($("#engineeringLoginButton"))$("#engineeringLoginButton").textContent=active?"Выйти в пользовательский режим":"Войти в инженерный режим";
    if($("#engineeringRole"))$("#engineeringRole").textContent=active?"engineer":"user";
    if($("#engineeringPermissionCount"))$("#engineeringPermissionCount").textContent=String(permissions.length);
    if($("#engineeringExpires"))$("#engineeringExpires").textContent=expires;
    if($("#engineeringPermissions"))$("#engineeringPermissions").innerHTML=permissions.length?permissions.map((permission)=>`<span>${esc(engineeringPermissionLabels[permission]||permission)}</span>`).join(""):'<span class="muted">Инженерные разрешения не выданы.</span>';
    if($("#brandModeButton"))$("#brandModeButton").title=active?"Выйти в пользовательский режим":"Войти в инженерный режим";
    Guide.syncMode(active,state.engineeringExpiresAt,document);
    save();
    const current=$(".view.active")?.id?.replace(/View$/,"")||viewFromHash();
    if(redirect&&!active&&engineeringOnlyViews.has(current))activateView("workspace",{updateHash:true,render:true});
  }
  function openEngineeringDialog(){if(engineeringSessionActive())return logoutEngineering();const dialog=$("#engineeringDialog");if(!dialog)return;$("#engineeringPasswordInput").value="";$("#engineeringLoginResult").textContent="Введите пароль инженерного режима.";$("#engineeringLoginResult").className="engineering-login-result muted";dialog.showModal();setTimeout(()=>$("#engineeringPasswordInput")?.focus(),0);}
  async function loginEngineering(password,ttlMinutes=480){
    if(!String(password||"").trim())throw new Error("Пароль инженерного режима не указан.");
    try{const session=await api("/engineering/login",{method:"POST",body:JSON.stringify({password,ttlMinutes})});state.engineeringMode=true;state.engineeringToken=session.token||"";state.engineeringExpiresAt=session.expiresAt||"";state.engineeringPermissions=session.permissions||[];}
    catch(error){if(!networkUnavailable(error))throw error;if(password!=="admin123")throw new Error("Неверный пароль инженерного режима.");state.engineeringMode=true;state.engineeringToken="local-"+crypto.randomUUID();state.engineeringExpiresAt=new Date(Date.now()+Math.max(1,Math.min(Number(ttlMinutes)||480,1440))*60000).toISOString();state.engineeringPermissions=[...engineeringPermissionList];}
    save();renderEngineeringState({redirect:false});$("#engineeringDialog")?.close();view("workspace");toast("Инженерный режим включён.");
  }
  async function logoutEngineering(){if(!engineeringSessionActive()){clearEngineeringSession();renderEngineeringState();return;}try{if(!String(state.engineeringToken||"").startsWith("local-"))await api("/engineering/logout",{method:"POST",body:JSON.stringify({})});}catch{}clearEngineeringSession();save();renderEngineeringState({redirect:false});view("workspace");toast("Включён пользовательский режим.");}
  async function loadEngineeringSession(){if(state.engineeringToken&&String(state.engineeringToken).startsWith("local-")){if(Date.parse(state.engineeringExpiresAt||"")>Date.now()){state.engineeringMode=true;save();renderEngineeringState();return;}clearEngineeringSession();save();renderEngineeringState();return;}if(!state.engineeringToken){clearEngineeringSession();save();renderEngineeringState();return;}try{const result=await api("/engineering/session");if(result.active&&result.session){state.engineeringMode=true;state.engineeringExpiresAt=result.session.expiresAt||state.engineeringExpiresAt;state.engineeringPermissions=result.session.permissions||[];}else clearEngineeringSession();save();renderEngineeringState();}catch{clearEngineeringSession();save();renderEngineeringState();}}
  let enrichmentController = null;
  let currentEnrichmentJobId = null;
  let pendingSingleFile = null;
  let pendingSingleFilePreview = null;
  let columnConflictContext = null;
  let dashboardFilteredDevices = null;
  let dashboardRefreshTimer = null;
  let dashboardChangeAnalysis = {summary:{total:0,critical:0,added:0,removed:0,modified:0},changes:[],snapshotOptions:[]};
  let dashboardChangeTypeFilter = "all";
  let browserDashboardCache = null;
  let localAnalyticsCache = null;
  let analysisDashboardCache = null;
  let analysisDashboardPromise = null;
  let analysisDashboardPromiseKey = "";
  let analysisDashboardRevision = 0;
  let historyPanelPromise = null;
  let analyticsPanelPromise = null;
  let analyticsRenderRevision=0,movementRenderRevision=0,analyticsRenderCache={signature:"",at:0},historyRenderCache={signature:"",at:0};
  let contextTableRow = null;
  let resultColumnResize = null;
  let enhancedMovementIds = [];
  let movementColumnSettings = {visible:["mac","count","dates","vendor","model","address","room","field","before","after","source"],widths:{mac:180,count:100,dates:170,vendor:160,model:160,address:220,room:120,field:120,before:240,after:240,source:160}};
  let movementColumnResize = null;
  let fileRenderVersion = 0;
  let mappingRenderVersion = 0;
  let pendingFileImports = [];
  const sourceFilesById = new Map();
  const workspacePreviewDataRows = 100;
  function releaseTransientAnalysisMemory(){
    dashboardFilteredDevices=null;
    browserDashboardCache=null;
    localAnalyticsCache=null;
    dashboardChangeAnalysis={summary:{total:0,critical:0,added:0,removed:0,modified:0},changes:[],snapshotOptions:[]};
    historyPanelPromise=null;
    analyticsPanelPromise=null;
    contextTableRow=null;
    const resultsBody=$("#resultsBody");
    if(resultsBody)resultsBody.replaceChildren();
    return MemoryGuard.yieldToMainThread();
  }
  function sourceFileStorageId(file){return [String(file?.name||"source-file"),Number(file?.size||0),Number(file?.lastModified||0)].join("|");}
  async function rememberSourceFile(fileRecord,file){
    if(!fileRecord||!file)return false;
    sourceFilesById.set(fileRecord.id,file);
    if(fileRecord.fileToken&&!fileRecord.clientImported)return true;
    fileRecord.sourceStorageId=sourceFileStorageId(file);
    let stored=false;
    try{await BrowserSnapshots?.saveSourceFile?.(fileRecord.sourceStorageId,file);stored=true;}catch{}
    if(localFolderStructure)try{await LocalFolderStore?.copyImport?.(localFolderStructure,file,fileRecord.sourceStorageId);stored=true;}catch(error){localFolderStatus("Не удалось скопировать исходный файл: "+error.message,"error");}
    return stored;
  }
  async function restoreSourceFile(fileRecord){
    if(!fileRecord)return null;
    const current=sourceFilesById.get(fileRecord.id);
    if(current)return current;
    const storageId=fileRecord.sourceStorageId;
    if(!storageId||!BrowserSnapshots?.loadSourceFile)return null;
    try{const restored=await BrowserSnapshots.loadSourceFile(storageId);if(restored)sourceFilesById.set(fileRecord.id,restored);return restored||null;}catch{return null;}
  }
  async function restoreWorkspaceSourceFiles(){
    for(const fileRecord of state.files||[])await restoreSourceFile(fileRecord);
    if(state.ddioFile)await restoreSourceFile(state.ddioFile);
    return sourceFilesById.size;
  }
  function compactWorkspaceFileRows(fileRecord){
    const rows=Array.isArray(fileRecord?.rows)?fileRecord.rows:[];
    if(rows.length<=workspacePreviewDataRows+1||!fileRecord.sourceStorageId)return false;
    fileRecord.rows=rows.slice(0,workspacePreviewDataRows+1);
    fileRecord.rowsComplete=false;
    return true;
  }
  async function releaseRetainedWorkspaceRows(){
    let released=0;
    for(const fileRecord of state.files||[]){
      if(!Array.isArray(fileRecord.rows)||fileRecord.rows.length<=workspacePreviewDataRows+1)continue;
      if(await restoreSourceFile(fileRecord))released+=compactWorkspaceFileRows(fileRecord)?1:0;
    }
    if(state.ddioFile&&Array.isArray(state.ddioFile.rows)&&state.ddioFile.rows.length>workspacePreviewDataRows+1&&await restoreSourceFile(state.ddioFile))released+=compactWorkspaceFileRows(state.ddioFile)?1:0;
    if(released)await MemoryGuard.yieldToMainThread();
    return released;
  }
  function pruneStoredSourceFiles(){const ids=(state.files||[]).map((file)=>file.sourceStorageId).filter(Boolean);if(state.ddioFile?.sourceStorageId)ids.push(state.ddioFile.sourceStorageId);return BrowserSnapshots?.pruneSourceFiles?.(ids).catch(()=>false);}
  async function replaceConsumedEnrichmentFiles(requestedRole){
    const selection=WorkspaceFileLifecycle.selectForNextImport(state.files,requestedRole),removed=selection.removed;
    if(!removed.length)return 0;
    state.files=selection.files;
    for(const file of removed)sourceFilesById.delete(file.id);
    const tokens=removed.map((file)=>file.fileToken).filter(Boolean);
    if(tokens.length&&backendAvailable)await api("/workspace/cache/discard",{method:"POST",body:JSON.stringify({tokens})}).catch(()=>{});
    ensureMappingSelection();
    await pruneStoredSourceFiles();
    await MemoryGuard.yieldToMainThread();
    return removed.length;
  }
  function markEnrichmentFilesConsumed(consumedAt=new Date().toISOString()){
    return WorkspaceFileLifecycle.markConsumed(state.files,consumedAt);
  }
  let activeProcessId = "";
  let processHideTimer = null;
  function processPercent(value){return Math.max(0,Math.min(100,Math.round(Number(value)||0)));}
  function beginProcess(title,detail="Подготовка операции...",value=0){
    const id="process-"+(Date.now())+"-"+(Math.random().toString(16).slice(2));
    activeProcessId=id;
    clearTimeout(processHideTimer);
    const panel=$("#processProgressPanel");
    if(panel){panel.hidden=false;panel.classList.remove("complete","warning","error");}
    const technical=$("#processProgressTechnical");if(technical){technical.hidden=true;technical.open=false;}if($("#processProgressTechnicalText"))$("#processProgressTechnicalText").textContent="";
    const bar=$("#processProgressBar");if(bar)bar.value=0;
    updateProcess(id,value,detail,title);
    return id;
  }
  function updateProcess(id,value,detail="",title=""){
    if(!id||id!==activeProcessId)return false;
    const bar=$("#processProgressBar"),percent=Math.max(Number(bar?.value||0),processPercent(value));
    if(title)$("#processProgressTitle").textContent=title;
    if(detail)$("#processProgressDetail").textContent=detail;
    if(bar){bar.value=percent;bar.textContent=percent+"%";bar.setAttribute("aria-valuenow",String(percent));}
    $("#processProgressPercent").textContent=percent+"%";
    return true;
  }
  function finishProcess(id,detail="Готово",status="complete"){
    if(!updateProcess(id,100,detail))return;
    const panel=$("#processProgressPanel");
    panel?.classList.add(status);
    clearTimeout(processHideTimer);
    processHideTimer=setTimeout(()=>{if(activeProcessId===id&&panel){panel.hidden=true;activeProcessId="";}},status==="error"?6000:2600);
  }
  function failProcess(id,error,context={}){const message=error instanceof Error?error.message:String(error||"Неизвестная ошибка"),stage=String(context.stage||error?.stage||error?.details?.stage||"неизвестный этап"),bar=$("#processProgressBar"),percent=Number(bar?.value||0),technical={enrichmentRunId:context.enrichmentRunId||error?.runId||error?.details?.enrichmentRunId||currentEnrichmentJobId||"",currentStage:stage,processedRows:context.processedRows??error?.details?.processedRows,totalRows:context.totalRows??error?.details?.totalRows,currentDevice:context.currentDevice||error?.details?.currentDevice||"",source:context.source||error?.details?.source||"",exception:error?.details?.exception||error?.name||"Error",message,stack:error?.details?.stack||error?.stack||""};if(updateProcess(id,percent,`Ошибка на этапе «${stage}»: ${message}`,"Обогащение остановлено"))$("#processProgressPanel")?.classList.add("error");const details=$("#processProgressTechnical"),output=$("#processProgressTechnicalText");if(details)details.hidden=false;if(output)output.textContent=JSON.stringify(technical,null,2);clearTimeout(processHideTimer);}
  function cancelProcess(id,detail="Операция отменена"){finishProcess(id,detail,"warning");}
  const api = async (path, options = {}) => {
    if(browserOnlyMode)throw new TypeError("Приложение работает без backend; используется локальная файловая база");
    const authHeaders=state.engineeringToken?{"Authorization":"Bearer "+state.engineeringToken}:{};
    const {headers:optionHeaders={},...fetchOptions}=options;
    const candidates=[backendBase,...backendCandidates.filter((item)=>item!==backendBase)].filter(Boolean);
    let lastError=null;
    for(const base of candidates){
      try{
        const response = await fetch(base + path, {
          ...fetchOptions,
          headers: {"Content-Type": "application/json", ...authHeaders, ...optionHeaders}
        });
        const responseText=await response.text();
        let data={};
        try{data=responseText?JSON.parse(responseText):{};}catch{const apiError=new Error("Backend вернул некорректный ответ (HTTP "+response.status+")");apiError.status=response.status;throw apiError;}
        if (!response.ok){const apiError=new Error(data.error||"Ошибка API");apiError.status=response.status;apiError.details=data;apiError.stage=data.stage||data.currentStage||"";apiError.runId=data.enrichmentRunId||data.jobId||"";throw apiError;}
        backendBase=base;
        backendAvailable=true;
        return data;
      }catch(error){
        lastError=error;
        if(!networkUnavailable(error))throw error;
      }
    }
    backendAvailable=false;
    throw lastError||new TypeError("Backend недоступен");
  };
  function compactAnalysisAutosaveState(){
    const activeSnapshot=state.snapshots?.[0];
    return {
      ...state,
      activeSnapshotId:activeSnapshot?.id||state.resultSnapshotId||"",
      files:(state.files||[]).map((file)=>({...file,rows:[]})),
      devices:[],
      invalid:[],
      snapshots:(state.snapshots||[]).slice(0,25).map((snapshot)=>({...snapshot,devices:[]})),
      movementHistory:(state.movementHistory||[]).slice(0,100),
      localVendorMappings:{},
      localModelMappings:{},
      engineeringMode:false,
      engineeringToken:"",
      engineeringExpiresAt:"",
      engineeringPermissions:[]
    };
  }
  async function persistAutosave(reason="manual") {
    const autosaveState=compactAnalysisAutosaveState();
    const result=await api("/autosave",{method:"POST",body:JSON.stringify({slot:"main",reason,state:autosaveState})});
    state.backendAutosaveUpdatedAt=result.updatedAt||state.backendAutosaveUpdatedAt||"";
    save();
    const status=$("#autosaveStatus");
    if(status)status.textContent=result.statusText||"Autosaved.";
    return result;
  }
  async function restoreAutosave() {
    const data=await api("/autosave?slot=main&compact=1");
    if(!data.autosave?.state)throw new Error("Autosave is empty");
    state=normalizeRestoredState(data.autosave.state);
    state.backendAutosaveUpdatedAt=data.autosave.updatedAt||"";
    applyVendorDetectorSettings(state.vendorDetectorSettings||{});
    applyHistoryEnrichmentSettings(state.historyEnrichmentSettings||{});
    save();
    await syncFromBackend();
    renderAll();
    const status=$("#autosaveStatus");
    if(status)status.textContent=data.autosave.statusText||"Autosave restored.";
    return data.autosave;
  }
  async function deleteAutosave() {
    const result=await api("/autosave?slot=main",{method:"DELETE"});
    const status=$("#autosaveStatus");
    if(status)status.textContent=result.statusText||"Autosave slot updated.";
    return result;
  }
  function currentWorkspaceIsEmpty(){
    return !currentDeviceCount()&&!state.files.length&&!state.invalid.length&&!(state.lastAnalysis);
  }
  function normalizeRestoredState(restored={}){
    const merged={...empty(),...restored};
    merged.importErrors=[];
    merged.files=normalizeFileRoles(merged.files);
    merged.movementHistory=Array.isArray(merged.movementHistory)?merged.movementHistory:[];
    merged.ipMappings=Array.isArray(merged.ipMappings)?merged.ipMappings:[];
    merged.smartroomMappings=merged.smartroomMappings&&typeof merged.smartroomMappings==="object"&&!Array.isArray(merged.smartroomMappings)?merged.smartroomMappings:{};
    merged.localVendorMappings=merged.localVendorMappings&&typeof merged.localVendorMappings==="object"?merged.localVendorMappings:{};
    merged.localModelMappings=merged.localModelMappings&&typeof merged.localModelMappings==="object"?merged.localModelMappings:{};
    merged.columnWidths=normalizeColumnWidths(merged.columnWidths);
    merged.vendorDetectorSettings=normalizeVendorDetectorSettings(merged.vendorDetectorSettings||{});
    merged.historyEnrichmentSettings=normalizeHistoryEnrichmentSettings(merged.historyEnrichmentSettings||{});
    if(!merged.resultSnapshotId&&merged.activeSnapshotId)merged.resultSnapshotId=String(merged.activeSnapshotId);
    if(merged.resultSnapshotId&&!merged.resultDeviceCount){const snapshot=merged.snapshots.find((item)=>item.id===merged.resultSnapshotId);merged.resultDeviceCount=Number(snapshot?.deviceCount||0);}
    return merged;
  }
  function shouldRestoreBootstrapAutosave(autosave){
    if(!autosave?.state)return false;
    if(state.resultBrowserSnapshotId&&Number(state.resultDeviceCount||0)>0)return false;
    const remoteUpdatedAt=Date.parse(autosave.updatedAt||"")||0;
    const localUpdatedAt=Date.parse(state.backendAutosaveUpdatedAt||"")||0;
    if(currentWorkspaceIsEmpty())return true;
    if(remoteUpdatedAt&&localUpdatedAt)return remoteUpdatedAt>=localUpdatedAt;
    return Boolean(remoteUpdatedAt&&!localUpdatedAt);
  }
  function restoreBootstrapAutosave(autosave){
    if(!shouldRestoreBootstrapAutosave(autosave))return false;
    const restored=normalizeRestoredState(autosave.state);
    if(!restored.devices.length&&!restored.files.length&&!restored.snapshots.length&&!restored.movementHistory.length)return false;
    if(!Object.keys(restored.localVendorMappings||{}).length)restored.localVendorMappings=state.localVendorMappings||{};
    if(!Object.keys(restored.localModelMappings||{}).length)restored.localModelMappings=state.localModelMappings||{};
    if(!(restored.ipMappings||[]).length)restored.ipMappings=state.ipMappings||[];
    if(!Object.keys(restored.smartroomMappings||{}).length)restored.smartroomMappings=state.smartroomMappings||{};
    state={...state,...restored,backendAutosaveUpdatedAt:autosave.updatedAt||"",bootstrapAutosaveRestoredAt:autosave.updatedAt||new Date().toISOString()};
    applyVendorDetectorSettings(state.vendorDetectorSettings||{});
    applyHistoryEnrichmentSettings(state.historyEnrichmentSettings||{});
    const status=$("#autosaveStatus");
    if(status)status.textContent=autosave.statusText||"Autosave restored from SQLite.";
    return true;
  }
  function setBackendStatus(available,message=""){
    backendAvailable=Boolean(available);
    const status=$("#storageStatus"),dot=$("#backendStatusDot"),button=$("#reconnectBackendButton");
    if(status)status.textContent=message||(backendAvailable?"SQLite подключена":"Автономный режим · локальная MADB и IndexedDB");
    if(dot){dot.classList.remove("offline");dot.classList.toggle("standalone",!backendAvailable);dot.classList.toggle("online",backendAvailable);}
    if(button){button.hidden=autonomousHtmlMode||backendAvailable;button.disabled=false;}
  }
  async function checkBackendConnection(){
    const button=$("#reconnectBackendButton");
    if(button)button.disabled=true;
    if(autonomousHtmlMode){setBackendStatus(false,localFolderStructure?"Локальная файловая база подключена · backend не используется":"Автономный HTML · выберите локальную папку данных");return null;}
    try{const health=await api("/health");setBackendStatus(true,"Backend и SQLite подключены");return health;}
    catch(error){setBackendStatus(false,"Автономный HTML-режим готов · XLSX и история сохраняются в браузере");throw error;}
    finally{if(button)button.disabled=false;}
  }
  async function syncFromBackend() {
    try {
      const data = await api("/bootstrap");
      const restoredFromAutosave=restoreBootstrapAutosave(data.autosave);
      if (data.snapshots?.length) {
        const restoredSnapshots=Array.isArray(state.snapshots)?state.snapshots:[];
        const snapshotMap=new Map(restoredSnapshots.map((item)=>[item.id,item]));
        data.snapshots.forEach((item)=>snapshotMap.set(item.id,item));
        state.snapshots=[...snapshotMap.values()];
      }
      const finalSnapshotsByRecency=(items=state.snapshots||[])=>items.filter((item)=>String(item.kind||"").toLowerCase()==="analysis"||String(item.name||"").toLowerCase().startsWith("анализ:")).sort((a,b)=>String(b.savedAt||b.createdAt||"").localeCompare(String(a.savedAt||a.createdAt||""))||Number(b.snapshotOrder||0)-Number(a.snapshotOrder||0));
      const backendFinals=finalSnapshotsByRecency((state.snapshots||[]).filter((item)=>item.backendStored));
      const latestBackend=backendFinals[0],activeBrowser=(state.snapshots||[]).find((item)=>item.id===state.resultBrowserSnapshotId&&item.browserStored);
      const browserTime=Date.parse(activeBrowser?.savedAt||activeBrowser?.createdAt||"")||0,backendTime=Date.parse(latestBackend?.savedAt||latestBackend?.createdAt||"")||0;
      if(latestBackend&&(!activeBrowser||backendTime>browserTime)){state.resultSnapshotId=String(latestBackend.id||"");state.resultBrowserSnapshotId="";state.resultBrowserSnapshotDirty=false;}
      else if(activeBrowser)state.resultSnapshotId="";
      else if(state.resultSnapshotId&&!backendFinals.some((item)=>String(item.id)===String(state.resultSnapshotId)))state.resultSnapshotId=String(latestBackend?.id||"");
      if(state.resultSnapshotId){
        try{
          let opened;
          try{opened=await api("/snapshots/open",{method:"POST",body:JSON.stringify({id:state.resultSnapshotId,compactResult:true,resultPageSize})});}
          catch(error){
            if(error.status!==404)throw error;
            const staleId=state.resultSnapshotId;
            state.snapshots=(state.snapshots||[]).filter((item)=>item.id!==staleId);
            clearResultReference();
            const latestFinal=backendFinals.find((item)=>String(item.id)!==String(staleId));
            if(!latestFinal)throw error;
            state.resultSnapshotId=String(latestFinal.id||"");
            opened=await api("/snapshots/open",{method:"POST",body:JSON.stringify({id:state.resultSnapshotId,compactResult:true,resultPageSize})});
          }
          const reference=opened.resultReference||{};
          state.resultDeviceCount=Number(reference.deviceCount||0);
          state.resultInvalidCount=Number(reference.invalidCount||0);
          state.resultSummary=opened.resultSummary||opened.resultPage?.summary||null;
          state.devices=opened.resultPage?.items||opened.devices||state.devices||[];
          state.invalid=opened.invalid||[];
        }catch(error){if(error.status!==404)throw error;clearResultReference();}
      }
      if (data.columns) {
        state.visibleColumns = data.columns.visible || state.visibleColumns;
        state.columnOrder = data.columns.order || state.columnOrder || state.visibleColumns;
        state.columnWidths = normalizeColumnWidths(data.columns.widths || state.columnWidths);
        state.customColumns = data.customColumns || [];
        state.customColumnMappings = data.customColumnMappings || {};
        Object.assign(labels, data.customLabels || {});
      }
      save(); renderAll(); setBackendStatus(true,restoredFromAutosave?"SQLite подключена, autosave восстановлен":"Backend и SQLite подключены");return true;
    } catch (error) {
      if (!networkUnavailable(error)) UiFeedback?.showError(error);
      setBackendStatus(false,"Автономный HTML-режим готов · XLSX и история сохраняются в браузере");return false;
    }
  }
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
  let toastTimer;
  const toast = (msg) => { const el=$("#toast"); el.textContent=msg; el.classList.add("show"); clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.classList.remove("show"),2600); };
  const normalize = (value) => { let v=String(value ?? "").toUpperCase().replace(/[^0-9A-F]/g,""); if(v.length===10)v="00"+v; if(v.length===11)v="0"+v; if(v.length===8)v="0000"+v; return v.length===12?v:null; };
  const formatMac = (mac) => mac ? mac.match(/.{1,2}/g).join(":") : "";
  function formatDisplayDateTime(value){return value?new Date(value).toLocaleString("ru-RU"):"";}
  function fileInfoDate(file){const value=Number(file?.lastModified||0);return value>0?new Date(value).toISOString():new Date().toISOString();}
  function primaryFileCreatedAt(){return state.files[0]?.createdAt||state.files[0]?.fileDate||new Date().toISOString();}
  function normalizePrefix(value){return String(value??"").toUpperCase().replace(/[^0-9A-F]/g,"");}
  function formatOuiValue(mac,length=state.ouiLength,style=state.ouiStyle){const hex=normalize(mac||"")||normalizePrefix(mac),bytes=Math.max(3,Math.min(Number(length||3),6)),prefix=hex.slice(0,bytes*2);if(prefix.length<bytes*2)return"";const pairs=prefix.match(/../g)||[];if(style==="colon")return pairs.join(":");if(style==="dash")return pairs.join("-");if(style==="dot"||style==="cisco-dot")return prefix.match(/.{1,4}/g).join(".");return prefix;}
  const headerName = (i) => "Колонка "+(i+1);
  const fileReaders=window.MacAnalyzerFileReaders;
  if(!fileReaders)throw new Error("Модуль frontend/file-readers.js не загружен");
  const {readClientTextFile,clientDelimiter,clientTableRows,clientJsonTable,clientZipEntries,clientXlsxTable,clientReadTable}=fileReaders;
  function localAutoMapping(headers){const find=(patterns)=>{const index=headers.findIndex(header=>patterns.some(pattern=>pattern.test(String(header).toLowerCase())));return index>=0?index:"";};return{mac:find([/mac/,/мак/]),vendor:find([/vendor/,/производ/,/вендор/]),model:find([/model/,/модель/]),ip:find([/^ip/,/ip address/,/адрес ip/]),address:find([/address/,/адрес/]),room:find([/room/,/помещ/,/кабин/]),smartroomId:find([/smart.?room.*id/,/id.*smart.?room/,/ид.*smart.?room/]),switchIp:find([/switch.*ip/,/коммутатор.*ip/]),switchPort:find([/port/,/порт/]),hostname:find([/host.?name/,/имя хоста/,/dns name/]),serialNumber:find([/serial/,/серийн/]),deviceId:find([/device.*id/,/id.*device/,/идентификатор.*устрой/]),deviceName:find([/device.*name/,/название.*устрой/,/наименование.*устрой/])};}
  function localMappingSummary(file){const mapped=Object.entries(file.mapping||{}).filter(([,value])=>value!==""&&value!==undefined).length;file.mappingSummary={summaryHtml:`<div class="bar-item"><div class="bar-label"><span>Сопоставлено полей</span><strong>${mapped}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${Math.min(100,mapped/fieldList.length*100)}%"></div></div></div>`};file.columnDetection={detectorHtml:'<p class="muted">Колонки определены в браузере, потому что backend недоступен.</p>'};renderColumnDetectionSummary(file);}
  function columnLetter(index){let n=Number(index)+1,letters="";while(n>0){const mod=(n-1)%26;letters=String.fromCharCode(65+mod)+letters;n=Math.floor((n-1)/26);}return letters||String(Number(index)+1);}
  function mappingOptionLabel(header,mode=state.mappingDisplayMode){const letter=columnLetter(header.index),name=header.name||headerName(header.index);return mode==="letter"?letter+" · "+name:name;}
  function selectedMappingFile(){return state.files.find((file)=>file.id===state.activeMappingFileId)||state.files[0]||null;}
  function ensureMappingSelection(){if(!state.files.some((file)=>file.id===state.activeMappingFileId))state.activeMappingFileId=state.files[0]?.id||"";}
  function fileRole(file,index=0){return normalizeSourceRole(file?.role,index);}
  function insertImportedFile(fileRecord,requestedRole="auto",batchIndex=0){
    state.files=normalizeFileRoles(state.files);
    let role=requestedRole;
    if(role==="primary"&&batchIndex>0)role="smartroom";
    if(role==="auto")role=state.files.some((file)=>file.role==="primary")?"smartroom":"primary";
    role=normalizeSourceRole(role,role==="primary"?0:1);
    fileRecord.role=role;
    if(role==="primary"){
      state.files.forEach((file)=>{if(file.role==="primary")file.role="smartroom";});
      state.files.unshift(fileRecord);
    }else state.files.push(fileRecord);
    state.files=normalizeFileRoles(state.files);
  }
  function renderMappingControls(){ensureMappingSelection();const select=$("#mappingFileSelect"),mode=$("#mappingDisplayMode");if(select){select.innerHTML=state.files.length?state.files.map((file,index)=>`<option value="${esc(file.id)}" ${file.id===state.activeMappingFileId?"selected":""}>${fileRole(file,index)==="primary"?"Файл №1 — основной":"Файл №2 — SmartRoom"}: ${esc(file.name)}</option>`).join(""):'<option value="">Файл №1 — основной</option>';select.disabled=!state.files.length;}if(mode){mode.value=state.mappingDisplayMode||"name";mode.disabled=!state.files.length;}$("#copyMappingToAllButton").disabled=state.files.length<2;}
  function localMappingGrid(file){if(!file)return'<p class="muted">Добавьте основной файл, чтобы настроить колонки.</p>';const options=['<option value="">Не использовать</option>'].concat(file.headers.map(h=>`<option value="${h.index}">${esc(mappingOptionLabel(h))}</option>`)).join("");return fieldList.map(([field,title])=>`<label>${esc(title)}<select data-map="${field}">${options.replace(`value="${file.mapping?.[field]}"`,`value="${file.mapping?.[field]}" selected`)}</select></label>`).join("");}
  function compileLocalRuleIndex(rules){const byPrefix=new Map(),compatible=new Map();Object.entries(rules||{}).forEach(([rawPrefix,value])=>{const prefix=normalizePrefix(rawPrefix);if(!value||![6,7,8,9,10].includes(prefix.length))return;byPrefix.set(prefix,value);if(prefix.length>=10){const key=prefix.slice(0,8),items=compatible.get(key)||[];items.push([prefix,value]);items.sort((a,b)=>b[0].length-a[0].length);compatible.set(key,items);}});return{byPrefix,lengths:[...new Set([...byPrefix.keys()].map((prefix)=>prefix.length))].sort((a,b)=>b-a),compatible};}
  function localRuleValue(mac,rules){const normalized=normalize(mac)||normalizePrefix(mac),index=rules?.byPrefix instanceof Map?rules:compileLocalRuleIndex(rules);for(const length of index.lengths){const value=index.byPrefix.get(normalized.slice(0,length));if(value)return value;}return"";}
  function localDetectorSettings(){return normalizeVendorDetectorSettings(state.vendorDetectorSettings||{});}
  let activeLocalDetectionContext=null;
  function createLocalDetectionContext(){const settings=localDetectorSettings(),allowPrefix=(prefix)=>normalizePrefix(prefix).length<=6?settings.useOui3:settings.useMac5,vendorRules=Object.fromEntries(Object.entries(state.localVendorMappings||{}).filter(([prefix])=>allowPrefix(prefix))),modelRules={...state.localModelMappings};return{settings,vendorRules:compileLocalRuleIndex(vendorRules),modelRules:compileLocalRuleIndex(modelRules)};}
  function localCompatibleRuleValue(mac,rules){const settings=activeLocalDetectionContext?.settings||localDetectorSettings();if(!settings.enabled||!settings.useMac5)return"";const normalized=normalize(mac)||normalizePrefix(mac),index=rules?.byPrefix instanceof Map?rules:compileLocalRuleIndex(rules);return index.compatible.get(normalized.slice(0,8))?.[0]?.[1]||"";}
  const localVendorKeywords={Apple:["apple","iphone","ipad","macbook","imac","mac","ios","ipod","airport"],Samsung:["samsung","galaxy","note","s series","gear","odyssey","ssd"],Huawei:["huawei","honor","mate","p series","mediapad","ascend"],Xiaomi:["xiaomi","mi ","redmi","poco","black shark","mijia"],Lenovo:["lenovo","thinkpad","ideapad","yoga","legion","thinkcentre"],Dell:["dell","xps","latitude","inspiron","precision","alienware","poweredge"],HP:["hp","hewlett packard","elitebook","probook","spectre","envy","pavilion","laserjet"],Acer:["acer","aspire","predator","nitro","swift","travelmate"],ASUS:["asus","rog","zenbook","vivobook","tuf","prime","expertbook"],Microsoft:["microsoft","surface","xbox","hololens","windows","lumia"],Cisco:["cisco","catalyst","meraki","asa","nexus","router","switch","firepower"],Juniper:["juniper","mx","ex","srx","qfx","netscreen"],"TP-Link":["tp-link","tplink","archer","deco","kasa","tapo"],Netgear:["netgear","orbi","nighthawk","prosafe","insight"],Intel:["intel","core i","xeon","pentium","celeron","ethernet"],AMD:["amd","ryzen","threadripper","epyc","radeon","athlon"],NVIDIA:["nvidia","geforce","quadro","tesla","rtx","gtx"],"Raspberry Pi":["raspberry","rpi","pi 3","pi 4","pi 5","pico"],Arduino:["arduino","uno","mega","nano","esp"],ESP32:["esp32","esp8266","espressif"]};
  function localVendorFromText(...values){const settings=activeLocalDetectionContext?.settings||localDetectorSettings();if(!settings.enabled||!settings.useText)return"";let best={vendor:"",score:0};values.map((value)=>String(value||"").toLowerCase()).forEach((text)=>{Object.entries(localVendorKeywords).forEach(([vendor,keywords])=>{const matches=keywords.filter((keyword)=>text.includes(keyword)).length,score=Math.min(matches/Math.max(1,keywords.length)*2,1)*0.8;if(score>best.score)best={vendor,score};});});return best.score>=settings.confidenceThreshold?best.vendor:"";}
  function localVendor(mac){const context=activeLocalDetectionContext||createLocalDetectionContext();if(!context.settings.enabled)return"Unknown";return localRuleValue(mac,context.vendorRules)||IeeeRegistry.lookup(mac)?.vendor||"Unknown";}
  function localModel(mac){const context=activeLocalDetectionContext||createLocalDetectionContext();if(!context.settings.enabled||!context.settings.useMac5)return"";return localRuleValue(mac,context.modelRules)||localCompatibleRuleValue(mac,context.modelRules);}
  function inferSwitchAddressMappings(devices=state.devices, source="analysis"){
    const observations=new Map();
    for(const device of devices||[]){
      const ip=normalizeIp(device.switchIp),address=String(device.address||"").trim();
      if(!ip||!address)continue;
      const values=observations.get(ip)||new Map();
      values.set(address,(values.get(address)||0)+1);observations.set(ip,values);
    }
    let imported=0;
    observations.forEach((values,ip)=>{
      if(values.size!==1)return;
      const [[address,count]]=values.entries();
      if(count>=2&&upsertLocalIpMapping(ip,address,"inferred-consensus"))imported++;
    });
    const autoSources=new Set(["analysis","current-file","inferred","automatic"]);
    const map=Object.fromEntries(localIpMappingRows().filter((item)=>!autoSources.has(String(item.source||"").toLowerCase())).map((item)=>[item.switchIp,item.address]));
    (devices||[]).forEach((device)=>{const address=map[normalizeIp(device.switchIp)];if(address&&!device.address){device.address=address;device.addressSource="switch-address-mapping";}});
    return imported;
  }
  async function historicalSwitchAddressMappings(switchIps){
    if(!BrowserSnapshots?.switchAddressConsensus)return new Map();
    try{return await BrowserSnapshots.switchAddressConsensus(switchIps,{minimumConfidence:0.90,minimumObservations:2});}
    catch{return new Map();}
  }
  async function applyHistoricalSwitchAddressMappings(devices=state.devices){
    const rows=Array.isArray(devices)?devices:[],switchIps=[];
    for(const device of rows){const switchIp=normalizeIp(device?.switchIp||device?.switch_ip);if(switchIp&&!device.address)switchIps.push(switchIp);}
    const mappings=await historicalSwitchAddressMappings(switchIps);
    let filled=0;
    for(const device of rows){
      if(device.address)continue;
      const item=mappings.get(normalizeIp(device.switchIp||device.switch_ip));
      if(!item?.address)continue;
      device.address=item.address;
      device.addressSource=item.source||"indexeddb-switch-consensus";
      device.addressConfidence=Number(item.confidence||0);
      device.fieldSources={...(device.fieldSources||{}),address:device.addressSource};
      filled++;
    }
    return{filled,mappings};
  }
  function normalizedRoomName(value){return String(value||"").trim().replace(/\s+/g," ");}
  function synchronizeSmartroomIdentity(device,mappings=state.smartroomMappings||{}){
    if(!device)return false;
    const smartroomId=normalizedRoomName(device.smartroomId||device.smartroom_id),room=normalizedRoomName(device.room),mapped=normalizedRoomName(mappings instanceof Map?mappings.get(smartroomId):mappings?.[smartroomId]),resolvedRoom=room||mapped;
    const changed=device.room!==resolvedRoom||device.smartroomId!==smartroomId||Object.prototype.hasOwnProperty.call(device,"smartroom_id");
    device.room=resolvedRoom;device.smartroomId=smartroomId;delete device.smartroom_id;
    if(smartroomId&&resolvedRoom){if(mappings instanceof Map)mappings.set(smartroomId,resolvedRoom);else mappings[smartroomId]=resolvedRoom;}
    return changed;
  }
  function inferSmartroomRoomMappings(devices=state.devices,source="analysis"){
    const learned={...(state.smartroomMappings||{})};let imported=0,filled=0;
    for(const device of devices||[]){const smartroomId=normalizedRoomName(device.smartroomId||device.smartroom_id),room=normalizedRoomName(device.room);if(smartroomId&&room&&learned[smartroomId]!==room){learned[smartroomId]=room;imported++;}}
    for(const device of devices||[]){const hadRoom=Boolean(normalizedRoomName(device.room));if(synchronizeSmartroomIdentity(device,learned)&&!hadRoom){device.roomSource="smartroom_mapping";filled++;}}
    state.smartroomMappings=learned;return{imported,filled,source};
  }
  function applyLocalVendorModelMappings(devices=state.devices){
    let changed=0;const previousContext=activeLocalDetectionContext;activeLocalDetectionContext=previousContext||createLocalDetectionContext();try{(devices||[]).forEach((device)=>{const mac=device.mac||device.macFormatted,vendor=localVendor(mac),model=localModel(mac);let rowChanged=false;if((!device.vendor||device.vendor==="Unknown"||device.vendor==="Не определено")&&vendor!=="Unknown"){device.vendor=vendor;rowChanged=true;}if(!device.model&&model){device.model=model;rowChanged=true;}if(rowChanged)changed++;});}finally{activeLocalDetectionContext=previousContext;}if(changed&&devices===state.devices){state.resultBrowserSnapshotDirty=true;if(state.resultBrowserSnapshotId&&BrowserSnapshots?.updateSnapshotWithTransform){snapshotMutationPromise=snapshotMutationPromise.then(async()=>{const result=await applyLocalVendorModelMappingsToCurrentResult();if(result?.updated){save({immediate:true});await flushBrowserStateSave().catch(()=>{});renderResults();renderAnalytics();renderHistory();}}).catch((error)=>toast("Не удалось обновить полный снимок правилами производителей и моделей: "+error.message));}}return changed;
  }
  async function applyLocalVendorModelMappingsToCurrentResult(source="local-vendor-model-rules"){
    if(!state.resultBrowserSnapshotId||!BrowserSnapshots?.updateSnapshotWithTransform)return{changed:applyLocalVendorModelMappings(state.devices),updated:false};
    const movements=[],limit=MemoryGuard.limits.movementRows||5000,changedAt=new Date().toISOString(),previousContext=activeLocalDetectionContext;activeLocalDetectionContext=createLocalDetectionContext();
    try{
      const result=await updateCurrentBrowserSnapshot("Автоопределение производителей и моделей",source,(device)=>{
        const beforeDevice=compactDashboardDevice(device),mac=device.mac||device.macFormatted,vendor=localVendor(mac),model=localModel(mac),changes=[];
        if((!device.vendor||device.vendor==="Unknown"||device.vendor==="Не определено")&&vendor!=="Unknown"){changes.push(["vendor",device.vendor||"",vendor]);device.vendor=vendor;}
        if(!device.model&&model){changes.push(["model",device.model||"",model]);device.model=model;}
        if(changes.length&&movements.length<limit){const afterDevice=compactDashboardDevice(device);for(const[field,before,after]of changes){if(movements.length>=limit)break;movements.push({mac:normalize(mac),type:"Изменено",field:labels[field]||field,before,after,beforeDevice,afterDevice,changedAt,source});}}
        return changes.length>0;
      });
      if(result?.updated&&movements.length)state.movementHistory=movements.concat((state.movementHistory||[]).slice(0,Math.max(0,limit-movements.length)));
      return result||{changed:0,updated:false};
    }finally{activeLocalDetectionContext=previousContext;}
  }
  async function applyBackendDetectionToCurrentResult(){
    if(!state.resultSnapshotId)return null;
    const result=await api("/detection/apply",{method:"POST",body:JSON.stringify(currentDevicePayload({compactResult:true,resultPageSize}))});
    state.devices=result.devices||[];state.resultDeviceCount=Number(result.resultReference?.deviceCount||state.resultDeviceCount||state.devices.length);state.resultInvalidCount=Number(result.resultReference?.invalidCount||0);state.resultSummary=result.resultSummary||state.resultSummary;
    const index=state.snapshots.findIndex((item)=>String(item.id)===String(state.resultSnapshotId));
    if(index>=0&&result.snapshot)state.snapshots.splice(index,1,{...state.snapshots[index],...result.snapshot,devices:[],backendStored:true});
    return result;
  }
  function learnLocalRulesFromDevices(rows=[],minCount=2){const threshold=Math.max(1,Number(minCount||2)),vendorCounts=new Map(),modelCounts=new Map(),count=(map,prefix,value)=>{if(!prefix||!value)return;const key=prefix+"\u0000"+value;map.set(key,(map.get(key)||0)+1);};for(const device of rows||[]){const mac=normalize(device.mac||device.macFormatted),vendor=String(device.vendor||"").trim(),model=String(device.model||"").trim();if(!mac)continue;for(const length of [6,8,10])if(vendor&&vendor!=="Unknown"&&vendor!=="Не определено")count(vendorCounts,mac.slice(0,length),vendor);if(model)count(modelCounts,mac.slice(0,10),model);}const learn=(target,counts,required)=>{let learned=0;const best=new Map();counts.forEach((total,key)=>{const[prefix,value]=key.split("\u0000");if(total<required||target[prefix])return;const current=best.get(prefix);if(!current||total>current.total)best.set(prefix,{value,total});});best.forEach((item,prefix)=>{target[prefix]=item.value;learned++;});return learned;};return{vendors:learn(state.localVendorMappings,vendorCounts,threshold),models:learn(state.localModelMappings,modelCounts,1)};}
  function localDeviceFromRow(file,row,rowIndex,fields){if(RecordValidation.isEmptyRow(row))return{skipped:true,reason:"EMPTY_ROW"};const pick=(field)=>{const index=file.mapping?.[field];return index===""||index===undefined?"":String(row[Number(index)]??"").trim();},rawMac=pick("mac"),mac=normalize(rawMac)||"",values={ip:fields.ip?pick("ip"):"",address:fields.address?pick("address"):"",room:fields.room?pick("room"):"",smartroomId:fields.smartroomId?pick("smartroomId"):"",switchIp:fields.switchIp?pick("switchIp"):"",switchPort:fields.switchPort?pick("switchPort"):"",hostname:pick("hostname"),serialNumber:pick("serialNumber"),deviceId:pick("deviceId"),deviceName:pick("deviceName")},role=normalizeSourceRole(file.role);const identityProbe={mac,...values};if(!DeviceIdentity.candidates(identityProbe).some((candidate)=>!candidate.startsWith("internal-id:")))return{invalid:RecordValidation.invalidIdentity({row,rowNumber:rowIndex+2,source:file.name,sourceRole:role,rawMac,macColumn:file.mapping?.mac??null})};const model=fields.model?(pick("model")||(mac?localModel(mac):"")):"",vendor=fields.vendor?(pick("vendor")||localVendorFromText(model,pick("name"),row.join(" "))||(mac?localVendor(mac):"Unknown")):"Не определено";Object.assign(values,{vendor,model});const fieldSources=Object.fromEntries(Object.entries(values).filter(([,value])=>value!=="").map(([field])=>[field,file.name])),device={mac,macFormatted:formatMac(mac),oui:formatOuiValue(mac),...values,fieldSources,sourceFiles:[file.name],sourceRoles:[role],sourceRole:role,source:file.name,row:rowIndex+2,valid:true};device.internalDeviceId=DeviceIdentity.stableId(device);device.identityKey=DeviceIdentity.key(device);device.matchConfidence=mac?"Exact":"High";return{device};}
  function mergeAnalysisDevice(previous,incoming,{preferExisting=false}={}){
    const merged=previous?{...previous}:{};
    const fieldSources={...(merged.fieldSources||{})},sourceFiles=Array.from(new Set([...(merged.sourceFiles||[]),merged.source,incoming?.source].filter(Boolean))),sourceRoles=Array.from(new Set([...(merged.sourceRoles||[]),incoming?.sourceRole].filter(Boolean))),conflicts=[...(merged.conflicts||[])];
    for(const[field,value]of Object.entries(incoming||{})){
      if(["fieldSources","sourceFiles","sourceRoles","conflicts"].includes(field))continue;
      if(value===""||value===undefined)continue;
      const hasExisting=merged[field]!==""&&merged[field]!==undefined&&merged[field]!==null;
      if(hasExisting&&String(merged[field])!==String(value)&&["vendor","model","ip","address","room","smartroomId","switchIp","switchPort","hostname","serialNumber","deviceId"].includes(field)){const conflict={field,selected:preferExisting?merged[field]:value,selectedSource:preferExisting?fieldSources[field]:incoming.source,alternative:preferExisting?value:merged[field],alternativeSource:preferExisting?incoming.source:fieldSources[field]};if(!conflicts.some((item)=>JSON.stringify(item)===JSON.stringify(conflict)))conflicts.push(conflict);}
      if(!preferExisting||!hasExisting)merged[field]=value;
      if((!preferExisting||!hasExisting)&&incoming.source)fieldSources[field]=incoming.source;
    }
    merged.fieldSources=fieldSources;merged.sourceFiles=sourceFiles;merged.sourceRoles=sourceRoles;merged.conflicts=conflicts;merged.hasConflict=conflicts.length>0;merged.mac=merged.mac||"";merged.macFormatted=merged.macFormatted||"";merged.oui=merged.oui||"";merged.identityKey=DeviceIdentity.key(merged);merged.internalDeviceId=previous?.internalDeviceId||DeviceIdentity.stableId(merged);merged.source=sourceFiles.length===1?sourceFiles[0]:sourceFiles.join(" + ");
    return merged;
  }
  function resolveOrCreateAnalysisDevice(devices,index,incoming,strategy,diagnostics){
    return EnrichmentStrategy.resolveOrCreate({candidate:incoming,index,devices,identityApi:DeviceIdentity,merge:mergeAnalysisDevice,strategy,sourceRole:incoming.sourceRole,diagnostics});
  }
  async function visitLocalRowsForAnalysis(file,fileIndex,fileCount,onProgress,onRow){
    const inlineRows=Array.isArray(file.rows)?file.rows:[];
    const expectedRows=Math.max(0,Number(file.rowCount||0));
    if(file.rowsComplete!==false&&inlineRows.length>expectedRows){
      for(let rowIndex=1;rowIndex<inlineRows.length;rowIndex++){
        await onRow(inlineRows[rowIndex],rowIndex-1);
        if(rowIndex%2000===0)await MemoryGuard.yieldToMainThread();
      }
      compactWorkspaceFileRows(file);
      return Math.max(0,inlineRows.length-1);
    }
    const sourceFile=await restoreSourceFile(file);
    if(!sourceFile)throw new Error(`Для автономного анализа повторно выберите файл «${file.name}»: исходный файл отсутствует в хранилище браузера.`);
    const progress=(value,detail)=>onProgress((fileIndex+value/100)/Math.max(1,fileCount)*35,`${file.name}: ${detail}`);
    if(/\.(xlsx|xlsm)$/i.test(sourceFile.name)){
      const data=await clientReadTable(sourceFile,progress,{collectRows:false,onRow});
      file.rowCount=Math.max(expectedRows,Number(data.rowCount||0));
      file.rowsComplete=false;
      return file.rowCount;
    }
    const data=await clientReadTable(sourceFile,progress),rows=Array.isArray(data.rows)?data.rows:[];
    for(let rowIndex=0;rowIndex<rows.length;rowIndex++){
      await onRow(rows[rowIndex],rowIndex);
      if((rowIndex+1)%2000===0)await MemoryGuard.yieldToMainThread();
    }
    const rowCount=rows.length;
    rows.length=0;
    return rowCount;
  }
  async function buildLocalDdioOverlay(switchTracker,onProgress=()=>{}){
    const changes=DdioOverlay.switchChanges(switchTracker),file=state.ddioFile;
    if(!file)return{overlay:{},index:new Map(),summary:{loaded:false,switchIpChanges:changes.size,newIpHints:0,ipFallbacks:0}};
    const validation=DdioOverlay.validateMapping(file.mapping||{});
    if(!validation.valid)throw new Error("DDIO: выберите полную пару MAC + IP для резервации или аренды");
    const candidates=new Map(),index=new Map();
    await visitLocalRowsForAnalysis(file,0,1,(value,detail)=>onProgress(value,`DDIO: ${detail}`),(row)=>{DdioOverlay.collectCandidate(row,file.mapping,changes,candidates);DdioOverlay.collectPossibleIp(row,file.mapping,index);});
    const currentIpByMac=new Map();
    for(const [mac,item] of changes.entries()){const current=switchTracker.get(mac);if(current?.currentIp)currentIpByMac.set(mac,current.currentIp);}
    const overlay=DdioOverlay.buildOverlay(changes,candidates,currentIpByMac);
    candidates.clear();currentIpByMac.clear();
    return{overlay,index,summary:{loaded:true,switchIpChanges:changes.size,newIpHints:Object.keys(overlay).length,ipFallbacks:0}};
  }
  async function seedHistorySwitchChanges(switchTracker,devices){
    if(!BrowserSnapshots?.switchChangesFromHistory)return 0;
    const changes=await BrowserSnapshots.switchChangesFromHistory(devices);
    for(const[mac,item]of changes)DdioOverlay.seedSwitchChange(switchTracker,mac,item.before,item.after,item.currentIp,item.deviceId);
    return changes.size;
  }
  async function localAnalyzeFiles(fields,strategy,onProgress=()=>{}){
    strategy=EnrichmentStrategy.normalize(strategy);
    MemoryGuard.assertStreamingEnrichmentCapacity(state.files,strategy);
    const resolvedDevices=[],identityIndex=new Map(),invalid=[],previousContext=activeLocalDetectionContext,switchTracker=DdioOverlay.createSwitchTracker(),strategyDiagnostics={strategy:EnrichmentStrategy.normalize(strategy),decisions:[],decisionLimit:5000};
    const totalRows=state.files.reduce((total,file)=>total+Math.max(0,Number(file.rowCount??Math.max(0,(file.rows?.length||1)-1))||0),0);
    let processed=0,invalidCount=0;
    activeLocalDetectionContext=createLocalDetectionContext();
    try{
      for(let fileIndex=0;fileIndex<state.files.length;fileIndex++){
        const file=state.files[fileIndex];
        await visitLocalRowsForAnalysis(file,fileIndex,state.files.length,onProgress,(row,rowIndex)=>{
          const result=localDeviceFromRow(file,row,rowIndex,fields);
          processed++;
          if(result.skipped){return;}
          if(result.invalid){
            invalidCount++;if(invalid.length<MemoryGuard.limits.invalidRows)invalid.push(result.invalid);
          }else{
            resolveOrCreateAnalysisDevice(resolvedDevices,identityIndex,result.device,strategy,strategyDiagnostics);
            DdioOverlay.observeSwitch(switchTracker,fileIndex,result.device.mac,result.device.switchIp,result.device.deviceId||result.device.device_id);
            DdioOverlay.observeCurrentIp(switchTracker,result.device.mac,result.device.ip);
          }
          if(processed%2000===0){MemoryGuard.assertTableCapacity(resolvedDevices.length,resolvedDevices.length*8);onProgress(35+(totalRows?processed/totalRows*60:60),`Обработано строк: ${processed.toLocaleString("ru-RU")} / ${totalRows.toLocaleString("ru-RU")}`);}
        });
        await MemoryGuard.yieldToMainThread();
      }
      const devices=resolvedDevices;
      if(state.historyEnrichmentSettings?.enabled!==false&&BrowserSnapshots?.enrichDevicesFromHistory)await BrowserSnapshots.enrichDevicesFromHistory(devices);
      await seedHistorySwitchChanges(switchTracker,devices);
      inferSwitchAddressMappings(devices,"current-file");
      await applyHistoricalSwitchAddressMappings(devices);
      inferSmartroomRoomMappings(devices,"current-file");
      learnLocalRulesFromDevices(devices,2);
      activeLocalDetectionContext=createLocalDetectionContext();
      applyLocalVendorModelMappings(devices);
      const ddio=await buildLocalDdioOverlay(switchTracker,(value,detail)=>onProgress(95+value*0.04,detail));
      ddio.summary.ipFallbacks=DdioOverlay.applyIpFallback(devices,ddio.index);
      state.ddioOverlay=ddio.overlay;state.ddioSummary=ddio.summary;
      if(BrowserSnapshots?.mergeDeviceHistoryRows)await BrowserSnapshots.mergeDeviceHistoryRows(devices,"current-file");
      onProgress(100,`Обработано устройств: ${devices.length.toLocaleString("ru-RU")}`);
      return{devices,invalid,invalidCount,diagnostics:{...strategyDiagnostics,counts:{finalUniqueDevices:devices.length}}};
    }finally{switchTracker.clear();activeLocalDetectionContext=previousContext;}
  }
  async function localAnalyzeFilesToSnapshot(fields,strategy,source,createdAt,onProgress=()=>{}){
    if(!BrowserSnapshots?.mergeEnrichmentRows||!BrowserSnapshots?.saveEnrichmentSnapshot)return null;
    strategy=EnrichmentStrategy.normalize(strategy);
    MemoryGuard.assertStreamingEnrichmentCapacity(state.files,strategy);
    const jobId="enrichment-"+(currentEnrichmentJobId||crypto.randomUUID()),batchSize=750,invalid=[],deviceBatch=new Map(),vendorCounts=new Map(),modelCounts=new Map(),switchTracker=DdioOverlay.createSwitchTracker(),diagnosticCounts={mainRawRows:0,mainNormalizedRows:0,mainUniqueDevices:0,smartroomRawRows:0,smartroomMatched:0,smartroomUnmatched:0,smartroomCreated:0,smartroomConflicts:0,ddioRawRows:Number(state.ddioFile?.rowCount||0),ddioMatched:0,ddioUnmatched:0,ddioCreated:0,previousFinalMatched:0,finalUniqueDevices:0,inventoryTotal:0,emptyRowsSkipped:0};
    const totalRows=state.files.reduce((total,file)=>total+Math.max(0,Number(file.rowCount??Math.max(0,(file.rows?.length||1)-1))||0),0);
    const automaticMappingSources=new Set(["analysis","current-file","inferred","automatic"]),switchAddresses=new Map(localIpMappingRows().filter((item)=>!automaticMappingSources.has(String(item.source||"").toLowerCase())).map((item)=>[normalizeIp(item.switchIp),item.address])),switchAddressCounts=new Map(),smartroomRooms=new Map(Object.entries(state.smartroomMappings||{}));
    let processed=0,invalidCount=0,storedRows=0,previousContext=activeLocalDetectionContext;
    const observe=(map,key,value)=>{if(!key||!value||map.size>=50000&&!map.has(key+"\u0000"+value))return;const item=key+"\u0000"+value;map.set(item,(map.get(item)||0)+1);};
    const observeDevice=(device)=>{const smartroomId=normalizedRoomName(device.smartroomId||device.smartroom_id),mac=normalize(device.mac||device.macFormatted),vendor=String(device.vendor||"").trim(),model=String(device.model||"").trim(),room=normalizedRoomName(device.room);if(mac){for(const length of [6,8,10])if(vendor&&vendor!=="Unknown"&&vendor!=="Не определено")observe(vendorCounts,mac.slice(0,length),vendor);if(model)observe(modelCounts,mac.slice(0,10),model);}if(device.switchIp&&device.address){const ip=normalizeIp(device.switchIp),address=String(device.address).trim();if(ip&&address)observe(switchAddressCounts,ip,address);}if(smartroomId&&room)smartroomRooms.set(smartroomId,room);};
    const flush=async(allowNew,preferExisting=false,stats=null)=>{if(!deviceBatch.size)return;const devices=Array.from(deviceBatch.values());deviceBatch.clear();await BrowserSnapshots.mergeEnrichmentRows(jobId,devices,{allowNew,preferExisting,stats});devices.length=0;await MemoryGuard.yieldToMainThread();};
    const learn=(target,counts,threshold=2)=>{const best=new Map();counts.forEach((count,key)=>{if(count<threshold)return;const split=key.indexOf("\u0000"),prefix=key.slice(0,split),value=key.slice(split+1);if(!prefix||!value||target[prefix])return;const current=best.get(prefix);if(!current||count>current.count)best.set(prefix,{value,count});});let learned=0;best.forEach((item,prefix)=>{target[prefix]=item.value;learned++;});return learned;};
    await BrowserSnapshots.clearEnrichment(jobId).catch(()=>false);
    activeLocalDetectionContext=createLocalDetectionContext();
    try{
      for(let fileIndex=0;fileIndex<state.files.length;fileIndex++){
        const file=state.files[fileIndex],role=EnrichmentStrategy.normalizeRole(file.role||(fileIndex?"smartroom":"primary")),allowNew=EnrichmentStrategy.allowsCreation(role,strategy),fileStats={created:0,matched:0,skipped:0,conflicts:0,invalidIdentity:0};
        await visitLocalRowsForAnalysis(file,fileIndex,state.files.length,onProgress,async(row,rowIndex)=>{
          const result=localDeviceFromRow(file,row,rowIndex,fields);processed++;if(result.skipped){diagnosticCounts.emptyRowsSkipped++;fileStats.skipped++;return;}if(role==="primary")diagnosticCounts.mainRawRows++;else diagnosticCounts.smartroomRawRows++;
          if(result.invalid){invalidCount++;fileStats.invalidIdentity++;if(invalid.length<MemoryGuard.limits.invalidRows)invalid.push(result.invalid);}
          else{
            if(role==="primary")diagnosticCounts.mainNormalizedRows++;
            const device=result.device,storageIdentity=device.internalDeviceId||DeviceIdentity.stableId(device),previous=deviceBatch.get(storageIdentity),merged=mergeAnalysisDevice(previous,device,{preferExisting:Boolean(previous)||fileIndex>0});
            merged.internalDeviceId=previous?.internalDeviceId||storageIdentity;merged.storageIdentity=merged.internalDeviceId;deviceBatch.set(storageIdentity,merged);observeDevice(merged);
            DdioOverlay.observeSwitch(switchTracker,fileIndex,device.mac,device.switchIp,device.deviceId||device.device_id);
            DdioOverlay.observeCurrentIp(switchTracker,device.mac,device.ip);
            if(deviceBatch.size>=batchSize)await flush(allowNew,fileIndex>0,fileStats);
          }
          if(processed%2000===0)onProgress(35+(totalRows?processed/totalRows*45:45),`Потоково обработано строк: ${processed.toLocaleString("ru-RU")} / ${totalRows.toLocaleString("ru-RU")}`);
        });
        await flush(allowNew,true,fileStats);
        if(role==="primary")diagnosticCounts.mainUniqueDevices+=fileStats.created;
        else{diagnosticCounts.smartroomMatched+=fileStats.matched;diagnosticCounts.smartroomCreated+=fileStats.created;diagnosticCounts.smartroomConflicts+=fileStats.conflicts;diagnosticCounts.smartroomUnmatched+=fileStats.created+fileStats.skipped;}
      }
      storedRows=await BrowserSnapshots.countEnrichmentRows(jobId);
      if(state.historyEnrichmentSettings?.enabled!==false&&BrowserSnapshots?.enrichEnrichmentRowsFromHistory)await BrowserSnapshots.enrichEnrichmentRowsFromHistory(jobId);
      const historicalSwitchIps=new Set();
      if(BrowserSnapshots?.streamEnrichmentRows)await BrowserSnapshots.streamEnrichmentRows(jobId,async(rows)=>{for(const device of rows){const switchIp=normalizeIp(device?.switchIp||device?.switch_ip);if(switchIp&&!device.address)historicalSwitchIps.add(switchIp);}if(BrowserSnapshots?.switchChangesFromHistory)await seedHistorySwitchChanges(switchTracker,rows);});
      const historicalAddresses=await historicalSwitchAddressMappings([...historicalSwitchIps]);
      historicalAddresses.forEach((item,ip)=>{if(!switchAddresses.has(ip)&&item?.address)switchAddresses.set(ip,item);});
      const ddio=await buildLocalDdioOverlay(switchTracker,(value,detail)=>onProgress(80+value*0.02,detail));
      state.ddioOverlay=ddio.overlay;state.ddioSummary=ddio.summary;
      const switchConsensus=new Map();
      switchAddressCounts.forEach((count,key)=>{const split=key.indexOf("\u0000"),ip=key.slice(0,split),address=key.slice(split+1),current=switchConsensus.get(ip)||{values:new Map(),total:0};current.values.set(address,count);current.total+=count;switchConsensus.set(ip,current);});
      switchConsensus.forEach((item,ip)=>{if(item.values.size===1&&item.total>=2){const address=item.values.keys().next().value;switchAddresses.set(ip,address);upsertLocalIpMapping(ip,address,"inferred-consensus");}});
      learn(state.localVendorMappings,vendorCounts,2);learn(state.localModelMappings,modelCounts,1);
      activeLocalDetectionContext=createLocalDetectionContext();
      await BrowserSnapshots.transformEnrichmentRows(jobId,(device)=>{
        let changed=false;const ip=normalizeIp(device.switchIp),addressItem=switchAddresses.get(ip),address=typeof addressItem==="string"?addressItem:addressItem?.address,vendor=localVendor(device.mac),model=localModel(device.mac);
        if(!device.ip){const fallbackCount=DdioOverlay.applyIpFallback([device],ddio.index);if(fallbackCount){ddio.summary.ipFallbacks+=fallbackCount;changed=true;}}
        if(address&&!device.address){device.address=address;device.addressSource=addressItem?.source||"switch-address-mapping";if(addressItem?.confidence!==undefined)device.addressConfidence=Number(addressItem.confidence||0);device.fieldSources={...(device.fieldSources||{}),address:device.addressSource};changed=true;}
        const hadRoom=Boolean(normalizedRoomName(device.room));if(synchronizeSmartroomIdentity(device,smartroomRooms)){if(!hadRoom&&device.room)device.roomSource="smartroom_mapping";changed=true;}
        if((!device.vendor||device.vendor==="Unknown"||device.vendor==="Не определено")&&vendor!=="Unknown"){device.vendor=vendor;changed=true;}
        if(!device.model&&model){device.model=model;changed=true;}
        const sourceFiles=Array.from(new Set([...(device.sourceFiles||[]),device.source].filter(Boolean)));const combinedSource=sourceFiles.length===1?sourceFiles[0]:sourceFiles.join(" + ");if(device.source!==combinedSource){device.source=combinedSource;changed=true;}device.sourceFiles=sourceFiles;
        return changed;
      });
      state.smartroomMappings=Object.fromEntries(smartroomRooms);
      const snapshotId=crypto.randomUUID(),name="Анализ: "+source,savedAt=new Date().toISOString(),rowBudget=MemoryGuard.limits.browserSnapshotRows||1000000;
      const metadata=await BrowserSnapshots.saveEnrichmentSnapshot(jobId,{id:snapshotId,name,source,createdAt,savedAt,kind:"analysis",signature:"stream:"+snapshotId},invalid,(count)=>onProgress(82+Math.min(14,Math.round(count/Math.max(1,storedRows)*14)),`Запись результата в локальную базу: ${count.toLocaleString("ru-RU")}`));
      let inventorySyncError="";
      if(BrowserSnapshots?.mergeDeviceHistoryRows){
        try{await BrowserSnapshots.streamSnapshot(snapshotId,(kind,rows)=>kind==="device"?BrowserSnapshots.mergeDeviceHistoryRows(rows,source||"browser-analysis"):0);}
        catch(error){inventorySyncError=String(error?.message||error||"Inventory synchronization failed");}
      }
      const previousBrowserSnapshots=state.snapshots.filter((entry)=>entry.browserStored),keepIds=[snapshotId];
      let remainingRows=Math.max(0,rowBudget-Number(metadata.deviceCount||0));
      for(const [index,item] of previousBrowserSnapshots.entries()){
        const count=Math.max(0,Number(item.deviceCount||0)),mustKeep=index===0;
        if(mustKeep||count<=remainingRows){keepIds.push(item.id);remainingRows=Math.max(0,remainingRows-count);}else item.browserStored=false;
      }
      await BrowserSnapshots.prune(keepIds);
      const page=await BrowserSnapshots.page(snapshotId,{offset:0,limit:resultPageSize});
      const snapshotMetadata={id:snapshotId,name,source,createdAt,savedAt,deviceCount:Number(metadata.deviceCount||0),invalidCount:Number(metadata.invalidCount||invalidCount),devices:[],signature:metadata.signature,kind:"analysis",browserStored:true,devicesTruncated:true,backendStored:false};
      state.snapshots.unshift(snapshotMetadata);state.snapshots=state.snapshots.slice(0,25);
      state.resultSnapshotId="";state.resultBrowserSnapshotId=snapshotId;state.resultBrowserSnapshotDirty=false;state.resultDeviceCount=snapshotMetadata.deviceCount;state.resultInvalidCount=invalidCount;state.resultSummary=page?.summary||null;
      diagnosticCounts.finalUniqueDevices=snapshotMetadata.deviceCount;
      return{streamed:true,devices:(page?.items||[]).filter((item)=>item?.valid!==false&&!item?.invalid),invalid:(page?.items||[]).filter((item)=>item?.valid===false||item?.invalid),invalidCount,deviceCount:snapshotMetadata.deviceCount,summary:page?.summary||null,diagnostics:{strategy,inventorySyncError,counts:diagnosticCounts}};
    }finally{
      deviceBatch.clear();vendorCounts.clear();modelCounts.clear();switchAddressCounts.clear();switchTracker.clear();activeLocalDetectionContext=previousContext;
      await BrowserSnapshots.clearEnrichment(jobId).catch(()=>false);
    }
  }
  function resultHeaderHtml(columns){return columns.map((column)=>{const active=column===resultSortField,direction=active?(resultSortDirection==="desc"?"descending":"ascending"):"none";return `<th class="sortable-column${active?" sorted":""}" data-sort-field="${esc(column)}" data-sort-direction="${active?resultSortDirection:""}" tabindex="0" role="button" aria-sort="${direction}" title="Сортировать по столбцу">${esc(labels[column]||column)}<span class="sort-indicator" aria-hidden="true">${active?(resultSortDirection==="desc"?"▼":"▲"):"↕"}</span></th>`;}).join("");}
  function renderLocalResultsHeader(){const columns=(state.visibleColumns||empty().visibleColumns).filter(Boolean);$("#resultsHeader").innerHTML=resultHeaderHtml(columns);return columns;}
  function updateResultPager(total=0,page=1,pages=1){const status=$("#resultPageStatus"),previous=$("#resultPreviousPageButton"),next=$("#resultNextPageButton"),size=$("#resultPageSizeSelect");if(status)status.textContent=`${page} / ${pages}`;if(previous)previous.disabled=page<=1;if(next)next.disabled=page>=pages;if(size)size.value=String(resultPageSize);resultPage=Math.max(1,Math.min(page,pages));}
  function invalidResultHtml(item,colspan){const title=item.error||"Некорректная строка",where=[item.source&&`файл ${item.source}`,item.row&&`строка ${item.row}`].filter(Boolean).join(" · "),rawMac=item.rawMac?`<div><strong>Исходный MAC:</strong> <code>${esc(item.rawMac)}</code></div>`:"",raw=item.raw?`<div><strong>Исходная строка:</strong> ${esc(item.raw)}</div>`:"";return`<tr class="invalid-result-row"><td colspan="${colspan}"><details><summary><strong>${esc(title)}</strong>${where?` · ${esc(where)}`:""}</summary><div class="invalid-result-details"><div>${esc(item.explanation||"Строка не содержит корректного MAC, серийного номера или Device ID.")}</div>${rawMac}${raw}<div><strong>Как исправить:</strong> ${esc(item.suggestion||"Проверьте сопоставление колонок и исходные значения.")}</div><small>Код: ${esc(item.errorCode||"INVALID_IDENTITY")}</small></div></details></td></tr>`;}
  function localResultPageRows(items,columns){return(items||[]).length?(items||[]).map((item)=>{if(item?.invalid||item?.valid===false)return invalidResultHtml(item,Math.max(1,columns.length));const mac=item.mac||normalize(item.macFormatted)||"",deviceKey=mac||(item.deviceId?`device-id:${String(item.deviceId).trim().toLowerCase()}`:item.internalDeviceId||"");return`<tr data-mac="${esc(mac)}" data-device-key="${esc(deviceKey)}">${columns.map((column)=>`<td>${esc(column==="oui"?formatOuiValue(item.mac||item.macFormatted||item.oui):item[column]||"")}</td>`).join("")}</tr>`;}).join(""):'<tr><td colspan="'+Math.max(1,columns.length)+'" class="empty-state">Нет записей.</td></tr>';}
  function applyDdioOverlayToResults(root,columns){
    const ipIndex=(columns||[]).indexOf("ip"),overlay=state.ddioOverlay||{};
    if(!root||ipIndex<0||!Object.keys(overlay).length)return 0;
    let applied=0;
    for(const row of root.querySelectorAll("tr[data-device-key]")){
      const mac=normalize(row.dataset.mac),key=String(row.dataset.deviceKey||""),hint=overlay[mac||key],cell=row.cells[ipIndex];
      if(!hint?.ip||!cell)continue;
      cell.querySelector(".ddio-new-ip")?.remove();
      const wrapper=document.createElement("span"),warning=document.createElement("span"),underline=document.createElement("u");
      wrapper.className="ddio-new-ip";warning.className="ddio-history-warning";warning.textContent="?";warning.setAttribute("aria-hidden","true");wrapper.append(warning," DDIO: ");underline.textContent=hint.ip;wrapper.append(underline);
      wrapper.title=`IP только для сверки DDIO. Коммутатор: ${hint.previousSwitchIp||"?"} → ${hint.currentSwitchIp||"?"}. Основные данные не изменены.`;
      cell.append(wrapper);cell.classList.add("ddio-highlight-cell");applied++;
    }
    return applied;
  }
  function localSearchText(item){if(!item||typeof item!=="object")return "";if(localSearchTextCache.has(item))return localSearchTextCache.get(item);const text=[item.mac,item.macFormatted,item.vendor,item.model,item.ip,item.address,item.room,item.smartroomId,item.switchIp,item.switchPort,item.hostname,item.serialNumber,item.deviceId,item.deviceName,item.source].map((value)=>String(value||"")).join(" ").toLowerCase();localSearchTextCache.set(item,text);return text;}
  function localResultsTable(){
    const columns=renderLocalResultsHeader(),query=$("#searchInput")?.value.trim().toLowerCase()||"",vendor=$("#vendorFilter")?.value||"",vendors=new Set(),filtered=[];
    for(const item of state.devices||[]){if(item.vendor)vendors.add(item.vendor);if((!vendor||item.vendor===vendor)&&(!query||localSearchText(item).includes(query)))filtered.push(item);}
    if(resultSortField){const direction=resultSortDirection==="desc"?-1:1,compare=window.MacAnalyzerTableSorter?.compareValues||((a,b)=>String(a||"").localeCompare(String(b||""),"ru",{numeric:true}));filtered.sort((a,b)=>{const left=a?.[resultSortField],right=b?.[resultSortField],emptyLeft=!String(left??"").trim(),emptyRight=!String(right??"").trim();return emptyLeft!==emptyRight?(emptyLeft?1:-1):direction*compare(left,right);});}
    const total=filtered.length,pages=Math.max(1,Math.ceil(total/resultPageSize));resultPage=Math.max(1,Math.min(resultPage,pages));const items=filtered.slice((resultPage-1)*resultPageSize,resultPage*resultPageSize);
    $("#vendorFilter").innerHTML='<option value="">Все вендоры</option>'+Array.from(vendors).sort().map(v=>`<option value="${esc(v)}" ${v===vendor?"selected":""}>${esc(v)}</option>`).join("");$("#resultCount").textContent=total+" записей";updateResultPager(total,resultPage,pages);return localResultPageRows(items,columns);
  }
  function devicesSignature(devices=[]){return MemoryGuard.datasetSignature(devices,["vendor","model","ip","address","room","smartroomId","switchIp","switchPort"],normalize);}
  async function storeLocalSnapshot(name,source,devices,invalid=[],createdAt=new Date().toISOString(),kind="analysis"){
    const rows=Array.isArray(devices)?devices:[],snapshotId=crypto.randomUUID(),signature=devicesSignature(rows),savedAt=new Date().toISOString();
    const record={id:snapshotId,name,source,createdAt,savedAt,deviceCount:rows.length,devices:rows,invalid:Array.isArray(invalid)?invalid:[],signature,kind};
    let browserStored=false;
    try{
      if(!BrowserSnapshots)throw new Error("Хранилище локальных снимков недоступно");
      const rowBudget=MemoryGuard.limits.browserSnapshotRows||1000000,keepIds=[];
      let remainingRows=Math.max(0,rowBudget-rows.length);
      for(const item of state.snapshots.filter((entry)=>entry.browserStored)){
        const rowsInSnapshot=Math.max(0,Number(item.deviceCount||0));
        if(rowsInSnapshot<=remainingRows){keepIds.push(item.id);remainingRows-=rowsInSnapshot;}
        else item.browserStored=false;
      }
      await BrowserSnapshots.prune(keepIds);
      await BrowserSnapshots.save(record,(percent)=>{if(activeProcessId)updateProcess(activeProcessId,90+Math.round(Math.min(100,percent)*0.06),`Сохранение снимка порциями: ${percent}%`);});
      browserStored=true;
    }catch(error){
      UiFeedback?.showError(error);
    }
    const previewLimit=MemoryGuard.limits.snapshotPreviewRows||500;
    const metadata={id:snapshotId,name,source,createdAt,savedAt,deviceCount:rows.length,devices:rows.slice(0,previewLimit),invalidCount:record.invalid.length,signature,kind,browserStored,devicesTruncated:rows.length>previewLimit,backendStored:false};
    state.snapshots.unshift(metadata);
    state.snapshots=state.snapshots.slice(0,25);
    if(browserStored&&kind!=="before-analysis"){state.resultSnapshotId="";state.resultBrowserSnapshotId=snapshotId;state.resultBrowserSnapshotDirty=false;state.resultDeviceCount=rows.length;state.resultInvalidCount=record.invalid.length;state.resultSummary=null;}
    return metadata;
  }
  async function loadLocalSnapshotRecord(snapshot){
    if(!snapshot)return null;
    if(snapshot.browserStored&&BrowserSnapshots){const stored=await BrowserSnapshots.load(snapshot.id);if(stored)return stored;}
    return snapshot;
  }
  async function updateCurrentBrowserSnapshot(name,source,transform,onProgress=()=>{}){
    const sourceId=String(state.resultBrowserSnapshotId||"");
    if(!sourceId||!BrowserSnapshots?.updateSnapshotWithTransform)return null;
    const result=await BrowserSnapshots.updateSnapshotWithTransform(sourceId,transform,onProgress,{name,source});
    if(!result.changed)return{...result,updated:false};
    const existingIndex=(state.snapshots||[]).findIndex((item)=>String(item.id)===sourceId),existing=existingIndex>=0?state.snapshots[existingIndex]:{};
    const metadata={...existing,id:sourceId,deviceCount:Number(result.metadata.deviceCount||0),invalidCount:Number(result.metadata.invalidCount||0),devices:[],signature:"",browserStored:true,devicesTruncated:true,backendStored:false,updatedAt:result.metadata.updatedAt||new Date().toISOString(),lastMutationName:name,lastMutationSource:source};
    if(existingIndex>=0)state.snapshots.splice(existingIndex,1,metadata);
    const page=await BrowserSnapshots.page(sourceId,{offset:0,limit:resultPageSize}),items=page?.items||[];
    state.resultSnapshotId="";state.resultBrowserSnapshotId=sourceId;state.resultBrowserSnapshotDirty=false;state.resultDeviceCount=metadata.deviceCount;state.resultInvalidCount=metadata.invalidCount;state.resultSummary=page?.summary||null;
    state.devices=items.filter((item)=>item?.valid!==false&&!item?.invalid);state.invalid=items.filter((item)=>item?.valid===false||item?.invalid);
    browserDashboardCache=null;localAnalyticsCache=null;state.dashboardFleetCache=null;
    return{...result,updated:true,snapshot:metadata};
  }
  function createLocalComparisonIndex(devices=[]){const fields=["vendor","model","ip","address","room","smartroomId","switchIp","switchPort"],index=new Map();for(const device of devices||[]){const mac=normalize(device.mac||device.macFormatted);if(!mac)continue;const values=[];for(const field of fields)values.push(String(device[field]??""));index.set(mac,JSON.stringify(values));}return{fields,index};}
  function ddioHistoryHint(item={}){const field=String(item.field||item.field_name||"");if(field!=="switchIp"&&field!=="switch_ip"&&field!==String(labels.switchIp||""))return null;const mac=normalize(item.mac||item.macFormatted),device=item.afterDevice||item.beforeDevice||{},deviceId=String(device.deviceId||device.device_id||item.deviceId||"").trim().toLowerCase(),overlayKey=mac||(deviceId?`device-id:${deviceId}`:""),storedIp=String(item.ddioCandidateIp||item.ddio_candidate_ip||"").trim(),overlay=overlayKey?(state.ddioOverlay||{})[overlayKey]:null,ip=storedIp||String(overlay?.ip||"").trim();if(!ip)return null;return{ip,possibleIps:Array.from(new Set([...(overlay?.possibleIps||[]),ip].filter(Boolean))),match:String(item.ddioMatch||item.ddio_match||overlay?.match||""),previousSwitchIp:String(item.before??item.from_value??overlay?.previousSwitchIp??""),currentSwitchIp:String(item.after??item.to_value??overlay?.currentSwitchIp??"")};}
  function attachDdioHistoryHint(item){const hint=ddioHistoryHint(item);if(hint){item.ddioCandidateIp=hint.ip;item.ddioMatch=hint.match;}return item;}
  function ddioHistoryBadge(item){const hint=ddioHistoryHint(item);if(!hint)return"";const match=hint.match==="reservation"?"резервация":"аренда",possibleIps=Array.from(new Set((hint.possibleIps||[hint.ip]).filter(Boolean))),title=`DDIO: IP устройства ${possibleIps.join(", ")} (${match}). IP коммутатора: ${hint.previousSwitchIp||"?"} → ${hint.currentSwitchIp||"?"}.`;const badges=possibleIps.map((ip)=>`<span class="ip-badge ip-v${esc(DdioOverlay?.ipVersion?.(ip)||0)}">${esc(ip)}</span>`).join("");return` <details class="possible-ip-dropdown ddio-history-warning"><summary title="${esc(title)}" aria-label="${esc(title)}">❗</summary><div role="note"><strong>IP устройства из DDIO:</strong><span class="ip-badge-list">${badges||"не найден"}</span><small>Источник: DDIO (${esc(match)}). IP коммутатора: ${esc(hint.previousSwitchIp||"?")} → ${esc(hint.currentSwitchIp||"?")}.</small></div></details>`;}
  function mergeDdioOverlayMovements(entries=[],limit=MemoryGuard.limits.movementRows){
    const rows=Array.isArray(entries)?entries:[],switchLabel=String(labels.switchIp||"switchIp");
    for(const [mac,hint] of Object.entries(state.ddioOverlay||{})){
      const before=String(hint?.previousSwitchIp||"").trim(),after=String(hint?.currentSwitchIp||"").trim();
      if(!hint?.ip||!before||!after||before===after)continue;
      let item=rows.find((row)=>normalize(row.mac||row.macFormatted)===normalize(mac)&&["switchIp","switch_ip",switchLabel].includes(String(row.field||row.field_name||""))&&String(row.before??row.from_value??"")===before&&String(row.after??row.to_value??"")===after);
      if(!item&&rows.length<limit){item={mac:normalize(mac),type:"Изменено",field:switchLabel,before,after,beforeDevice:{mac:normalize(mac),switchIp:before},afterDevice:{mac:normalize(mac),switchIp:after}};rows.push(item);}
      if(item){item.ddioCandidateIp=String(hint.ip);item.ddioMatch=String(hint.match||"");}
    }
    return rows;
  }
  function recordLocalMovementsFromIndex(previous,afterDevices=[],source="analysis",changedAt=new Date().toISOString()){
    if(!previous?.index)return recordLocalMovements([],afterDevices,source,changedAt);
    const entries=[],limit=MemoryGuard.limits.movementRows;
    for(const device of afterDevices||[]){const mac=normalize(device.mac||device.macFormatted);if(!mac)continue;const encoded=previous.index.get(mac);if(encoded===undefined){if(entries.length<limit)entries.push({mac,type:"Добавлено",field:"-",before:"",after:device.macFormatted||formatMac(mac),beforeDevice:null,afterDevice:compactDashboardDevice(device)});continue;}previous.index.delete(mac);const before=JSON.parse(encoded),beforeDevice={mac};previous.fields.forEach((field,index)=>{beforeDevice[field]=before[index]||"";});for(let fieldIndex=0;fieldIndex<previous.fields.length&&entries.length<limit;fieldIndex++){const field=previous.fields[fieldIndex],oldValue=String(before[fieldIndex]??"").trim(),next=String(device[field]??"").trim();if(oldValue===next||oldValue&&!next)continue;entries.push({mac,type:"Изменено",field:labels[field]||field,before:oldValue,after:next,beforeDevice,afterDevice:compactDashboardDevice(device)});}}
    if(entries.length<limit)for(const [mac,encoded] of previous.index.entries()){const values=JSON.parse(encoded),beforeDevice={mac};previous.fields.forEach((field,index)=>{beforeDevice[field]=values[index]||"";});entries.push({mac,type:"Удалено",field:"-",before:formatMac(mac),after:"",beforeDevice,afterDevice:null});if(entries.length>=limit)break;}
    mergeDdioOverlayMovements(entries,limit);
    for(const item of entries){item.changedAt=changedAt;item.source=source;attachDdioHistoryHint(item);}
    previous.index.clear();
    state.movementHistory=entries.concat((state.movementHistory||[]).slice(0,Math.max(0,limit-entries.length)));
    return entries.length;
  }
  async function preserveCurrentBeforeAnalysis(source){
    if(!state.devices.length)return false;
    if(backendAvailable)return false;
    if(state.resultBrowserSnapshotId&&state.resultBrowserSnapshotDirty!==true)return false;
    const currentSignature=devicesSignature(state.devices),latest=state.snapshots?.[0];
    if(latest&&latest.signature===currentSignature)return false;
    await storeLocalSnapshot("До анализа: "+(source||"текущие данные"),source||"browser-before-analysis",state.devices,state.invalid,new Date().toISOString(),"before-analysis");
    return true;
  }
  function localComparisonBetweenDevices(beforeDevices=[], afterDevices=[], fields=["vendor","model","ip","address","room","smartroomId","switchIp","switchPort"],limit=MemoryGuard.limits.movementRows){
    const items=[],paired=DeviceIdentity.pairSets(Array.isArray(beforeDevices)?beforeDevices:[],Array.isArray(afterDevices)?afterDevices:[]);
    for(const device of paired.added){if(items.length>=limit)break;const mac=normalize(device?.mac||device?.macFormatted)||"";items.push({mac,type:"Добавлено",field:"-",before:"",after:device.macFormatted||formatMac(mac)||device.deviceId||device.serialNumber||"Устройство",beforeDevice:null,afterDevice:compactDashboardDevice(device)});}
    for(const [previous,device] of paired.pairs){if(items.length>=limit)break;const mac=normalize(device?.mac||device?.macFormatted)||normalize(previous?.mac||previous?.macFormatted)||"";for(const field of fields){const oldValue=String(previous?.[field]??"").trim(),newValue=String(device?.[field]??"").trim();if(oldValue===newValue||oldValue&&!newValue)continue;items.push({mac,type:"Изменено",field:labels[field]||field,before:oldValue,after:newValue,beforeDevice:compactDashboardDevice(previous),afterDevice:compactDashboardDevice(device)});if(items.length>=limit)break;}}
    if(items.length<limit)for(const device of paired.removed){if(items.length>=limit)break;const mac=normalize(device?.mac||device?.macFormatted)||"";items.push({mac,type:"Удалено",field:"-",before:device.macFormatted||formatMac(mac)||device.deviceId||device.serialNumber||"Устройство",after:"",beforeDevice:compactDashboardDevice(device),afterDevice:null});}
    return items;
  }
  function recordLocalMovements(beforeDevices=[], afterDevices=[], source="analysis", changedAt=new Date().toISOString()){
    const entries=localComparisonBetweenDevices(beforeDevices,afterDevices);mergeDdioOverlayMovements(entries);for(const item of entries){item.changedAt=changedAt;item.source=source;attachDdioHistoryHint(item);}
    if(!entries.length)return 0;
    state.movementHistory=entries.concat((state.movementHistory||[]).slice(0,Math.max(0,MemoryGuard.limits.movementRows-entries.length)));
    return entries.length;
  }
  function defaultColumnMapping(){return Object.fromEntries(fieldList.map(([field])=>[field,""]));}
  async function detectColumnsWithBackend(file, options={}) {
    const mode=options.mode||"ai", ai=options.ai!==undefined?Boolean(options.ai):mode==="ai";
    const result=await api("/columns/detect",{method:"POST",body:JSON.stringify({headers:file.headers.map((h)=>h.name),rows:file.rows.slice(1,101),ai,mode})});
    const mapping={...defaultColumnMapping(),...(result.mapping||{})};
    file.columnDetection=result;
    if(ai&&options.review!==false){const reviewed=await showColumnConflictReview(file,result);return reviewed?{...defaultColumnMapping(),...reviewed}:null;}
    return mapping;
  }
  function columnConflictMapping(){const mapping={};$$('[data-conflict-column]').forEach((select)=>{if(select.value!=="")mapping[select.dataset.conflictColumn]=Number(select.value);});return mapping;}
  function resolveColumnConflict(mapping){const context=columnConflictContext;if(!context)return;columnConflictContext=null;$("#columnConflictDialog").close();context.resolve(mapping);}
  function showColumnConflictReview(file,result){
    const review=result.review||{},dialog=$("#columnConflictDialog"),body=$("#columnConflictBody"),status=$("#columnConflictStatus");
    if(!dialog||!body||!review.rowsHtml)return Promise.resolve(result.mapping||{});
    if(columnConflictContext)resolveColumnConflict(null);
    body.innerHTML=review.rowsHtml||review.emptyRowsHtml;const conflicts=(review.conflicts||[]).length,warnings=(review.warnings||[]).length;
    $("#columnConflictSubtitle").textContent=`${file.name}: конфликтов ${conflicts}, предупреждений ${warnings}.`;
    status.textContent="MAC-адрес является обязательным полем. Изменения применятся только после подтверждения.";
    dialog.showModal();
    return new Promise((resolve)=>{columnConflictContext={file,result,resolve};});
  }
  function autoSelectConflictColumns(){$$('[data-conflict-field]').forEach((row)=>{const select=row.querySelector('[data-conflict-column]'),index=row.dataset.aiIndex;if(select)select.value=index!==""?index:"";});$("#columnConflictStatus").textContent="Рекомендации AI выбраны. Проверьте MAC и нажмите «Применить».";}
  function applyColumnConflictSelection(){const mapping=columnConflictMapping();if(mapping.mac===undefined){$("#columnConflictStatus").textContent="Выберите обязательную колонку MAC-адреса.";const macSelect=$('[data-conflict-column="mac"]');macSelect?.focus();return;}resolveColumnConflict(mapping);}
  async function refreshMappingSummary(file) {
    if(!file)return null;
    const fields=Object.fromEntries($$("[data-field]").map((input)=>[input.dataset.field,input.checked]));
    const result=await api("/mapping/summary",{method:"POST",body:JSON.stringify({headers:file.headers.map((h)=>h.name),mapping:file.mapping||{},fields})});
    file.mappingSummary=result;
    renderColumnDetectionSummary(file);
    return result;
  }  function renderColumnDetectionSummary(file) {
    const root=$("#columnDetectionSummary");
    if(!root)return;
    const result=file?.columnDetection, summary=file?.mappingSummary;
    if(!file){root.innerHTML="";return;}
    root.innerHTML=(summary?.summaryHtml||"")+(result?.detectorHtml||"");
  }
  async function clientFileRecord(file,fileCreatedAt,onProgress=()=>{}){
    MemoryGuard.assertImportCapacity(file,state.files);
    const data=await clientReadTable(file,onProgress,{maxRows:workspacePreviewDataRows}),rows=[data.headers||[],...(data.rows||[])];
    if(rows.length<2)throw new Error("файл не содержит строк данных");
    const headers=rows[0].map((name,index)=>({name:String(name||headerName(index)),index}));
    const rowCount=Math.max(0,Number(data.rowCount??rows.length-1)||0),previewRows=rows.slice(0,workspacePreviewDataRows+1);
    const fileRecord={id:crypto.randomUUID(),name:file.name,sheet:data.sheet||"",rows:previewRows,headers,mapping:localAutoMapping(rows[0]),createdAt:fileCreatedAt,fileLastModified:file.lastModified||0,sourceBytes:file.size||0,clientImported:true,rowCount,rowsComplete:data.truncated!==true&&rowCount<=workspacePreviewDataRows};
    localMappingSummary(fileRecord);
    return fileRecord;
  }
  async function backendFileRecord(file,fileCreatedAt,onProgress=()=>{}){
    onProgress(5,"Передача файла в backend без копии Base64");
    const data=await api("/files/import-binary",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name),"X-Sheet-Name":"","X-Preview-Rows":"100"},body:file});
    onProgress(75,"Backend прочитал таблицу");
    const rows=[data.headers||[],...(data.rows||[])];
    if(rows.length<2)throw new Error("файл не содержит строк данных");
    const headers=rows[0].map((name,index)=>({name:String(name||headerName(index)),index}));
    const fileRecord={id:crypto.randomUUID(),name:file.name,sheet:data.sheet||"",rows,headers,mapping:defaultColumnMapping(),createdAt:fileCreatedAt,fileLastModified:file.lastModified||0,sourceBytes:file.size||0,fileToken:data.fileToken||"",rowCount:Number(data.rowCount??data.rows?.length??0),rowsComplete:data.compactResult!==true};
    try{onProgress(85,"Автоопределение колонок");fileRecord.mapping=await detectColumnsWithBackend(fileRecord,{mode:"auto",ai:false});await refreshMappingSummary(fileRecord);}catch(error){fileRecord.columnDetection={mapping:fileRecord.mapping,warnings:[{field:"backend",message:error.message}]};}
    onProgress(100,"Файл обработан backend");
    return fileRecord;
  }
  function ddioMappingOptions(file,selected){
    const options=['<option value="">Не использовать</option>'];
    for(const header of file?.headers||[]){const isSelected=selected!==""&&selected!==undefined&&selected!==null&&Number(selected)===Number(header.index);options.push(`<option value="${header.index}"${isSelected?" selected":""}>${esc(mappingOptionLabel(header,"letter"))}</option>`);}
    return options.join("");
  }
  function renderDdioPanel(){
    const file=state.ddioFile,summary=$("#ddioFileSummary"),grid=$("#ddioMappingGrid"),clearButton=$("#clearDdioFileButton"),overlaySummary=$("#ddioOverlaySummary");
    if(!summary||!grid)return;
    clearButton.hidden=!file;
    grid.hidden=!file;
    if(!file){summary.textContent="Файл DDIO не выбран.";grid.innerHTML="";if(overlaySummary)overlaySummary.textContent="";return;}
    const validation=DdioOverlay.validateMapping(file.mapping||{});
    summary.textContent=`${file.name} · строк: ${Number(file.rowCount||0).toLocaleString("ru-RU")} · ${validation.valid?"колонки готовы":"проверьте сопоставление колонок"}`;
    const fields=[["deviceId","Device ID"],["reservationMac","MAC резервации"],["reservationIp","IP резервации"],["leaseMac","MAC аренды"],["leaseIp","IP аренды"],["possibleIps","Возможные IP"]];
    grid.innerHTML=fields.map(([field,title])=>`<label>${title}<select data-ddio-map="${field}">${ddioMappingOptions(file,file.mapping?.[field]??((field==="reservationIp"||field==="leaseIp")?file.mapping?.ip:""))}</select></label>`).join("");
    const hints=Number(state.ddioSummary?.newIpHints||Object.keys(state.ddioOverlay||{}).length),changes=Number(state.ddioSummary?.switchIpChanges||0);
    if(overlaySummary)overlaySummary.textContent=state.ddioSummary?`Смен коммутатора: ${changes} · новых IP: ${hints}`:"Подсказки появятся после анализа.";
  }
  async function clearDdioFile(){
    const file=state.ddioFile;
    if(file?.fileToken&&backendAvailable)await api("/workspace/cache/discard",{method:"POST",body:JSON.stringify({tokens:[file.fileToken]})}).catch(()=>{});
    if(file?.id)sourceFilesById.delete(file.id);
    state.ddioFile=null;state.ddioOverlay={};state.ddioSummary=null;
    await pruneStoredSourceFiles();save({immediate:true});renderDdioPanel();renderResults();
  }
  let ddioLoadRevision=0;
  async function loadDdioFile(input,sourceInput=null){
    const file=Array.from(input||[])[0];
    if(!file)return;
    const revision=++ddioLoadRevision,loadingToken=UiFeedback?.start("Загрузка DDIO…");
    const processId=beginProcess("Загрузка DDIO","Чтение третьей выгрузки",5);
    try{
      if(state.ddioFile)await clearDdioFile();
      let fileRecord=null;
      const progress=(value,detail)=>updateProcess(processId,processPercent(value),file.name+": "+detail);
      if(backendAvailable)try{fileRecord=await backendFileRecord(file,fileInfoDate(file),progress);}catch(error){if(networkUnavailable(error))setBackendStatus(false,"Автономный HTML-режим · DDIO обрабатывается в браузере");else throw error;}
      if(!fileRecord)fileRecord=await clientFileRecord(file,fileInfoDate(file),progress);
      if(revision!==ddioLoadRevision)return;
      fileRecord.role="ddio";
      fileRecord.mapping=DdioOverlay.detectMapping(fileRecord.headers||[]);
      if(fileRecord.clientImported)await rememberSourceFile(fileRecord,file);else{sourceFilesById.delete(fileRecord.id);fileRecord.sourceStorageId="";}
      state.ddioFile=fileRecord;state.ddioOverlay={};state.ddioSummary=null;
      save({immediate:true});renderDdioPanel();
      finishProcess(processId,`DDIO загружен: ${Number(fileRecord.rowCount||0).toLocaleString("ru-RU")} строк`);
      toast("DDIO загружен. Проверьте отдельные пары MAC + IP резервации и аренды.");
    }catch(error){failProcess(processId,error);UiFeedback?.showError(error);toast("Не удалось загрузить DDIO: "+error.message);}
    finally{UiFeedback?.stop(loadingToken);if(sourceInput)sourceInput.value="";}
  }
  async function loadFiles(input, sourceInput=null, requestedRole="auto") {
    const files=Array.from(input||[]);
    if(!files.length)return;
    state.files=normalizeFileRoles(state.files);
    if(["smartroom","enrichment"].includes(requestedRole)&&!state.files.some((file)=>file.role==="primary")){
      const message="Сначала добавьте файл №1 — основной, затем выберите файл №2 — SmartRoom.";
      if($("#analysisStatus"))$("#analysisStatus").textContent=message;
      if($("#fileImportStatus"))$("#fileImportStatus").textContent=message;
      if(sourceInput)sourceInput.value="";
      toast(message);
      return;
    }
    const replacedEnrichmentFiles=await replaceConsumedEnrichmentFiles(requestedRole);
    state.importErrors=[];
    state.ddioOverlay={};state.ddioSummary=null;
    await releaseRetainedWorkspaceRows();
    await releaseTransientAnalysisMemory();
    const processId=beginProcess("Загрузка файлов","Подготовка списка файлов",2);
    const status=$("#analysisStatus");
    const importStatus=$("#fileImportStatus");
    if(status)status.textContent="Загрузка файлов...";
    if(importStatus)importStatus.textContent=(replacedEnrichmentFiles?`Предыдущих файлов перенесено в историю: ${replacedEnrichmentFiles}. `:"")+"Чтение файлов: "+files.map((file)=>file.name).join(", ");
    const primaryAlreadySelected=state.files.some((file)=>file.role==="primary");
    const pendingBatch=files.map((file,fileIndex)=>({id:"pending-"+crypto.randomUUID(),name:file.name,role:["smartroom","enrichment"].includes(requestedRole)||requestedRole==="primary"&&fileIndex>0||requestedRole==="auto"&&(primaryAlreadySelected||fileIndex>0)?"smartroom":"primary"}));
    pendingFileImports=[...pendingFileImports,...pendingBatch];
    renderFiles();
    let imported=0;
    for (const [fileIndex,file] of files.entries()) {
      const pendingId=pendingBatch[fileIndex]?.id;
      const fileCreatedAt=fileInfoDate(file);
      let fileRecord=null,backendError=null;
      const fileProgress=(value,detail)=>updateProcess(processId,((fileIndex+processPercent(value)/100)/files.length)*100,file.name+": "+detail);
      try {
        fileProgress(1,"начало чтения");
        if(backendAvailable)try{fileRecord=await backendFileRecord(file,fileCreatedAt,fileProgress);}catch(error){backendError=error;if(networkUnavailable(error))setBackendStatus(false,"Автономный HTML-режим · файлы обрабатываются в браузере");}
        if(!fileRecord)fileRecord=await clientFileRecord(file,fileCreatedAt,fileProgress);
        if(fileRecord.clientImported)await rememberSourceFile(fileRecord,file);
        else{sourceFilesById.delete(fileRecord.id);fileRecord.sourceStorageId="";}
        insertImportedFile(fileRecord,requestedRole,fileIndex);
        imported++;
        ensureMappingSelection();
        pendingFileImports=pendingFileImports.filter((item)=>item.id!==pendingId);
        renderFiles();
        renderMapping();
        save();
        if(fileRecord.clientImported&&!backendAvailable)setBackendStatus(false,"Автономный HTML-режим · XLSX/CSV обрабатываются в браузере");
        if(importStatus)importStatus.textContent=`Загружен ${fileRecord.role==="primary"?"файл №1 — основной":"файл №2 — SmartRoom"}: ${file.name} · строк: ${fileRecord.rowCount}`;
        fileProgress(100,"загружен, строк: "+fileRecord.rowCount);
      } catch(localError) {
        const details=backendError&&!networkUnavailable(backendError)?` (backend: ${backendError.message})`:"";
        const message="Не удалось прочитать "+file.name+": "+localError.message+details;
        state.importErrors.push({filename:file.name,message});
        pendingFileImports=pendingFileImports.filter((item)=>item.id!==pendingId);
        renderFiles();
        toast(message);
        fileProgress(100,"ошибка чтения");
      }
    }
    ensureMappingSelection();
    if(sourceInput)sourceInput.value="";
    if(status)status.textContent=imported?"Загружено файлов: "+imported+(state.importErrors.length?", ошибок: "+state.importErrors.length:""):"Файл не загружен";
    if(importStatus)importStatus.textContent=imported?"Загружено файлов: "+imported+(state.importErrors.length?", ошибок: "+state.importErrors.length:""):"Файл не загружен. "+((state.importErrors||[])[0]?.message||"Проверьте формат файла.");
    save({immediate:true}); await flushBrowserStateSave().catch(()=>{}); renderAll();
    const resultText=imported?"Загружено файлов: "+imported+(state.importErrors.length?", ошибок: "+state.importErrors.length:""):"Файлы не загружены";
    if(imported)finishProcess(processId,resultText,state.importErrors.length?"warning":"complete");else failProcess(processId,(state.importErrors||[])[0]?.message||"Проверьте формат файлов");
  }
  async function fileToBase64(file){
    const bytes=new Uint8Array(await file.arrayBuffer());
    let binary="",chunkSize=0x8000;
    for(let offset=0;offset<bytes.length;offset+=chunkSize)binary+=String.fromCharCode(...bytes.subarray(offset,offset+chunkSize));
    return btoa(binary);
  }
  async function renderSingleMappingGrid(){
    const root=$("#singleMappingGrid");
    if(!root)return;
    const headers=pendingSingleFilePreview?.headers||[];
    if(browserOnlyMode){
      if(!headers.length){root.innerHTML='<p class="muted">Колонки появятся после выбора файла.</p>';return;}
      const names=headers.map((header)=>typeof header==="object"?String(header.name||""):String(header||""));
      const auto=localAutoMapping(names);
      root.innerHTML=fieldList.map(([field,title])=>`<label>${esc(title)}<select data-single-map="${field}"><option value="">Не выбрано</option>${names.map((name,index)=>`<option value="${index}" ${Number(auto[field])===index?"selected":""}>${esc(name||headerName(index))}</option>`).join("")}</select></label>`).join("");
      return;
    }
    try{
      const data=await api("/workspace/single-mapping-grid",{method:"POST",body:JSON.stringify({headers})});
      root.innerHTML=data.singleMappingGridHtml||'<p class="muted">Колонки появятся после выбора файла.</p>';
    }catch(error){
      root.innerHTML='<p class="muted">Сопоставление одного файла недоступно: '+esc(error.message)+'</p>';
    }
  }
  function singleManualMapping(){
    if(!$("#singleManualMappingToggle")?.checked)return null;
    const mapping={};
    $$("[data-single-map]").forEach((select)=>{if(select.value!=="")mapping[select.dataset.singleMap]=Number(select.value);});
    return mapping;
  }
  async function renderSinglePreview(headers=[],rows=[],invalid=[]){
    const head=$("#singlePreviewHead"),body=$("#singlePreviewBody"),count=$("#singlePreviewCount");
    if(!head||!body)return;
    if(browserOnlyMode){
      const names=(headers||[]).map((header)=>typeof header==="object"?String(header.name||""):String(header||""));
      head.innerHTML="<tr>"+names.map((name,index)=>`<th>${esc(name||headerName(index))}</th>`).join("")+"</tr>";
      const preview=(rows||[]).slice(0,100);
      body.innerHTML=preview.length?preview.map((row)=>"<tr>"+names.map((_name,index)=>`<td>${esc(row?.[index]??"")}</td>`).join("")+"</tr>").join(""):'<tr><td class="empty-state" colspan="'+Math.max(1,names.length)+'">Нет строк для предпросмотра.</td></tr>';
      if(count)count.textContent=`Показано ${preview.length} строк · ошибок ${invalid.length}`;
      return;
    }
    try{
      const data=await api("/single-file/preview",{method:"POST",body:JSON.stringify({headers,rows,invalid})});
      head.innerHTML=data.previewHeadHtml||"";
      body.innerHTML=data.previewBodyHtml||"";
      if(count)count.textContent=data.previewCountText||"";
    }catch(error){
      head.innerHTML="<tr><th>Ошибка</th></tr>";
      body.innerHTML='<tr><td class="empty-state">Предпросмотр недоступен: '+esc(error.message)+'</td></tr>';
      if(count)count.textContent="";
    }
  }
  function renderSingleReport(result){
    const summary=result?.summary||{},mode=$("#singleFileMode");
    if(mode)mode.textContent=result?.mappingMode==="manual"?"Ручное":"Авто";
    const root=$("#singleFileSummary");
    if(root){
      root.innerHTML=result?.summaryHtml||"";
    }
    const detected=$("#singleDetectedColumns");
    if(detected){
      detected.innerHTML=result?.detectedColumnsHtml||'<p class="muted">Колонки не определены.</p>';
    }
    if(result?.previewHeadHtml&&result?.previewBodyHtml){
      $("#singlePreviewHead").innerHTML=result.previewHeadHtml;
      $("#singlePreviewBody").innerHTML=result.previewBodyHtml;
      const count=$("#singlePreviewCount"); if(count)count.textContent=result.previewCountText||"";
    }else{
      renderSinglePreview(result?.preview?.headers||result?.headers||[],result?.preview?.rows||result?.rows||[],result?.invalid||[]);
    }
  }
  async function inspectSingleFile(){
    if(!pendingSingleFile){pendingSingleFilePreview=null;renderSingleMappingGrid();renderSinglePreview();return;}
    const status=$("#singleFileStatus");
    const processId=beginProcess("Чтение одного файла",pendingSingleFile.name,5);
    try{
      status.textContent="Чтение файла...";
      updateProcess(processId,15,"Подготовка "+pendingSingleFile.name);
      MemoryGuard.assertImportCapacity(pendingSingleFile);
      if(browserOnlyMode){
        updateProcess(processId,35,"Чтение файла локальным XLSX/CSV-модулем");
        const data=await clientReadTable(pendingSingleFile,(value,detail)=>updateProcess(processId,35+processPercent(value)*0.45,detail));
        const previewRows=(data.rows||[]).slice(0,100);
        pendingSingleFilePreview={headers:data.headers||[],rows:previewRows,rowCount:(data.rows||[]).length,sourceName:pendingSingleFile.name,sourceBytes:pendingSingleFile.size||0};
        renderSingleMappingGrid();
        renderSinglePreview(data.headers||[],previewRows,[]);
        status.textContent="Файл выбран: "+pendingSingleFile.name+" · строк: "+(data.rows||[]).length;
        data.rows.length=0;
        finishProcess(processId,"Файл прочитан локально");
        return;
      }
      updateProcess(processId,35,"Бинарная передача файла без Base64-копии");
      const data=await api("/files/import-binary",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(pendingSingleFile.name),"X-Sheet-Name":encodeURIComponent($("#singleSheetInput")?.value||""),"X-Preview-Rows":"100"},body:pendingSingleFile});
      updateProcess(processId,82,"Построение предпросмотра");
      pendingSingleFilePreview={...data,sourceName:pendingSingleFile.name,sourceBytes:pendingSingleFile.size||0};
      renderSingleMappingGrid();
      renderSinglePreview(data.headers||[],data.rows||[],[]);
      status.textContent="Файл выбран: "+pendingSingleFile.name+" · строк: "+((data.rows||[]).length);
      finishProcess(processId,"Файл прочитан, строк: "+((data.rows||[]).length));
    }catch(error){
      pendingSingleFilePreview=null;
      renderSingleMappingGrid();
      status.textContent="Ошибка чтения: "+error.message;
      toast(error.message);
      failProcess(processId,error);
    }
  }
  async function analyzeSingleFile(){
    state.ddioOverlay={};state.ddioSummary=null;
    if(!pendingSingleFile)return toast("Сначала выберите файл.");
    const status=$("#singleFileStatus");
    let previousDevices=state.devices||[];
    const fileCreatedAt=fileInfoDate(pendingSingleFile);
    const processId=beginProcess("Анализ одного файла",pendingSingleFile.name,5);
    try{
      status.textContent="Анализ выполняется...";
      updateProcess(processId,15,"Подготовка файла");
      MemoryGuard.assertImportCapacity(pendingSingleFile);
      if(browserOnlyMode){
        const fileRecord=await clientFileRecord(pendingSingleFile,fileCreatedAt,(value,detail)=>updateProcess(processId,15+processPercent(value)*0.2,detail));
        const manual=singleManualMapping();
        if(manual)fileRecord.mapping={...fileRecord.mapping,...manual};
        state.files=[{...fileRecord,role:"primary"}];
        await rememberSourceFile(state.files[0],pendingSingleFile);
        await MemoryGuard.yieldToMainThread();
        const previousIndex=createLocalComparisonIndex(previousDevices);
        previousDevices=[];
        const fields={vendor:true,model:true,ip:true,address:true,room:true,smartroomId:true,switchIp:true,switchPort:true,history:true};
        const local=await localAnalyzeFiles(fields,"primary",(value,detail)=>updateProcess(processId,35+processPercent(value)*0.5,detail));
        clearResultReference();
        state.devices=SmartroomStore?await SmartroomStore.enrichData(local.devices,{registry:IeeeRegistry}):local.devices;
        state.invalid=local.invalid;
        state.lastAnalysis=fileCreatedAt;
        recordLocalMovementsFromIndex(previousIndex,state.devices,pendingSingleFile.name,state.lastAnalysis);
        await storeLocalSnapshot("Single file: "+pendingSingleFile.name,pendingSingleFile.name,state.devices,state.invalid,state.lastAnalysis,"single-file");
        const result={
          mappingMode:manual?"manual":"auto",
          summaryHtml:`<div class="bar-label"><span>Устройств</span><strong>${state.devices.length}</strong></div><div class="bar-label"><span>Ошибок MAC</span><strong>${state.invalid.length}</strong></div>`,
          detectedColumnsHtml:fileRecord.mappingSummary?.summaryHtml||'<p class="muted">Колонки определены локально.</p>',
          headers:fileRecord.headers.map((item)=>item.name),
          rows:fileRecord.rows.slice(1,101),
          invalid:state.invalid,
        };
        save({immediate:true});
        await flushBrowserStateSave().catch(()=>{});
        await flushPortableDatabaseSave().catch(()=>{});
        renderAll();renderSingleReport(result);view("single");
        status.textContent="Готово: "+state.devices.length+" устройств, ошибок: "+state.invalid.length;
        finishProcess(processId,"Локально проанализировано устройств: "+state.devices.length);
        toast("Один файл проанализирован без backend.");
        return;
      }
      let fileToken=pendingSingleFilePreview?.sourceName===pendingSingleFile.name?pendingSingleFilePreview.fileToken||"":"";
      if(!fileToken){
        const imported=await api("/files/import-binary",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(pendingSingleFile.name),"X-Sheet-Name":encodeURIComponent($("#singleSheetInput")?.value||""),"X-Preview-Rows":"100"},body:pendingSingleFile});
        pendingSingleFilePreview={...imported,sourceName:pendingSingleFile.name,sourceBytes:pendingSingleFile.size||0};
        fileToken=imported.fileToken||"";
      }
      updateProcess(processId,30,"Определение колонок и MAC-адресов");
      const result=await api("/single-file/analyze",{method:"POST",body:JSON.stringify({filename:pendingSingleFile.name,fileToken,sheet:$("#singleSheetInput")?.value||"",mapping:singleManualMapping(),createdAt:fileCreatedAt,saveHistory:true,saveSnapshot:true,compactResult:true,resultPageSize})});
      updateProcess(processId,76,"Сохранение результатов и истории");
      const headers=result.headers.map((name,index)=>({name,index}));
      state.files=[{id:crypto.randomUUID(),name:pendingSingleFile.name,role:"primary",rows:[result.headers,...result.rows],headers,mapping:result.mapping,createdAt:fileCreatedAt,fileLastModified:pendingSingleFile.lastModified||0,sourceBytes:pendingSingleFile.size||0,fileToken,rowCount:Number(result.rowCount??result.rows?.length??0),rowsComplete:result.rowsComplete!==false,columnDetection:result.detection}];
      await rememberSourceFile(state.files[0],pendingSingleFile);
      clearResultReference();
      state.devices=result.devices||[];
      state.invalid=result.invalid||[];
      state.lastAnalysis=fileCreatedAt;
      const resultReference=result.resultReference||{};
      if(result.compactResult){state.resultSnapshotId=String(resultReference.snapshotId||result.snapshot?.id||"");state.resultDeviceCount=Number(resultReference.deviceCount||0);state.resultInvalidCount=Number(resultReference.invalidCount||0);state.resultSummary=result.resultSummary||result.resultPage?.summary||null;}
      if(!state.resultSnapshotId)recordLocalMovements(previousDevices,state.devices,pendingSingleFile.name,state.lastAnalysis);
      if(result.snapshot?.id){state.snapshots.unshift({id:result.snapshot.id,name:"Single file: "+pendingSingleFile.name,source:pendingSingleFile.name,createdAt:result.snapshot.createdAt||state.lastAnalysis,deviceCount:Number(resultReference.deviceCount||state.devices.length),devices:[],backendStored:true});state.snapshots=state.snapshots.slice(0,25);}
      else await storeLocalSnapshot("Single file: "+pendingSingleFile.name,pendingSingleFile.name,state.devices,state.invalid,state.lastAnalysis,"single-file");
      save();persistAutosave("single-file-analysis").catch(()=>{});renderAll();renderSingleReport(result);view("single");
      status.textContent="Готово: "+(result.progress?.valid||state.devices.length)+" устройств, ошибок: "+(result.progress?.invalid||state.invalid.length);
      finishProcess(processId,"Проанализировано устройств: "+state.devices.length);
      toast("Один файл проанализирован.");
    }catch(error){
      status.textContent="Ошибка: "+error.message;
      toast(error.message);
      failProcess(processId,error);
    }
  }
  function localFileListHtml(){
    const grouped=(role,title)=>{const files=state.files.filter((file,index)=>fileRole(file,index)===role),pending=pendingFileImports.filter((file)=>file.role===role);return `<section class="file-group" data-file-group="${role}"><div class="file-group-head"><strong>${title}</strong><span>${files.length+pending.length}</span></div>${files.map(file=>`<div class="file-row" data-file-id="${esc(file.id)}" data-file-role="${role}"><span><strong>${esc(file.name)}</strong><small>${Number(file.rowCount??Math.max(0,(file.rows?.length||1)-1))} строк · ${file.clientImported?"браузер":"backend"} · дата файла: ${esc(file.createdAt?new Date(file.createdAt).toLocaleString("ru-RU"):"")}</small></span><button data-remove-file="${esc(file.id)}">×</button></div>`).join("")}${pending.map(file=>`<div class="file-row file-row-pending" data-file-role="${role}" aria-busy="true"><span><strong>${esc(file.name)}</strong><small>Чтение Excel в браузере...</small></span><span class="file-loading-indicator">...</span></div>`).join("")||(!files.length?'<span class="muted">'+(role==="primary"?'Файл №1 — основной не выбран':'Файл №2 — SmartRoom не добавлен')+'</span>':"")}</section>`;};
    const errors=(state.importErrors||[]).map((item)=>'<div class="import-error"><strong>'+esc(item.filename||"Файл")+'</strong><span>'+esc(item.message||"Ошибка импорта")+'</span></div>').join("");
    return grouped("primary","Файл №1 — основной")+grouped("smartroom","Файл №2 — SmartRoom")+errors;
  }
  function workspaceFileSummary(file){return{id:file.id,name:file.name,role:file.role,createdAt:file.createdAt||"",fileDate:file.fileDate||"",sourceBytes:Number(file.sourceBytes||0),rowCount:Number(file.rowCount??Math.max(0,(file.rows?.length||1)-1)),fileToken:file.fileToken||""};}
  function workspaceMappingPayload(file){if(!file)return null;return{id:file.id,name:file.name,role:file.role,headers:file.headers||[],mapping:file.mapping||{},mappingDisplayMode:file.mappingDisplayMode||state.mappingDisplayMode||"name"};}
  function paintLocalFileList(root){root.innerHTML=localFileListHtml();root.querySelectorAll("[data-file-id]").forEach((row)=>row.classList.toggle("active-file",row.dataset.fileId===state.activeMappingFileId));}
  async function renderFiles() {
    const root=$("#fileList"); if(!root)return;
    renderDdioPanel();
    const renderVersion=++fileRenderVersion;
    state.files=normalizeFileRoles(state.files);
    const primaryCount=state.files.filter((file,index)=>fileRole(file,index)==="primary").length;
    const smartroomCount=state.files.filter((file,index)=>fileRole(file,index)==="smartroom").length;
    if($("#primaryFileSummary"))$("#primaryFileSummary").textContent=primaryCount?"Основной файл выбран":"Основной файл не выбран";
    if($("#enrichmentFileSummary"))$("#enrichmentFileSummary").textContent="Файлов SmartRoom: "+smartroomCount;
    paintLocalFileList(root);
    if(pendingFileImports.length||!backendAvailable)return;
    try{
      const data=await api("/workspace/files",{method:"POST",body:JSON.stringify({files:state.files.map(workspaceFileSummary)})});
      if(renderVersion!==fileRenderVersion)return;
      const errors=(state.importErrors||[]).map((item)=>'<div class="import-error"><strong>'+esc(item.filename||"Файл")+'</strong><span>'+esc(item.message||"Ошибка импорта")+'</span></div>').join("");
      root.innerHTML=(data.fileRowsHtml||data.emptyFilesHtml||'<span class="muted">Файлы пока не добавлены</span>')+errors;
    }catch(error){
      if(renderVersion===fileRenderVersion)paintLocalFileList(root);
    }
    root.querySelectorAll("[data-file-id]").forEach((row)=>row.classList.toggle("active-file",row.dataset.fileId===state.activeMappingFileId));
  }
  async function renderMapping() {
    renderMappingControls();
    const root=$("#mappingGrid"),file=selectedMappingFile()||state.files[0];
    const renderVersion=++mappingRenderVersion;
    if(file)file.mappingDisplayMode=state.mappingDisplayMode||"name";
    root.innerHTML=localMappingGrid(file);
    const source=$("#customColumnSource");
    if(source)source.innerHTML=file?'<option value="">Колонка файла</option>'+file.headers.map((header)=>`<option value="${header.index}">${esc(mappingOptionLabel(header))}</option>`).join(""):'<option value="">Колонка файла</option>';
    if(file)localMappingSummary(file);else renderColumnDetectionSummary(null);
    if(!backendAvailable)return;
    try{
      const data=await api("/workspace/mapping-grid",{method:"POST",body:JSON.stringify({file:workspaceMappingPayload(file)})});
      if(renderVersion!==mappingRenderVersion)return;
      root.innerHTML=data.mappingGridHtml||'<p class="muted">Добавьте основной файл, чтобы настроить колонки.</p>';
      $("#customColumnSource").innerHTML=data.customColumnOptionsHtml||'<option value="">Колонка файла</option>';
      renderColumnDetectionSummary(file||null);
    }catch(error){
      if(renderVersion===mappingRenderVersion){root.innerHTML=localMappingGrid(file);if(file)localMappingSummary(file);else renderColumnDetectionSummary(null);}
    }
  }
  function sourceFilesPayload(compact=true){
    return state.files.map((file)=>{
      if(!compact||!file.fileToken)return file;
      return {id:file.id,name:file.name,role:file.role,sheet:file.sheet||"",mapping:file.mapping||{},createdAt:file.createdAt||"",sourceBytes:Number(file.sourceBytes||0),fileToken:file.fileToken,rowCount:Number(file.rowCount??Math.max(0,(file.rows?.length||1)-1))};
    });
  }
  function ddioFilePayload(compact=true){
    const file=state.ddioFile;
    if(!file)return null;
    if(!compact||!file.fileToken)return file;
    return {id:file.id,name:file.name,role:"ddio",sheet:file.sheet||"",mapping:file.mapping||{},createdAt:file.createdAt||"",sourceBytes:Number(file.sourceBytes||0),fileToken:file.fileToken,rowCount:Number(file.rowCount??Math.max(0,(file.rows?.length||1)-1))};
  }
  function analysisFileRecords(){return [...(state.files||[]),...(state.ddioFile?[state.ddioFile]:[])];}
  async function uploadWorkspaceFilesToCache(fileRecords,onProgress=()=>{}){
    const records=Array.isArray(fileRecords)?fileRecords:[];
    for(const [index,fileRecord] of records.entries()){
      const sourceFile=await restoreSourceFile(fileRecord);
      if(!sourceFile)throw new Error(`Кэш файла «${fileRecord.name}» недоступен. Выберите этот файл снова.`);
      onProgress(Math.round((index/Math.max(1,records.length))*100),`Повторная загрузка ${fileRecord.name}`);
      const data=await api("/files/import-binary",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(sourceFile.name),"X-Sheet-Name":encodeURIComponent(fileRecord.sheet||""),"X-Preview-Rows":"100"},body:sourceFile});
      fileRecord.fileToken=data.fileToken||"";
      fileRecord.rows=[data.headers||[],...(data.rows||[])];
      fileRecord.headers=(data.headers||[]).map((name,columnIndex)=>({name:String(name||headerName(columnIndex)),index:columnIndex}));
      fileRecord.rowCount=Number(data.rowCount??data.rows?.length??0);
      fileRecord.rowsComplete=data.compactResult!==true;
    }
    save({immediate:true});
    onProgress(100,"Кэш файлов восстановлен");
  }
  async function refreshWorkspaceFileCache(onProgress=()=>{}){return uploadWorkspaceFilesToCache(analysisFileRecords().filter((file)=>file.fileToken),onProgress);}
  async function ensureWorkspaceFileCache(onProgress=()=>{}){return uploadWorkspaceFilesToCache(analysisFileRecords().filter((file)=>!file.fileToken),onProgress);}
  function browserEnrichmentFallbackAllowed(){
    const totalRows=analysisFileRecords().reduce((sum,file)=>sum+Math.max(0,Number(file.rowCount||0)),0);
    const totalBytes=analysisFileRecords().reduce((sum,file)=>sum+Math.max(0,Number(file.sourceBytes||0)),0);
    return totalRows<=(MemoryGuard.limits.browserEnrichmentRows||220000)&&totalBytes<=(MemoryGuard.limits.browserInputBatchBytes||96*1024*1024);
  }
  function currentDeviceCount(){return state.resultSnapshotId||state.resultBrowserSnapshotId?Number(state.resultDeviceCount||0):(state.devices||[]).length;}
  function currentDevicePayload(extra={}){return state.resultSnapshotId?{...extra,snapshotId:state.resultSnapshotId,devices:[]}:{...extra,devices:state.devices||[]};}
  function clearResultReference(){state.resultSnapshotId="";state.resultBrowserSnapshotId="";state.resultBrowserSnapshotDirty=false;state.resultDeviceCount=0;state.resultInvalidCount=0;state.resultSummary=null;browserDashboardCache=null;localAnalyticsCache=null;resultResponseCache.clear();deviceDialogCache.clear();}
  function syncEnrichmentStrategyUi(value=state.enrichmentStrategy){
    const strategy=EnrichmentStrategy.normalize(value);state.enrichmentStrategy=strategy;
    if($("#strategySelect"))$("#strategySelect").value=strategy;
    if($("#strategyHint"))$("#strategyHint").textContent=strategy===EnrichmentStrategy.ALLOW_EXPANSION
      ?"Режим B: файл №1 остаётся базой; только достоверно новые устройства SmartRoom могут расширить Final. DDIO строки не создаёт."
      :"Режим A: количество строк Final определяется только уникальными устройствами файла №1. SmartRoom и DDIO только обогащают.";
    return strategy;
  }
  async function pollEnrichmentProgress(jobId,processId,control){
    const stageLabels={validation:"Проверка входных данных","parsing-normalization":"Разбор и нормализация","main-device-creation":"Формирование основного набора","smartroom-matching":"Сопоставление SmartRoom",ddio:"Обработка DDIO","previous-final-history":"Сопоставление с предыдущим Final","identity-conflicts-finalization":"Идентификация и конфликты","database-save":"Транзакционное сохранение","history-analytics":"История и аналитика",completed:"Завершено"};
    while(!control.stopped&&currentEnrichmentJobId===jobId){
      try{const job=await api("/enrichment/jobs/"+encodeURIComponent(jobId));const item=job.progress||{},stage=String(item.stage||""),detail=stageLabels[stage]||stage||"Обогащение";updateProcess(processId,Number(item.percent||0),`${detail}: ${Number(item.rows||0).toLocaleString("ru-RU")} / ${Number(item.totalRows||0).toLocaleString("ru-RU")}`);if(["completed","failed","cancelled"].includes(String(job.status||item.status)))break;}catch(error){if(!networkUnavailable(error))break;}
      await new Promise((resolve)=>setTimeout(resolve,300));
    }
  }
  syncEnrichmentStrategyUi();
  function applyRefreshedFileTokens(fileTokens=[]){
    (Array.isArray(fileTokens)?fileTokens:[]).forEach((item)=>{const file=analysisFileRecords().find((entry)=>entry.id===item.id);if(file&&item.fileToken)file.fileToken=item.fileToken;});
  }
  async function analyze() {
    if(!state.files.length){toast("Сначала добавьте файл.");return;}
    if(state.ddioFile){const validation=DdioOverlay.validateMapping(state.ddioFile.mapping||{});if(!validation.valid){toast("DDIO: выберите полную пару MAC + IP для резервации или аренды");renderDdioPanel();return;}}
    await snapshotMutationPromise;
    const enrich=Object.fromEntries($$("[data-field]").map((input)=>[input.dataset.field,input.checked]));
    const strategy=syncEnrichmentStrategyUi($("#strategySelect").value),progress=$("#enrichmentProgress"),cancelButton=$("#cancelAnalyzeButton");
    save({immediate:true});
    let previousDevices=state.devices||[];
    const processId=beginProcess("Обогащение MAC-адресов","Подготовка основного файла и файлов обогащения",5);
    try{
      updateProcess(processId,10,"Запуск сервиса обогащения");
      const startProgress=await api("/enrichment/progress",{method:"POST",body:JSON.stringify({status:"starting"})});
      progress.innerHTML=startProgress.progressHtml||'<p class="muted">Обогащение запускается...</p>';
    }catch{
      progress.innerHTML='<p class="muted">Обогащение запускается...</p>';
    }
    cancelButton.disabled=false;
    enrichmentController=new AbortController();
    currentEnrichmentJobId=crypto.randomUUID();
    const enrichmentProgressControl={stopped:false};
    const enrichmentProgressPromise=pollEnrichmentProgress(currentEnrichmentJobId,processId,enrichmentProgressControl);
    const source = state.files[0].name;
    const sourceCreatedAt = primaryFileCreatedAt();
    state.ddioOverlay={};state.ddioSummary=null;
    await preserveCurrentBeforeAnalysis(source);
    try {
      updateProcess(processId,30,"Сопоставление файлов и обработка MAC-адресов");
      if(analysisFileRecords().some((file)=>!file.fileToken)){
        updateProcess(processId,32,"Потоковая подготовка браузерных файлов для backend");
        await ensureWorkspaceFileCache((value,detail)=>updateProcess(processId,32+Math.round(value*0.08),detail));
      }
      const requestPayload={jobId:currentEnrichmentJobId,files:sourceFilesPayload(true),ddioFile:ddioFilePayload(true),strategy,fields:enrich,source,createdAt:sourceCreatedAt,saveHistory:enrich.history,saveSnapshot:true,snapshotName:"Анализ: "+source,compactResult:true,resultPageSize:resultPageSize};
      let serverResult;
      try{
        serverResult=await api("/enrichment/run",{method:"POST",signal:enrichmentController.signal,body:JSON.stringify(requestPayload)});
      }catch(cacheError){
        if(cacheError.status!==409)throw cacheError;
        updateProcess(processId,38,"Обновление кэша импортированных файлов после перезапуска backend");
        await refreshWorkspaceFileCache((value,detail)=>updateProcess(processId,38+Math.round(value*0.12),detail));
        serverResult=await api("/enrichment/run",{method:"POST",signal:enrichmentController.signal,body:JSON.stringify({...requestPayload,files:sourceFilesPayload(true),ddioFile:ddioFilePayload(true)})});
      }
      applyRefreshedFileTokens(serverResult.fileTokens);
      updateProcess(processId,75,"Определение производителей, моделей и адресов");
      const resultReference=serverResult.resultReference||{};
      state.resultSnapshotId=serverResult.compactResult?String(resultReference.snapshotId||serverResult.snapshot?.id||""):"";
      state.resultBrowserSnapshotId="";
      state.resultBrowserSnapshotDirty=false;
      state.resultDeviceCount=serverResult.compactResult?Number(resultReference.deviceCount||0):0;
      state.resultInvalidCount=serverResult.compactResult?Number(resultReference.invalidCount||0):0;
      state.resultSummary=serverResult.resultSummary||serverResult.resultPage?.summary||null;
      state.ddioOverlay=serverResult.ddioOverlay||{};
      state.ddioSummary=serverResult.ddioSummary||{loaded:Boolean(state.ddioFile),switchIpChanges:0,newIpHints:0};
      state.devices = serverResult.devices||[];
      state.lastAnalysis=sourceCreatedAt;
      if(!state.resultSnapshotId){
        if(!enrich.vendor)state.devices.forEach((item)=>{item.vendor="Не определено";});
        if(!enrich.model)state.devices.forEach((item)=>{item.model="";});
        ["ip","address","room","smartroomId","switchIp","switchPort"].forEach((field)=>{if(!enrich[field])state.devices.forEach((item)=>{item[field]="";});});
        inferSwitchAddressMappings(state.devices,source);
        inferSmartroomRoomMappings(state.devices,source);
        applyLocalVendorModelMappings(state.devices);
      }
      state.invalid = serverResult.invalid || [];
      if(!state.resultSnapshotId)recordLocalMovements(previousDevices,state.devices,source,state.lastAnalysis);
      progress.innerHTML=serverResult.progressHtml||'<p class="muted">Обогащение завершено.</p>';
      updateProcess(processId,90,"Сохранение снимка и истории изменений");
      const snapshotResult = serverResult.snapshot||await api("/snapshots", {method:"POST", body:JSON.stringify(currentDevicePayload({name:"Анализ: "+source,source,createdAt:sourceCreatedAt}))});
      state.snapshots.unshift({id:snapshotResult.id,name:snapshotResult.name||"Анализ: "+source,source,createdAt:snapshotResult.createdAt||sourceCreatedAt,savedAt:snapshotResult.savedAt||new Date().toISOString(),snapshotOrder:snapshotResult.snapshotOrder||0,deviceCount:snapshotResult.deviceCount??state.devices.length,devices:[],kind:"analysis",backendStored:true});
      $("#storageStatus").textContent = "SQLite подключена";
    } catch(error) {
      if(error.name==="AbortError"){progress.innerHTML='<p class="muted">Обогащение отменено.</p>';toast("Обогащение отменено.");cancelProcess(processId,"Обогащение отменено пользователем");cancelButton.disabled=true;return;}
      if(networkUnavailable(error)){
        if(!browserEnrichmentFallbackAllowed()){
          const message="Набор превышает безопасный автономный предел. Разделите файлы на части; операция остановлена до выделения опасного объёма памяти.";
          setBackendStatus(false,"Автономная локальная база · превышен безопасный предел набора");
          progress.innerHTML='<p class="muted">'+esc(message)+'</p>';
          toast(message);
          failProcess(processId,message);
          return;
        }
        updateProcess(processId,45,"Backend недоступен: локальное обогащение в браузере");
        let local,previousComparisonIndex=null;
        try{
          await releaseTransientAnalysisMemory();
          clearResultReference();
          if(previousDevices.length>(MemoryGuard.limits.inlineComparisonRows||20000)){
            updateProcess(processId,48,"Освобождение памяти предыдущего результата");
            previousComparisonIndex=createLocalComparisonIndex(previousDevices);
            previousDevices=[];
            state.devices=[];
            await MemoryGuard.yieldToMainThread();
          }
          local=await localAnalyzeFilesToSnapshot(enrich,strategy,source,sourceCreatedAt,(value,detail)=>updateProcess(processId,45+Math.round(value*0.45),detail));
          if(!local)local=await localAnalyzeFiles(enrich,strategy,(value,detail)=>updateProcess(processId,60+Math.round(value*0.25),detail));
        }catch(localError){progress.innerHTML='<p class="muted">Автономный анализ остановлен безопасно: '+esc(localError.message)+'</p>';toast(localError.message);failProcess(processId,localError);return;}
        state.devices=SmartroomStore?await SmartroomStore.enrichData(local.devices,{registry:IeeeRegistry}):local.devices;
        state.invalid=local.invalid;
        state.resultInvalidCount=local.invalidCount;
        state.lastAnalysis=sourceCreatedAt;
        if(previousComparisonIndex)recordLocalMovementsFromIndex(previousComparisonIndex,state.devices,source,state.lastAnalysis);else recordLocalMovements(previousDevices,state.devices,source,state.lastAnalysis);
        let fullDeviceCount=Number(local.deviceCount||state.devices.length);
        if(!local.streamed){
          await storeLocalSnapshot("Анализ: "+source,source,state.devices,state.invalid,sourceCreatedAt,"analysis");
          let knownCount=0;const vendors=new Set();for(const item of state.devices){if(item.vendor)vendors.add(item.vendor);if(item.vendor&&item.vendor!=="Unknown"&&item.vendor!=="Не определено")knownCount++;}
          fullDeviceCount=state.devices.length;const firstPage=state.devices.slice(0,resultPageSize),invalidPreview=state.invalid.slice(0,Math.min(resultPageSize,MemoryGuard.limits.invalidRows||5000));
          state.devices.length=0;state.invalid.length=0;state.devices=firstPage;state.invalid=invalidPreview;state.resultDeviceCount=fullDeviceCount;state.resultInvalidCount=local.invalidCount;state.resultSummary={devices:fullDeviceCount,invalid:local.invalidCount,vendors:vendors.size,knownPercent:fullDeviceCount?Math.round(knownCount/fullDeviceCount*100):0};
        }else{state.resultDeviceCount=fullDeviceCount;state.resultInvalidCount=local.invalidCount;state.resultSummary=local.summary||state.resultSummary;}
        progress.innerHTML='<div class="bar-item"><div class="bar-label"><span>Автономная локальная база</span><strong>'+fullDeviceCount+' устройств</strong></div><div class="bar-track"><div class="bar-fill" style="width:100%"></div></div><p class="muted">Полный результат сохранён порциями в IndexedDB; в памяти оставлена только текущая страница.</p></div>';
        updateProcess(processId,90,"Сохранение локального снимка и истории");
        $("#storageStatus").textContent="Автономная локальная база IndexedDB · результат хранится постранично";
      }else{
        progress.innerHTML='<p class="muted">Backend analysis error: '+esc(error.message)+'</p>';
        toast("Backend analysis error: "+error.message);
        failProcess(processId,error);
        return;
      }
    } finally {
      cancelButton.disabled=true;
      enrichmentController=null;
      enrichmentProgressControl.stopped=true;
      await enrichmentProgressPromise.catch(()=>{});
      currentEnrichmentJobId=null;
    }
    markEnrichmentFilesConsumed();
    state.snapshots=state.snapshots.slice(0,25);
    selectLatestDashboardPair();
    browserDashboardCache=null;
    save({immediate:true});await flushBrowserStateSave().catch(()=>{});await flushPortableDatabaseSave().catch(()=>{});persistAutosave("enrichment-analysis").catch(()=>{});renderAll();toast("Анализ завершён: "+currentDeviceCount()+" устройств.");
    finishProcess(processId,"Обогащение завершено: "+currentDeviceCount()+" устройств");
  }
  async function loadFilteredResults(signal=null) {
    const filters={query:$("#searchInput").value.trim(),vendor:$("#vendorFilter").value,validity:$("#validityFilter").value,ouiLength:state.ouiLength,ouiStyle:state.ouiStyle,offset:(resultPage-1)*resultPageSize,limit:resultPageSize,sortField:resultSortField,sortDirection:resultSortDirection};
    const columns=(state.visibleColumns||empty().visibleColumns).filter(Boolean);
    const labelMap=Object.fromEntries(columns.map((column)=>[column,labels[column]||column]));
    const cacheKey=[resultStateRevision,state.resultSnapshotId,state.resultBrowserSnapshotId,state.lastAnalysis,currentDeviceCount(),JSON.stringify(filters),columns.join(",")].join("|");
    const cached=resultResponseCache.get(cacheKey);if(cached&&Date.now()-cached.at<30000)return cached.data;
    const data=await api("/results/filter",{method:"POST",signal,body:JSON.stringify(currentDevicePayload({invalid:state.invalid,filters,columns,labels:labelMap}))});
    resultResponseCache.set(cacheKey,{at:Date.now(),data});while(resultResponseCache.size>20)resultResponseCache.delete(resultResponseCache.keys().next().value);return data;
  }
  async function renderResults() {
    const renderRevision=++resultRenderRevision;
    const body=$("#resultsBody");
    const columns=(state.visibleColumns||empty().visibleColumns).filter(Boolean);
    renderLocalResultsHeader();
    resultRequestController?.abort();resultRequestController=new AbortController();
    try{
      const data=await loadFilteredResults(resultRequestController.signal);
      if(renderRevision!==resultRenderRevision)return;
      $("#resultsHeader").innerHTML=data.headerHtml||resultHeaderHtml(columns);
      body.innerHTML=data.tableRowsHtml||data.emptyTableRowsHtml||'<tr><td colspan="'+columns.length+'" class="empty-state">Нет записей по заданному фильтру.</td></tr>';
      $("#vendorFilter").innerHTML=data.vendorOptionsHtml||'<option value="">Все вендоры</option>';
      $("#resultCount").textContent=data.summaryText||"0 записей";
      updateResultPager(data.pagination?.total||0,data.pagination?.page||1,data.pagination?.pages||1);
    }catch(error){
      if(state.resultBrowserSnapshotId&&BrowserSnapshots?.page&&networkUnavailable(error)){
        const selectedVendor=$("#vendorFilter")?.value||"";
        const localPage=await BrowserSnapshots.page(state.resultBrowserSnapshotId,{query:$("#searchInput")?.value||"",vendor:selectedVendor,validity:$("#validityFilter")?.value||"",offset:(resultPage-1)*resultPageSize,limit:resultPageSize,sortField:resultSortField,sortDirection:resultSortDirection});
        if(renderRevision!==resultRenderRevision)return;
        const items=localPage?.items||[];
        renderLocalResultsHeader();
        body.innerHTML=localResultPageRows(items,columns);
        $("#vendorFilter").innerHTML='<option value="">Все вендоры</option>'+((localPage?.vendors||[]).map((value)=>`<option value="${esc(value)}" ${value===selectedVendor?"selected":""}>${esc(value)}</option>`).join(""));
        $("#resultCount").textContent=(localPage?.pagination?.total||0)+" записей";
        updateResultPager(localPage?.pagination?.total||0,localPage?.pagination?.page||1,localPage?.pagination?.pages||1);
        state.devices=items.filter((item)=>item?.valid!==false&&!item?.invalid);state.invalid=items.filter((item)=>item?.valid===false||item?.invalid);state.resultSummary=localPage?.summary||state.resultSummary;
      }else if(error?.name==="AbortError")return;
      else if(state.devices.length&&networkUnavailable(error)){
        body.innerHTML=localResultsTable();
      }else{
        renderLocalResultsHeader();
        body.innerHTML='<tr><td colspan="'+columns.length+'" class="empty-state">'+esc(error.message||"Backend unavailable")+'</td></tr>';
        $("#resultCount").textContent="0 записей";
        updateResultPager(0,1,1);
      }
    }
    applyDdioOverlayToResults(body,columns);
    renderDdioPanel();
    $("#analysisStatus").textContent=state.lastAnalysis?"Последний анализ: "+new Date(state.lastAnalysis).toLocaleString("ru-RU"):"Готов к работе";
    applyResultColumnWidths();
    renderAnalysisDashboard();
  }
  async function renderMetrics() {
    try{
      const data=await api("/dashboard/metrics",{method:"POST",body:JSON.stringify(currentDevicePayload({invalid:state.invalid,snapshots:state.snapshots,settings:{vendor:"",room:"",chartLimit:8,showUnknown:true}}))});
      const metrics=data.metrics||{};
      $("#metricDevices").textContent=metrics.devices||0;
      $("#metricVendors").textContent=metrics.vendors||0;
      renderAnalysisHeaderMetrics();
      $("#metricKnown").textContent=(metrics.knownPercent||0)+"%";
      $("#metricInvalid").textContent=metrics.invalid||0;
    }catch(error){
      const summary=state.resultSummary||{},vendors=new Set(state.devices.map(item=>item.vendor).filter(v=>v&&v!=="Unknown"&&v!=="Не определено"));
      $("#metricDevices").textContent=summary.devices??state.devices.length??0;
      $("#metricVendors").textContent=summary.vendors??vendors.size??0;
      renderAnalysisHeaderMetrics();
      $("#metricKnown").textContent=(summary.knownPercent??(state.devices.length?Math.round(state.devices.filter(item=>item.vendor&&item.vendor!=="Unknown"&&item.vendor!=="Не определено").length/state.devices.length*100):0))+"%";
      $("#metricInvalid").textContent=summary.invalid??state.resultInvalidCount??(state.invalid||[]).length??0;
    }
  }
  async function collectLocalMacContext(mac){
    const normalized=normalize(mac),snapshots=finalDashboardSnapshots();
    let current=(state.devices||[]).find((item)=>normalize(item.mac||item.macFormatted)===normalized)||null;
    if(!current&&state.resultBrowserSnapshotId&&BrowserSnapshots?.findDevice){
      current=await BrowserSnapshots.findDevice(state.resultBrowserSnapshotId,normalized).catch(()=>null);
    }
    const appearances=await MacChronology.collectAppearances({
      mac:normalized,
      snapshots,
      findSnapshotDevice:async(snapshot,targetMac)=>{
        if(snapshot.browserStored&&BrowserSnapshots?.findDevice)return BrowserSnapshots.findDevice(snapshot.id,targetMac).catch(()=>null);
        return null;
      },
    });
    const movements=(state.movementHistory||[]).filter((item)=>normalize(item.mac||item.macFormatted)===normalized);
    return{mac:normalized,current:current||appearances.at(-1)?.device||{},appearances,movements};
  }
  function renderDeviceDialog(analytics,local,requestedMac){
    const normalized=normalize(analytics?.mac||local?.mac||requestedMac),device=Object.keys(analytics?.current||{}).length?analytics.current:(local?.current||{});
    const appearances=MacChronology.mergeAppearances(analytics?.appearances||[],local?.appearances||[]);
    const history=analytics?.history||[],movements=[...(analytics?.movements||[]),...(local?.movements||[])];
    const events=MacChronology.buildEvents({appearances,history,movements});
    const dialog=$("#deviceDialog"),title=analytics?.macFormatted||device.macFormatted||formatMac(normalized)||requestedMac;
    $("#deviceDialogTitle").textContent=title;
    dialog.dataset.mac=normalized||requestedMac;
    $("#deviceDialogSubtitle").textContent=(device.vendor||"Unknown")+(device.model?" · "+device.model:"");
    const localFields=["vendor","model","ip","address","room","smartroomId","switchIp","switchPort","source"].map((field)=>`<div class="device-field"><span>${esc(labels[field]||field)}</span><strong>${esc(device[field]||"—")}</strong></div>`).join("");
    $("#deviceMetrics").innerHTML=analytics?.metricsHtml||`<div class="metric"><span>Появлений в выгрузках</span><strong>${appearances.length}</strong></div><div class="metric"><span>Событий хронологии</span><strong>${events.length}</strong></div>`;
    $("#deviceFields").innerHTML=analytics?.fieldsHtml||localFields||'<p class="muted">Нет локальных полей устройства.</p>';
    $("#deviceDetailedReport").textContent=analytics?.detailedReportText||localDeviceDetailedReport(device,normalized||requestedMac);
    $("#deviceChronologySummary").innerHTML=MacChronology.renderSummary(events,appearances);
    $("#deviceChronologyBody").innerHTML=MacChronology.renderTimeline(events,{formatDate:formatDisplayDateTime});
    const localHistory=localMacHistoryRows(normalized,appearances,movements),localMovements=localMacMovementRows(normalized,movements);
    $("#macHistoryStats").innerHTML=localHistory.statsHtml;
    $("#deviceHistoryRecordsBody").innerHTML=appearances.length?MacChronology.appearancesRowsHtml(appearances,{formatDate:formatDisplayDateTime}):(analytics?.historyRecordsRowsHtml||localHistory.html);
    $("#deviceHistoryBody").innerHTML=analytics?.movementRowsHtml||localMovements.html;
  }
  function showDeviceLoading(mac){
    const dialog=$("#deviceDialog"),formatted=formatMac(normalize(mac))||mac;
    $("#deviceDialogTitle").textContent=formatted;
    $("#deviceDialogSubtitle").textContent="Загрузка полной хронологии из сохранённых выгрузок…";
    $("#deviceMetrics").innerHTML="";
    $("#deviceFields").innerHTML='<p class="muted">Поиск устройства в локальной базе…</p>';
    $("#deviceDetailedReport").textContent="Подготавливается подробная информация.";
    $("#deviceChronologySummary").innerHTML="";
    $("#deviceChronologyBody").innerHTML='<div class="mac-timeline-empty"><strong>Загрузка хронологии</strong><span>Проверяются сохранённые выгрузки без загрузки всей базы в память.</span></div>';
    $("#macHistoryStats").innerHTML="";
    $("#deviceHistoryRecordsBody").innerHTML='<tr><td colspan="8" class="empty-state">Загрузка появлений MAC…</td></tr>';
    $("#deviceHistoryBody").innerHTML='<tr><td colspan="5" class="empty-state">Загрузка изменений…</td></tr>';
    if(!dialog.open)dialog.showModal();
  }
  async function showDevice(mac){
    const normalized=normalize(mac);
    if(!normalized){toast("MAC не найден.");return;}
    const cacheKey=[resultStateRevision,state.resultSnapshotId,state.resultBrowserSnapshotId,state.lastAnalysis,normalized].join("|");
    const cached=deviceDialogCache.get(cacheKey);
    if(cached&&Date.now()-cached.at<30000){showDeviceLoading(normalized);renderDeviceDialog(cached.analytics,cached.local,normalized);return;}
    showDeviceLoading(normalized);
    const quick=(state.devices||[]).find((item)=>normalize(item.mac||item.macFormatted)===normalized);
    if(quick)renderDeviceDialog(null,{mac:normalized,current:quick,appearances:[],movements:[]},normalized);
    const [backendResult,localResult]=await Promise.allSettled([
      api("/device/analytics",{method:"POST",body:JSON.stringify(currentDevicePayload({mac:normalized,snapshots:state.snapshots}))}),
      collectLocalMacContext(normalized),
    ]);
    const analytics=backendResult.status==="fulfilled"?backendResult.value:null;
    const local=localResult.status==="fulfilled"?localResult.value:{mac:normalized,current:{},appearances:[],movements:[]};
    renderDeviceDialog(analytics,local,normalized);
    deviceDialogCache.set(cacheKey,{analytics,local,at:Date.now()});while(deviceDialogCache.size>50)deviceDialogCache.delete(deviceDialogCache.keys().next().value);
    if(!analytics&&!local.appearances.length&&!Object.keys(local.current||{}).length)toast("Для этого MAC не найдены сохранённые данные.");
  }
  async function showLocalDevice(mac){
    const normalized=normalize(mac);
    if(!normalized){toast("MAC не найден.");return;}
    showDeviceLoading(normalized);
    const local=await collectLocalMacContext(normalized);
    renderDeviceDialog(null,local,normalized);
  }
  function localDeviceDetailedReport(device={},mac=""){const value=(fallback,...keys)=>{for(const key of keys){if(Object.prototype.hasOwnProperty.call(device,key)){const result=String(device[key]??"").trim();return result||fallback;}}return fallback;};return["=== ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ОБ УСТРОЙСТВЕ ===","",`MAC-адрес: ${value(formatMac(mac),"macFormatted","mac_formatted","mac")}`,`Производитель: ${value("Unknown","vendor")}`,`Модель: ${value("Не указана","model")}`,`IP-адрес: ${value("Не указан","ip")}`,`Физический адрес: ${value("Не указан","address")}`,`Помещение: ${value("Не указано","room")}`,`Smartroom ID: ${value("Не указан","smartroomId","smartroom_id")}`,`Коммутатор: ${value("Не указан","switchIp","switch_ip")}`,`Порт: ${value("Не указан","switchPort","switch_port")}`,"","Источники данных:",`  Производитель: ${value("Неизвестен","vendorSource","vendor_source")}`,`  Модель: ${value("Неизвестен","modelSource","model_source")}`,"",`Примечания: ${value("Нет","matchDetails","match_details")}`].join("\n");}
  function localMacHistoryRows(mac,loadedAppearances=null,loadedMovements=null){
    const normalized=normalize(mac),rows=loadedAppearances||((state.snapshots||[]).flatMap((snapshot)=>(snapshot.devices||[]).filter((device)=>normalize(device.mac||device.macFormatted)===normalized).map((device)=>({snapshotId:snapshot.id,snapshotName:snapshot.name,source:snapshot.source||device.source,createdAt:snapshot.createdAt,device}))));
    const dates=rows.map((item)=>item.createdAt||"").filter(Boolean).sort(),sources=new Set(rows.map((item)=>item.source||item.device?.source||item.snapshotName).filter(Boolean)),movements=loadedMovements||(state.movementHistory||[]).filter((item)=>normalize(item.mac||item.macFormatted)===normalized);
    const statsHtml=`<div class="bar-label"><span>Всего появлений</span><strong>${rows.length}</strong></div><div class="bar-label"><span>Первое появление</span><strong>${esc(dates[0]?formatDisplayDateTime(dates[0]):"-")}</strong></div><div class="bar-label"><span>Последнее появление</span><strong>${esc(dates.length?formatDisplayDateTime(dates[dates.length-1]):"-")}</strong></div><div class="bar-label"><span>Файлов</span><strong>${sources.size}</strong></div><div class="bar-label"><span>Изменений</span><strong>${movements.length}</strong></div>`;
    return{count:rows.length,statsHtml,html:MacChronology.appearancesRowsHtml(rows,{formatDate:formatDisplayDateTime})};
  }
  function localMacMovementRows(mac,loadedRows=null){const normalized=normalize(mac),rows=(loadedRows||(state.movementHistory||[]).filter((item)=>normalize(item.mac||item.macFormatted)===normalized)).slice().sort((a,b)=>String(b.changedAt||b.changed_at||"").localeCompare(String(a.changedAt||a.changed_at||"")));return{count:rows.length,html:rows.length?rows.map((item)=>`<tr><td>${esc(formatDisplayDateTime(item.changedAt||item.changed_at||""))}</td><td>${esc(item.field||item.field_name||"-")}${ddioHistoryBadge(item)}</td><td>${esc(item.before??item.from_value??"-")}</td><td>${esc(item.after??item.to_value??"-")}</td><td>${esc(item.source||"-")}</td></tr>`).join(""):'<tr><td colspan="5" class="empty-state">Локальные изменения параметров MAC отсутствуют.</td></tr>'};}
  function localMacChronology(mac){
    const normalized=normalize(mac),events=[];
    (state.snapshots||[]).forEach((snapshot)=>(snapshot.devices||[]).forEach((device)=>{if(normalize(device.mac||device.macFormatted)===normalized)events.push({date:snapshot.createdAt||"",event:"Появление в снимке",field:"snapshot",before:"",after:[device.vendor,device.model,device.ip,device.address].filter(Boolean).join(" / "),source:snapshot.name||snapshot.source||device.source||"snapshot"});}));
    (state.movementHistory||[]).forEach((item)=>{if(normalize(item.mac||item.macFormatted)===normalized)events.push({date:item.changedAt||item.changed_at||"",event:item.type||"Изменение поля",field:item.field||item.field_name||"",before:item.before??item.from_value??"",after:item.after??item.to_value??"",source:item.source||""});});
    events.sort((a,b)=>String(b.date).localeCompare(String(a.date)));
    const richEvents=MacChronology.buildEvents({events}),appearances=events.filter((item)=>item.field==="snapshot");
    const summaryHtml=MacChronology.renderSummary(richEvents,appearances);
    const html=MacChronology.renderTimeline(richEvents,{formatDate:formatDisplayDateTime});
    return{events,summaryHtml,html};
  }
  async function exportDeviceAnalytics(){
    const mac=$("#deviceDialog").dataset.mac;
    if(!mac)return;
    try{
      const data=await api("/device/analytics",{method:"POST",body:JSON.stringify(currentDevicePayload({mac,snapshots:state.snapshots,exportFormat:"html"}))});
      if(!data.export)throw new Error("Device analytics export is empty");
      download(data.export.filename||"mac-device-analytics.html",data.export.content,data.export.mimeType||"text/html");
      toast("Аналитика устройства экспортирована.");
    }catch(error){toast(error.message);}
  }
  function formatModelPrefix(prefix){const value=normalizePrefix(prefix);return value.match(/.{1,2}/g)?.join(":")||"";}
  function localModelAnalytics(model){
    const query=String(model||"").trim().toLowerCase(),custom=state.localModelMappings||{},rules={...custom};
    const prefixes=Object.entries(rules).filter(([,value])=>query&&(String(value).toLowerCase()===query||String(value).toLowerCase().includes(query))).sort((a,b)=>String(a[1]).localeCompare(String(b[1]),"ru")||a[0].localeCompare(b[0])).map(([prefix,value])=>({prefix,formattedPrefix:formatModelPrefix(prefix),model:value,sourceLabel:Object.prototype.hasOwnProperty.call(custom,prefix)?"Пользовательское правило":"Встроенная база"}));
    const matchedDevices=(state.devices||[]).filter((device)=>String(device.model||"").toLowerCase()===query||prefixes.some((item)=>normalize(device.mac||device.macFormatted).startsWith(normalizePrefix(item.prefix))));
    return{model,prefixes,metrics:{prefixes:prefixes.length,matchedDevices:matchedDevices.length,vendors:new Set(matchedDevices.map((device)=>device.vendor).filter(Boolean)).size},tableRowsHtml:prefixes.length?prefixes.map((item)=>`<tr><td>${esc(item.formattedPrefix)}</td><td>${esc(item.model)}</td><td>${esc(item.sourceLabel)}</td></tr>`).join(""):'<tr><td>Нет данных</td><td></td><td></td></tr>'};
  }
  function renderModelAnalyticsDialog(data,model){
    const metrics=data.metrics||{};
    $("#modelDialogTitle").textContent="Префиксы MAC для модели "+model;
    $("#modelDialogSubtitle").textContent="Правила определения модели по MAC: точное имя или совпадение по названию.";
    $("#modelPrefixBody").innerHTML=data.tableRowsHtml||'<tr><td>Нет данных</td><td></td><td></td></tr>';
    $("#modelPrefixSummary").innerHTML=`<div class="bar-label"><span>Префиксов</span><strong>${Number(metrics.prefixes||0)}</strong></div><div class="bar-label"><span>Устройств в текущем наборе</span><strong>${Number(metrics.matchedDevices||0)}</strong></div><div class="bar-label"><span>Производителей</span><strong>${Number(metrics.vendors||0)}</strong></div>`;
    $("#modelDialog").showModal();
  }
  async function showModelAnalytics(model){
    try{
      const data=await api("/model/analytics",{method:"POST",body:JSON.stringify(currentDevicePayload({model}))});
      renderModelAnalyticsDialog(data,model);
    }catch(error){renderModelAnalyticsDialog(localModelAnalytics(model),model);toast("Префиксы модели показаны из встроенной HTML-базы.");}
  }
  async function renderSnapshots() {
    const finalSnapshots=finalDashboardSnapshots();
    try{
      const data=await api("/snapshots/options",{method:"POST",body:JSON.stringify({snapshots:finalSnapshots})}),options=data.optionsHtml||"",emptyOption=data.emptyOptionHtml||"<option>Нет финальных обогащений</option>";
      $("#baselineSelect").innerHTML=options||emptyOption;$("#comparisonSelect").innerHTML=options||emptyOption;$("#multiComparisonSelect").innerHTML=options;if(options){$("#baselineSelect").selectedIndex=data.baselineSelectedIndex||0;$("#comparisonSelect").selectedIndex=data.comparisonSelectedIndex||0;}
    }catch(error){
      renderLocalSnapshotOptions();
    }
  }
  function localSnapshotOptionHtml(){
    const options=[];
    for(const entry of finalDashboardSnapshots()){
      options.push(`<option value="${esc(entry.id)}">${esc(entry.name||entry.source||"Snapshot")} · ${esc(entry.createdAt?new Date(entry.createdAt).toLocaleString("ru-RU"):"")}</option>`);
    }
    return options.join("");
  }
  function renderLocalSnapshotOptions(){
    const options=localSnapshotOptionHtml(),emptyOption='<option value="">Нет снимков</option>';
    $("#baselineSelect").innerHTML=options||emptyOption;
    $("#comparisonSelect").innerHTML=options||emptyOption;
    $("#multiComparisonSelect").innerHTML=options;
    const count=finalDashboardSnapshots().length;
    if(count>1)$("#comparisonSelect").selectedIndex=count-1;
    if(count>1)$("#baselineSelect").selectedIndex=count-2;
  }
  function localAnalyticsKey(devices=[]){
    const settings=dashboardSettings();
    return [state.resultBrowserSnapshotId||"",state.resultSnapshotId||"",currentDeviceCount(),state.resultInvalidCount||state.invalid.length,state.lastAnalysis||"",Array.isArray(devices)?devices.length:0,settings.vendor||"",settings.room||"",settings.showUnknown!==false].join("|");
  }
  async function collectLocalAnalytics(devices=dashboardDevices(),force=false){
    const key=localAnalyticsKey(devices);
    if(!force&&localAnalyticsCache?.key===key)return localAnalyticsCache.payload;
    const settings=dashboardSettings();
    const collector=LocalAnalytics.createCollector({invalidCount:Math.max(Number(state.resultInvalidCount||0),Number(state.invalid.length||0)),vendor:settings.vendor||"",room:settings.room||"",showUnknown:settings.showUnknown!==false});
    if(state.resultBrowserSnapshotId&&BrowserSnapshots?.streamSnapshot){
      const metadata=await BrowserSnapshots.streamSnapshot(state.resultBrowserSnapshotId,async(kind,rows)=>{if(kind==="device")collector.accept(rows);});
      if(!metadata)collector.accept(devices);
    }else collector.accept(devices);
    const payload=collector.finish();
    localAnalyticsCache={key,payload};
    return payload;
  }
  async function renderBackendStatistics(){
    const root=$("#backendStatisticsChart"); if(!root)return;
    try{
      const data=await api("/statistics/panel");
      root.innerHTML=data.statisticsHtml||'<p class="muted">SQLite statistics are empty.</p>';
    }catch(error){
      root.innerHTML=LocalAnalytics.renderStatistics(finalDashboardSnapshots(),currentDeviceCount(),state.movementHistory.length);
    }
  }
  async function renderTemporalStatistics(){
    const root=$("#temporalStatisticsChart"); if(!root)return;
    try{
      const data=await api("/statistics/panel");
      root.innerHTML=data.temporalHtml||'<p class="muted">Нет SQLite-снимков для временной статистики.</p>';
    }catch(error){
      root.innerHTML=LocalAnalytics.renderTemporal(finalDashboardSnapshots());
    }
  }
  async function renderBackendCharts(){
    const root=$("#backendChartsPanel"); if(!root)return;
    try{
      const data=await(analyticsPanelPromise||loadAnalyticsPanel());
      root.innerHTML=data.backendChartsHtml||'<p class="muted">Backend не вернул диаграммы.</p>';
    }catch(error){
      root.innerHTML=LocalAnalytics.renderOverview(await collectLocalAnalytics());
    }
  }
  function localTally(items,key,limit=8){const counts={};items.forEach((item)=>{const value=String(item[key]||"Unknown").trim()||"Unknown";counts[value]=(counts[value]||0)+1;});return Object.entries(counts).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,limit);}
  function localChartHtml(items,emptyText="Недостаточно данных."){const max=Math.max(1,...items.map((item)=>item[1]));return items.length?items.map(([label,count])=>`<div class="bar-item"><div class="bar-label"><span>${esc(label)}</span><strong>${count}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${Math.round(count/max*100)}%"></div></div></div>`).join(""):`<p class="muted">${esc(emptyText)}</p>`;}
  function buildLocalAnalyticsReport(devices=state.devices){
    const rows=Array.isArray(devices)?devices:[],total=rows.length;
    if(!total)return{total:0,reportText:"Нет данных",vendors:[],models:[],rooms:[],roomOccupancy:{assignedDevices:0,unassignedDevices:0,assignedPercent:0,uniqueRooms:0,averageDevicesPerRoom:0,mostOccupied:null,rooms:[]},coverage:{uniqueVendors:0,uniqueModels:0,address:{count:0,percent:0},room:{count:0,percent:0},ip:{count:0,percent:0},switch:{count:0,percent:0}}};
    const value=(device,...keys)=>{for(const key of keys){const found=String(device?.[key]??"").trim();if(found)return found;}return"";};
    const ranked=(keyGetter)=>{const counts=new Map();rows.forEach((device)=>{const item=keyGetter(device);if(item)counts.set(item,(counts.get(item)||0)+1);});return[...counts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,20).map(([label,count])=>({label,count,percent:Number((count/total*100).toFixed(1))}));};
    const vendors=ranked((device)=>value(device,"vendor")||"Unknown"),models=ranked((device)=>value(device,"model")),rooms=ranked((device)=>value(device,"room"));
    const filled=(field)=>rows.filter((device)=>{const item=field(device);return item&&!['Unknown','Не указано'].includes(item);}).length;
    const address=filled((device)=>value(device,"address")),room=filled((device)=>value(device,"room")),ip=filled((device)=>value(device,"ip")),switchCount=filled((device)=>value(device,"switchIp","switch_ip"));
    const percent=(count)=>Number((count/total*100).toFixed(1)),lines=["=== АНАЛИТИКА ПО УСТРОЙСТВАМ ===","",`Всего устройств: ${total}`,"","=== ПРОИЗВОДИТЕЛИ ==="];
    vendors.forEach((item)=>lines.push(`  ${item.label}: ${item.count} (${item.percent.toFixed(1)}%)`));lines.push("","=== МОДЕЛИ ===");models.forEach((item)=>lines.push(`  ${item.label}: ${item.count} (${item.percent.toFixed(1)}%)`));lines.push("","=== ПОМЕЩЕНИЯ ===");rooms.forEach((item)=>lines.push(`  ${item.label}: ${item.count} (${item.percent.toFixed(1)}%)`));
    const allRoomCounts=new Map();rows.forEach((device)=>{const item=value(device,"room");if(item&&!['Unknown','Не указано'].includes(item))allRoomCounts.set(item,(allRoomCounts.get(item)||0)+1);});const roomRows=[...allRoomCounts.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,50).map(([label,count])=>({label,count,percentOfAssigned:Number((count/Math.max(1,room)*100).toFixed(1)),percentOfAll:percent(count)})),roomOccupancy={assignedDevices:room,unassignedDevices:total-room,assignedPercent:percent(room),uniqueRooms:allRoomCounts.size,averageDevicesPerRoom:allRoomCounts.size?Number((room/allRoomCounts.size).toFixed(1)):0,mostOccupied:roomRows[0]||null,rooms:roomRows};
    lines.push("","=== ЗАПОЛНЕННОСТЬ ===",`  Производитель: ${vendors.length} уникальных`,`  Модель: ${models.length} уникальных`,`  Адрес: ${address} (${percent(address).toFixed(1)}%)`,`  Помещение: ${room} (${percent(room).toFixed(1)}%)`,`  IP-адрес: ${ip} (${percent(ip).toFixed(1)}%)`,`  Коммутатор: ${switchCount} (${percent(switchCount).toFixed(1)}%)`,"","=== ЗАПОЛНЕННОСТЬ ПОМЕЩЕНИЙ ===",`  Распределено: ${room} (${roomOccupancy.assignedPercent.toFixed(1)}%)`,`  Без помещения: ${roomOccupancy.unassignedDevices}`,`  Уникальных помещений: ${roomOccupancy.uniqueRooms}`,`  Среднее устройств на помещение: ${roomOccupancy.averageDevicesPerRoom.toFixed(1)}`);
    return{total,vendors,models,rooms,roomOccupancy,coverage:{uniqueVendors:vendors.length,uniqueModels:models.length,address:{count:address,percent:percent(address)},room:{count:room,percent:percent(room)},ip:{count:ip,percent:percent(ip)},switch:{count:switchCount,percent:percent(switchCount)}},reportText:lines.join("\n")};
  }
  function renderAnalyticsReport(report,source="local"){const preview=$("#analyticsReportPreview"),status=$("#analyticsReportStatus"),occupancy=report?.roomOccupancy||{};if(preview)preview.textContent=report?.reportText||"Нет данных";if(status)status.textContent=`${report?.total||0} устройств · ${source==="backend"?"расчёт backend":"локальный расчёт"}`;if($("#roomOccupancyStatus"))$("#roomOccupancyStatus").textContent=`Распределено ${Number(occupancy.assignedDevices||0).toLocaleString("ru-RU")} из ${Number(report?.total||0).toLocaleString("ru-RU")} (${Number(occupancy.assignedPercent||0).toFixed(1)}%) · без помещения ${Number(occupancy.unassignedDevices||0).toLocaleString("ru-RU")} · среднее ${Number(occupancy.averageDevicesPerRoom||0).toFixed(1)}`;if($("#roomOccupancyChart"))$("#roomOccupancyChart").innerHTML=localChartHtml((occupancy.rooms||[]).slice(0,20).map((item)=>[`${item.label} · ${Number(item.percentOfAssigned||0).toFixed(1)}%`,item.count]),"Нет данных о помещениях.");return report;}
  async function refreshAnalyticsReport(){const local=buildLocalAnalyticsReport(state.devices);renderAnalyticsReport(local,"local");try{const report=await api("/analytics/report",{method:"POST",body:JSON.stringify(currentDevicePayload())});return renderAnalyticsReport(report,"backend");}catch{return local;}}
  async function exportAnalyticsReport(){try{const report=await api("/analytics/report",{method:"POST",body:JSON.stringify(currentDevicePayload({exportFormat:"txt"}))});if(!report.export)throw new Error("TXT export is empty");download(report.export.filename||"analytics_report.txt",report.export.content,report.export.mimeType||"text/plain");renderAnalyticsReport(report,"backend");toast("Аналитический отчёт экспортирован.");}catch{const report=renderAnalyticsReport(buildLocalAnalyticsReport(state.devices),"local");download(`analytics_report_${new Date().toISOString().slice(0,19).replace(/[-:T]/g,"")}.txt`,report.reportText,"text/plain");toast("Аналитический отчёт экспортирован локально.");}}
  function localAnalyticsPayload(devices=dashboardDevices()){const known=devices.filter((device)=>device.vendor&&device.vendor!=="Unknown").length,unknown=Math.max(0,devices.length-known),invalid=state.invalid.length;return{vendors:localChartHtml(localTally(devices,"vendor")),models:localChartHtml(localTally(devices,"model")),quality:localChartHtml([["Опознано",known],["Unknown",unknown],["Ошибки",invalid]].filter((item)=>item[1]>0),"Ошибок качества не найдено."),timeline:localChartHtml((state.snapshots||[]).slice(-8).map((snap)=>[String(snap.name||snap.createdAt||"snapshot").slice(0,24),(snap.devices||[]).length]),"Снимков пока нет.")};}
  function renderLocalAnalytics(devices=dashboardDevices()){const charts=localAnalyticsPayload(devices);$("#vendorChart").innerHTML=charts.vendors;$("#modelChart").innerHTML=charts.models;$("#qualityChart").innerHTML=charts.quality;$("#timelineChart").innerHTML=charts.timeline;}
  function analysisHeaderMetrics(devices=state.devices){if(state.resultSnapshotId&&state.resultSummary){const summary=state.resultSummary;return{models:Number(summary.models||0),oui3:Number(summary.oui3||0),oui4:Number(summary.oui4||0),oui5:Number(summary.oui5||0),autoVendors:Number(summary.autoVendors||0),autoModels:Number(summary.autoModels||0)};}const knownVendor=(device)=>device.vendor&&device.vendor!=="Unknown"&&device.vendor!=="Не определено",models=new Set(devices.map((item)=>item.model).filter(Boolean)),oui3=new Set(devices.map((item)=>formatOuiValue(item.mac||item.macFormatted||item.oui,3,"plain")).filter(Boolean)),oui4=new Set(devices.map((item)=>formatOuiValue(item.mac||item.macFormatted||item.oui,4,"plain")).filter(Boolean)),oui5=new Set(devices.map((item)=>formatOuiValue(item.mac||item.macFormatted||item.oui,5,"plain")).filter(Boolean)),autoVendors=devices.filter((item)=>knownVendor(item)&&(item.vendorMatchedPrefix||!item.vendorSource||!["file","history"].includes(item.vendorSource))).length,autoModels=devices.filter((item)=>item.model&&(item.modelMatchedPrefix||!item.modelSource||!["file","history"].includes(item.modelSource))).length;return{models:models.size,oui3:oui3.size,oui4:oui4.size,oui5:oui5.size,autoVendors,autoModels};}
  function renderAnalysisHeaderMetrics(devices=state.devices){const header=analysisHeaderMetrics(devices);$("#metricModels").textContent=header.models;$("#metricOuiCoverage").textContent=header.oui3+" / "+header.oui4+" / "+header.oui5;$("#metricAutoDetected").textContent=header.autoVendors+" / "+header.autoModels;}
  function analysisDashboardLocalPayload(devices=state.devices,summary=state.resultSummary){
    const rows=Array.isArray(devices)?devices:[],unknownLabels=new Set(["","unknown","не определено","неизвестный вендор","unknown vendor"]);
    const value=(device,...keys)=>{for(const key of keys){const current=String(device?.[key]??"").trim();if(current)return current;}return"";};
    const rank=(keyGetter)=>{const counts=new Map();for(const device of rows){const item=keyGetter(device);if(item)counts.set(item,(counts.get(item)||0)+1);}return[...counts.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,20).map(([label,count])=>({label,value:count}));};
    const prefixes=(length)=>{const values=rows.map((device)=>formatOuiValue(value(device,"mac","macFormatted","mac_formatted","oui"),length,"plain")).filter(Boolean),counts=new Map();for(const prefix of values)counts.set(prefix,(counts.get(prefix)||0)+1);return{unique:new Set(values).size,rows:[...counts.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,20).map(([label,count])=>({label,value:count}))};};
    const knownLocal=rows.filter((device)=>!unknownLabels.has(value(device,"vendor").toLowerCase())).length,total=Number(summary?.devices??currentDeviceCount()??rows.length),knownPercent=Number(summary?.knownPercent??(total?Math.round(knownLocal/Math.max(1,rows.length)*100):0)),known=Number(summary?.knownDevices??summary?.known??Math.round(total*knownPercent/100)),invalid=Number(summary?.invalid??state.resultInvalidCount??state.invalid.length),vendors=new Set(rows.map((device)=>value(device,"vendor")).filter((item)=>!unknownLabels.has(item.toLowerCase()))),models=new Set(rows.map((device)=>value(device,"model")).filter(Boolean)),rooms=new Set(rows.map((device)=>value(device,"room")).filter(Boolean)),switches=new Set(rows.map((device)=>value(device,"switchIp","switch_ip")).filter(Boolean)),withValue=(...keys)=>rows.filter((device)=>value(device,...keys)).length,oui3=prefixes(3),oui4=prefixes(4),oui5=prefixes(5),withModel=withValue("model"),autoVendors=rows.filter((device)=>!unknownLabels.has(value(device,"vendor").toLowerCase())&&(device.vendorMatchedPrefix||!device.vendorSource||!["file","history"].includes(device.vendorSource))).length,autoModels=rows.filter((device)=>value(device,"model")&&(device.modelMatchedPrefix||!device.modelSource||!["file","history"].includes(device.modelSource))).length;
    return{metrics:{devices:total,knownDevices:known,unknownVendor:Math.max(0,total-known),knownPercent,vendors:Number(summary?.vendors??vendors.size),models:Number(summary?.models??models.size),rooms:rooms.size,switches:switches.size,invalid,withAddress:withValue("address"),withRoom:withValue("room"),withIp:withValue("ip"),withSwitch:withValue("switchIp","switch_ip"),withModel,autoVendors,autoModels,uniqueOui3:oui3.unique,uniqueOui4:oui4.unique,uniqueOui5:oui5.unique},distributions:{vendors:rank((device)=>value(device,"vendor")||"Unknown"),models:rank((device)=>value(device,"model")),rooms:rank((device)=>value(device,"room")),switches:rank((device)=>value(device,"switchIp","switch_ip")),oui3:oui3.rows,oui4:oui4.rows,oui5:oui5.rows}};
  }
  function analysisDashboardAggregatePayload(aggregate={}){
    return{metrics:{devices:Number(aggregate.devices||0),knownDevices:Number(aggregate.known||0),unknownVendor:Number(aggregate.unknown||0),knownPercent:Number(aggregate.knownPercent||0),vendors:Number(aggregate.uniqueVendors||0),models:Number(aggregate.uniqueModels||0),rooms:Number(aggregate.uniqueRooms||0),switches:Number(aggregate.uniqueSwitches||0),invalid:Number(aggregate.invalid||0),withAddress:Number(aggregate.withAddress||0),withRoom:Number(aggregate.withRoom||0),withIp:Number(aggregate.withIp||0),withSwitch:Number(aggregate.withSwitch||0),withModel:Number(aggregate.withModel||0),autoVendors:Number(aggregate.autoVendors||0),autoModels:Number(aggregate.autoModels||0),uniqueOui3:Number(aggregate.uniqueOui3||0),uniqueOui4:Number(aggregate.uniqueOui4||0),uniqueOui5:Number(aggregate.uniqueOui5||0)},distributions:{vendors:aggregate.vendors||[],models:aggregate.models||[],rooms:aggregate.rooms||[],switches:aggregate.switches||[],oui3:aggregate.oui3||[],oui4:aggregate.oui4||[],oui5:aggregate.oui5||[]}};
  }
  function analysisDashboardRows(items=[]){return(items||[]).map((item)=>Array.isArray(item)?item:[item.label,Number(item.value??item.count??0)]);}
  function renderAnalysisDashboardPayload(payload={},statusText=""){
    const metrics=payload.metrics||{},distributions=payload.distributions||{},total=Number(metrics.devices||0),known=Number(metrics.knownDevices||0),unknown=Number(metrics.unknownVendor??Math.max(0,total-known)),percent=Number(metrics.knownPercent??(total?Math.round(known/total*100):0)),set=(selector,value)=>{const node=$(selector);if(node)node.textContent=String(value);},chart=(selector,items,empty)=>{const node=$(selector);if(node)node.innerHTML=localChartHtml(analysisDashboardRows(items),empty);},coverage=[["Производитель",known],["Модель",Number(metrics.withModel||0)],["Адрес помещения",Number(metrics.withAddress||0)],["Помещение",Number(metrics.withRoom||0)],["IP устройства",Number(metrics.withIp||0)],["IP коммутатора",Number(metrics.withSwitch||0)]].map(([label,count])=>[`${label} · ${total?Math.round(count/total*100):0}%`,count]);
    set("#analysisMetricDevices",total);set("#analysisMetricKnown",`${known} / ${percent}%`);set("#analysisMetricUnknown",unknown);set("#analysisMetricVendors",Number(metrics.vendors||0));set("#analysisMetricModels",Number(metrics.models||0));set("#analysisMetricRooms",Number(metrics.rooms||0));set("#analysisMetricSwitches",Number(metrics.switches||0));set("#analysisMetricInvalid",Number(metrics.invalid||0));if($("#analysisDashboardStatus"))$("#analysisDashboardStatus").textContent=statusText||(total?"Dashboard построен по полному финальному результату.":"Запустите анализ, чтобы построить dashboard.");
    chart("#analysisVendorChart",distributions.vendors,"Нет данных производителей.");chart("#analysisModelChart",distributions.models,"Нет данных моделей.");chart("#analysisRoomChart",distributions.rooms,"Нет данных помещений.");chart("#analysisSwitchChart",distributions.switches,"Нет данных коммутаторов.");chart("#analysisOuiChart",[["3 байта",Number(metrics.uniqueOui3||0)],["4 байта",Number(metrics.uniqueOui4||0)],["5 байт",Number(metrics.uniqueOui5||0)]],"Нет OUI.");chart("#analysisOui3Chart",distributions.oui3,"Нет OUI 3 байта.");chart("#analysisOui4Chart",distributions.oui4,"Нет OUI 4 байта.");chart("#analysisOui5Chart",distributions.oui5,"Нет OUI 5 байт.");chart("#analysisCoverageChart",coverage,"Нет данных заполненности.");chart("#analysisQualityChart",[["Опознано",known],["Unknown",unknown],["Ошибки",Number(metrics.invalid||0)]].filter((item)=>item[1]>0),"Ошибок качества не найдено.");
    set("#metricModels",Number(metrics.models||0));set("#metricOuiCoverage",`${Number(metrics.uniqueOui3||0)} / ${Number(metrics.uniqueOui4||0)} / ${Number(metrics.uniqueOui5||0)}`);set("#metricAutoDetected",`${Number(metrics.autoVendors||0)} / ${Number(metrics.autoModels||0)}`);
  }
  async function refreshAnalysisDashboard(key){
    if(analysisDashboardCache?.key===key){renderAnalysisDashboardPayload(analysisDashboardCache.payload,"Dashboard построен по полному финальному результату.");return analysisDashboardCache.payload;}
    if(analysisDashboardPromise&&analysisDashboardPromiseKey===key)return analysisDashboardPromise;
    const revision=++analysisDashboardRevision;analysisDashboardPromiseKey=key;
    analysisDashboardPromise=(async()=>{
      let payload=null;
      if(state.resultBrowserSnapshotId&&BrowserSnapshots?.aggregate){const aggregate=await BrowserSnapshots.aggregate(state.resultBrowserSnapshotId,{limit:20});if(aggregate)payload=analysisDashboardAggregatePayload(aggregate);}
      else if(state.resultSnapshotId){const data=await api("/dashboard/metrics",{method:"POST",body:JSON.stringify(currentDevicePayload({invalid:state.invalid,snapshots:state.snapshots,settings:{vendor:"",room:"",chartLimit:20,showUnknown:true}}))});if(data?.metrics)data.metrics.invalid=Math.max(Number(data.metrics.invalid||0),Number(state.resultInvalidCount||0));payload=data||null;}
      if(payload&&revision===analysisDashboardRevision){analysisDashboardCache={key,payload};renderAnalysisDashboardPayload(payload,"Dashboard построен по полному финальному результату.");}
      return payload;
    })().catch(()=>{if(revision===analysisDashboardRevision&&$("#analysisDashboardStatus"))$("#analysisDashboardStatus").textContent="Показаны доступные данные; полный источник временно недоступен.";return null;}).finally(()=>{if(analysisDashboardPromiseKey===key){analysisDashboardPromise=null;analysisDashboardPromiseKey="";}});
    return analysisDashboardPromise;
  }
  function renderAnalysisDashboard(){
    const root=$("#analysisDashboardPanel");if(!root)return;
    const immediate=analysisDashboardLocalPayload(state.devices,state.resultSummary);renderAnalysisDashboardPayload(immediate,currentDeviceCount()?"Обновление полной статистики…":"Запустите анализ, чтобы построить dashboard.");
    const key=[state.resultBrowserSnapshotId||"",state.resultSnapshotId||"",currentDeviceCount(),state.lastAnalysis||""].join("|");
    if(state.resultBrowserSnapshotId||state.resultSnapshotId)void refreshAnalysisDashboard(key);else{$("#analysisDashboardStatus").textContent=currentDeviceCount()?"Dashboard построен по текущему полному результату.":"Запустите анализ, чтобы построить dashboard.";}
  }
  async function renderPrimaryCharts(){
    try{
      const data=await(analyticsPanelPromise||loadAnalyticsPanel()),charts=data.primaryChartsHtml||{};
      $("#vendorChart").innerHTML=charts.vendors||'<p class="muted">Недостаточно данных.</p>';
      $("#modelChart").innerHTML=charts.models||'<p class="muted">Недостаточно данных.</p>';
      $("#qualityChart").innerHTML=charts.quality||'<p class="muted">Недостаточно данных.</p>';
      $("#timelineChart").innerHTML=charts.timeline||'<p class="muted">Недостаточно данных.</p>';
    }catch(error){
      renderLocalAnalytics(dashboardDevices());
    }
  }
  async function exportChartsSvg(){
    try{
      const data=await api("/charts",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload({snapshots:state.snapshots,exportFormat:"svg"}):{devices:dashboardDevices(),snapshots:state.snapshots,exportFormat:"svg"})});
      if(!data.export)throw new Error("SVG export is empty");
      download(data.export.filename||"mac-charts.svg",data.export.content,data.export.mimeType||"image/svg+xml");
      toast("SVG-диаграммы экспортированы.");
    }catch(error){
      const payload=await collectLocalAnalytics();
      download("mac-charts.svg",LocalAnalytics.chartsSvg(payload),"image/svg+xml");
      toast("SVG-диаграммы экспортированы локально.");
    }
  }
  function normalizeDashboardSettings(settings={}){
    const defaults={query:"",vendor:"",room:"",status:"all",chartLimit:8,showUnknown:true,visibleCards:{total:true,changed:true,missing:true,unchanged:true,vendors:true,rooms:true,changedRooms:true},visibleCharts:{dynamics:true,vendors:true,fields:true,missing:true},autoRefresh:true,refreshInterval:60,changeMode:"snapshots",changeDateFrom:"",changeDateTo:"",baselineSnapshotId:"",comparisonSnapshotId:""},source=settings&&typeof settings==="object"?settings:{};
    const changeMode=source.changeMode==="period"?"period":"snapshots";
    return{...defaults,...source,changeMode,visibleCards:{...defaults.visibleCards,...(source.visibleCards||{})},visibleCharts:{...defaults.visibleCharts,...(source.visibleCharts||{})},autoRefresh:source.autoRefresh!==false,refreshInterval:Math.max(10,Math.min(300,Number(source.refreshInterval||60)))};
  }
  function configureDashboardAutoRefresh(settings=state.dashboardSettings){
    if(dashboardRefreshTimer){clearInterval(dashboardRefreshTimer);dashboardRefreshTimer=null;}
    if(settings.autoRefresh!==false)dashboardRefreshTimer=setInterval(()=>{if($("#analyticsView")?.classList.contains("active"))renderAnalytics();},Math.max(10,Math.min(300,Number(settings.refreshInterval||60)))*1000);
  }
  function applyDashboardVisibility(settings=state.dashboardSettings){
    const normalized=normalizeDashboardSettings(settings);
    $$('[data-dashboard-card]').forEach((node)=>{node.hidden=normalized.visibleCards[node.dataset.dashboardCard]===false;});
    $$('[data-dashboard-chart]').forEach((node)=>{node.hidden=normalized.visibleCharts[node.dataset.dashboardChart]===false;});
  }
  function applyDashboardSettings(settings){state.dashboardSettings=normalizeDashboardSettings({...state.dashboardSettings,...(settings||{})});const query=$("#dashboardSearchInput"),vendor=$("#dashboardVendorFilter"),room=$("#dashboardRoomFilter"),status=$("#dashboardStatusFilter");if(query&&document.activeElement!==query)query.value=state.dashboardSettings.query||"";if(vendor)vendor.value=state.dashboardSettings.vendor||"";if(room)room.value=state.dashboardSettings.room||"";if(status)status.value=state.dashboardSettings.status||"all";syncDashboardChangeControls(state.dashboardSettings);applyDashboardVisibility(state.dashboardSettings);configureDashboardAutoRefresh(state.dashboardSettings);save();}
  async function loadDashboardSettings(){try{const result=await api("/dashboard/settings");applyDashboardSettings(result.settings||{});renderAnalytics();}catch{applyDashboardSettings(state.dashboardSettings);}}
  function dashboardSettings(){const current=normalizeDashboardSettings(state.dashboardSettings);const query=$("#dashboardSearchInput"),vendor=$("#dashboardVendorFilter"),room=$("#dashboardRoomFilter"),status=$("#dashboardStatusFilter");if(query)current.query=query.value.trim();if(vendor)current.vendor=vendor.value;if(room)current.room=room.value;if(status)current.status=status.value||"all";current.chartLimit=Number(current.chartLimit||8);current.showUnknown=current.showUnknown!==false;state.dashboardSettings=current;return current;}
  function selectDashboardSettingsTab(name="cards"){$$('[data-dashboard-settings-tab]').forEach((button)=>{const active=button.dataset.dashboardSettingsTab===name;button.classList.toggle("active-filter",active);button.setAttribute("aria-selected",String(active));});$$('[data-dashboard-settings-panel]').forEach((panel)=>{panel.hidden=panel.dataset.dashboardSettingsPanel!==name;});}
  function fillDashboardSettingsDialog(settings=dashboardSettings()){const normalized=normalizeDashboardSettings(settings);$$('[data-dashboard-card-toggle]').forEach((input)=>{input.checked=normalized.visibleCards[input.dataset.dashboardCardToggle]!==false;});$$('[data-dashboard-chart-toggle]').forEach((input)=>{input.checked=normalized.visibleCharts[input.dataset.dashboardChartToggle]!==false;});$("#dashboardAutoRefresh").checked=normalized.autoRefresh!==false;$("#dashboardRefreshInterval").value=normalized.refreshInterval;}
  function dashboardDialogSettings(){const current=normalizeDashboardSettings(dashboardSettings());$$('[data-dashboard-card-toggle]').forEach((input)=>{current.visibleCards[input.dataset.dashboardCardToggle]=input.checked;});$$('[data-dashboard-chart-toggle]').forEach((input)=>{current.visibleCharts[input.dataset.dashboardChartToggle]=input.checked;});current.autoRefresh=$("#dashboardAutoRefresh").checked;current.refreshInterval=Math.max(10,Math.min(300,Number($("#dashboardRefreshInterval").value||60)));return current;}
  function showDashboardSettingsDialog(){fillDashboardSettingsDialog();selectDashboardSettingsTab("cards");if(!$("#dashboardSettingsDialog").open)$("#dashboardSettingsDialog").showModal();}
  function dashboardDevices(){return dashboardFilteredDevices||state.devices;}
  function renderDashboardFilterOptions(filters={}, settings=dashboardSettings(), filterOptionsHtml={}){
    const vendorChoice=settings.vendor||"",roomChoice=settings.room||"";
    $("#dashboardVendorFilter").innerHTML=filterOptionsHtml.vendors||'<option value="">Все производители</option>';
    $("#dashboardRoomFilter").innerHTML=filterOptionsHtml.rooms||'<option value="">Все помещения</option>';
    applyDashboardSettings({...settings,vendor:$("#dashboardVendorFilter").value,room:$("#dashboardRoomFilter").value});
  }
  function renderLocalDashboardFilterOptions(settings=dashboardSettings()){const vendorOptions=['<option value="">Все производители</option>',...localTally(state.devices,"vendor",200).map(([value])=>`<option value="${esc(value)}" ${value===settings.vendor?"selected":""}>${esc(value)}</option>`)].join(""),roomOptions=['<option value="">Все помещения</option>',...localTally(state.devices,"room",200).map(([value])=>`<option value="${esc(value)}" ${value===settings.room?"selected":""}>${esc(value)}</option>`)].join("");$("#dashboardVendorFilter").innerHTML=vendorOptions;$("#dashboardRoomFilter").innerHTML=roomOptions;applyDashboardSettings(settings);}
  function dashboardStatusContext(){
    const current=new Map((state.devices||[]).map((device)=>[normalize(device.mac||device.macFormatted),device]).filter(([mac])=>mac));
    if(!current.size)return{all:[],changed:[],missing:[],unchanged:[]};
    const changed=new Set((state.movementHistory||[]).map((item)=>normalize(item.mac||item.macFormatted)).filter((mac)=>mac&&current.has(mac)));
    const latestHistory=new Map();
    (state.snapshots||[]).forEach((snapshot)=>(snapshot.devices||[]).forEach((device)=>{const mac=normalize(device.mac||device.macFormatted);if(mac&&!latestHistory.has(mac))latestHistory.set(mac,device);}));
    (state.movementHistory||[]).forEach((item)=>{const mac=normalize(item.mac||item.macFormatted);if(mac&&!latestHistory.has(mac))latestHistory.set(mac,{mac,macFormatted:formatMac(mac),vendor:"Unknown"});});
    const changedDevices=[],unchangedDevices=[];
    current.forEach((device,mac)=>{const row={...device,dashboardStatus:changed.has(mac)?"changed":"unchanged"};(changed.has(mac)?changedDevices:unchangedDevices).push(row);});
    const missingDevices=[...latestHistory.entries()].filter(([mac])=>!current.has(mac)).map(([mac,device])=>({...device,mac:device.mac||mac,macFormatted:device.macFormatted||formatMac(mac),dashboardStatus:"missing"}));
    return{all:[...changedDevices,...unchangedDevices],changed:changedDevices,missing:missingDevices,unchanged:unchangedDevices};
  }
  function dashboardScope(devices,settings){const query=String(settings.query||"").trim().toLowerCase(),queryMac=normalize(query);return(devices||[]).filter((device)=>(!settings.vendor||String(device.vendor||"Unknown")===settings.vendor)&&(!settings.room||String(device.room||"Unknown")===settings.room)&&((settings.showUnknown!==false)||device.vendor&&device.vendor!=="Unknown")&&(!query||Object.values(device).join(" ").toLowerCase().includes(query)||(queryMac&&normalize(device.mac||device.macFormatted).includes(queryMac))));}
  function dashboardMovementCharts(displayed,missing,limit=8){
    const daily={},fields={},fieldLabels={vendor:"Производитель",model:"Модель",ip:"IP-адрес",address:"Адрес",room:"Помещение",switch_ip:"Коммутатор",switchIp:"Коммутатор",switch_port:"Порт",switchPort:"Порт"};
    (state.movementHistory||[]).forEach((item)=>{const date=String(item.changedAt||item.changed_at||item.date_str||"").slice(0,10),field=item.field||item.field_name;if(date)daily[date]=(daily[date]||0)+1;if(field)fields[fieldLabels[field]||field]=(fields[fieldLabels[field]||field]||0)+1;});
    const top=(items)=>Object.entries(items).sort((a,b)=>b[1]-a[1]).slice(0,limit),tally=(devices)=>top((devices||[]).reduce((result,device)=>{const key=device.vendor||"Unknown";result[key]=(result[key]||0)+1;return result;},{}));
    return{dynamics:Object.entries(daily).sort((a,b)=>a[0].localeCompare(b[0])).slice(-limit),vendors:tally(displayed),fields:top(fields),missing:tally(missing)};
  }
  function dashboardSnapshotId(snapshot,index){return String(snapshot?.id||snapshot?.snapshotId||snapshot?.name||`snapshot-${index+1}`);}
  function isFinalDashboardSnapshot(snapshot={}){const source=String(snapshot.source||"").toLowerCase(),name=String(snapshot.name||"").toLowerCase();if(["ip-mapping-apply","local-ip-mapping","local-vendor-model-rules"].includes(source))return false;if(["ip-маппинг","обогащение: ip-маппинг","автоопределение производителей и моделей"].includes(name))return false;return snapshot?.kind==="analysis"||["анализ:","analysis:"].some((prefix)=>name.startsWith(prefix));}
  function finalDashboardSnapshots(){
    const final=(state.snapshots||[]).map((snapshot,index)=>({snapshot,index})).filter(({snapshot})=>isFinalDashboardSnapshot(snapshot));
    return final.sort((left,right)=>{const order=(item)=>Number(item.snapshot?.snapshotOrder||0)||Date.parse(item.snapshot?.savedAt||"")||((state.snapshots||[]).length-item.index);return order(left)-order(right);}).map(({snapshot})=>snapshot);
  }
  function dashboardSnapshotOptions(){return finalDashboardSnapshots().map((snapshot,index)=>({id:dashboardSnapshotId(snapshot,index),name:String(snapshot.name||dashboardSnapshotId(snapshot,index)),date:String(snapshot.fileCreatedAt||snapshot.createdAt||snapshot.created_at||snapshot.savedAt||""),savedAt:String(snapshot.savedAt||"")}));}
  function dashboardSnapshotPair(settings=dashboardSettings(),options=dashboardSnapshotOptions()){
    if(options.length<2)return{baselineId:options[0]?.id||"",comparisonId:options[0]?.id||"",dateFrom:settings.changeDateFrom||"",dateTo:settings.changeDateTo||""};
    if(settings.changeMode!=="period"){
      const comparisonId=options.some((item)=>item.id===settings.comparisonSnapshotId)?settings.comparisonSnapshotId:options.at(-1).id;
      const comparisonIndex=Math.max(1,options.findIndex((item)=>item.id===comparisonId));
      const baselineId=options.some((item)=>item.id===settings.baselineSnapshotId)&&settings.baselineSnapshotId!==comparisonId?settings.baselineSnapshotId:options[comparisonIndex-1].id;
      return{baselineId,comparisonId,dateFrom:settings.changeDateFrom||"",dateTo:settings.changeDateTo||""};
    }
    const dated=options.map((item,index)=>({...item,index,time:Date.parse(item.date||item.savedAt||"")||0}));
    const fromTime=settings.changeDateFrom?Date.parse(`${settings.changeDateFrom}T00:00:00`):-Infinity;
    const toTime=settings.changeDateTo?Date.parse(`${settings.changeDateTo}T23:59:59`):Infinity;
    let comparison=dated.filter((item)=>item.time<=toTime).at(-1)||dated.at(-1);
    let baseline=dated.filter((item)=>item.time<fromTime&&item.index<comparison.index).at(-1);
    if(!baseline)baseline=dated.filter((item)=>item.time>=fromTime&&item.time<=toTime&&item.index<comparison.index)[0];
    if(!baseline)baseline=dated[Math.max(0,comparison.index-1)];
    if(baseline.id===comparison.id){comparison=dated[Math.min(dated.length-1,baseline.index+1)]||comparison;}
    return{baselineId:baseline.id,comparisonId:comparison.id,dateFrom:settings.changeDateFrom||new Date(baseline.time||Date.now()).toISOString().slice(0,10),dateTo:settings.changeDateTo||new Date(comparison.time||Date.now()).toISOString().slice(0,10)};
  }
  function localDashboardFleet(){
    const unique=new Set(),series=[];
    for(const [index,snapshot] of finalDashboardSnapshots().entries()){
      const snapshotIdentities=new Set();for(const device of snapshot.devices||[]){const identity=dashboardDeviceIdentity(device);if(identity){snapshotIdentities.add(identity);unique.add(identity);}}
      const count=Number(snapshot.deviceCount??snapshotIdentities.size),previous=Number(series.at(-1)?.count||0);series.push({id:dashboardSnapshotId(snapshot,index),name:snapshot.name||`Выгрузка ${index+1}`,date:snapshot.fileCreatedAt||snapshot.createdAt||"",count,delta:index?count-previous:0});
    }
    if(!series.length&&state.devices.length){for(const device of state.devices){const identity=dashboardDeviceIdentity(device);if(identity)unique.add(identity);}series.push({id:"current",name:"Текущий набор",date:state.lastAnalysis||"",count:unique.size,delta:0});}
    return{uniqueAcrossUploads:Math.max(unique.size,Number(series.at(-1)?.count||0)),latestCount:Number(series.at(-1)?.count||0),series};
  }
  function selectLatestDashboardPair(){const options=dashboardSnapshotOptions();if(options.length<2)return false;state.dashboardSettings=normalizeDashboardSettings({...state.dashboardSettings,changeMode:"snapshots",changeDateFrom:"",changeDateTo:"",baselineSnapshotId:options.at(-2).id,comparisonSnapshotId:options.at(-1).id});return true;}
  function compactDashboardDevice(device){
    if(!device||typeof device!=="object")return null;
    const value=(...keys)=>{for(const key of keys){const found=String(device[key]??"").trim();if(found)return found;}return"";};
    return{internalDeviceId:value("internalDeviceId","internal_device_id"),mac:normalize(device.mac||device.macFormatted)||"",vendor:value("vendor"),model:value("model"),ip:value("ip"),address:value("address"),room:value("room"),smartroomId:value("smartroomId","smartroom_id"),switchIp:value("switchIp","switch_ip"),switchPort:value("switchPort","switch_port"),hostname:value("hostname","host_name"),serialNumber:value("serialNumber","serial_number","serial"),deviceId:value("deviceId","device_id"),deviceName:value("deviceName","device_name"),hasConflict:Boolean(device.hasConflict||(device.conflicts||[]).length)};
  }
  function dashboardDeviceIdentity(device){return DeviceIdentity.comparisonKey(compactDashboardDevice(device)||{});}
  function dashboardChangeIdentity(item){return dashboardDeviceIdentity(item.afterDevice||item.beforeDevice||{mac:item.mac,smartroomId:item.smartroomId});}
  function dashboardChangeSeverity(type,field,beforeDevice=null,afterDevice=null){
    const previous=compactDashboardDevice(beforeDevice),current=compactDashboardDevice(afterDevice);
    if(field==="switchIp"&&previous?.switchIp&&current?.switchIp&&previous.switchIp!==current.switchIp)return"critical";
    if(field==="ip"&&previous?.ip&&current?.ip&&previous.ip!==current.ip)return"critical";
    if(field==="mac")return"critical";
    if(current?.hasConflict)return"critical";
    if(["ip","address","room"].includes(field)||type==="removed")return"high";
    if(["vendor","model","smartroomId","smartroom_id","switchIp","switchPort","switch_ip","switch_port"].includes(field))return"medium";
    return"low";
  }
  function summarizeDashboardChanges(changes=[]){
    const identities=(type)=>new Set(changes.filter((item)=>item.type===type).map(dashboardChangeIdentity).filter(Boolean));
    const changedRooms=new Set(changes.map((item)=>String(item.afterDevice?.room||item.beforeDevice?.room||"").trim()).filter(Boolean));
    return{added:identities("added").size,removed:identities("removed").size,modified:identities("modified").size,critical:new Set(changes.filter((item)=>item.severity==="critical").map(dashboardChangeIdentity).filter(Boolean)).size,changedRooms:changedRooms.size,changedRoomValues:Array.from(changedRooms).sort(),total:new Set(changes.map(dashboardChangeIdentity).filter(Boolean)).size,fieldChanges:changes.length};
  }
  function dashboardDurationMs(fromValue="",toValue=""){const from=Date.parse(String(fromValue||"")),to=Date.parse(String(toValue||""));return Number.isFinite(from)&&Number.isFinite(to)?Math.max(0,to-from):0;}
  function dashboardDurationLabel(milliseconds=0){const value=Math.max(0,Number(milliseconds)||0),days=Math.floor(value/86400000),hours=Math.floor(value%86400000/3600000),minutes=Math.floor(value%3600000/60000);if(days)return`${days} дн. ${hours} ч.`;if(hours)return`${hours} ч. ${minutes} мин.`;return`${Math.max(0,minutes)} мин.`;}
  function groupDashboardChanges(changes=[]){
    const priority={critical:4,high:3,medium:2,low:1},groups=new Map();
    for(const item of changes){
      const mac=normalize(item.mac||item.macFormatted),identity=dashboardChangeIdentity(item);if(!identity)continue;
      let group=groups.get(identity);
      if(!group){const context=compactDashboardDevice(item.afterDevice)||compactDashboardDevice(item.beforeDevice)||{};group={identity,mac,macFormatted:formatMac(mac)||(context.deviceId?`ID: ${context.deviceId}`:context.serialNumber?`S/N: ${context.serialNumber}`:context.internalDeviceId||"Устройство"),date:item.date||"",source:item.source||"",severity:item.severity||"low",types:new Set(),changes:[],beforeDevice:compactDashboardDevice(item.beforeDevice),afterDevice:compactDashboardDevice(item.afterDevice)};groups.set(identity,group);}
      group.types.add(item.type||"modified");group.changes.push(item);
      if(priority[item.severity]>priority[group.severity])group.severity=item.severity;
      if(String(item.date||"")>String(group.date||""))group.date=item.date;
      group.beforeDevice=group.beforeDevice||compactDashboardDevice(item.beforeDevice);group.afterDevice=group.afterDevice||compactDashboardDevice(item.afterDevice);
    }
    for(const group of groups.values()){
      const fields=new Set(group.changes.map((item)=>item.field));
      if(fields.has("switchIp")&&!fields.has("ip")&&!fields.has("room")&&!group.changes.some((item)=>item.beforeDevice||item.afterDevice)){
        group.severity="critical";group.changes.forEach((item)=>{if(item.field==="switchIp")item.severity="critical";});
      }
      group.device=group.afterDevice||group.beforeDevice||{};
      group.type=group.types.has("modified")?"modified":group.types.has("added")?"added":"removed";
    }
    return Array.from(groups.values()).sort((a,b)=>String(b.date).localeCompare(String(a.date))||a.mac.localeCompare(b.mac));
  }
  function localDashboardChangeAnalysis(settings=dashboardSettings()){
    const fieldLabels={vendor:"Производитель",model:"Модель",ip:"IP-адрес",address:"Адрес помещения",room:"Помещение",smartroomId:"Smartroom ID",switchIp:"IP коммутатора",switchPort:"Порт",hostname:"Hostname",serialNumber:"Серийный номер",deviceId:"ID устройства",deviceName:"Название устройства",mac:"MAC / физический адрес",identityConflict:"Конфликт идентификации",device:"Устройство"},typeLabels={added:"Добавлено",removed:"Отсутствует",modified:"Изменено"},snapshotRows=finalDashboardSnapshots(),options=dashboardSnapshotOptions(),changes=[];
    const row=(mac,date,type,field="device",before="",after="",source="history",beforeDevice=null,afterDevice=null)=>{field=({switch_ip:"switchIp",switch_port:"switchPort"})[field]||field;changes.push({mac,macFormatted:formatMac(mac),date,type,typeLabel:typeLabels[type]||"Изменено",field,fieldLabel:fieldLabels[field]||field,before:String(before||"-"),after:String(after||"-"),source:String(source||"history"),beforeDevice:compactDashboardDevice(beforeDevice),afterDevice:compactDashboardDevice(afterDevice),severity:dashboardChangeSeverity(type,field,beforeDevice,afterDevice)});};
    const pair=dashboardSnapshotPair(settings,options);
    let baselineSnapshotId=pair.baselineId,comparisonSnapshotId=pair.comparisonId,dateFrom=pair.dateFrom,dateTo=pair.dateTo;
    if(snapshotRows.length>=2&&baselineSnapshotId&&comparisonSnapshotId&&baselineSnapshotId!==comparisonSnapshotId){
      const byId=new Map(snapshotRows.map((snapshot,index)=>[dashboardSnapshotId(snapshot,index),snapshot])),baseline=byId.get(baselineSnapshotId)||snapshotRows.at(-2),comparison=byId.get(comparisonSnapshotId)||snapshotRows.at(-1),date=comparison.fileCreatedAt||comparison.createdAt||comparison.created_at||"",paired=DeviceIdentity.pairSets(baseline.devices||[],comparison.devices||[]);
      paired.added.forEach((device)=>row(normalize(device.mac||device.macFormatted),date,"added","device","",device.source||"Устройство","snapshot",null,device));
      paired.removed.forEach((device)=>row(normalize(device.mac||device.macFormatted),date,"removed","device",device.source||"Устройство","","snapshot",device,null));
      const fields=["mac","vendor","model","ip","address","room","smartroomId","switchIp","switchPort","hostname","serialNumber","deviceId","deviceName"];
      paired.pairs.forEach(([before,device])=>{fields.forEach((field)=>{const oldValue=field==="mac"?normalize(before.mac||before.macFormatted):String(before[field]||""),newValue=field==="mac"?normalize(device.mac||device.macFormatted):String(device[field]||"");if(oldValue===newValue||oldValue&&!newValue)return;row(normalize(device.mac||device.macFormatted)||normalize(before.mac||before.macFormatted),date,"modified",field,oldValue,newValue,"snapshot",before,device);});if(device.hasConflict||(device.conflicts||[]).length)row(normalize(device.mac||device.macFormatted),date,"modified","identityConflict","","Обнаружен конфликт источников","snapshot",before,device);});
    }else{
      let end=dateTo?new Date(`${dateTo}T23:59:59`):null,start=dateFrom?new Date(`${dateFrom}T00:00:00`):null;const validMovementDates=(state.movementHistory||[]).map((item)=>Date.parse(item.changedAt||item.changed_at||item.date_str||"")).filter(Number.isFinite);if(!end)end=new Date(validMovementDates.length?Math.max(...validMovementDates):Date.now());if(!start)start=new Date(end.getTime()-30*86400000);if(start>end){const oldStart=start;start=new Date(end);end=new Date(oldStart);end.setHours(23,59,59,999);}dateFrom=start.toISOString().slice(0,10);dateTo=end.toISOString().slice(0,10);
      const localTypes={"добавлено":"added","удалено":"removed","отсутствует":"removed","изменено":"modified"},localFields=Object.fromEntries(Object.entries(labels).map(([key,value])=>[String(value).toLowerCase(),key]));
      (state.movementHistory||[]).forEach((item)=>{const date=String(item.changedAt||item.changed_at||item.date_str||""),parsed=date?new Date(date):null;if(!parsed||Number.isNaN(parsed.valueOf())||parsed<start||parsed>end)return;let type=String(item.type||item.change_type||"modified").toLowerCase();type=localTypes[type]||type;if(!["added","removed","modified"].includes(type))type="modified";const rawField=item.field||item.field_name||"device",field=localFields[String(rawField).toLowerCase()]||rawField;row(normalize(item.mac||item.macFormatted),date,type,field,item.before??item.from_value??item.old_value,item.after??item.to_value??item.new_value,item.source||item.file_name||"history",item.beforeDevice,item.afterDevice);});
    }
    const baselineDate=settings.changeMode==="period"?`${dateFrom}T00:00:00`:options.find((item)=>item.id===baselineSnapshotId)?.date||"",comparisonDate=settings.changeMode==="period"?`${dateTo}T23:59:59.999`:options.find((item)=>item.id===comparisonSnapshotId)?.date||"";changes.forEach(attachDdioHistoryHint);const groups=groupDashboardChanges(changes);changes.sort((a,b)=>String(b.date).localeCompare(String(a.date)));return{mode:settings.changeMode,dateFrom,dateTo,baselineSnapshotId,comparisonSnapshotId,baselineDate,comparisonDate,durationMs:dashboardDurationMs(baselineDate,comparisonDate),snapshotOptions:options,summary:summarizeDashboardChanges(changes),changes,groups};
  }
  function browserSnapshotChangeAnalysis(comparison,options=[],settings=dashboardSettings()){
    if(!comparison)return{mode:"snapshots",baselineSnapshotId:"",comparisonSnapshotId:"",snapshotOptions:options,summary:{added:0,removed:0,modified:0,critical:0,total:0},changes:[]};
    const fieldLabels={vendor:"Производитель",model:"Модель",ip:"IP-адрес",address:"Адрес помещения",room:"Помещение",smartroomId:"Smartroom ID",switchIp:"IP коммутатора",switchPort:"Порт",device:"Устройство"},typeLabels={added:"Добавлено",removed:"Отсутствует",modified:"Изменено"};
    const inScope=(item)=>{const devices=[item.afterDevice,item.beforeDevice].filter(Boolean),query=String(settings.query||"").trim().toLowerCase(),queryMac=normalize(query);return(!settings.vendor||devices.some((device)=>String(device.vendor||"")===settings.vendor))&&(!settings.room||devices.some((device)=>String(device.room||"")===settings.room))&&(!query||devices.some((device)=>Object.values(device).join(" ").toLowerCase().includes(query)||(queryMac&&normalize(device.mac||device.macFormatted).includes(queryMac))));};
    const changes=(comparison.changes||[]).filter(inScope).map((item)=>{const field=item.field||"device",type=item.type||"modified",change={...item,date:item.changedAt||comparison.changedAt||"",macFormatted:formatMac(item.mac),typeLabel:typeLabels[type]||"Изменено",fieldLabel:fieldLabels[field]||field,before:String(item.before||"-"),after:String(item.after||"-"),severity:dashboardChangeSeverity(type,field,item.beforeDevice,item.afterDevice)};return attachDdioHistoryHint(change);});
    const raw=comparison.summary||{},derived=summarizeDashboardChanges(changes),filtered=Boolean(settings.query||settings.vendor||settings.room),summary=filtered?{...derived,modifiedFields:changes.filter((item)=>item.type==="modified").length,modifiedDevices:derived.modified,changedDevices:derived.total,unchanged:0}:{...derived,added:Number(raw.added??derived.added),removed:Number(raw.removed??derived.removed),modified:Number(raw.modifiedDevices??raw.modified??derived.modified),critical:Number(raw.critical??derived.critical),total:Number(raw.total??derived.total),modifiedFields:Number(raw.modifiedFields??changes.filter((item)=>item.type==="modified").length),modifiedDevices:Number(raw.modifiedDevices??derived.modified),changedDevices:Number(raw.changedDevices??raw.total??derived.total),unchanged:Number(raw.unchanged||0)};
    const baselineDate=options.find((item)=>item.id===comparison.baselineSnapshotId)?.date||"",comparisonDate=options.find((item)=>item.id===comparison.comparisonSnapshotId)?.date||comparison.changedAt||"";
    return{mode:settings.changeMode||"snapshots",dateFrom:settings.changeDateFrom||"",dateTo:settings.changeDateTo||"",baselineSnapshotId:comparison.baselineSnapshotId,comparisonSnapshotId:comparison.comparisonSnapshotId,baselineDate,comparisonDate,durationMs:dashboardDurationMs(baselineDate,comparisonDate),snapshotOptions:options,summary,changes,groups:groupDashboardChanges(changes),fieldCounts:comparison.fieldCounts||[]};
  }
  async function loadBrowserDashboardCache(settings=dashboardSettings()){
    if(!state.resultBrowserSnapshotId||!BrowserSnapshots?.aggregate)return null;
    const options=dashboardSnapshotOptions(),currentId=state.resultBrowserSnapshotId,pair=dashboardSnapshotPair(settings,options),baselineId=pair.baselineId,comparisonId=pair.comparisonId;
    const effectiveSettings={...settings,baselineSnapshotId:baselineId,comparisonSnapshotId:comparisonId,changeDateFrom:pair.dateFrom,changeDateTo:pair.dateTo};
    const fleetCacheKey=JSON.stringify({snapshots:options.map((item)=>[item.id,item.date,item.savedAt]),query:settings.query,vendor:settings.vendor,room:settings.room,showUnknown:settings.showUnknown}),cacheKey=JSON.stringify({fleetCacheKey,currentId,baselineId,comparisonId,mode:settings.changeMode,dateFrom:pair.dateFrom,dateTo:pair.dateTo});
    if(browserDashboardCache?.cacheKey===cacheKey)return{...browserDashboardCache,settings:effectiveSettings};
    const aggregate=await BrowserSnapshots.aggregate(currentId,{limit:200,vendor:settings.vendor,room:settings.room,query:settings.query,showUnknown:settings.showUnknown});if(!aggregate)return null;
    const filterAggregate=settings.query||settings.vendor||settings.room||settings.showUnknown===false?await BrowserSnapshots.aggregate(currentId,{limit:200}):aggregate;
    let fleet=state.dashboardFleetCache?.key===fleetCacheKey?state.dashboardFleetCache.value:null;
    if(!fleet){fleet=BrowserSnapshots.aggregateSeries?await BrowserSnapshots.aggregateSeries(options,{vendor:settings.vendor,room:settings.room,query:settings.query,showUnknown:settings.showUnknown}):{uniqueAcrossUploads:aggregate.uniqueMacs,latestCount:aggregate.devices,series:options.map((item)=>({id:item.id,name:item.name,date:item.date,count:Number(finalDashboardSnapshots().find((snapshot,index)=>dashboardSnapshotId(snapshot,index)===item.id)?.deviceCount||0)}))};state.dashboardFleetCache={key:fleetCacheKey,value:fleet};save();}
    const comparison=baselineId&&comparisonId&&baselineId!==comparisonId&&BrowserSnapshots.compareSnapshots?await BrowserSnapshots.compareSnapshots(baselineId,comparisonId,{limit:MemoryGuard.limits.movementRows||5000}):null;
    const changeAnalysis=comparison?browserSnapshotChangeAnalysis(comparison,options,effectiveSettings):localDashboardChangeAnalysis(effectiveSettings),roomRows=(aggregate.rooms||[]).map((item)=>({label:item.label,count:item.value,percentOfAssigned:Number((item.value/Math.max(1,aggregate.withRoom)*100).toFixed(1)),percentOfAll:Number((item.value/Math.max(1,aggregate.devices)*100).toFixed(1))}));
    const report={total:aggregate.devices,vendors:(aggregate.vendors||[]).map((item)=>({label:item.label,count:item.value,percent:Number((item.value/Math.max(1,aggregate.devices)*100).toFixed(1))})),models:(aggregate.models||[]).map((item)=>({label:item.label,count:item.value,percent:Number((item.value/Math.max(1,aggregate.devices)*100).toFixed(1))})),rooms:roomRows,roomOccupancy:{assignedDevices:aggregate.withRoom,unassignedDevices:Math.max(0,aggregate.devices-aggregate.withRoom),assignedPercent:Number((aggregate.withRoom/Math.max(1,aggregate.devices)*100).toFixed(1)),uniqueRooms:aggregate.uniqueRooms,averageDevicesPerRoom:aggregate.uniqueRooms?Number((aggregate.withRoom/aggregate.uniqueRooms).toFixed(1)):0,mostOccupied:roomRows[0]||null,rooms:roomRows},coverage:{uniqueVendors:aggregate.uniqueVendors,uniqueModels:aggregate.uniqueModels,address:{count:aggregate.withAddress,percent:Number((aggregate.withAddress/Math.max(1,aggregate.devices)*100).toFixed(1))},room:{count:aggregate.withRoom,percent:Number((aggregate.withRoom/Math.max(1,aggregate.devices)*100).toFixed(1))},ip:{count:aggregate.withIp,percent:Number((aggregate.withIp/Math.max(1,aggregate.devices)*100).toFixed(1))},switch:{count:aggregate.withSwitch,percent:Number((aggregate.withSwitch/Math.max(1,aggregate.devices)*100).toFixed(1))}}};
    report.reportText=["=== АНАЛИТИКА ПО ФИНАЛЬНОМУ ОБОГАЩЁННОМУ ФАЙЛУ ===","",`Всего устройств: ${aggregate.devices}`,`Определено производителей: ${aggregate.known} (${aggregate.knownPercent}%)`,`Не определено: ${aggregate.unknown}`,`Уникальных производителей: ${aggregate.uniqueVendors}`,`Уникальных моделей: ${aggregate.uniqueModels}`,`Помещений: ${aggregate.uniqueRooms}`,`Коммутаторов: ${aggregate.uniqueSwitches}`,"",`С адресом: ${aggregate.withAddress}`,`С помещением: ${aggregate.withRoom}`,`С IP: ${aggregate.withIp}`,`С коммутатором: ${aggregate.withSwitch}`].join("\n");
    return{cacheKey,aggregate,filterAggregate,fleet,comparison,changeAnalysis,report,settings:effectiveSettings};
  }
  function renderBrowserDashboardCache(cache){
    if(!cache)return false;browserDashboardCache=cache;const {aggregate,comparison,changeAnalysis,report}=cache,filterAggregate=cache.filterAggregate||aggregate,fleet=cache.fleet||{uniqueAcrossUploads:aggregate.uniqueMacs,latestCount:aggregate.devices,series:[]},settings=cache.settings||dashboardSettings(),summary=changeAnalysis.summary||{},status=settings.status||"all",changeDevices=(type)=>groupDashboardChanges(changeAnalysis.changes||[]).filter((item)=>item.types.has(type)).map((item)=>item.device||{}),vendorCounts=(devices)=>{const counts=new Map();for(const device of devices){const vendor=String(device.vendor||"Unknown");counts.set(vendor,(counts.get(vendor)||0)+1);}return[...counts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,20).map(([label,value])=>({label,value}));},vendorRows=status==="changed"?(comparison?.changedVendors||vendorCounts(changeDevices("modified"))):status==="missing"?(comparison?.missingVendors||vendorCounts(changeDevices("removed"))):status==="unchanged"?(comparison?.unchangedVendors||[]):aggregate.vendors||[];
    state.dashboardSettings=normalizeDashboardSettings({...state.dashboardSettings,...settings});dashboardFilteredDevices=state.devices;
    const optionHtml=(emptyLabel,rows,selected)=>`<option value="">${emptyLabel}</option>`+(rows||[]).map((item)=>`<option value="${esc(item.label)}" ${item.label===selected?"selected":""}>${esc(item.label)}</option>`).join("");$("#dashboardVendorFilter").innerHTML=optionHtml("Все производители",filterAggregate.vendors,settings.vendor);$("#dashboardRoomFilter").innerHTML=optionHtml("Все помещения",filterAggregate.rooms,settings.room);
    const modifiedDevices=Number(summary.modifiedDevices??summary.modified??0),addedDevices=Number(summary.added||0),unchangedDevices=Math.max(0,Number(fleet.latestCount||aggregate.devices)-modifiedDevices-addedDevices),fieldCounts=new Map();for(const item of changeAnalysis.changes||[]){const label=item.fieldLabel||item.field||"Устройство";fieldCounts.set(label,(fieldCounts.get(label)||0)+1);}const derivedFields=[...fieldCounts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,20).map(([label,value])=>({label,value}));
    const metrics={devices:aggregate.devices,total:Number(fleet.latestCount||aggregate.devices),totalAcross:Number(fleet.uniqueAcrossUploads||aggregate.uniqueMacs),changed:modifiedDevices,missing:Number(summary.removed||0),unchanged:unchangedDevices,vendors:aggregate.uniqueVendors,rooms:aggregate.uniqueRooms,uniqueMacs:Number(fleet.uniqueAcrossUploads||aggregate.uniqueMacs),switches:aggregate.uniqueSwitches},statusCharts={dynamics:(fleet.series||[]).slice(-20).map((item)=>({label:String(item.name||item.date||item.id).slice(0,28),value:Number(item.count||0)})),vendors:vendorRows,fields:comparison?.fieldCounts||changeAnalysis.fieldCounts||derivedFields,missing:comparison?.missingVendors||vendorCounts(changeDevices("removed"))};
    renderDashboardStatus({metrics,settings:state.dashboardSettings,changeAnalysis,statusCharts});$("#snapshotMetric").textContent=finalDashboardSnapshots().length;$("#uniqueMacMetric").textContent=fleet.uniqueAcrossUploads||aggregate.uniqueMacs;$("#switchMetric").textContent=aggregate.uniqueSwitches;$("#roomMetric").textContent=aggregate.uniqueRooms;
    $("#vendorChart").innerHTML=localChartHtml((aggregate.vendors||[]).slice(0,20).map((item)=>[item.label,item.value]));$("#modelChart").innerHTML=localChartHtml((aggregate.models||[]).slice(0,20).map((item)=>[item.label,item.value]),"Нет данных моделей.");$("#qualityChart").innerHTML=localChartHtml([["Опознано",aggregate.known],["Unknown",aggregate.unknown],["Ошибки",aggregate.invalid]].filter((item)=>item[1]>0));$("#timelineChart").innerHTML=localChartHtml((fleet.series||[]).slice(-20).map((item)=>[String(item.name||item.date||item.id).slice(0,28),Number(item.count||0)]));renderAnalyticsReport(report,"local");
    const overview=[["Устройств",aggregate.devices],["Производителей",aggregate.uniqueVendors],["Моделей",aggregate.uniqueModels],["Помещений",aggregate.uniqueRooms],["Коммутаторов",aggregate.uniqueSwitches]];$("#backendChartsPanel").innerHTML=localChartHtml(overview);$("#backendStatisticsChart").innerHTML=localChartHtml([["Финальных снимков",finalDashboardSnapshots().length],["Текущих устройств",aggregate.devices],["Изменений",Number(summary.total||0)]]);$("#temporalStatisticsChart").innerHTML=localChartHtml(dashboardSnapshotOptions().slice(-12).map((item)=>[item.date?.slice(0,10)||item.name,Number(finalDashboardSnapshots().find((snapshot,index)=>dashboardSnapshotId(snapshot,index)===item.id)?.deviceCount||0)]),"Снимков пока нет.");$("#clusterChart").innerHTML=localChartHtml((aggregate.rooms||[]).slice(0,12).map((item)=>[item.label,item.value]),"Нет данных для кластеров помещений.");$("#topologyGraph").innerHTML=localChartHtml([["Коммутаторов",aggregate.uniqueSwitches],["Устройств с коммутатором",aggregate.withSwitch],["Без коммутатора",Math.max(0,aggregate.devices-aggregate.withSwitch)]]);$("#qualityInsights").innerHTML=localChartHtml([["Не определён производитель",aggregate.unknown],["Нет IP",Math.max(0,aggregate.devices-aggregate.withIp)],["Нет помещения",Math.max(0,aggregate.devices-aggregate.withRoom)],["Ошибки MAC",aggregate.invalid]].filter((item)=>item[1]>0),"Проблем качества не найдено.");$("#qualityReportsList").innerHTML='<p class="muted">Показан потоковый анализ текущего финального снимка.</p>';return true;
  }
  function syncDashboardChangeControls(settings=state.dashboardSettings,options=dashboardSnapshotOptions()){
    const mode=$("#dashboardChangeMode");if(mode)mode.value=settings.changeMode||"period";if($("#dashboardChangeDateFrom"))$("#dashboardChangeDateFrom").value=settings.changeDateFrom||"";if($("#dashboardChangeDateTo"))$("#dashboardChangeDateTo").value=settings.changeDateTo||"";
    if($("#dashboardPeriodControls"))$("#dashboardPeriodControls").hidden=(settings.changeMode==="snapshots");if($("#dashboardSnapshotControls"))$("#dashboardSnapshotControls").hidden=(settings.changeMode!=="snapshots");
    const fill=(selector,selected)=>{const node=$(selector);if(!node)return;node.innerHTML=options.length?options.map((item)=>`<option value="${esc(item.id)}" ${item.id===selected?"selected":""}>${esc(item.name)}${item.date?` · ${esc(item.date.slice(0,10))}`:""}</option>`).join(""):'<option value="">Нет сохранённых выгрузок</option>';};fill("#dashboardBaselineSnapshot",settings.baselineSnapshotId||options.at(-2)?.id||"");fill("#dashboardComparisonSnapshot",settings.comparisonSnapshotId||options.at(-1)?.id||"");
  }
  function renderDashboardChanges(analysis={}){dashboardChangeAnalysis=analysis?.changes?analysis:localDashboardChangeAnalysis();dashboardChangeAnalysis.groups=groupDashboardChanges(dashboardChangeAnalysis.changes||[]);const derived=summarizeDashboardChanges(dashboardChangeAnalysis.changes||[]),provided=dashboardChangeAnalysis.summary&&typeof dashboardChangeAnalysis.summary==="object"?dashboardChangeAnalysis.summary:{};dashboardChangeAnalysis.summary={...derived,...provided,changedRoomValues:provided.changedRoomValues||derived.changedRoomValues};const summary=dashboardChangeAnalysis.summary||{},set=(selector,value)=>{if($(selector))$(selector).textContent=Number(value||0).toLocaleString("ru-RU");};set("#dashboardChangeTotal",summary.total);set("#dashboardCriticalCount",summary.critical);set("#dashboardAddedCount",summary.added);set("#dashboardRemovedCount",summary.removed);set("#dashboardModifiedCount",summary.modified);set("#dashboardChangedRoomMetric",summary.changedRooms);const duration=dashboardChangeAnalysis.durationMs?` · ${dashboardDurationLabel(dashboardChangeAnalysis.durationMs)}`:"",label=dashboardChangeAnalysis.mode==="snapshots"?`Выгрузки: ${dashboardChangeAnalysis.baselineSnapshotId||"-"} → ${dashboardChangeAnalysis.comparisonSnapshotId||"-"}${duration}`:`Период: ${dashboardChangeAnalysis.dateFrom||"-"} → ${dashboardChangeAnalysis.dateTo||"-"}${duration}`;if($("#dashboardChangesPeriodLabel"))$("#dashboardChangesPeriodLabel").textContent=label;syncDashboardChangeControls({...state.dashboardSettings,...dashboardChangeAnalysis},dashboardChangeAnalysis.snapshotOptions||dashboardSnapshotOptions());renderDashboardChangesTable();}
  function syncDashboardChangeTabState(){
    const active=DashboardChangeTabs.tabForFilters($("#dashboardChangeSeverityFilter")?.value,$("#dashboardChangeTypeFilter")?.value);
    $$('[data-dashboard-change-type]').forEach((button)=>{const selected=Boolean(active)&&button.dataset.dashboardChangeType===active;button.classList.toggle("active-filter",selected);button.setAttribute("aria-selected",String(selected));button.tabIndex=selected?0:-1;});
    return active;
  }
  function selectDashboardChangeTab(type="all",focus=false){
    const tab=DashboardChangeTabs.normalizeTab(type),filters=DashboardChangeTabs.filtersForTab(tab),severity=$("#dashboardChangeSeverityFilter"),typeFilter=$("#dashboardChangeTypeFilter");
    if(severity)severity.value=filters.severity;if(typeFilter)typeFilter.value=filters.type;dashboardChangeTypeFilter=filters.type;syncDashboardChangeTabState();renderDashboardChangesTable();
    if(focus){const button=$(`[data-dashboard-change-type="${tab}"]`);if(button)button.focus();}
  }
  function handleDashboardChangeTabKeydown(event){
    const button=event.target.closest("[data-dashboard-change-type]");if(!button||!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
    event.preventDefault();selectDashboardChangeTab(DashboardChangeTabs.nextTab(button.dataset.dashboardChangeType,event.key),true);
  }
  function renderDashboardChangesTable(){
    const severity=$("#dashboardChangeSeverityFilter")?.value||"all",type=$("#dashboardChangeTypeFilter")?.value||dashboardChangeTypeFilter||"all",query=($("#dashboardChangeSearch")?.value||"").trim().toLowerCase(),macQuery=String($("#dashboardChangeMacSearch")?.value||"").toUpperCase().replace(/[^0-9A-F]/g,""),labels={critical:"Критическое",high:"Высокое",medium:"Среднее",low:"Низкое"},typeLabels={added:"Добавлено",removed:"Отсутствует",modified:"Изменено"};
    dashboardChangeTypeFilter=type;syncDashboardChangeTabState();
    const groups=(dashboardChangeAnalysis.groups||groupDashboardChanges(dashboardChangeAnalysis.changes||[])).filter((group)=>(severity==="all"||group.severity===severity)&&(type==="all"||group.types.has(type))&&(!macQuery||String(group.mac||"").includes(macQuery))&&(!query||[group.macFormatted,group.device.vendor,group.device.model,group.device.ip,group.device.address,group.device.room,group.device.smartroomId,group.device.switchIp,group.source,...group.changes.flatMap((item)=>[item.fieldLabel,item.before,item.after])].some((value)=>String(value||"").toLowerCase().includes(query)))).slice(0,1000);
    $("#dashboardChangesBody").innerHTML=groups.length?groups.map((group,index)=>{
      const groupId=`dashboard-change-${index}`,device=group.device||{},fields=group.changes.map((item)=>item.fieldLabel).filter((value,index,all)=>all.indexOf(value)===index).join(", ");
      const criticalHint=group.changes.map(ddioHistoryBadge).find(Boolean)||"";
      const deviceLink=group.mac?`<button class="link-button" data-mac="${esc(group.mac)}">${esc(group.macFormatted||group.mac)}</button>`:`<span>${esc(group.macFormatted||group.identity)}</span>`,parent=`<tr class="change-row change-${esc(group.severity)} dashboard-change-parent" data-dashboard-change-group="${groupId}"><td><span class="severity-badge severity-${esc(group.severity)}">${labels[group.severity]||group.severity}</span>${criticalHint}</td><td>${esc(String(group.date||"-").replace("T"," ").slice(0,19))}</td><td><button class="movement-group-toggle" data-toggle-dashboard-change="${groupId}" aria-expanded="false" title="Развернуть изменения">▸</button> ${deviceLink}</td><td>${esc(typeLabels[group.type]||group.type)}</td><td>${esc(device.model||"-")}</td><td>${esc(device.address||"-")}</td><td>${esc(device.room||"-")}</td><td>${esc(fields||"Устройство")}</td><td>${esc(group.source||"-")}</td></tr>`;
      const children=group.changes.map((item)=>`<tr class="dashboard-change-child change-${esc(item.severity)}" data-dashboard-change-child="${groupId}" hidden><td>${ddioHistoryBadge(item)}</td><td></td><td></td><td>${esc(typeLabels[item.type]||item.type)}</td><td colspan="3">${esc(item.fieldLabel)}</td><td><span class="change-before">${esc(item.before)}</span> → <span class="change-after">${esc(item.after)}</span></td><td>${esc(item.source||group.source||"-")}</td></tr>`).join("");
      return parent+children;
    }).join(""):'<tr><td colspan="9" class="empty-state">Изменений по выбранным условиям не найдено.</td></tr>';
  }
  function showDashboardChangesDialog(type="all"){selectDashboardChangeTab(type);const dialog=$("#dashboardChangesDialog");if(dialog&&!dialog.open)dialog.showModal();}
  function showDashboardDynamicsDialog(){
    const series=browserDashboardCache?.fleet?.series||dashboardSnapshotOptions().map((item)=>{const snapshot=finalDashboardSnapshots().find((entry,index)=>dashboardSnapshotId(entry,index)===item.id);return{...item,count:Number(snapshot?.deviceCount||(snapshot?.devices||[]).length||0)};});
    const body=$("#dashboardDynamicsBody");if(body)body.innerHTML=series.length?series.map((item,index)=>`<tr><td>${esc(String(item.date||item.savedAt||"-").replace("T"," ").slice(0,19))}</td><td>${esc(item.name||item.id)}</td><td>${Number(item.count||0)}</td><td class="${Number(item.delta||0)<0?"negative-delta":"positive-delta"}">${index?`${Number(item.delta||0)>0?"+":""}${Number(item.delta||0)}`:"-"}</td></tr>`).join(""):'<tr><td colspan="4" class="empty-state">Сохранённых выгрузок пока нет.</td></tr>';const dialog=$("#dashboardDynamicsDialog");if(dialog&&!dialog.open)dialog.showModal();
  }
  function readDashboardChangeControls(){const current=dashboardSettings();current.changeMode=$("#dashboardChangeMode")?.value||"period";current.changeDateFrom=$("#dashboardChangeDateFrom")?.value||"";current.changeDateTo=$("#dashboardChangeDateTo")?.value||"";current.baselineSnapshotId=$("#dashboardBaselineSnapshot")?.value||"";current.comparisonSnapshotId=$("#dashboardComparisonSnapshot")?.value||"";state.dashboardSettings=normalizeDashboardSettings(current);save();return state.dashboardSettings;}
  function renderDashboardStatus(payload={}){
    const metrics=payload.metrics||{},total=Number(metrics.total||0),changeSummary=payload.changeAnalysis?.summary,changed=Number(changeSummary?.modified??metrics.changed??0),missing=Number(changeSummary?.removed??metrics.missing??0),added=Number(changeSummary?.added||0),unchanged=changeSummary?Math.max(0,total-changed-added):Number(metrics.unchanged||0),settings=payload.settings||dashboardSettings(),charts=payload.statusCharts||{};
    const set=(selector,value)=>{const node=$(selector);if(node)node.textContent=value;};
    set("#dashboardTotalMetric",metrics.totalAcross!==undefined?`${Number(metrics.totalAcross||0).toLocaleString("ru-RU")} / ${total.toLocaleString("ru-RU")}`:total.toLocaleString("ru-RU"));set("#dashboardChangedMetric",changed.toLocaleString("ru-RU"));set("#dashboardMissingMetric",missing.toLocaleString("ru-RU"));set("#dashboardUnchangedMetric",unchanged.toLocaleString("ru-RU"));set("#dashboardVendorMetric",Number(metrics.vendors||0).toLocaleString("ru-RU"));set("#dashboardRoomCountMetric",Number(metrics.rooms||0).toLocaleString("ru-RU"));set("#dashboardChangedRoomMetric",Number(payload.changeAnalysis?.summary?.changedRooms||0).toLocaleString("ru-RU"));
    const critical=Number(payload.changeAnalysis?.summary?.critical||0);set("#dashboardChangedHint",`${total?Math.round(changed/total*100):0}% от всех · критических: ${critical}`);set("#dashboardUnchangedHint",`${total?Math.round(unchanged/total*100):0}% от всех`);
    $$("[data-dashboard-status]").forEach((button)=>button.classList.toggle("active-filter",button.dataset.dashboardStatus===(settings.status||"all")));
    const draw=(selector,items,empty)=>{const node=$(selector);if(node)node.innerHTML=localChartHtml((items||[]).map((item)=>Array.isArray(item)?item:[item.label,item.value]),empty);};
    draw("#dashboardDynamicsChart",charts.dynamics,"Нет сохранённых финальных выгрузок.");draw("#dashboardStatusVendorChart",charts.vendors,"Нет данных производителей.");draw("#dashboardFieldChangesChart",charts.fields,"Изменения полей не найдены.");draw("#dashboardMissingChart",charts.missing,"Отсутствовавших устройств нет.");
    renderDashboardChanges(payload.changeAnalysis||localDashboardChangeAnalysis(settings));
  }
  function applyLocalDashboard(settings=dashboardSettings()){
    renderLocalDashboardFilterOptions(settings);
    const context=dashboardStatusContext(),scope={all:dashboardScope(context.all,settings),changed:dashboardScope(context.changed,settings),missing:dashboardScope(context.missing,settings),unchanged:dashboardScope(context.unchanged,settings)};
    dashboardFilteredDevices=scope[settings.status]||scope.all;
    const devices=dashboardFilteredDevices,unique=new Set(devices.map((device)=>normalize(device.mac||device.macFormatted)).filter(Boolean)),analysis=localDashboardChangeAnalysis(settings),fleet=localDashboardFleet(),added=Number(analysis.summary.added||0),changed=Number(analysis.summary.modified||0),metrics={devices:devices.length,total:fleet.latestCount||scope.all.length,totalAcross:fleet.uniqueAcrossUploads||scope.all.length,changed,missing:Number(analysis.summary.removed||0),unchanged:Math.max(0,(fleet.latestCount||scope.all.length)-changed-added),vendors:new Set(scope.all.map((device)=>device.vendor).filter((value)=>value&&value!=="Unknown")).size,rooms:new Set(scope.all.map((device)=>device.room).filter((value)=>value&&value!=="Unknown")).size,switches:new Set(devices.map((device)=>device.switchIp||device.switch_ip).filter(Boolean)).size};
    const chartRows=dashboardMovementCharts(devices,scope.missing,settings.chartLimit),statusCharts=Object.fromEntries(Object.entries(chartRows).map(([key,items])=>[key,items.map(([label,value])=>({label,value}))]));statusCharts.dynamics=fleet.series.slice(-20).map((item)=>({label:String(item.name||item.date).slice(0,28),value:item.count}));
    browserDashboardCache={fleet,changeAnalysis:analysis,settings,local:true};renderDashboardStatus({metrics,settings,changeAnalysis:analysis,statusCharts});
    $("#snapshotMetric").textContent=finalDashboardSnapshots().length||0;$("#uniqueMacMetric").textContent=fleet.uniqueAcrossUploads||unique.size;$("#switchMetric").textContent=metrics.switches;$("#roomMetric").textContent=new Set(devices.map((device)=>device.room).filter(Boolean)).size;renderLocalAnalytics(devices);return devices;
  }
  async function loadDashboardPayload(settings=dashboardSettings()){
    const data=await api("/dashboard",{method:"POST",body:JSON.stringify(currentDevicePayload({snapshots:state.snapshots,movements:state.movementHistory,settings,compactResult:Boolean(state.resultSnapshotId),resultPageSize:500}))});
    dashboardFilteredDevices=data.devices||state.devices;
    renderDashboardFilterOptions(data.filters||{},data.settings||settings,data.filterOptionsHtml||{});
    renderDashboardStatus(data);
    return data;
  }
  function loadAnalyticsPanel(devices=dashboardDevices()){
    const snapshots=finalDashboardSnapshots();
    return api("/analytics/panel",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload({snapshots}):{devices,snapshots})});
  }
  async function renderBackendDashboard(){
    try{
      const data=await api("/dashboard",{method:"POST",body:JSON.stringify(currentDevicePayload({snapshots:state.snapshots,movements:state.movementHistory,settings:dashboardSettings(),compactResult:Boolean(state.resultSnapshotId),resultPageSize:500}))});
      if(data.metrics){
        $("#snapshotMetric").textContent=finalDashboardSnapshots().length||0;
        $("#uniqueMacMetric").textContent=data.metrics.uniqueMacs||0;
        $("#switchMetric").textContent=data.metrics.switches||0;
        $("#roomMetric").textContent=data.metrics.rooms||0;
      }
      renderDashboardStatus(data);
      return data;
    }catch(error){
      applyLocalDashboard(dashboardSettings());
      return null;
    }
  }
  async function saveDashboardSettings(settings=dashboardSettings()){
    applyDashboardSettings(settings);
    try{
      const result=await api("/dashboard",{method:"POST",body:JSON.stringify(currentDevicePayload({snapshots:state.snapshots,movements:state.movementHistory,settings:state.dashboardSettings,saveSettings:true,compactResult:Boolean(state.resultSnapshotId),resultPageSize:500}))});
      applyDashboardSettings(result.settings||state.dashboardSettings);
      toast("Настройки dashboard сохранены.");
    }catch(error){
      applyLocalDashboard(state.dashboardSettings);save();toast("Настройки dashboard сохранены локально.");
    }
    $("#dashboardSettingsDialog")?.close();renderAnalytics();
  }
  function exportLocalDashboardPng(){
    const settings=dashboardSettings(),context=dashboardStatusContext(),scope={all:dashboardScope(context.all,settings),changed:dashboardScope(context.changed,settings),missing:dashboardScope(context.missing,settings),unchanged:dashboardScope(context.unchanged,settings)},devices=scope[settings.status]||scope.all,charts=dashboardMovementCharts(devices,scope.missing,8);
    const canvas=document.createElement("canvas");canvas.width=2000;canvas.height=1200;const ctx=canvas.getContext("2d"),surface="#ffffff",text="#172033",muted="#667085",accent="#2563eb";ctx.fillStyle="#f4f7fb";ctx.fillRect(0,0,canvas.width,canvas.height);ctx.fillStyle=text;ctx.font="bold 34px Arial";ctx.fillText("MAC Analyzer Dashboard",40,60);ctx.fillStyle=muted;ctx.font="17px Arial";ctx.fillText("Создано: "+new Date().toLocaleString("ru-RU"),40,90);
    const metrics=[["Всего устройств",scope.all.length],["Изменённые",scope.changed.length],["Отсутствовавшие",scope.missing.length],["Без изменений",scope.unchanged.length],["Производителей",new Set(scope.all.map((item)=>item.vendor).filter((value)=>value&&value!=="Unknown")).size],["Помещений",new Set(scope.all.map((item)=>item.room).filter(Boolean)).size]],gap=14,cardW=(1920-gap*5)/6;
    metrics.forEach(([label,value],index)=>{const x=40+index*(cardW+gap);ctx.fillStyle=surface;ctx.fillRect(x,112,cardW,112);ctx.strokeStyle="#d7dee8";ctx.strokeRect(x,112,cardW,112);ctx.fillStyle=muted;ctx.font="16px Arial";ctx.fillText(label,x+18,146);ctx.fillStyle=text;ctx.font="bold 31px Arial";ctx.fillText(String(value),x+18,193);});
    const chartSpecs=[["Динамика общего числа устройств",charts.dynamics],["Топ производителей",charts.vendors],["Изменения по полям",charts.fields],["Отсутствовавшие устройства",charts.missing]],panelW=950,panelH=445,panelGap=20;
    chartSpecs.forEach(([title,items],index)=>{const x=40+(index%2)*(panelW+panelGap),y=250+Math.floor(index/2)*(panelH+panelGap);ctx.fillStyle=surface;ctx.fillRect(x,y,panelW,panelH);ctx.strokeStyle="#d7dee8";ctx.strokeRect(x,y,panelW,panelH);ctx.fillStyle=text;ctx.font="bold 21px Arial";ctx.fillText(title,x+22,y+42);const rows=(items||[]).slice(0,8),max=Math.max(1,...rows.map((item)=>Number(item[1]||0)));if(!rows.length){ctx.fillStyle=muted;ctx.font="15px Arial";ctx.fillText("Нет данных",x+22,y+92);return;}rows.forEach(([label,value],row)=>{const rowY=y+72+row*43,barX=x+245,barW=610;ctx.fillStyle=text;ctx.font="15px Arial";ctx.fillText(String(label).slice(0,25),x+22,rowY+18);ctx.fillStyle="#e8edf5";ctx.fillRect(barX,rowY,barW,20);ctx.fillStyle=accent;ctx.fillRect(barX,rowY,Math.max(2,barW*Number(value||0)/max),20);ctx.fillStyle=text;ctx.fillText(String(value),barX+barW+12,rowY+17);});});
    return new Promise((resolve,reject)=>canvas.toBlob((blob)=>{if(!blob)return reject(new Error("Canvas PNG is empty"));const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`dashboard_${new Date().toISOString().replace(/[-:T]/g,"").slice(0,14)}.png`;a.click();URL.revokeObjectURL(a.href);resolve();},"image/png"));
  }
  async function exportDashboard(){
    try{
      const data=await api("/dashboard",{method:"POST",body:JSON.stringify(currentDevicePayload({snapshots:state.snapshots,movements:state.movementHistory,settings:dashboardSettings(),exportFormat:"png",compactResult:Boolean(state.resultSnapshotId),resultPageSize:500}))});
      if(!data.export?.binary||!data.export.content)throw new Error("Dashboard PNG export is empty");
      downloadBase64(data.export.filename||"mac-dashboard.png",data.export.content,data.export.mimeType||"image/png");
      toast("Dashboard экспортирован в PNG.");
    }catch(error){
      await exportLocalDashboardPng();toast("Dashboard экспортирован в PNG локально.");
    }
  }
  function externalApiSettings(){
    return {
      enabled:$("#externalApiEnabled")?.checked||false,
      provider:$("#externalProviderSelect")?.value||"macvendors",
      endpoint:$("#externalEndpointInput")?.value||"",
      rateLimit:Number($("#externalRateLimitInput")?.value||25),
      cacheTtlDays:30,
      onlyUnknown:true
    };
  }
  function applyExternalApiSettings(settings={},providers=[]){
    const normalized={...empty().externalApiSettings,...settings,provider:String(settings.provider||"macvendors")};
    state.externalApiSettings=normalized;
    if(Array.isArray(providers)&&providers.length){
      const optionHtml=providers.map((item)=>`<option value="${esc(item.key)}">${esc(item.description||item.key)}</option>`).join("");
      const dialogOptionHtml=providers.filter((item)=>item.key!=="custom").map((item)=>`<option value="${esc(item.key)}">${esc(item.key+" - "+(item.description||item.key))}</option>`).join("");
      if(optionHtml)$("#externalProviderSelect").innerHTML=optionHtml;
      if(dialogOptionHtml)$("#apiSettingsServiceSelect").innerHTML=dialogOptionHtml;
    }
    if($("#externalApiEnabled"))$("#externalApiEnabled").checked=Boolean(normalized.enabled);
    if($("#externalProviderSelect"))$("#externalProviderSelect").value=normalized.provider;
    if($("#externalEndpointInput"))$("#externalEndpointInput").value=normalized.endpoint||"";
    if($("#externalRateLimitInput"))$("#externalRateLimitInput").value=normalized.rateLimit||25;
    if($("#apiSettingsServiceSelect")&&normalized.provider!=="custom")$("#apiSettingsServiceSelect").value=normalized.provider;
    save();
  }
  async function saveExternalApiSettings(){
    const settings=externalApiSettings();
    try{
      const result=await api("/external-enrichment/settings",{method:"POST",body:JSON.stringify({settings})});
      applyExternalApiSettings(result.settings||settings,result.providers||[]);
      toast("Настройки внешнего API сохранены: "+result.settings.provider);
      return result.settings;
    }catch(error){applyExternalApiSettings(settings);toast("Настройки API сохранены локально.");return settings;}
  }
  async function loadExternalApiSettings(){
    try{
      const result=await api("/external-enrichment/settings");
      applyExternalApiSettings(result.settings||{},result.providers||[]);
    }catch{applyExternalApiSettings(state.externalApiSettings||{});}
  }
  function showApiSettingsDialog(){const provider=$("#externalProviderSelect").value;if(provider!=="custom")$("#apiSettingsServiceSelect").value=provider;$("#apiSettingsTestResult").textContent="Введите MAC-адрес для тестирования.";$("#apiSettingsTestResult").className="api-test-result muted";$("#apiSettingsDialog").showModal();}
  async function testApiSettingsDialog(){
    const input=$("#apiSettingsTestMacInput"),resultNode=$("#apiSettingsTestResult"),mac=input.value.trim(),normalized=normalize(mac);
    if(!normalized){resultNode.textContent="Введите корректный MAC-адрес из 12 шестнадцатеричных символов.";resultNode.className="api-test-result error";return;}
    resultNode.textContent="Выполняется запрос...";resultNode.className="api-test-result muted";
    const provider=$("#apiSettingsServiceSelect").value,settings={...externalApiSettings(),provider,enabled:true};
    try{const response=await api("/external-enrichment/test",{method:"POST",body:JSON.stringify({mac,settings})});resultNode.textContent=response.vendor?"Найден производитель: "+response.vendor:"Производитель не найден или API недоступен";resultNode.className="api-test-result "+(response.vendor?"success":"error");await refreshApiCacheStatus();}
    catch(error){const vendor=localVendor(mac);resultNode.textContent=vendor!=="Unknown"?"Найден производитель: "+vendor+" (встроенная HTML-база)":"Производитель не найден или API недоступен";resultNode.className="api-test-result "+(vendor!=="Unknown"?"success":"error");}
  }
  async function saveApiSettingsDialog(){const provider=$("#apiSettingsServiceSelect").value;$("#externalProviderSelect").value=provider;await saveExternalApiSettings();$("#apiSettingsDialog").close();}
  async function refreshApiCacheStatus(){
    try{
      const result=await api("/api-cache?limit=5"),cache=result.cache||{};
      if($("#apiCacheStatus"))$("#apiCacheStatus").textContent=(cache.total||0)+" entries";
      return cache;
    }catch(error){if($("#apiCacheStatus"))$("#apiCacheStatus").textContent="cache unavailable";throw error;}
  }
  async function clearApiCache(){
    try{
      const result=await api("/api-cache/clear",{method:"POST",body:JSON.stringify({prefix:"external_vendor:"})});
      await refreshApiCacheStatus();
      toast("API cache cleared: "+result.deleted);
    }catch(error){toast(error.message);}
  }
  async function renderBackendClusters(devices=state.devices){
    const root=$("#clusterChart"); if(!root)return;
    try{
      const data=await(analyticsPanelPromise||loadAnalyticsPanel(devices));
      root.innerHTML=data.clusterRowsHtml||data.emptyClusterRowsHtml||'<p class="muted">Backend не нашёл кластеров.</p>';
    }catch(error){
      root.innerHTML=LocalAnalytics.renderClusters(await collectLocalAnalytics(devices));
    }
  }
  async function exportClusters(){
    try{
      const data=await api("/clusters",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload({fields:["vendor","room","switchIp"],minSize:1,exportFormat:"csv"}):{devices:dashboardDevices(),fields:["vendor","room","switchIp"],minSize:1,exportFormat:"csv"})});
      if(!data.export)throw new Error("Cluster export is empty");
      download(data.export.filename||"mac-clusters.csv","\uFEFF"+data.export.content,data.export.mimeType||"text/csv");
      toast("Кластеры экспортированы backend-сервисом.");
    }catch(error){
      const payload=await collectLocalAnalytics(dashboardDevices(),true);
      download("mac-clusters.csv",LocalAnalytics.clustersCsv(payload),"text/csv");
      toast("Кластеры экспортированы локально.");
    }
  }
  async function renderBackendTopology(devices=state.devices){
    const root=$("#topologyGraph"); if(!root)return;
    try{
      const data=await api("/topology",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload():{devices})});
      root.innerHTML=data.topologyHtml||data.emptyTopologyHtml||'<p class="muted">Backend не нашёл связей топологии.</p>';
    }catch(error){
      root.innerHTML=LocalAnalytics.renderTopology(await collectLocalAnalytics(devices));
    }
  }
  async function exportTopology(){
    try{
      const data=await api("/topology",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload({exportFormat:"html"}):{devices:dashboardDevices(),exportFormat:"html"})});
      if(!data.export)throw new Error("Topology export is empty");
      download(data.export.filename||"mac-topology.html",data.export.content,data.export.mimeType||"text/html");
      toast("Топология экспортирована backend-сервисом.");
    }catch(error){
      const payload=await collectLocalAnalytics(dashboardDevices(),true);
      download("mac-topology.html",LocalAnalytics.topologyDocument(payload),"text/html");
      toast("Топология экспортирована локально.");
    }
  }
  function renderQualityReport(panel){
    $("#qualityInsights").innerHTML=panel.insightsHtml||'<p class="muted">Backend не нашёл проблем качества.</p>';
  }
  async function renderQualityReportsHistory(){
    const root=$("#qualityReportsList"); if(!root)return;
    try{
      const data=await api("/quality/reports?limit=5");
      root.innerHTML=data.reportsHtml||data.emptyReportsHtml||'<p class="muted">Saved quality reports are empty.</p>';
    }catch(error){
      root.innerHTML='<p class="muted">Локальный анализ качества доступен по кнопке «Проверить».</p>';
    }
  }
  function analyzeLocalQuality(){const devices=dashboardDevices(),missingMac=devices.filter((device)=>!normalize(device.mac||device.macFormatted)).length,unknown=devices.filter((device)=>!device.vendor||device.vendor==="Unknown").length,missingIp=devices.filter((device)=>!device.ip).length;$("#qualityInsights").innerHTML=localChartHtml([["Ошибки MAC",missingMac+state.invalid.length],["Unknown vendor",unknown],["Нет IP",missingIp]].filter((item)=>item[1]>0),"Проблем качества не найдено.");toast("Локальный анализ качества данных завершён.");}
  async function analyzeQuality(){
    try{
      const data=await api("/quality/panel",{method:"POST",body:JSON.stringify(state.resultSnapshotId?currentDevicePayload({invalid:state.invalid,source:"current-browser-dataset",save:true}):{devices:dashboardDevices(),invalid:state.invalid,source:"current-browser-dataset",save:true})});
      renderQualityReport(data);
      await renderQualityReportsHistory();
      toast("Backend анализ качества данных завершён.");
    }catch(error){analyzeLocalQuality();}
  }
  function initializeAnalyticsExpanders(){
    $$("#analyticsView .analytics-grid .tool-panel").forEach((panel)=>{
      if(panel.dataset.analyticsExpandable==="ready")return;
      panel.dataset.analyticsExpandable="ready";
      const head=panel.querySelector(".panel-head");
      if(!head)return;
      const actions=document.createElement("div");
      actions.className="analytics-panel-actions";
      actions.innerHTML='<button class="icon-button" type="button" data-analytics-collapse title="Свернуть раздел" aria-label="Свернуть раздел">−</button><button class="icon-button" type="button" data-analytics-expand title="Развернуть раздел" aria-label="Развернуть раздел">⛶</button>';
      head.append(actions);
    });
  }
  async function renderAnalytics(){
    const signature=[state.resultBrowserSnapshotId,state.resultSnapshotId,currentDeviceCount(),state.lastAnalysis,JSON.stringify(dashboardSettings())].join("|");
    if(analyticsRenderCache.signature===signature&&Date.now()-analyticsRenderCache.at<30000)return;
    analyticsRenderCache={signature,at:Date.now()};
    const revision=++analyticsRenderRevision;
    initializeAnalyticsExpanders();
    if(browserOnlyMode&&state.resultBrowserSnapshotId&&BrowserSnapshots?.aggregate){
      try{
        const cache=await loadBrowserDashboardCache(dashboardSettings());
        if(revision===analyticsRenderRevision&&renderBrowserDashboardCache(cache)){
          const details=await collectLocalAnalytics(state.devices);
          $("#backendChartsPanel").innerHTML=LocalAnalytics.renderOverview(details);
          $("#clusterChart").innerHTML=LocalAnalytics.renderClusters(details);
          $("#topologyGraph").innerHTML=LocalAnalytics.renderTopology(details);
          applyDashboardVisibility(state.dashboardSettings);
          return;
        }
      }catch(error){toast("Не удалось построить полный локальный dashboard: "+error.message);}
    }
    applyLocalDashboard(dashboardSettings());try{await loadDashboardPayload();}catch(error){applyLocalDashboard(dashboardSettings());}if(revision!==analyticsRenderRevision)return;const devices=dashboardDevices();analyticsPanelPromise=loadAnalyticsPanel(devices);renderPrimaryCharts();renderBackendStatistics();renderTemporalStatistics();renderBackendCharts();renderBackendDashboard();renderBackendClusters(devices);renderBackendTopology(devices);renderQualityReportsHistory();refreshAnalyticsReport();
  }
  function historyQueryParams(query="", from="", to="", limit="500"){
    const params=new URLSearchParams({limit});
    if(query)params.set("query",query);
    if(from)params.set("from",from);
    if(to)params.set("to",to);
    return params;
  }
  function loadHistoryPanel(query="", from="", to="", limit="500"){
    return api("/history/panel?"+historyQueryParams(query,from,to,limit).toString());
  }
  function renderHistory(){
    const query=($("#historySearchInput")?.value||"").trim();
    const from=$("#historyDateFrom").value,to=$("#historyDateTo").value;
    const signature=[query,from,to,state.snapshots?.length,state.movementHistory?.length,state.lastAnalysis].join("|");
    if(historyRenderCache.signature===signature&&Date.now()-historyRenderCache.at<15000)return;
    historyRenderCache={signature,at:Date.now()};
    historyPanelPromise=loadHistoryPanel(query, from, to);
    renderSnapshotHistory(query, from, to);
    renderBackendHistorySummaries(query, from, to);
    renderSqliteHistory(query, from, to);
    renderVendorModelHistory(query, from, to);
    renderMovementHistory(query, from, to);
  }
  async function runGlobalSearch(){
    const query=($("#globalSearchInput")?.value||"").trim();
    if(!query){$("#globalSearchInput")?.focus();return;}
    const mac=normalize(query);
    if(mac){await showDevice(mac);return;}
    const historyInput=$("#historySearchInput");
    if(historyInput)historyInput.value=query;
    view("history");
    renderHistory();
  }
  function localHistoryItems(query="", from="", to=""){
    const q=String(query||"").toLowerCase(),fromTime=from?Date.parse(from+"T00:00:00"):0,toTime=to?Date.parse(to+"T23:59:59"):Infinity;
    return finalDashboardSnapshots().filter((snapshot)=>{const time=Date.parse(snapshot.createdAt||snapshot.date||"")||0,text=[snapshot.name,snapshot.source,(snapshot.devices||[]).map((device)=>[device.mac,device.macFormatted,device.vendor,device.model,device.ip,device.address,device.room,device.smartroomId,device.switchIp].join(" ")).join(" ")].join(" ").toLowerCase();return time>=fromTime&&time<=toTime&&(!q||text.includes(q));});
  }
  function localSnapshotHistoryRows(query="", from="", to=""){
    const snapshots=localHistoryItems(query,from,to);
    return localSnapshotHistoryRowsFrom(snapshots);
  }
  function localSnapshotHistoryRowsFrom(snapshots=[]){
    return snapshots.length?snapshots.map((snapshot)=>`<tr><td><input type="checkbox" data-snapshot-select value="${esc(snapshot.id)}" aria-label="Выбрать выгрузку"></td><td>${esc(snapshot.createdAt?new Date(snapshot.createdAt).toLocaleString("ru-RU"):"")}</td><td>${esc(snapshot.name||"Snapshot")}${snapshot._matchCount!==undefined?`<small class="muted">Совпадений: ${Number(snapshot._matchCount||0)}</small>`:""}</td><td>${Number(snapshot.deviceCount??(snapshot.devices||[]).length)}</td><td>${esc(snapshot.source||"browser")}</td><td><button class="button secondary" data-local-snapshot="${esc(snapshot.id)}">Открыть</button></td></tr>`).join(""):'<tr><td colspan="6" class="empty-state">Локальная история снимков пока пуста.</td></tr>';
  }
  async function localHistoryItemsAsync(query="",from="",to=""){
    if(!query)return localHistoryItems("",from,to);
    const q=String(query).trim(),fromTime=from?Date.parse(from+"T00:00:00"):0,toTime=to?Date.parse(to+"T23:59:59"):Infinity,matched=[];
    for(const snapshot of finalDashboardSnapshots()){
      const time=Date.parse(snapshot.fileCreatedAt||snapshot.createdAt||snapshot.savedAt||"")||0;
      if(time<fromTime||time>toTime)continue;
      if(snapshot.browserStored&&BrowserSnapshots?.page){
        const result=await BrowserSnapshots.page(snapshot.id,{query:q,offset:0,limit:25}).catch(()=>null);
        if(Number(result?.pagination?.total||0)>0)matched.push({...snapshot,_matchCount:result.pagination.total});
      }else{
        const text=[snapshot.name,snapshot.source,...(snapshot.devices||[]).flatMap((device)=>[device.mac,device.macFormatted,device.vendor,device.model,device.ip,device.address,device.room,device.smartroomId,device.switchIp])].join(" ").toLowerCase();
        if(text.includes(q.toLowerCase()))matched.push({...snapshot,_matchCount:(snapshot.devices||[]).filter((device)=>Object.values(device).join(" ").toLowerCase().includes(q.toLowerCase())).length});
      }
      await MemoryGuard.yieldToMainThread();
    }
    return matched;
  }
  function selectedSnapshotIds(){return $$("[data-snapshot-select]:checked").map((input)=>input.value).filter(Boolean);}
  async function deleteSelectedSnapshots(){
    const ids=selectedSnapshotIds();if(!ids.length){toast("Выберите хотя бы одну выгрузку.");return;}
    if(!confirm(`Удалить выбранные выгрузки (${ids.length})? История остальных выгрузок сохранится.`))return;
    const selected=new Set(ids);
    try{await api("/database/snapshots/delete",{method:"POST",body:JSON.stringify({ids})});}catch(error){if(!networkUnavailable(error))throw error;}
    for(const id of selected)await BrowserSnapshots?.removeSnapshot?.(id).catch(()=>false);
    state.snapshots=(state.snapshots||[]).filter((snapshot)=>!selected.has(String(snapshot.id)));
    if(selected.has(String(state.resultBrowserSnapshotId||""))||selected.has(String(state.resultSnapshotId||""))){clearResultReference();state.devices=[];state.invalid=[];}
    browserDashboardCache=null;localAnalyticsCache=null;save();renderHistory();renderSnapshots();toast(`Удалено выгрузок: ${ids.length}`);
  }
  function localFlatHistory(query="", from="", to=""){
    return localHistoryItems(query,from,to).flatMap((snapshot)=>(snapshot.devices||[]).map((device)=>({...device,_snapshot:snapshot})));
  }
  function localMovementItems(query="", from="", to=""){
    const snapshots=localHistoryItems(query,from,to).slice().sort((a,b)=>(Date.parse(a.createdAt||"")||0)-(Date.parse(b.createdAt||"")||0));
    const q=String(query||"").toLowerCase(),fromTime=from?Date.parse(from+"T00:00:00"):0,toTime=to?Date.parse(to+"T23:59:59"):Infinity;
    const movements=(state.movementHistory||[]).filter((item)=>{const time=Date.parse(item.changedAt||"")||0,text=[item.mac,item.type,item.field,item.before,item.after,item.source].join(" ").toLowerCase();return time>=fromTime&&time<=toTime&&(!q||text.includes(q));});
    for(let index=1;index<snapshots.length;index++){
      const before=snapshots[index-1],after=snapshots[index],result=localComparisonPayload({baselineId:before.id,currentId:after.id,fields:["vendor","model","ip","address","room","smartroomId","switchIp","switchPort"]});
      for(const change of result.changes||[])movements.push({...change,changedAt:after.createdAt||"",source:(before.name||before.source||"snapshot")+" → "+(after.name||after.source||"snapshot")});
    }
    return movements.reverse();
  }
  function localMovementTableRows(items){
    return items.length?items.slice(0,500).map((item)=>`<tr data-mac="${esc(item.mac||"")}"><td>${esc((item.changedAt||item.changed_at)?new Date(item.changedAt||item.changed_at).toLocaleString("ru-RU"):"")}</td><td>${esc(formatMac(item.mac)||item.mac)}${ddioHistoryBadge(item)}</td><td>${esc(item.type||"Изменено")}</td><td>${esc(item.field||item.field_name||"")}</td><td>${esc(item.before??item.from_value??"")}</td><td>${esc(item.after??item.to_value??"")}</td><td>${esc(item.source||"")}</td></tr>`).join(""):'<tr><td colspan="7" class="empty-state">Изменений между загрузками пока нет.</td></tr>';
  }
  function movementHistoryFilters(){return{query:($("#movementSearchInput")?.value||"").trim(),changeType:$("#movementTypeFilter")?.value||"",field:$("#movementFieldFilter")?.value||"",dateFrom:$("#movementDateFrom")?.value||"",dateTo:$("#movementDateTo")?.value||""};}
  function movementHistoryParams(filters=movementHistoryFilters()){
    const params=new URLSearchParams({limit:"5000"}),names={query:"query",changeType:"type",field:"field",dateFrom:"from",dateTo:"to"};
    Object.entries(names).forEach(([key,name])=>{if(filters[key])params.set(name,filters[key]);});return params;
  }
  function localMovementChangeType(item){const before=String(item.before??item.from_value??""),after=String(item.after??item.to_value??"");return!before&&after?"added":before&&!after?"removed":"modified";}
  function localEnhancedMovementRows(items){
    const latest=new Map();
    for(const device of state.devices||[]){const context=compactDashboardDevice(device);if(context?.mac)latest.set(context.mac,context);}
    for(const snapshot of state.snapshots||[])for(const device of snapshot.devices||[]){const context=compactDashboardDevice(device);if(context?.mac&&!latest.has(context.mac))latest.set(context.mac,context);}
    return items.length?items.slice(0,500).map((item)=>{const type=localMovementChangeType(item),mac=normalize(item.mac)||"",device=compactDashboardDevice(item.afterDevice)||compactDashboardDevice(item.beforeDevice)||latest.get(mac)||{};return`<tr class="movement-child-row movement-${type}" data-mac="${esc(mac)}"><td data-movement-column="mac">${esc(formatMac(mac)||mac)}${ddioHistoryBadge(item)}</td><td data-movement-column="count">1</td><td data-movement-column="dates">${esc((item.changedAt||item.changed_at)?new Date(item.changedAt||item.changed_at).toLocaleString("ru-RU"):"")}</td><td data-movement-column="vendor">${esc(device.vendor||"Unknown")}</td><td data-movement-column="model">${esc(device.model||"")}</td><td data-movement-column="address">${esc(device.address||"")}</td><td data-movement-column="room">${esc(device.room||"")}</td><td data-movement-column="field">${esc(item.field||item.field_name||"")}</td><td data-movement-column="before">${esc(item.before??item.from_value??"")}</td><td data-movement-column="after">${esc(item.after??item.to_value??"")}</td><td data-movement-column="source">${esc(item.source||"")}</td></tr>`;}).join(""):'<tr><td colspan="11" class="empty-state">Нет изменений за выбранный период.</td></tr>';
  }
  function applyMovementColumnSettings(settings=movementColumnSettings){
    movementColumnSettings=settings||movementColumnSettings;const visible=new Set(movementColumnSettings.visible||[]),widths=movementColumnSettings.widths||{};
    $$('[data-movement-column]').forEach((cell)=>{const key=cell.dataset.movementColumn;cell.hidden=!visible.has(key);const width=Math.max(64,Math.min(600,Number(widths[key])||150));cell.style.width=width+"px";cell.style.minWidth=width+"px";cell.style.maxWidth=width+"px";});
    $$('[data-movement-column-toggle]').forEach((input)=>{input.checked=visible.has(input.dataset.movementColumnToggle);});
    $$('[data-movement-column-width]').forEach((input)=>{input.value=String(Math.max(64,Math.min(600,Number(widths[input.dataset.movementColumnWidth])||150)));});
  }
  function readMovementColumnSettings(){
    const visible=$$('[data-movement-column-toggle]:checked').map((input)=>input.dataset.movementColumnToggle),widths={...movementColumnSettings.widths};
    $$('[data-movement-column-width]').forEach((input)=>{widths[input.dataset.movementColumnWidth]=Math.max(64,Math.min(600,Number(input.value)||150));});
    return{visible,widths};
  }
  async function saveMovementColumnSettings(settings=readMovementColumnSettings(),showToast=true){
    if(!settings.visible.length){toast("Оставьте видимой хотя бы одну колонку.");return false;}
    try{const result=await api("/history/movements/columns",{method:"POST",body:JSON.stringify({settings})});movementColumnSettings=result.settings;applyMovementColumnSettings();if(showToast)toast("Колонки расширенной истории сохранены.");return true;}catch(error){toast(error.message);return false;}
  }
  function optimizeMovementColumns(){
    const widths={...movementColumnSettings.widths};
    for(const key of movementColumnSettings.visible||[]){const texts=$$(`[data-movement-column="${key}"]`).slice(0,250).map((cell)=>String(cell.textContent||"").trim().length);widths[key]=Math.max(72,Math.min(420,Math.max(8,...texts)*8+28));}
    movementColumnSettings={...movementColumnSettings,widths};applyMovementColumnSettings();
  }
  function startMovementColumnResize(event){const handle=event.target.closest("[data-movement-resize]");if(!handle)return;event.preventDefault();const column=handle.dataset.movementResize,startWidth=Number(movementColumnSettings.widths?.[column])||150;movementColumnResize={column,startX:event.clientX,startWidth,handle};handle.classList.add("active");handle.setPointerCapture?.(event.pointerId);}
  function resizeMovementColumn(event){if(!movementColumnResize)return;const width=Math.max(64,Math.min(600,movementColumnResize.startWidth+event.clientX-movementColumnResize.startX));movementColumnSettings.widths[movementColumnResize.column]=Math.round(width);applyMovementColumnSettings();}
  function finishMovementColumnResize(){if(!movementColumnResize)return;movementColumnResize.handle?.classList.remove("active");movementColumnResize=null;saveMovementColumnSettings(movementColumnSettings,false);}
  function setMovementGroupsExpanded(expanded){$$('[data-movement-child]').forEach((row)=>{row.hidden=!expanded;});$$('[data-toggle-movement-group]').forEach((button)=>{button.textContent=expanded?"▾":"▸";button.setAttribute("aria-expanded",expanded?"true":"false");button.title=expanded?"Свернуть группу":"Развернуть группу";});}
  async function exportMovementHistory(){
    const params=movementHistoryParams();params.set("format","xlsx");
    try{const result=await api("/history/movements/export?"+params.toString());downloadBase64(result.filename||"filtered-history.xlsx",result.content,result.mimeType);toast("Расширенная история экспортирована в XLSX.");return result;}
    catch(error){
      const filters=movementHistoryFilters();let items=localMovementItems(filters.query,filters.dateFrom.slice(0,10),filters.dateTo.slice(0,10));
      if(filters.field)items=items.filter((item)=>(item.field||item.field_name)===filters.field);
      if(filters.changeType)items=items.filter((item)=>localMovementChangeType(item)===filters.changeType);
      const columns=["Дата","MAC-адрес","Тип","Поле","Было","Стало","Производитель","Модель","IP","Адрес","Помещение","Smartroom ID","IP коммутатора","Порт","Источник"];
      const result=await XlsxExporter.createWorkbook({columns,totalRows:items.length,sheetName:"Изменения",streamRows:async(accept)=>accept(items),rowMapper:(item)=>{const device=compactDashboardDevice(item.afterDevice)||compactDashboardDevice(item.beforeDevice)||{};return[item.changedAt||item.changed_at||"",formatMac(item.mac)||item.mac||"",item.type||localMovementChangeType(item),item.field||item.field_name||"",item.before??item.from_value??"",item.after??item.to_value??"",device.vendor||"",device.model||"",device.ip||"",device.address||"",device.room||"",device.smartroomId||"",device.switchIp||"",device.switchPort||"",item.source||""];}});deliverDownload("mac-movement-history.xlsx",result.blob);toast("История изменений экспортирована локально в XLSX.");return result;
    }
  }
  async function deleteShownMovementHistory(){if(!enhancedMovementIds.length){toast("Нет показанных SQLite-изменений для удаления.");return;}if(!state.engineeringMode||!state.engineeringToken){toast("Для удаления включите инженерный режим.");return;}if(!confirm(`Удалить показанные записи изменений (${enhancedMovementIds.length})?`))return;try{const result=await api("/history/movements/delete",{method:"POST",body:JSON.stringify({ids:enhancedMovementIds})});toast("Удалено изменений: "+result.deleted);renderMovementHistory();renderServices();}catch(error){toast(error.message);}}
  async function renderMovementHistory(){
    const revision=++movementRenderRevision;
    const root=$("#localMovementBody");
    if(!root)return;
    const filters=movementHistoryFilters();
    try{
      const data=await api("/history/movements?"+movementHistoryParams(filters).toString());
      if(revision!==movementRenderRevision)return;
      enhancedMovementIds=data.ids||[];root.innerHTML=data.rowsHtml||data.emptyRowsHtml;$("#movementHistorySummary").innerHTML=data.summaryHtml||"";
      movementColumnSettings=data.columnSettings||movementColumnSettings;$("#movementColumnControls").innerHTML=movementColumnSettings.controlsHtml||"";applyMovementColumnSettings();
    }catch(error){
      if(revision!==movementRenderRevision)return;
      let items=localMovementItems(filters.query,filters.dateFrom.slice(0,10),filters.dateTo.slice(0,10));
      if(filters.field)items=items.filter((item)=>(item.field||item.field_name)===filters.field);if(filters.changeType)items=items.filter((item)=>localMovementChangeType(item)===filters.changeType);
      enhancedMovementIds=[];root.innerHTML=localEnhancedMovementRows(items);$("#movementHistorySummary").innerHTML=`<div class="bar-label"><span>Локальных изменений</span><strong>${items.length}</strong></div>`;applyMovementColumnSettings();
    }
  }
  function renderLocalHistorySummaries(query="", from="", to=""){
    const rows=localFlatHistory(query,from,to),vendorRows=localTally(rows,"vendor",20),modelRows=localTally(rows,"model",20),summary=(items,label)=>items.length?items.map(([name,count])=>`<tr><td>${esc(name)}</td><td>${count}</td><td>${new Set(rows.filter((device)=>String(device[label]||"Unknown")===name).map((device)=>device.mac||device.macFormatted).filter(Boolean)).size}</td></tr>`).join(""):'<tr><td colspan="3" class="empty-state">Локальная история пуста.</td></tr>';
    $("#vendorHistoryBody").innerHTML=summary(vendorRows,"vendor");
    $("#modelHistoryBody").innerHTML=summary(modelRows,"model");
  }
  function renderLocalSqliteHistory(query="", from="", to=""){
    const rows=localFlatHistory(query,from,to),body=$("#sqliteHistoryBody"),summary=$("#sqliteHistorySummary");
    if(summary)summary.innerHTML=`<div class="bar-label"><span>Local history</span><strong>${rows.length}</strong></div>`;
    if(body)body.innerHTML=rows.length?rows.slice(0,500).map((device)=>`<tr data-mac="${esc(device.mac||device.macFormatted||"")}"><td>${esc(device.macFormatted||formatMac(device.mac)||device.mac||"")}</td><td>${esc(device.vendor||"")}</td><td>${esc(device.model||"")}</td><td>${esc(device.ip||"")}</td><td>${esc(device.address||"")}</td><td>${esc(device._snapshot?.source||device.source||"browser")}</td><td>${esc(device._snapshot?.createdAt?new Date(device._snapshot.createdAt).toLocaleString("ru-RU"):"")}</td></tr>`).join(""):'<tr><td colspan="7" class="empty-state">Локальная история устройств пока пуста.</td></tr>';
  }
  function renderLocalVendorModelHistory(query="", from="", to=""){
    const rows=localFlatHistory(query,from,to).filter((device)=>device.vendor||device.model),body=$("#vendorModelHistoryBody"),summary=$("#vendorModelHistorySummary");
    if(summary)summary.innerHTML=`<div class="bar-label"><span>Local learning</span><strong>${rows.length}</strong></div>`;
    if(body)body.innerHTML=rows.length?rows.slice(0,500).map((device)=>`<tr data-mac="${esc(device.mac||device.macFormatted||"")}"><td>${esc(device.macFormatted||formatMac(device.mac)||device.mac||"")}</td><td>${esc(device.oui||normalize(device.mac||device.macFormatted)?.slice(0,6)||"")}</td><td>${esc((normalize(device.mac||device.macFormatted)||"").slice(0,10))}</td><td>${esc(device.vendor||"")}</td><td>${esc(device.model||"")}</td><td>${esc(device._snapshot?.source||device.source||"browser")}</td><td>${esc(device._snapshot?.createdAt?new Date(device._snapshot.createdAt).toLocaleString("ru-RU"):"")}</td></tr>`).join(""):'<tr><td colspan="7" class="empty-state">Локальная история vendor/model пока пуста.</td></tr>';
  }
  async function renderSnapshotHistory(query="", from="", to=""){
    const root=$("#historyBody");
    if(!root)return;
    try{
      const data=await api("/statistics/snapshots?"+historyQueryParams(query,from,to,"500").toString());
      root.innerHTML=data.tableRowsHtml||data.emptyTableRowsHtml||'<tr><td colspan="5" class="empty-state">Backend snapshot history is empty.</td></tr>';
    }catch(error){
      root.innerHTML=localSnapshotHistoryRowsFrom(await localHistoryItemsAsync(query,from,to));
    }
  }
  async function renderBackendHistorySummaries(query="", from="", to=""){
    const vendorBody=$("#vendorHistoryBody"), modelBody=$("#modelHistoryBody");
    if(!vendorBody||!modelBody)return;
    try{
      const panel=await(historyPanelPromise||loadHistoryPanel(query,from,to));
      const summary=panel.summaryTables||{};
      vendorBody.innerHTML=summary.vendorRowsHtml||summary.emptyRowsHtml||'<tr><td colspan="3" class="empty-state">Backend history is empty.</td></tr>';
      modelBody.innerHTML=summary.modelRowsHtml||summary.emptyRowsHtml||'<tr><td colspan="3" class="empty-state">Backend history is empty.</td></tr>';
    }catch(error){
      renderLocalHistorySummaries(query,from,to);
    }
  }
  async function exportHistory(){
    const processId=beginProcess("Экспорт истории","Подготовка записей истории",10);
    const params=new URLSearchParams({format:"html",limit:"1000"});
    const query=($("#historySearchInput")?.value||"").trim();
    const from=$("#historyDateFrom").value,to=$("#historyDateTo").value;
    if(query)params.set("query",query);
    if(from)params.set("from",from);
    if(to)params.set("to",to);
    try{
      updateProcess(processId,35,"Формирование отчёта backend-сервисом");
      const result=await api("/statistics/snapshots/export?"+params.toString());
      updateProcess(processId,85,"Сохранение файла истории");
      download(result.filename||"mac-history.html",result.content||"",result.mimeType||"text/html");
      toast("История экспортирована backend-сервисом.");
      finishProcess(processId,"История экспортирована");
    }catch(error){
      updateProcess(processId,55,"Backend недоступен: локальная подготовка истории");
      const rows=localHistoryItems(query,from,to).map((snapshot)=>`<tr><td>${esc(snapshot.createdAt||"")}</td><td>${esc(snapshot.name||"Snapshot")}</td><td>${(snapshot.devices||[]).length}</td><td>${esc(snapshot.source||"browser")}</td></tr>`).join("");
      download("mac-history.html",`<!doctype html><html><head><meta charset="utf-8"><title>MAC history</title><style>body{font:14px Arial;margin:32px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:7px;text-align:left}th{background:#eee}</style></head><body><h1>MAC Analyzer history</h1><table><thead><tr><th>Date</th><th>Snapshot</th><th>Devices</th><th>Source</th></tr></thead><tbody>${rows||'<tr><td colspan="4">Local history is empty.</td></tr>'}</tbody></table></body></html>`,"text/html");
      toast("История экспортирована локально.");
      finishProcess(processId,"История экспортирована в автономном режиме","warning");
    }
  }
  async function renderSqliteHistory(query="", from="", to=""){
    const body=$("#sqliteHistoryBody"), summary=$("#sqliteHistorySummary");
    if(!body||!summary)return;
    try{
      const panel=await(historyPanelPromise||loadHistoryPanel(query,from,to));
      const data=panel.historySearch||{};
      summary.innerHTML=data.summaryHtml||'<div class="bar-label"><span>SQLite</span><strong>empty</strong></div>';
      body.innerHTML=data.tableRowsHtml||data.emptyTableRowsHtml||'<tr><td colspan="7" class="empty-state">SQLite history is empty.</td></tr>';
    }catch(error){
      renderLocalSqliteHistory(query,from,to);
    }
  }
  async function renderVendorModelHistory(query="", from="", to=""){
    const body=$("#vendorModelHistoryBody"), summary=$("#vendorModelHistorySummary");
    if(!body||!summary)return;
    try{
      const panel=await(historyPanelPromise||loadHistoryPanel(query,from,to));
      const data=panel.vendorModelHistory||{};
      summary.innerHTML=data.summaryHtml||'<div class="bar-label"><span>SQLite</span><strong>empty</strong></div>';
      body.innerHTML=data.tableRowsHtml||data.emptyTableRowsHtml||'<tr><td colspan="7" class="empty-state">Vendor/model history is empty.</td></tr>';
    }catch(error){
      renderLocalVendorModelHistory(query,from,to);
    }
  }
  async function renderMappings(){try{const data=await api("/mappings/panel");state.localVendorMappings=data.vendors||state.localVendorMappings||{};state.localModelMappings=data.models||state.localModelMappings||{};save();$("#vendorMappingList").innerHTML=data.vendorRowsHtml||'<p class="muted">Правила пока не загружены.</p>';$("#modelMappingList").innerHTML=data.modelRowsHtml||'<p class="muted">Правила пока не загружены.</p>';}catch(error){renderLocalMappings();}}
  function ouiReferenceStatusText(data={}){const files=data.files||[],file=files[0],count=Number(data.referenceMappings||0),bundled=Number(data.ieee?.total||IeeeRegistry.status().total||0);return`IEEE офлайн: ${bundled.toLocaleString("ru-RU")} HEX-записей${count?` · пользовательских правил: ${count.toLocaleString("ru-RU")}${file?` · ${file.name}`:""}`:""}`;}
  async function loadOuiReferenceStatus(){const target=$("#ouiReferenceStatus");if(!target)return;try{const data=await api("/reference/oui/status");target.textContent=ouiReferenceStatusText(data);}catch{target.textContent=ouiReferenceStatusText({});}}
  async function parseLocalOuiReference(file){const mappings={};if(/\.csv$/i.test(file.name)){const table=await clientReadTable(file),normalized=(table.headers||[]).map((name)=>String(name||"").toLowerCase().replace(/[^a-zа-я0-9]/gi,"")),prefixIndex=normalized.findIndex((name)=>["assignment","oui","prefix","macprefix"].includes(name)),vendorIndex=normalized.findIndex((name)=>["organizationname","organization","vendor","manufacturer","производитель"].includes(name));if(prefixIndex<0||vendorIndex<0)throw new Error("В CSV нужны колонки Assignment/OUI и Organization/Vendor.");for(const row of table.rows||[]){const prefix=normalizePrefix(row[prefixIndex]),vendor=String(row[vendorIndex]||"").trim();if([6,8,10].includes(prefix.length)&&vendor)mappings[prefix]=vendor;}}else{const text=await readClientTextFile(file);for(const line of text.split(/\r?\n/)){let parts;if(line.includes("(hex)"))parts=line.split("(hex)",2);else if(line.includes("\t"))parts=line.split("\t",2);else if(line.includes(";"))parts=line.split(";",2);else continue;const prefix=normalizePrefix(parts[0]),vendor=String(parts[1]||"").trim().replace(/^"|"$/g,"");if([6,8,10].includes(prefix.length)&&vendor)mappings[prefix]=vendor;}}if(!Object.keys(mappings).length)throw new Error("В файле не найдены правила OUI 3/4/5 байт.");return mappings;}
  async function importOuiReference(){const input=$("#ouiReferenceFileInput"),file=input?.files?.[0],target=$("#ouiReferenceStatus");if(!file){toast("Выберите OUI-справочник TXT или CSV.");return;}if(file.size>64*1024*1024){toast("Справочник больше 64 МБ.");return;}const processId=beginProcess("Импорт OUI-справочника",file.name,5);try{target.textContent="Загрузка справочника...";updateProcess(processId,25,"Передача справочника без Base64-копии");const result=await api("/reference/oui/import",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name)},body:file});target.textContent=ouiReferenceStatusText(result.status||{});updateProcess(processId,80,`Импортировано: ${Number(result.imported?.count||0).toLocaleString("ru-RU")}`);await renderMappings();applyLocalVendorModelMappings(state.devices);await applyBackendDetectionToCurrentResult();save();renderResults();renderAnalytics();renderHistory();finishProcess(processId,"OUI-справочник загружен и применён к текущему результату");toast(`Загружено OUI-правил: ${Number(result.imported?.count||0).toLocaleString("ru-RU")}`);}catch(error){if(!networkUnavailable(error)){target.textContent=error.message;failProcess(processId,error);toast(error.message);return;}try{updateProcess(processId,45,"Backend недоступен: разбор справочника в браузере");const mappings=await parseLocalOuiReference(file);state.localVendorMappings={...state.localVendorMappings,...mappings};applyLocalVendorModelMappings(state.devices);save({immediate:true});await flushBrowserStateSave().catch(()=>{});renderMappings();renderResults();renderAnalytics();renderHistory();target.textContent=`Автономно загружено: ${Object.keys(mappings).length.toLocaleString("ru-RU")} правил`;finishProcess(processId,"OUI-справочник сохранён в браузере","warning");toast(`Автономно загружено OUI-правил: ${Object.keys(mappings).length.toLocaleString("ru-RU")}`);}catch(localError){target.textContent=localError.message;failProcess(processId,localError);toast(localError.message);}}finally{if(input)input.value="";}}
  function localMappingRows(rules,type){
    const entries=Object.entries(rules||{}).sort((a,b)=>a[0].localeCompare(b[0]));
    return entries.length?entries.map(([prefix,name])=>`<div class="summary-line"><strong>${esc(prefix)}</strong><span>${esc(name)}</span>${type==="model"?`<button class="button secondary" data-model-prefixes="${esc(name)}">Префиксы</button>`:""}<button class="icon-button" data-local-remove-${type}="${esc(prefix)}" title="Удалить">×</button></div>`).join(""):'<p class="muted">Локальные правила пока не добавлены.</p>';
  }
  function renderLocalMappings(){
    $("#vendorMappingList").innerHTML=localMappingRows(state.localVendorMappings,"vendor");
    $("#modelMappingList").innerHTML=localMappingRows(state.localModelMappings,"model");
  }
  function vendorModelLearnSettings(){return{minCount:Math.max(1,Math.min(999,Number($("#vendorModelLearnMinCount")?.value||2))),source:($("#vendorModelLearnSource")?.value||"").trim()};}
  function learnLocalVendorModelMappings(settings=vendorModelLearnSettings()){
    const source=String(settings.source||"").toLowerCase(),rows=localFlatHistory().concat(state.devices||[]).filter((device)=>!source||[device.source,device._snapshot?.source,device._snapshot?.name].join(" ").toLowerCase().includes(source)),learned=learnLocalRulesFromDevices(rows,settings.minCount);
    applyLocalVendorModelMappings(state.devices);
    save();renderMappings();renderResults();renderAnalytics();
    return learned;
  }
  function deliverDownload(name,blob){
    if(localFolderStructure)LocalFolderStore?.writeExport?.(localFolderStructure,name,blob).catch((error)=>localFolderStatus("Не удалось сохранить экспорт: "+error.message,"error"));
    const url=URL.createObjectURL(blob),link=document.createElement("a");
    link.href=url;link.download=name;link.hidden=true;document.body.appendChild(link);link.click();
    setTimeout(()=>{URL.revokeObjectURL(url);link.remove();},15_000);
  }
  function download(name,text,type){deliverDownload(name,new Blob([text],{type:type+";charset=utf-8"}));}
  function downloadBase64(name,content,type){const bytes=Uint8Array.from(atob(content),(char)=>char.charCodeAt(0));deliverDownload(name,new Blob([bytes],{type}));}
  function clipboardSafeCell(value){return String(value??"").replace(/\t|\r?\n/g," ").trim();}
  function tableRowsToTsv(rows){return rows.map((row)=>row.map(clipboardSafeCell).join("\t")).join("\n");}
  async function copyTextToClipboard(value,label="данные"){
    const text=String(value||"");
    if(!text.trim()){toast("Нет данных для копирования.");return false;}
    try{
      if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(text);
      else{
        const area=document.createElement("textarea");area.value=text;area.readOnly=true;area.style.position="fixed";area.style.opacity="0";document.body.appendChild(area);area.select();document.execCommand("copy");area.remove();
      }
      toast("Скопировано: "+label);return true;
    }catch(error){toast("Не удалось скопировать: "+error.message);return false;}
  }
  function tableClipboardText(table){
    if(!table)return"";
    const headers=Array.from(table.querySelectorAll("thead th")).map((cell)=>cell.textContent);
    const rows=Array.from(table.querySelectorAll("tbody tr:not([hidden])")).filter((row)=>!row.querySelector(".empty-state")).map((row)=>Array.from(row.cells).map((cell)=>cell.textContent));
    return tableRowsToTsv(headers.length?[headers,...rows]:rows);
  }
  function selectTableRow(row){
    if(!row||!row.closest("table"))return null;
    row.closest("table").querySelectorAll("tbody tr.selected-row").forEach((item)=>{item.classList.remove("selected-row");item.setAttribute("aria-selected","false");});
    row.classList.add("selectable-row","selected-row");row.setAttribute("aria-selected","true");return row;
  }
  function selectedTableRow(table){return table?.querySelector("tbody tr.selected-row")||null;}
  function rowMac(row){return normalize(row?.dataset.mac||row?.cells?.[0]?.textContent||"");}
  function copySelectedTableMac(table){const mac=rowMac(selectedTableRow(table));return copyTextToClipboard(mac?formatMac(mac):"","MAC-адрес");}
  function copyTable(table,label){return copyTextToClipboard(tableClipboardText(table),label);}
  function hideTableContextMenu(){const menu=$("#tableContextMenu");if(menu)menu.hidden=true;contextTableRow=null;}
  function showTableContextMenu(event,row){
    const menu=$("#tableContextMenu");if(!menu||!rowMac(row))return;
    event.preventDefault();contextTableRow=selectTableRow(row);menu.hidden=false;
    const width=menu.offsetWidth||190,height=menu.offsetHeight||120;
    menu.style.left=Math.max(6,Math.min(event.clientX,window.innerWidth-width-6))+"px";
    menu.style.top=Math.max(6,Math.min(event.clientY,window.innerHeight-height-6))+"px";
    menu.querySelector("button")?.focus();
  }
  function bindSelectableMacTable(body){
    body?.addEventListener("click",(event)=>{const row=event.target.closest("tr[data-mac]");if(row)selectTableRow(row);});
    body?.addEventListener("contextmenu",(event)=>{const row=event.target.closest("tr[data-mac]");if(row)showTableContextMenu(event,row);});
  }
  function focusViewSection(viewName,selector){view(viewName);requestAnimationFrame(()=>{const target=$(selector);target?.scrollIntoView({block:"center"});target?.focus?.();});}
  function closeActiveDialog(){const dialogs=$$("dialog[open]");if(!dialogs.length)return false;dialogs[dialogs.length-1].close();return true;}
  function cancelActiveEnrichment(){if(!enrichmentController&&!currentEnrichmentJobId)return false;if(currentEnrichmentJobId)api("/enrichment/jobs/"+encodeURIComponent(currentEnrichmentJobId),{method:"DELETE"}).catch(()=>{});enrichmentController?.abort();return true;}
  function handleAppShortcut(event){
    const keyName=String(event.key||"").toLowerCase(),ctrl=event.ctrlKey||event.metaKey;
    if(!keyName)return;
    if(keyName==="escape"){if(!$("#tableContextMenu")?.hidden){event.preventDefault();hideTableContextMenu();return;}if(closeActiveDialog()){event.preventDefault();return;}if(cancelActiveEnrichment())event.preventDefault();return;}
    if(keyName==="f1"){event.preventDefault();$("#helpDialog").showModal();return;}
    if(ctrl&&keyName==="o"){event.preventDefault();$("#fileInput").click();return;}
    if(ctrl&&keyName==="s"){event.preventDefault();exportManagedBinary("xlsx").catch((error)=>toast(error.message));return;}
    if(ctrl&&keyName==="e"){event.preventDefault();exportData("csv");return;}
    if(ctrl&&keyName==="a"){event.preventDefault();view("analytics");return;}
    if(ctrl&&keyName==="h"){event.preventDefault();view("history");return;}
    if(ctrl&&keyName==="f"){event.preventDefault();focusViewSection("workspace","#searchInput");return;}
    if(event.altKey||ctrl||event.shiftKey)return;
    if(keyName==="f5"){event.preventDefault();analyze();return;}
    if(keyName==="f6"){event.preventDefault();view("compare");return;}
    if(keyName==="f7"){event.preventDefault();focusViewSection("analytics","#backendChartsPanel");return;}
    if(keyName==="f8"){event.preventDefault();focusViewSection("analytics","#topologyGraph");return;}
    if(keyName==="f9"){event.preventDefault();focusViewSection("compare","#multiComparisonSelect");}
  }
  function exportColumns(){return(state.visibleColumns||empty().visibleColumns).filter(Boolean).map((key)=>({key,title:labels[key]||key}));}
  function exportCell(device,key,index){if(key==="row")return index+1;if(key==="oui")return formatOuiValue(device.mac||device.macFormatted||device.oui);if(key==="macFormatted")return device.macFormatted||formatMac(device.mac);return device[key]??"";}
  function localExportTable(){const columns=exportColumns();return{columns,rows:state.devices.map((device,index)=>columns.map((column)=>exportCell(device,column.key,index)))};}
  function localCsvLine(row,separator=","){return row.map((value)=>'"'+String(value??"").replace(/"/g,'""')+'"').join(separator);}
  function localYamlScalar(value){const text=String(value??"");return text===""?'""':/[\n:#\[\]{},"']|^\s|\s$/.test(text)?JSON.stringify(text):text;}
  function localSpreadsheetXml(table){const header='<Row>'+table.columns.map((column)=>`<Cell><Data ss:Type="String">${esc(column.title)}</Data></Cell>`).join("")+'</Row>',body=table.rows.map((row)=>'<Row>'+row.map((cell)=>`<Cell><Data ss:Type="String">${esc(cell)}</Data></Cell>`).join("")+'</Row>').join("");return'<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="MAC Analyzer"><Table>'+header+body+'</Table></Worksheet></Workbook>';}
  function localHtmlExport(table){const head=table.columns.map((column)=>`<th>${esc(column.title)}</th>`).join(""),body=table.rows.map((row)=>`<tr>${row.map((cell)=>`<td>${esc(cell)}</td>`).join("")}</tr>`).join("");return`<!doctype html><html><head><meta charset="utf-8"><title>MAC Analyzer Export</title><style>body{font:14px Arial;margin:32px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:7px;text-align:left}th{background:#eee}</style></head><body><h1>MAC Analyzer Export</h1><p>Created: ${new Date().toISOString()}</p><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></body></html>`;}
  function localExportData(type){if(!currentDeviceCount()){toast("Нет результатов для экспорта.");return false;}try{MemoryGuard.assertLocalExportCapacity(state.devices.length,state.devices.length*exportColumns().length);}catch(error){toast(error.message);return false;}const table=localExportTable(),date=new Date().toISOString().replace(/[:.]/g,"-").slice(0,19),name="mac-analysis-"+date;let filename=name+"."+type,mime="text/plain",content="";if(type==="csv"){filename=name+".csv";mime="text/csv";content="\uFEFF"+[table.columns.map((c)=>c.title),...table.rows].map((row)=>localCsvLine(row)).join("\n");}else if(type==="txt"){filename=name+".txt";content=[table.columns.map((c)=>c.title),...table.rows].map((row)=>row.map((value)=>String(value??"")).join("\t")).join("\n");}else if(type==="json"){filename=name+".json";mime="application/json";content=JSON.stringify({export_date:new Date().toISOString(),count:state.devices.length,devices:state.devices},null,2);}else if(type==="yaml"){filename=name+".yaml";content=["export_date: "+new Date().toISOString(),"count: "+state.devices.length,"devices:",...state.devices.map((device)=>"  - "+exportColumns().map((column)=>`${column.key}: ${localYamlScalar(exportCell(device,column.key,0))}`).join("\n    "))].join("\n");}else if(type==="html"){filename=name+".html";mime="text/html";content=localHtmlExport(table);}else if(type==="spreadsheetml"||type==="xls"||type==="xlsx"){filename=name+".xls";mime="application/vnd.ms-excel";content=localSpreadsheetXml(table);}else{return false;}download(filename,content,mime);toast("Экспорт выполнен в браузере без backend.");return true;}
  async function streamCurrentXlsxRows(acceptRows){
    await snapshotMutationPromise;
    if(state.resultBrowserSnapshotId){
      if(!BrowserSnapshots?.streamSnapshot)throw new Error("Хранилище полного результата недоступно");
      const metadata=await BrowserSnapshots.streamSnapshot(state.resultBrowserSnapshotId,async(kind,rows)=>{if(kind==="device")await acceptRows(rows);});
      if(!metadata)throw new Error("Полный результат анализа не найден в локальной базе");
      return;
    }
    await acceptRows(state.devices||[]);
  }
  async function exportLocalXlsx(processId){
    const columns=exportColumns(),totalRows=currentDeviceCount(),date=new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);
    updateProcess(processId,15,`Потоковый XLSX: ${totalRows.toLocaleString("ru-RU")} строк`);
    const result=await XlsxExporter.createWorkbook({
      columns:columns.map((column)=>column.title),
      totalRows,
      sheetName:"MAC Analyzer",
      streamRows:streamCurrentXlsxRows,
      rowMapper:(device,index)=>columns.map((column)=>exportCell(device,column.key,index)),
      onProgress:(percent,message)=>updateProcess(processId,Math.max(15,Math.min(95,percent)),message),
    });
    if(result.rows!==totalRows)throw new Error(`XLSX содержит ${result.rows.toLocaleString("ru-RU")} из ${totalRows.toLocaleString("ru-RU")} строк`);
    deliverDownload(`mac-analysis-${date}.xlsx`,result.blob);
    return result;
  }
  async function exportAllDevices(){
    if(!BrowserSnapshots?.countDeviceHistory||!BrowserSnapshots?.streamDeviceHistory)throw new Error("Накопительная база устройств недоступна");
    let firstBackendPage=null;
    if(backendAvailable)firstBackendPage=await api("/database/devices/all?offset=0&limit=1000").catch(()=>null);
    const totalRows=Number(firstBackendPage?.total||0)||await BrowserSnapshots.countDeviceHistory();
    if(!totalRows){toast("В накопительной базе пока нет устройств.");return null;}
    const processId=beginProcess("Все устройства","Потоковая выгрузка накопительной базы",5);
    try{
      const columns=["MAC","Производитель","Модель","IP","Физический адрес","Помещение","Smartroom ID","IP коммутатора","Порт","Источник","Последнее обновление"];
      const result=await XlsxExporter.createWorkbook({
        columns,totalRows,sheetName:"Все устройства",
        streamRows:async(accept)=>{
          if(!firstBackendPage?.total)return BrowserSnapshots.streamDeviceHistory(accept);
          let page=firstBackendPage;
          while(page){await accept(page.items||[]);page=page.nextOffset===null?null:await api(`/database/devices/all?offset=${page.nextOffset}&limit=1000`);}
        },
        rowMapper:(device)=>[formatMac(device.mac),device.vendor||"",device.model||"",device.ip||"",device.address||"",device.room||"",device.smartroomId||"",device.switchIp||"",device.switchPort||"",device.source||"",device.updatedAt||""],
        onProgress:(percent,message)=>updateProcess(processId,Math.max(5,Math.min(98,percent)),message),
      });
      if(result.rows!==totalRows)throw new Error(`Выгружено ${result.rows} из ${totalRows} устройств`);
      const date=new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);
      deliverDownload(`mac-analyzer-all-devices-${date}.xlsx`,result.blob);
      finishProcess(processId,`Выгружено устройств: ${totalRows.toLocaleString("ru-RU")}`);
      return result;
    }catch(error){failProcess(processId,error);toast(error.message);throw error;}
  }
  async function streamAllDeviceRows(acceptRows){
    let page=backendAvailable?await api("/database/devices/all?offset=0&limit=1000").catch(()=>null):null;
    if(page?.total){while(page){await acceptRows(page.items||[]);page=page.nextOffset===null?null:await api(`/database/devices/all?offset=${page.nextOffset}&limit=1000`);}return;}
    if(!BrowserSnapshots?.streamDeviceHistory)throw new Error("Накопительная база устройств недоступна");
    await BrowserSnapshots.streamDeviceHistory(acceptRows);
  }
  async function streamFullReportSnapshotRows(snapshot,acceptRows){
    if(snapshot?.browserStored&&BrowserSnapshots?.streamSnapshot){
      const metadata=await BrowserSnapshots.streamSnapshot(snapshot.id,async(kind,rows)=>{if(kind==="device")await acceptRows(rows);});
      if(metadata)return;
    }
    await acceptRows(snapshot?.devices||[]);
  }
  async function streamFullReportInvalidRows(acceptRows){
    if(state.resultBrowserSnapshotId&&BrowserSnapshots?.streamSnapshot){
      const metadata=await BrowserSnapshots.streamSnapshot(state.resultBrowserSnapshotId,async(kind,rows)=>{if(kind==="invalid")await acceptRows(rows);});
      if(metadata)return;
    }
    await acceptRows(state.invalid||[]);
  }
  async function fullExportAnalyticsPayload(){
    if(state.resultBrowserSnapshotId&&BrowserSnapshots?.aggregate){
      const aggregate=await BrowserSnapshots.aggregate(state.resultBrowserSnapshotId,{limit:200});
      if(aggregate)return analysisDashboardAggregatePayload(aggregate);
    }
    return analysisDashboardLocalPayload(state.devices,state.resultSummary);
  }
  async function exportFullWorkbook(){
    if(!currentDeviceCount()&&!(state.snapshots||[]).length){toast("Нет данных для полного Excel-отчёта.");return null;}
    const processId=beginProcess("Полный Excel","Сбор аналитики и всей истории",5);
    try{
      updateProcess(processId,8,"Расчёт аналитики полного результата");
      const report=await FullXlsxReport.buildReport({
        state,
        currentDeviceCount:currentDeviceCount(),
        currentInvalidCount:state.resultBrowserSnapshotId?Number(state.resultInvalidCount||0):(state.invalid||[]).length,
        maximumRows:XlsxExporter.maximumRows,
        streamCurrentRows:streamCurrentXlsxRows,
        streamInvalidRows:streamFullReportInvalidRows,
        streamSnapshotRows:streamFullReportSnapshotRows,
        analyticsPayload:fullExportAnalyticsPayload,
        formatMac,
        formatOuiValue,
        compactDevice:compactDashboardDevice,
        movementType:localMovementChangeType,
      });
      updateProcess(processId,12,`Формирование ${report.sheets.length} листов Excel`);
      const result=await XlsxExporter.createWorkbook({
        sheets:report.sheets,
        onProgress:(percent,message)=>updateProcess(processId,Math.max(12,Math.min(98,percent)),message),
      });
      const date=new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);
      deliverDownload(`mac-analyzer-full-${date}.xlsx`,result.blob);
      finishProcess(processId,`Полный Excel готов: ${result.sheets.length} листов`);
      toast(`Полный Excel сохранён: ${result.sheets.length} листов, ${result.rows.toLocaleString("ru-RU")} строк.`);
      return result;
    }catch(error){failProcess(processId,error);toast(error.message);throw error;}
  }
  async function exportFullJson(){
    if(!currentDeviceCount()&&!(state.snapshots||[]).length){toast("Нет данных для полного JSON-отчёта.");return null;}
    const processId=beginProcess("Полный JSON","Потоковая упаковка устройств, аналитики и истории",5);
    try{
      const result=await FullJsonReport.createReport({
        state,
        streamCurrentRows:streamCurrentXlsxRows,
        streamInventoryRows:streamAllDeviceRows,
        streamInvalidRows:streamFullReportInvalidRows,
        streamSnapshotRows:streamFullReportSnapshotRows,
        analyticsPayload:fullExportAnalyticsPayload,
        onProgress:(percent,message)=>updateProcess(processId,Math.max(5,Math.min(98,percent)),message),
      });
      const date=new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);
      deliverDownload(`mac-analyzer-full-${date}.json`,result.blob);
      finishProcess(processId,`Полный JSON готов: ${result.snapshots} выгрузок, ${result.snapshotRows.toLocaleString("ru-RU")} строк истории`);
      toast("Полный JSON сохранён.");
      return result;
    }catch(error){failProcess(processId,error);toast(error.message);throw error;}
  }
  async function exportCurrentJson(){
    const processId=beginProcess("Экспорт JSON","Потоковая упаковка полного текущего результата",5);
    try{
      const result=await FullJsonReport.createDeviceExport({
        streamRows:streamCurrentXlsxRows,
        onProgress:(count)=>updateProcess(processId,Math.min(96,10+Math.round(count/Math.max(1,currentDeviceCount())*86)),`Упаковано устройств: ${count.toLocaleString("ru-RU")}`),
      });
      const date=new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);
      deliverDownload(`mac-analysis-${date}.json`,result.blob);
      finishProcess(processId,`JSON готов: ${result.rows.toLocaleString("ru-RU")} устройств`);
      toast("JSON сохранён полностью.");
      return result;
    }catch(error){failProcess(processId,error);throw error;}
  }
  async function exportManagedBinary(type){
    if(!currentDeviceCount()){toast("Нет результатов для экспорта.");return;}
    const processId=beginProcess("Экспорт "+type.toUpperCase(),"Подготовка "+currentDeviceCount()+" записей",10),columns=exportColumns(),ouiSettings={length:state.ouiLength,style:state.ouiStyle};
    if(type==="xlsx"&&!state.resultSnapshotId){
      try{const result=await exportLocalXlsx(processId);toast(`XLSX сохранён: ${result.rows.toLocaleString("ru-RU")} строк.`);finishProcess(processId,"XLSX полностью сформирован в браузере");return result;}
      catch(error){failProcess(processId,error);throw error;}
    }
    try{updateProcess(processId,35,"Формирование файла ExportManager");const result=await api("/export",{method:"POST",body:JSON.stringify(currentDevicePayload({format:type,columns,ouiSettings}))});if(!result.binary)throw new Error("Backend returned text export for "+type);updateProcess(processId,85,"Сохранение сформированного файла");downloadBase64(result.filename||("mac-analysis."+type),result.content,result.mimeType||"application/octet-stream");toast("Экспорт подготовлен ExportManager.");finishProcess(processId,"Экспорт "+type.toUpperCase()+" готов");}
    catch(error){if(type==="xlsx"){failProcess(processId,error);throw new Error("Полный backend-снимок временно недоступен для XLSX: "+error.message);}if(type==="pdf"){updateProcess(processId,60,"Локальное формирование отчёта");localExportData("html");toast("Backend недоступен: скачан HTML-отчёт для печати/PDF.");finishProcess(processId,"HTML-отчёт подготовлен для печати/PDF","warning");return;}failProcess(processId,error);throw error;}
  }
  async function exportData(type){
    if(!currentDeviceCount()){toast("Нет результатов для экспорта.");return;}
    if(type==="json"){try{return await exportCurrentJson();}catch(error){toast(error.message);return;}}
    const processId=beginProcess("Экспорт данных","Подготовка формата "+type,10),columns=exportColumns(),ouiSettings={length:state.ouiLength,style:state.ouiStyle};
    try{updateProcess(processId,35,"Формирование файла backend-сервисом");const result=await api("/export",{method:"POST",body:JSON.stringify(currentDevicePayload({format:type,columns,ouiSettings}))});updateProcess(processId,85,"Сохранение файла");if(result.binary){downloadBase64(result.filename||("mac-analysis."+type),result.content,result.mimeType||"application/octet-stream");}else{download(result.filename||("mac-analysis."+type),type==="csv"?"\uFEFF"+result.content:result.content,result.mimeType||"text/plain");}toast("Экспорт подготовлен backend-сервисом.");finishProcess(processId,"Экспорт завершён: "+type);}
    catch(error){updateProcess(processId,60,"Backend недоступен: локальный экспорт");if(localExportData(type))finishProcess(processId,"Экспорт завершён в браузере: "+type,"warning");else{toast("Backend export error: "+error.message);failProcess(processId,error);}}
  }
  async function renderServices(){
    try {
      const serviceData=await api("/services/panel"),notificationData=serviceData.notifications||{},html=serviceData.html||{};
      $("#ipMappingList").innerHTML=html.ipRowsHtml||'<p class="muted">Соответствия пока не добавлены.</p>';
      $("#taskList").innerHTML=html.taskRowsHtml||'<p class="muted">Задачи пока не созданы.</p>';
      const channel=notificationData.channels.find((item)=>item.channel===$("#notificationChannel").value);
      if(channel){$("#notificationEnabled").checked=Boolean(channel.enabled);$("#notificationConfig").value=JSON.stringify(channel.config||{},null,2);}
      $("#appLogList").innerHTML=html.logRowsHtml||'<p class="muted">Журнал пока пуст.</p>';
      $("#metricList").innerHTML=html.metricRowsHtml||'<p class="muted">Метрики пока пусты.</p>';
      $("#timeStatsSummary").innerHTML=html.timeStatsSummaryHtml||'<div class="bar-label"><span>Operations</span><strong>0</strong></div>';
      $("#timeStatsBody").innerHTML=html.timeStatsRowsHtml||'<tr><td colspan="6" class="empty-state">Статистика по времени пока пуста.</td></tr>';
      const autosaveStatus=$("#autosaveStatus"); if(autosaveStatus)autosaveStatus.textContent=html.autosaveStatusText||"Autosave slots are empty.";
      $("#databaseSummary").innerHTML=html.databaseSummaryHtml||"";
      $("#legacyImportSummary").innerHTML=html.legacySummaryHtml||"";
    } catch { renderLocalIpMappings(); renderLocalTimeStats(); }
  }
  function normalizeIp(value){const parts=String(value||"").trim().match(/\d{1,3}(?:\.\d{1,3}){3}/);if(!parts)return"";const ip=parts[0].split(".").map(Number);return ip.every((part)=>part>=0&&part<=255)?ip.join("."):"";}
  function localIpMappingRows(){return Array.isArray(state.ipMappings)?state.ipMappings:[];}
  function renderLocalIpMappings(){
    const mappings=localIpMappingRows();
    $("#ipMappingList").innerHTML=mappings.length?mappings.map((item)=>`<div class="summary-line"><strong>${esc(item.switchIp)}</strong><span>${esc(item.address||"")} ${item.source?("· "+esc(item.source)):""}</span><button class="icon-button" data-remove-local-ip="${esc(item.switchIp)}" title="Удалить">×</button></div>`).join(""):'<p class="muted">Локальные соответствия IP коммутаторов пока не добавлены.</p>';
    const summary=$("#databaseSummary");
    if(summary&&!summary.innerHTML)summary.innerHTML=`<div class="bar-item"><div class="bar-label"><span>Локальные IP-маппинги</span><strong>${mappings.length}</strong></div></div>`;
  }
  function renderLocalTimeStats(){
    const snapshots=Array.isArray(state.snapshots)?state.snapshots:[],movements=Array.isArray(state.movementHistory)?state.movementHistory:[];
    const summary=$("#timeStatsSummary"),body=$("#timeStatsBody");
    if(summary)summary.innerHTML=`<div class="bar-label"><span>Local snapshots</span><strong>${snapshots.length}</strong></div><div class="bar-label"><span>Local movements</span><strong>${movements.length}</strong></div><div class="bar-label"><span>Current devices</span><strong>${state.devices.length}</strong></div>`;
    if(body)body.innerHTML=snapshots.slice(0,50).map((snapshot)=>`<tr><td>${esc((snapshot.createdAt||"").slice(0,10))}</td><td>${esc((snapshot.createdAt||"").slice(11,19))}</td><td>snapshot</td><td>${esc(snapshot.source||snapshot.name||"browser")}</td><td>${(snapshot.devices||[]).length}</td><td>-</td></tr>`).join("")||'<tr><td colspan="6" class="empty-state">Локальная статистика по времени пока пуста.</td></tr>';
  }
  function upsertLocalIpMapping(switchIp,address,source="manual"){
    const ip=normalizeIp(switchIp),addr=String(address||"").trim();
    if(!ip||!addr)return false;
    const next=localIpMappingRows().filter((item)=>item.switchIp!==ip);
    next.unshift({switchIp:ip,address:addr,source,updatedAt:new Date().toISOString()});
    state.ipMappings=next.slice(0,2000);
    save();
    return true;
  }
  function localIpMappingFields(headers){
    const lower=headers.map((header)=>String(header||"").toLowerCase());
    const find=(patterns)=>lower.findIndex((header)=>patterns.some((pattern)=>pattern.test(header)));
    return{switchIp:find([/switch.*ip/,/ip.*switch/,/коммутатор.*ip/,/ip.*коммут/,/^ip$/]),address:find([/address/,/addr/,/адрес/,/location/,/room/,/помещ/,/стойк/])};
  }
  async function importLocalIpMappings(file){
    const table=await clientReadTable(file),fields=localIpMappingFields(table.headers),switchIndex=fields.switchIp>=0?fields.switchIp:0,addressIndex=fields.address>=0?fields.address:1;
    let imported=0,skipped=0;
    table.rows.forEach((row)=>{if(upsertLocalIpMapping(row[switchIndex],row[addressIndex],file.name))imported++;else skipped++;});
    renderLocalIpMappings();
    return{imported,skipped};
  }
  async function applyLocalIpMappings(){
    const operation=snapshotMutationPromise.then(()=>applyLocalIpMappingsNow());
    snapshotMutationPromise=operation.catch(()=>{});
    return operation;
  }
  async function applyLocalIpMappingsNow(){
    const map=Object.fromEntries(localIpMappingRows().map((item)=>[item.switchIp,item.address]));
    let matched=0,filled=0;const movements=[],limit=MemoryGuard.limits.movementRows||5000,changedAt=new Date().toISOString();
    const apply=(device)=>{const address=map[normalizeIp(device.switchIp)];if(!address)return false;matched++;if(device.address===address)return false;const before=device.address||"",beforeDevice=compactDashboardDevice(device);device.address=address;filled++;if(movements.length<limit)movements.push({mac:normalize(device.mac||device.macFormatted),type:"Изменено",field:labels.address||"Адрес помещения",before,after:address,beforeDevice,afterDevice:compactDashboardDevice(device),changedAt,source:"local-ip-mapping"});return true;};
    if(state.resultBrowserSnapshotId&&BrowserSnapshots?.updateSnapshotWithTransform){
      const processId=beginProcess("Применение IP-маппинга","Потоковое обновление текущего финального результата",5);
      try{
        const result=await updateCurrentBrowserSnapshot("Обогащение: IP-маппинг","local-ip-mapping",apply,(percent)=>updateProcess(processId,5+Math.round(percent*0.9),`Обработано полного снимка: ${percent}%`));
        if(result?.updated&&movements.length)state.movementHistory=movements.concat((state.movementHistory||[]).slice(0,Math.max(0,limit-movements.length)));
        finishProcess(processId,result?.updated?"IP-маппинг применён к текущему финальному результату":"Подходящих изменений не найдено");
      }catch(error){failProcess(processId,error);throw error;}
    }else{
      state.devices.forEach(apply);
      if(filled&&state.resultBrowserSnapshotId)state.resultBrowserSnapshotDirty=true;
    }
    save();
    renderResults();
    renderAnalytics();
    renderLocalIpMappings();
    return{matched,filled};
  }
  function autodetectLocalIpMappings(){
    let imported=0;
    state.devices.forEach((device)=>{if(upsertLocalIpMapping(device.switchIp,device.address||device.room||device.location||"",device.source||"current-results"))imported++;});
    renderLocalIpMappings();
    return imported;
  }
  function exportLocalIpMappings(){
    const content="\uFEFFswitch_ip,address,source,updated_at\n"+localIpMappingRows().map((item)=>localCsvLine([item.switchIp,item.address,item.source,item.updatedAt])).join("\n");
    download("ip-address-mappings.csv",content,"text/csv");
  }
  async function exportModelPrefixes(){
    let rows=[];
    try{const data=await api("/mappings/models");rows=(data.rules||[]).map((item)=>[item.prefix||"",item.model||"",item.source||"",item.updated_at||item.updatedAt||""]);}
    catch{rows=Object.entries(state.localModelMappings||{}).map(([prefix,model])=>[prefix,model,"browser-history",""]);}
    rows.sort((a,b)=>String(a[0]).localeCompare(String(b[0])));
    const content="\uFEFFprefix_hex,model,source,updated_at\n"+rows.map((row)=>localCsvLine(row)).join("\n");
    download("mac-model-hex-prefixes.csv",content,"text/csv");
    toast(`Выгружено HEX-правил моделей: ${rows.length.toLocaleString("ru-RU")}`);
  }
  async function searchDatabase(){
    const root=$("#databaseSearchResults"); if(!root)return;
    const query=($("#databaseSearchInput")?.value||"").trim();
    try{
      const data=await api("/database/search?query="+encodeURIComponent(query)+"&limit=100");
      root.innerHTML=data.resultsHtml||data.emptyResultsHtml||'<p class="muted">Ничего не найдено.</p>';
    }catch(error){
      root.innerHTML='<p class="muted">Поиск недоступен: '+esc(error.message)+'</p>';
    }
  }
  async function importDatabaseFile(file){
    const status=$("#databaseImportStatus");
    if(!file)return;
    if(file.size>1024*1024*1024){toast("Файл базы превышает 1 ГБ.");return;}
    const processId=beginProcess("Загрузка базы SQLite",file.name,5);
    try{
      if(status)status.textContent="Передача и проверка целостности базы...";
      updateProcess(processId,20,"Передача файла без Base64-копии");
      const result=await api("/database/import",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name)},body:file});
      updateProcess(processId,85,`Объединено записей: ${Number(result.imported||0).toLocaleString("ru-RU")}`);
      await syncFromBackend();await loadDatabaseHistoryManagement();renderServices();renderAll();
      const tableCount=Object.keys(result.tables||{}).length;
      if(status)status.textContent=`База загружена: объединено ${Number(result.imported||0).toLocaleString("ru-RU")} записей из ${tableCount} таблиц; integrity: ${result.integrity||"ok"}.`;
      finishProcess(processId,"База SQLite проверена и объединена");toast("База SQLite успешно загружена.");
    }catch(error){if(status)status.textContent=error.message;failProcess(processId,error);toast(error.message);}
    finally{if($("#databaseImportInput"))$("#databaseImportInput").value="";}
  }
  function databaseHistoryFilters(){
    return{
      mac:($("#dbHistoryMacFilter")?.value||"").trim(),
      source:($("#dbHistorySourceFilter")?.value||"").trim(),
      vendor:($("#dbHistoryVendorFilter")?.value||"").trim(),
      model:($("#dbHistoryModelFilter")?.value||"").trim(),
      room:($("#dbHistoryRoomFilter")?.value||"").trim(),
      dateFrom:$("#dbHistoryDateFrom")?.value||"",
      dateTo:$("#dbHistoryDateTo")?.value||""
    };
  }
  function databaseHistoryParams(filters=databaseHistoryFilters()){
    const params=new URLSearchParams({limit:"1000"});
    const names={mac:"mac",source:"source",vendor:"vendor",model:"model",room:"room",dateFrom:"from",dateTo:"to"};
    Object.entries(names).forEach(([key,name])=>{if(filters[key])params.set(name,filters[key]);});
    return params;
  }
  async function loadDatabaseHistoryManagement(){
    const body=$("#databaseHistoryBody"),summary=$("#databaseHistorySummary");
    if(!body||!summary)return;
    body.innerHTML='<tr><td colspan="13" class="empty-state">История загружается...</td></tr>';
    try{
      const data=await api("/database/history/records?"+databaseHistoryParams().toString());
      body.innerHTML=data.rowsHtml||data.emptyRowsHtml||'<tr><td colspan="13" class="empty-state">Записи истории не найдены.</td></tr>';
      summary.innerHTML=data.summaryHtml||"";
      const selectAll=$("#selectAllDatabaseHistory");if(selectAll){selectAll.checked=false;selectAll.indeterminate=false;}
    }catch(error){
      body.innerHTML='<tr><td colspan="13" class="empty-state">История SQLite недоступна: '+esc(error.message)+'</td></tr>';
      summary.innerHTML="";
    }
  }
  function selectedDatabaseHistoryIds(){return $$('[data-db-history-select]:checked').map((input)=>Number(input.value)).filter((id)=>Number.isInteger(id)&&id>0);}
  async function deleteDatabaseHistoryEntries(ids=[],filters={}){
    if(!state.engineeringMode||!state.engineeringToken){toast("Для удаления включите инженерный режим.");return false;}
    const selected=Array.isArray(ids)?ids:[];
    const activeFilters=Object.fromEntries(Object.entries(filters||{}).filter(([,value])=>String(value||"").trim()));
    if(!selected.length&&!Object.keys(activeFilters).length){toast("Выберите записи или задайте хотя бы один фильтр.");return false;}
    const message=selected.length?`Удалить выбранные записи (${selected.length})?`:`Удалить все записи по текущему фильтру?`;
    if(!confirm(message))return false;
    try{
      const result=await api("/database/history/delete",{method:"POST",body:JSON.stringify({ids:selected,filters:activeFilters})});
      await loadDatabaseHistoryManagement();
      renderServices();
      toast("Удалено записей истории: "+result.deleted);
      return true;
    }catch(error){toast(error.message);return false;}
  }
  async function openDatabaseDevice(mac){
    if(!mac)return;
    if(!state.devices.some((item)=>item.mac===mac)){
      const result=await api("/database/device?mac="+encodeURIComponent(mac));
      state.devices.unshift(result.device);
      save();
      renderResults();
    }
    showDevice(mac);
  }
  async function renderParityStatus(){
    const root=$("#parityStatusSummary"),details=$("#parityDetailsList");
    if(!root)return;
    try{
      const data=await api("/parity/status");
      root.innerHTML=data.summaryHtml||'<p class="muted">Parity status is empty.</p>';
      if(details){
        details.innerHTML=data.detailsHtml||data.emptyDetailsHtml||'<p class="muted">Нет данных parity.</p>';
      }
    }catch(error){
      root.innerHTML='<p class="muted">Parity status недоступен: '+esc(error.message)+'</p>';
      if(details)details.innerHTML="";
    }
  }
  async function exportParityReport(){
    try{
      const report=await api("/parity/report");
      download(report.filename||"mac-analyzer-parity-report.json",report.content||"{}",report.mimeType||"application/json");
      toast("Parity report exported.");
    }catch(error){
      toast(error.message);
    }
  }
  function localSystemDiagnostics(){
    const checks=[
      ["Frontend","Основной контроллер",Boolean(window.MacAnalyzerAppReady),"app.js загружен"],
      ["Frontend","Чтение XLSX",Boolean(window.MacAnalyzerFileReaders),"Потоковый browser parser"],
      ["Frontend","DDIO-подсказки",Boolean(DdioOverlay),"Две MAC-колонки без изменения основных данных"],
      ["Большие файлы","Защита памяти",Boolean(window.MacAnalyzerMemoryGuard),"Лимиты, paging и yield"],
      ["Хранение","IndexedDB",Boolean(window.indexedDB),"Автономное хранение больших файлов"],
      ["Хранение","Файловая база MADB",Boolean(PortableDatabase),"Потоковый перенос данных между браузерами"],
      ["Интерфейс","Руководство",Boolean(window.MacAnalyzerGuide),"Навигация и режимы"],
    ].map(([group,name,passed,detail])=>({group,name,passed,status:passed?"passed":"failed",detail}));
    const passed=checks.filter(item=>item.passed).length,total=checks.length,failed=total-passed,readinessPercent=Math.round(passed/total*100);
    return{status:failed?"error":"healthy",summary:{passed,total,failed,warnings:0,readinessPercent,parityPercent:100},checks,
      summaryHtml:`<div class="bar-label"><span>Готовность HTML</span><strong>${readinessPercent}%</strong></div><div class="bar-label"><span>Frontend</span><strong>${passed}/${total}</strong></div><div class="bar-label"><span>Backend</span><strong>offline</strong></div><div class="bar-label"><span>Ошибки</span><strong>${failed}</strong></div>`,
      detailsHtml:checks.map(item=>`<div class="diagnostic-row diagnostic-${item.status}"><span><strong>${esc(item.name)}</strong><small>${esc(item.group)} · ${esc(item.detail)}</small></span><b>${item.passed?"OK":"Ошибка"}</b></div>`).join("")};
  }
  function paintSystemDiagnostics(data){
    const summary=$("#systemDiagnosticsSummary"),details=$("#systemDiagnosticsDetails");
    if(summary)summary.innerHTML=data.summaryHtml||'<p class="muted">Нет итогов диагностики.</p>';
    if(details)details.innerHTML=data.detailsHtml||'<p class="muted">Нет подробностей диагностики.</p>';
    if(summary){summary.dataset.loaded="true";summary.dataset.status=data.status||"unknown";}
  }
  async function runSystemDiagnostics(){
    const button=$("#runSystemDiagnosticsButton"),summary=$("#systemDiagnosticsSummary");
    if(button)button.disabled=true;
    if(summary)summary.innerHTML='<p class="muted">Проверка файлов, SQLite, API и защиты памяти...</p>';
    try{
      const data=await api("/system/diagnostics");
      paintSystemDiagnostics(data);
      toast(data.status==="healthy"?"Самодиагностика: программа готова.":"Самодиагностика обнаружила проблему.");
      return data;
    }catch(error){
      const data=localSystemDiagnostics();
      paintSystemDiagnostics(data);
      toast("Backend недоступен: выполнена локальная диагностика HTML.");
      return data;
    }finally{if(button)button.disabled=false;}
  }
  function applyResultColumnWidths(){
    const table=$("#resultsTable"),header=$("#resultsHeader"),columns=(state.visibleColumns||empty().visibleColumns).filter(Boolean);
    if(!table||!header)return;
    const cells=Array.from(header.querySelectorAll("th"));
    if(!cells.length)return;
    state.columnWidths=normalizeColumnWidths(state.columnWidths);
    let total=0;
    cells.forEach((cell,index)=>{
      const column=columns[index]||"column_"+index,width=state.columnWidths[column]||150;
      total+=width;cell.dataset.resultColumn=column;cell.style.width=width+"px";cell.style.minWidth=width+"px";cell.style.maxWidth=width+"px";
      if(!cell.querySelector(".column-resize-handle")){
        const handle=document.createElement("span");handle.className="column-resize-handle";handle.title="Изменить ширину столбца";handle.setAttribute("aria-hidden","true");
        handle.addEventListener("pointerdown",(event)=>{event.preventDefault();event.stopPropagation();resultColumnResize={column,startX:event.clientX,startWidth:state.columnWidths[column]||150,handle};handle.classList.add("active");handle.setPointerCapture?.(event.pointerId);});
        cell.appendChild(handle);
      }
    });
    const tableWidth=Math.max(900,total);table.style.tableLayout="fixed";table.style.width=tableWidth+"px";table.style.minWidth=tableWidth+"px";
    $$("#columnPreferenceList [data-column-width]").forEach((input)=>{if(document.activeElement!==input&&state.columnWidths[input.dataset.columnWidth])input.value=String(state.columnWidths[input.dataset.columnWidth]);});
  }
  function resizeResultColumn(event){if(!resultColumnResize)return;const width=Math.max(64,Math.min(600,resultColumnResize.startWidth+event.clientX-resultColumnResize.startX));state.columnWidths[resultColumnResize.column]=Math.round(width);applyResultColumnWidths();}
  function finishResultColumnResize(){if(!resultColumnResize)return;resultColumnResize.handle?.classList.remove("active");resultColumnResize=null;save();saveResultColumnWidths("Ширина столбца сохранена в SQLite.");}
  function optimizedResultColumnWidths(){
    const columns=(state.visibleColumns||empty().visibleColumns).filter(Boolean),rows=Array.from($("#resultsBody")?.querySelectorAll("tr:not([hidden])")||[]).slice(0,200),next=normalizeColumnWidths(state.columnWidths);
    columns.forEach((column,index)=>{let length=String(labels[column]||column).length;rows.forEach((row)=>{length=Math.max(length,String(row.cells[index]?.textContent||"").trim().length);});next[column]=Math.max(72,Math.min(420,Math.round(length*7.5+36)));});
    return next;
  }
  function resultColumnWidthsFromInputs(){const widths={};$$("#columnPreferenceList [data-column-width]").forEach((input)=>{const width=Number(input.value);if(Number.isFinite(width))widths[input.dataset.columnWidth]=Math.max(64,Math.min(600,Math.round(width)));});return widths;}
  async function saveResultColumnWidths(message="Ширина столбцов сохранена в SQLite."){
    state.columnWidths=normalizeColumnWidths({...state.columnWidths,...resultColumnWidthsFromInputs()});save();applyResultColumnWidths();
    try{const result=await api("/columns/preferences/results",{method:"POST",body:JSON.stringify(columnPreferencesPayload({widths:state.columnWidths}))});applyColumnPreferences(result.preferences);toast(message);return result.preferences;}
    catch(error){renderColumnPreferences();toast("Ширина столбцов сохранена локально.");return null;}
  }
  async function loadResultColumnWidths(){
    try{const result=await api("/columns/preferences/results");applyColumnPreferences(result.preferences);toast("Ширина столбцов загружена из SQLite.");}
    catch(error){state.columnWidths=normalizeColumnWidths(state.columnWidths);applyResultColumnWidths();toast("Используется локально сохранённая ширина.");}
  }
  function optimizeResultColumnWidths(){state.columnWidths=optimizedResultColumnWidths();applyResultColumnWidths();saveResultColumnWidths("Ширина оптимизирована и сохранена.");}
  function resetResultColumnWidths(){const custom=Object.fromEntries((state.customColumns||[]).map((column)=>[column,150]));state.columnWidths=normalizeColumnWidths({...defaultColumnWidths,...custom});applyResultColumnWidths();saveResultColumnWidths("Ширина сброшена к стандартной.");}
  async function renderColumnPreferences(){
    const root=$("#columnPreferenceList");
    if(!root)return;
    try{
      const data=await api("/columns/preferences/results/render",{method:"POST",body:JSON.stringify({preferences:columnPreferencesPayload(),labels})});
      root.innerHTML=data.listHtml||data.emptyListHtml||'<p class="muted">Колонки не настроены.</p>';
      if(data.preferences){
        state.columnOrder=data.preferences.order||state.columnOrder;
        state.visibleColumns=data.preferences.visible||state.visibleColumns;
        state.columnWidths=normalizeColumnWidths(data.preferences.widths||state.columnWidths);
      }
      applyResultColumnWidths();
    }catch(error){
      root.innerHTML='<p class="muted">Настройки колонок недоступны: '+esc(error.message)+'</p>';
    }
  }
  function applyColumnPreferences(preferences){
    if(!preferences)return;
    state.visibleColumns=preferences.visible||state.visibleColumns;
    state.columnOrder=preferences.order||state.columnOrder||state.visibleColumns;
    state.customColumns=(preferences.custom||[]).map((item)=>item.key);
    state.customColumnMappings=Object.fromEntries((preferences.custom||[]).map((item)=>[item.key,item.sourceIndex]));
    state.columnWidths=normalizeColumnWidths(preferences.widths||state.columnWidths);
    (preferences.custom||[]).forEach((item)=>{labels[item.key]=item.title||item.key;});
    save();
    renderColumnPreferences();
    renderResults();
  }
  function columnPreferencesPayload(overrides={}){
    const order=overrides.order||state.columnOrder||empty().columnOrder;
    const visible=overrides.visible||state.visibleColumns||empty().visibleColumns;
    const customSource=overrides.customKeys||state.customColumns||[];
    const custom=customSource.map((key)=>({
      key,
      title:(overrides.labels&&overrides.labels[key])||labels[key]||key,
      sourceIndex:(overrides.customColumnMappings||state.customColumnMappings||{})[key],
    }));
    const widths=normalizeColumnWidths(overrides.widths||state.columnWidths);
    return {order,visible,custom,widths};
  }
  const viewConfig={workspace:["Поиск устройств","Введите hostname, IP, IP коммутатора, MAC, физический адрес или серийный номер."],single:["Анализ одного файла","Загрузите файл и перейдите к основному анализу."],compare:["Сравнение снимков","Сопоставьте результаты двух загрузок."],analytics:["Аналитика","Сводка по текущему набору, критическим изменениям и истории."],history:["История","Снимки результатов и хронология изменений."],rooms:["Помещения","Smartroom ID — основной ключ помещения и оборудования."],roomhistory:["Хронология помещения","Полная цепочка замен оборудования по Smartroom ID."],data:["Данные","IP-маппинг, колонки результатов и SQLite-данные."],automation:["Автоматизация","Планировщик, уведомления и API-обогащение."],settings:["Настройки","Справочники и резервная копия приложения."],guide:["Руководство","Назначение программы и рабочие сценарии для пользователя и инженера."]};
  function normalizeViewName(name){if(name==="iphistory")return"analytics";return Object.prototype.hasOwnProperty.call(viewConfig,name)?name:"workspace";}
  function viewFromHash(){return normalizeViewName((location.hash||"").replace(/^#/,""));}
  function renderViewContent(name){if(name==="workspace"){renderFiles();renderMapping();renderMetrics();renderResults();return Promise.resolve();}if(name==="data"){renderServices();loadDatabaseHistoryManagement();}else if(name==="automation")renderServices();if(name==="settings")renderParityStatus();if(name==="analytics")renderAnalytics();if(name==="history")renderHistory();const smartroomTask=["analytics","rooms","roomhistory"].includes(name)?SmartroomUI?.render(name):null;if(name==="single")renderSingleMappingGrid();if(name==="compare")renderSnapshots();if(name==="guide"){Guide.syncMode(engineeringSessionActive(),state.engineeringExpiresAt,document);if(!$("#systemDiagnosticsSummary")?.dataset.loaded)runSystemDiagnostics();}return Promise.resolve(smartroomTask);}
  let viewRenderRevision=0;
  function scheduleViewContent(name){const revision=++viewRenderRevision,token=UiFeedback?.start("Открытие вкладки…");(window.requestAnimationFrame||((callback)=>setTimeout(callback,0)))(()=>{if(revision!==viewRenderRevision||activeViewName()!==name){UiFeedback?.stop(token);return;}renderViewContent(name).catch((error)=>{UiFeedback?.showError(error);toast(error.message);}).finally(()=>UiFeedback?.stop(token));});}
  function activateView(name,{updateHash=true,render=true}={}){name=normalizeViewName(name);if(!engineeringSessionActive()&&engineeringOnlyViews.has(name))name="history";LazyTabs?.activate(name);$$(".nav-item").forEach((b)=>{const active=b.dataset.view===name;b.classList.toggle("active",active);b.setAttribute("aria-selected",active?"true":"false");});$$(".view").forEach((panel)=>{const active=panel.id===name+"View";panel.classList.toggle("active",active);panel.hidden=!active;});const title=viewConfig[name];$("#viewTitle").textContent=title[0];$("#viewSubtitle").textContent=title[1];if(updateHash&&location.hash!=="#"+name)history.pushState(null,"","#"+name);if(render)scheduleViewContent(name);return name;}
  function view(name,options={}){return activateView(name,options);}
  let lastComparisonResult=null;
  function comparisonPayload(exportFormat=""){
    const fields=$$("#compareView input[type=checkbox]:checked").map((input)=>input.value);
    return {snapshots:finalDashboardSnapshots(),baselineId:$("#baselineSelect").value,currentId:$("#comparisonSelect").value,fields,exportFormat};
  }
  function renderComparisonResult(result){
    lastComparisonResult=result;
    $("#comparisonBody").innerHTML=result.changesRowsHtml||result.emptyRowsHtml||'<tr><td colspan="5" class="empty-state">Изменений не найдено.</td></tr>';
    $("#comparisonSummary").innerHTML=result.summaryHtml||'<h2>Результат сравнения</h2><span class="summary-number">0</span><p class="muted">Добавлено: 0 · Удалено: 0 · Изменено: 0</p>';
  }
  function localSnapshotById(id){for(const entry of (state.snapshots||[])){if(entry.id===id)return entry;}return null;}
  function localComparisonPayload(payload=comparisonPayload()){
    const snapshotRows=payload.__snapshotRows||finalDashboardSnapshots();
    const byId=(id)=>snapshotRows.find((entry)=>entry.id===id),baseline=byId(payload.baselineId)||snapshotRows.at(-2)||snapshotRows[0],current=byId(payload.currentId)||snapshotRows.at(-1),fields=payload.fields&&payload.fields.length?payload.fields:["vendor","model","ip","address","room","smartroomId","switchIp","switchPort","hostname","serialNumber","deviceId","deviceName"];
    if(!baseline||!current||baseline.id===current.id)return{changes:[],changesRowsHtml:'<tr><td colspan="5" class="empty-state">Нужно минимум два разных снимка для локального сравнения.</td></tr>',emptyRowsHtml:'<tr><td colspan="5" class="empty-state">Нужно минимум два разных снимка для локального сравнения.</td></tr>',summaryHtml:'<h2>Результат сравнения</h2><span class="summary-number">0</span><p class="muted">Добавлено: 0 · Удалено: 0 · Изменено: 0</p>'};
    const paired=DeviceIdentity.pairSets(baseline.devices||[],current.devices||[]),changes=[];
    for(const device of paired.added){const mac=normalize(device.mac||device.macFormatted);changes.push({mac,type:"Добавлено",field:"-",before:"",after:device.macFormatted||formatMac(mac),beforeDevice:null,afterDevice:compactDashboardDevice(device)});}
    for(const device of paired.removed){const mac=normalize(device.mac||device.macFormatted);changes.push({mac,type:"Удалено",field:"-",before:device.macFormatted||formatMac(mac),after:"",beforeDevice:compactDashboardDevice(device),afterDevice:null});}
    for(const [previous,device] of paired.pairs){const mac=normalize(device.mac||device.macFormatted)||normalize(previous.mac||previous.macFormatted);for(const field of fields){const oldValue=String(previous[field]??""),newValue=String(device[field]??"");if(oldValue===newValue||oldValue&&!newValue)continue;changes.push({mac,type:"Изменено",field:labels[field]||field,before:oldValue,after:newValue,beforeDevice:compactDashboardDevice(previous),afterDevice:compactDashboardDevice(device)});}if(device.hasConflict||(device.conflicts||[]).length)changes.push({mac,type:"Изменено",field:"Конфликт идентификации",before:"",after:"Обнаружены противоречащие источники",beforeDevice:compactDashboardDevice(previous),afterDevice:compactDashboardDevice(device)});}
    const added=changes.filter((item)=>item.type==="Добавлено").length,removed=changes.filter((item)=>item.type==="Удалено").length,modified=changes.filter((item)=>item.type==="Изменено").length;
    const rows=changes.map((item)=>`<tr><td>${esc(formatMac(item.mac)||item.mac)}</td><td>${esc(item.type)}</td><td>${esc(item.field)}</td><td>${esc(item.before)}</td><td>${esc(item.after)}</td></tr>`).join("");
    return{changes,changesRowsHtml:rows||'<tr><td colspan="5" class="empty-state">Изменений не найдено.</td></tr>',emptyRowsHtml:'<tr><td colspan="5" class="empty-state">Изменений не найдено.</td></tr>',summaryHtml:`<h2>Результат сравнения</h2><span class="summary-number">${changes.length}</span><p class="muted">Добавлено: ${added} · Удалено: ${removed} · Изменено: ${modified}</p>`,baseline,current};
  }
  async function storedLocalComparisonPayload(payload=comparisonPayload()){
    const finalSnapshots=finalDashboardSnapshots(),candidates=[localSnapshotById(payload.baselineId)||finalSnapshots.at(-2)||finalSnapshots[0],localSnapshotById(payload.currentId)||finalSnapshots.at(-1)].filter(Boolean);
    const hydrated=await Promise.all(candidates.map(loadLocalSnapshotRecord));
    return localComparisonPayload({...payload,__snapshotRows:hydrated});
  }
  function localComparisonExport(result,format){
    const rows=[["MAC","Тип изменения","Поле","Было","Стало"],...(result.changes||[]).map((item)=>[formatMac(item.mac)||item.mac,item.type,item.field,item.before,item.after])];
    if(format==="csv")return{filename:"mac-comparison.csv",mimeType:"text/csv",content:"\uFEFF"+rows.map((row)=>localCsvLine(row)).join("\n")};
    if(format==="txt")return{filename:"mac-comparison.txt",mimeType:"text/plain",content:rows.map((row)=>row.join("\t")).join("\n")};
    return{filename:"mac-comparison.xls",mimeType:"application/vnd.ms-excel",content:localSpreadsheetXml({columns:rows[0].map((title)=>({title})),rows:rows.slice(1)})};
  }
  async function compare(){
    const payload=comparisonPayload();
    const processId=beginProcess("Сравнение снимков","Подготовка выбранных выгрузок",10);
    try{
      updateProcess(processId,35,"Сопоставление устройств и полей");
      renderComparisonResult(await api("/compare/snapshots",{method:"POST",body:JSON.stringify(payload)}));
      toast("Сравнение выполнено backend-сервисом.");
      finishProcess(processId,"Сравнение снимков завершено");
    }catch(error){
      updateProcess(processId,65,"Локальное сравнение снимков");
      renderComparisonResult(await storedLocalComparisonPayload(payload));
      toast("Сравнение выполнено локально.");
      finishProcess(processId,"Сравнение выполнено в браузере","warning");
    }
  }
  async function exportComparison(format){
    const payload=comparisonPayload(format);
    const processId=beginProcess("Экспорт сравнения","Расчёт различий",10);
    try{
      updateProcess(processId,35,"Формирование сравнения backend-сервисом");
      const result=await api("/compare/snapshots",{method:"POST",body:JSON.stringify(payload)});
      renderComparisonResult(result);
      const exported=result.export;
      if(!exported)throw new Error("Экспорт сравнения не сформирован.");
      updateProcess(processId,85,"Сохранение файла сравнения");
      download(exported.filename||("mac-comparison."+format),format==="csv"?"\uFEFF"+exported.content:exported.content,exported.mimeType||"text/plain");
      toast("Экспорт сравнения готов.");
      finishProcess(processId,"Экспорт сравнения готов");
    }catch(error){
      updateProcess(processId,60,"Локальное формирование файла сравнения");
      const exported=localComparisonExport(await storedLocalComparisonPayload(payload),format);
      download(exported.filename,exported.content,exported.mimeType);
      toast("Экспорт сравнения выполнен локально.");
      finishProcess(processId,"Экспорт сравнения готов в автономном режиме","warning");
    }
  }
  async function multiCompare(event){
    if(event){
      event.preventDefault();
      event.stopImmediatePropagation();
    }
    const baselineId=$("#baselineSelect").value;
    const comparisonIds=Array.from($("#multiComparisonSelect").selectedOptions).map((option)=>option.value).filter((id)=>id!==baselineId).slice(0,10);
    const fields=$$("#compareView input[type=checkbox]:checked").map((input)=>input.value);
    const processId=beginProcess("Массовое сравнение","Подготовка "+comparisonIds.length+" снимков",10);
    try{
      updateProcess(processId,35,"Сопоставление выбранных снимков");
      const result=await api("/compare/snapshots/many",{method:"POST",body:JSON.stringify({snapshots:state.snapshots,baselineId,comparisonIds,fields})});
      renderComparisonResult(result);
      toast("Массовое сравнение выполнено backend-сервисом.");
      finishProcess(processId,"Массовое сравнение завершено");
    }catch(error){
      const allChanges=[];
      for(const [targetIndex,targetId] of comparisonIds.entries()){
        updateProcess(processId,45+Math.round((targetIndex/Math.max(1,comparisonIds.length))*45),"Локальное сравнение "+(targetIndex+1)+" / "+comparisonIds.length);
        const result=await storedLocalComparisonPayload({baselineId,currentId:targetId,fields});
        for(const change of result.changes||[])allChanges.push({...change,target:result.current?.name||targetId});
      }
      const rows=allChanges.map((item)=>`<tr><td>${esc(formatMac(item.mac)||item.mac)}</td><td>${esc(item.type)}</td><td>${esc(item.field)}</td><td>${esc(item.before)}</td><td>${esc(item.after)}</td></tr>`).join("");
      renderComparisonResult({changes:allChanges,changesRowsHtml:rows||'<tr><td colspan="5" class="empty-state">Изменений не найдено.</td></tr>',summaryHtml:`<h2>Массовое сравнение</h2><span class="summary-number">${allChanges.length}</span><p class="muted">Локально сравнено наборов: ${comparisonIds.length}</p>`});
      toast("Массовое сравнение выполнено локально.");
      finishProcess(processId,"Локально сравнено снимков: "+comparisonIds.length,"warning");
    }
  }
  function activeViewName(){return $(".view.active")?.id?.replace(/View$/,"")||viewFromHash();}
  function renderAll(){
    const name=activeViewName();
    if(name==="workspace"){renderFiles();renderMapping();renderMetrics();renderResults();return;}
    if(name==="compare"){renderSnapshots();return;}
    if(name==="analytics"){renderAnalytics();return;}
    if(name==="history"){renderHistory();return;}
    if(name==="settings"){renderMappings();loadOuiReferenceStatus();return;}
    renderViewContent(name);
  }
  $$(".nav-item").forEach((b)=>b.setAttribute("aria-controls",b.dataset.view+"View"));
  document.addEventListener("click",(event)=>{const button=event.target.closest?.(".nav-item[data-view]");if(button)view(button.dataset.view);});
  window.addEventListener("hashchange",()=>view(viewFromHash(),{updateHash:true}));
  $("#browseFilesButton")?.addEventListener("click",()=>$("#fileInput")?.click());$("#browseEnrichmentFilesButton")?.addEventListener("click",()=>$("#enrichFileInput")?.click());$("#browseDdioFileButton")?.addEventListener("click",()=>$("#ddioFileInput")?.click());$("#clearDdioFileButton")?.addEventListener("click",clearDdioFile);$("#singleBrowseFileButton")?.addEventListener("click",()=>$("#singleFileInput")?.click());$("#dropZone")?.addEventListener("keydown",(e)=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();$("#fileInput")?.click();}});$("#fileInput").addEventListener("change",(e)=>loadFiles(e.target.files,e.target,"primary"));$("#enrichFileInput")?.addEventListener("change",(e)=>loadFiles(e.target.files,e.target,"smartroom"));$("#ddioFileInput")?.addEventListener("change",(e)=>loadDdioFile(e.target.files,e.target));$("#singleFileInput").addEventListener("change",(e)=>{pendingSingleFile=e.target.files[0]||null;inspectSingleFile();});$("#singleSheetInput").addEventListener("change",inspectSingleFile);$("#singleManualMappingToggle").addEventListener("change",renderSingleMappingGrid);$("#singleFileAnalyzeButton").addEventListener("click",analyzeSingleFile);$("#dropZone").addEventListener("dragover",(e)=>{e.preventDefault();$("#dropZone").classList.add("dragover");});$("#dropZone").addEventListener("dragleave",()=>$("#dropZone").classList.remove("dragover"));$("#dropZone").addEventListener("drop",(e)=>{e.preventDefault();$("#dropZone").classList.remove("dragover");loadFiles(e.dataTransfer.files,null,"auto");});
  $("#ddioMappingGrid")?.addEventListener("change",(event)=>{const select=event.target.closest("[data-ddio-map]");if(!select||!state.ddioFile)return;const mapping={...(state.ddioFile.mapping||{})};if((select.dataset.ddioMap==="reservationIp"||select.dataset.ddioMap==="leaseIp")&&mapping.ip!==""&&mapping.ip!==undefined){mapping.reservationIp=mapping.reservationIp??mapping.ip;mapping.leaseIp=mapping.leaseIp??mapping.ip;delete mapping.ip;}mapping[select.dataset.ddioMap]=select.value===""?"":Number(select.value);state.ddioFile.mapping=mapping;state.ddioOverlay={};state.ddioSummary=null;save({immediate:true});renderDdioPanel();renderResults();});
  $("#reconnectBackendButton")?.addEventListener("click",async()=>{try{await checkBackendConnection();await syncFromBackend();toast("Backend и SQLite подключены.");}catch{toast("Backend не отвечает на http://127.0.0.1:8080");}});
  $("#fileList").addEventListener("click",(e)=>{const id=e.target.dataset.removeFile,row=e.target.closest("[data-file-id]");if(id){state.files=state.files.filter((f)=>f.id!==id);state.ddioOverlay={};state.ddioSummary=null;sourceFilesById.delete(id);pruneStoredSourceFiles();ensureMappingSelection();save();renderAll();return;}if(row){state.activeMappingFileId=row.dataset.fileId;save();renderFiles();renderMapping();}});
  $("#cancelAnalyzeButton").addEventListener("click",cancelActiveEnrichment);
  bindSelectableMacTable($("#resultsBody"));bindSelectableMacTable($("#sqliteHistoryBody"));bindSelectableMacTable($("#vendorModelHistoryBody"));bindSelectableMacTable($("#localMovementBody"));
  $("#resultsBody").addEventListener("dblclick",(e)=>{const row=e.target.closest("tr[data-mac]");if(row)showDevice(row.dataset.mac);});
  $("#sqliteHistoryBody").addEventListener("dblclick",(e)=>{const row=e.target.closest("tr[data-mac]");if(row)showDevice(row.dataset.mac);});
  $("#vendorModelHistoryBody").addEventListener("dblclick",(e)=>{const row=e.target.closest("tr[data-mac]");if(row)showDevice(row.dataset.mac);});
  $("#localMovementBody").addEventListener("dblclick",(e)=>{const row=e.target.closest("tr[data-mac]");if(row)showDevice(row.dataset.mac);});
  $("#copyResultsTableButton").addEventListener("click",()=>copyTable($("#resultsTable"),"таблица результатов"));
  $("#copyResultsMacButton").addEventListener("click",()=>copySelectedTableMac($("#resultsTable")));
  $("#copyHistoryTableButton").addEventListener("click",()=>copyTable($("#sqliteHistoryTable"),"история MAC"));
  $("#copyHistoryMacButton").addEventListener("click",()=>copySelectedTableMac($("#sqliteHistoryTable")));
  $("#tableContextMenu").addEventListener("click",(event)=>{const action=event.target.dataset.contextAction,row=contextTableRow;if(!action||!row)return;if(action==="copy-mac")copyTextToClipboard(rowMac(row)?formatMac(rowMac(row)):"","MAC-адрес");if(action==="copy-row")copyTextToClipboard(tableRowsToTsv([Array.from(row.cells).map((cell)=>cell.textContent)]),"строка");if(action==="show-history"&&rowMac(row))showDevice(rowMac(row));hideTableContextMenu();});
  document.addEventListener("click",(event)=>{if(!event.target.closest("#tableContextMenu"))hideTableContextMenu();});
  window.addEventListener("blur",hideTableContextMenu);window.addEventListener("resize",hideTableContextMenu);window.addEventListener("scroll",hideTableContextMenu,true);
  $("#closeDeviceDialog").addEventListener("click",()=>$("#deviceDialog").close());
  $("#exportDeviceAnalyticsButton").addEventListener("click",exportDeviceAnalytics);
  $("#deleteDeviceHistoryButton").addEventListener("click",async()=>{const mac=$("#deviceDialog").dataset.mac;if(!mac||!confirm("Удалить всю историю этого MAC из SQLite и локальных снимков?"))return;try{await api("/history?mac="+encodeURIComponent(mac),{method:"DELETE"});await showDevice(mac);renderHistory();toast("История MAC удалена.");}catch(error){const normalized=normalize(mac);state.snapshots=(state.snapshots||[]).map((snapshot)=>({...snapshot,devices:(snapshot.devices||[]).filter((device)=>normalize(device.mac||device.macFormatted)!==normalized)}));state.movementHistory=(state.movementHistory||[]).filter((item)=>normalize(item.mac)!==normalized);save();showLocalDevice(mac);renderHistory();toast("Локальная история MAC удалена.");}});
  $("#closeModelDialog").addEventListener("click",()=>$("#modelDialog").close());
  $("#helpButton").addEventListener("click",()=>$("#helpDialog").showModal());
  $("#closeHelpDialog").addEventListener("click",()=>$("#helpDialog").close());
  $("#portableDatabaseButton")?.addEventListener("click",()=>$("#portableDatabaseDialog")?.showModal());
  $("#closePortableDatabaseDialog")?.addEventListener("click",()=>$("#portableDatabaseDialog")?.close());
  $("#chooseLocalFolderButton")?.addEventListener("click",connectLocalFolder);
  $("#importPortableFolderButton")?.addEventListener("click",()=>$("#portableFolderInput")?.click());
  $("#openPortableDatabaseButton")?.addEventListener("click",connectPortableDatabase);
  $("#createPortableDatabaseButton")?.addEventListener("click",createPortableDatabase);
  $("#savePortableDatabaseButton")?.addEventListener("click",savePortableDatabaseNow);
  $("#portableDatabaseInput")?.addEventListener("change",async(event)=>{
    const file=event.target.files?.[0];event.target.value="";if(!file)return;
    try{await importPortableDatabaseFile(file,file.name);}
    catch(error){toast(error.message);}
  });
  $("#portableFolderInput")?.addEventListener("change",async(event)=>{
    const files=Array.from(event.target.files||[]);event.target.value="";if(!files.length)return;
    try{await importPortableFolderFiles(files);toast("Данные из папки восстановлены в этом браузере.");}
    catch(error){localFolderStatus(error.message,"error");toast(error.message);}
  });
  $("#openGuideFromHelpButton")?.addEventListener("click",()=>{$("#helpDialog").close();view("guide");});
  $("#guideView")?.addEventListener("click",(event)=>{
    const tab=event.target.closest("[data-guide-tab]");
    if(tab){Guide.activateTab(tab.dataset.guideTab,document);return;}
    const destination=event.target.closest("[data-guide-view]")?.dataset.guideView;
    if(destination)view(destination);
  });
  $("#guideView")?.addEventListener("keydown",(event)=>{
    const tab=event.target.closest("[data-guide-tab]");
    if(!tab||!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
    event.preventDefault();
    const tabs=$$("[data-guide-tab]"),index=tabs.indexOf(tab);
    const next=event.key==="Home"?0:event.key==="End"?tabs.length-1:(index+(event.key==="ArrowRight"?1:-1)+tabs.length)%tabs.length;
    Guide.activateTab(tabs[next].dataset.guideTab,document);tabs[next].focus();
  });
  $("#guideEngineeringLoginButton")?.addEventListener("click",()=>engineeringSessionActive()?view("workspace"):openEngineeringDialog());
  $("#runSystemDiagnosticsButton")?.addEventListener("click",runSystemDiagnostics);
  $("#mappingFileSelect").addEventListener("change",(e)=>{state.activeMappingFileId=e.target.value;save();renderMapping();});
  $("#mappingDisplayMode").addEventListener("change",(e)=>{state.mappingDisplayMode=e.target.value==="letter"?"letter":"name";save();renderMapping();});
  $("#copyMappingToAllButton").addEventListener("click",()=>{const file=selectedMappingFile();if(!file)return toast("Сначала выберите файл для сопоставления.");state.files.forEach((item)=>{item.mapping={...file.mapping};localMappingSummary(item);});state.ddioOverlay={};state.ddioSummary=null;save();renderMapping();renderResults();toast("Сопоставление скопировано во все файлы.");});
  $("#mappingGrid").addEventListener("change",(e)=>{const f=e.target.dataset.map,file=selectedMappingFile();if(f&&file){file.mapping[f]=e.target.value===""?"":Number(e.target.value);state.ddioOverlay={};state.ddioSummary=null;refreshMappingSummary(file).catch(()=>localMappingSummary(file));save();renderResults();}});
  $("#autoMapColumnsButton").addEventListener("click",async()=>{const file=selectedMappingFile();if(!file)return toast("Сначала добавьте основной файл.");try{file.mapping=await detectColumnsWithBackend(file,{mode:"auto",ai:false});await refreshMappingSummary(file);toast("Колонки определены backend-детектором.");}catch(error){file.mapping=localAutoMapping(file.headers.map(h=>h.name));localMappingSummary(file);toast(networkUnavailable(error)?"Колонки определены в браузере.":"Backend column detector error: "+error.message);}state.ddioOverlay={};state.ddioSummary=null;save();renderMapping();renderResults();});
  $("#sampleMapColumnsButton").addEventListener("click",async()=>{const file=selectedMappingFile();if(!file)return toast("Сначала добавьте основной файл.");try{const reviewed=await detectColumnsWithBackend(file);if(!reviewed){renderColumnDetectionSummary(file);toast("Выбор колонок отменён.");return;}file.mapping=reviewed;await refreshMappingSummary(file);toast("Проверенное сопоставление AI применено.");}catch(error){file.mapping=localAutoMapping(file.headers.map(h=>h.name));localMappingSummary(file);toast(networkUnavailable(error)?"Колонки определены в браузере.":"Backend column detector error: "+error.message);}state.ddioOverlay={};state.ddioSummary=null;save();renderMapping();renderResults();});
  $("#autoSelectConflictColumnsButton").addEventListener("click",autoSelectConflictColumns);
  $("#clearConflictColumnsButton").addEventListener("click",()=>{$$('[data-conflict-column]').forEach((select)=>{select.value="";});$("#columnConflictStatus").textContent="Выбор очищен. MAC-адрес необходимо указать вручную.";});
  $("#applyConflictColumnsButton").addEventListener("click",applyColumnConflictSelection);
  $("#cancelConflictColumnsButton").addEventListener("click",()=>resolveColumnConflict(null));
  $("#closeColumnConflictDialog").addEventListener("click",()=>resolveColumnConflict(null));
  $("#columnConflictDialog").addEventListener("cancel",(event)=>{event.preventDefault();resolveColumnConflict(null);});
  $("#strategySelect").addEventListener("change",(event)=>{syncEnrichmentStrategyUi(event.target.value);save({immediate:true});});
  $("#analyzeButton").addEventListener("click",analyze);const renderSearchResults=debounce(()=>{resultPage=1;renderResults();},180);$("#searchInput").addEventListener("input",renderSearchResults);["#vendorFilter","#validityFilter"].forEach((s)=>$(s).addEventListener("change",()=>{resultPage=1;renderResults();}));$("#resultsTable").addEventListener("table-sort-change",(event)=>{const field=String(event.detail?.field||"");if(!field)return;resultSortField=field;resultSortDirection=event.detail?.direction==="desc"?"desc":"asc";resultPage=1;renderResults();});$("#exportExcelButton").addEventListener("click",()=>exportData("spreadsheetml"));$("#exportCsvButton").addEventListener("click",()=>exportData("csv"));$("#exportTxtButton").addEventListener("click",()=>exportData("txt"));$("#exportYamlButton").addEventListener("click",()=>exportData("yaml"));$("#exportJsonButton").addEventListener("click",()=>exportData("json"));$("#exportHtmlButton").addEventListener("click",()=>exportData("html"));$("#compareButton").addEventListener("click",compare);
  $("#resultPreviousPageButton").addEventListener("click",()=>{if(resultPage>1){resultPage--;renderResults();}});
  $("#resultNextPageButton").addEventListener("click",()=>{resultPage++;renderResults();});
  $("#resultPageSizeSelect").addEventListener("change",(event)=>{resultPageSize=Math.max(25,Math.min(Number(event.target.value)||50,1000));resultPage=1;renderResults();});
  $("#exportComparisonExcelButton").addEventListener("click",()=>exportComparison("excel"));
  $("#exportComparisonCsvButton").addEventListener("click",()=>exportComparison("csv"));
  $("#exportComparisonTxtButton").addEventListener("click",()=>exportComparison("txt"));
  $("#multiCompareButton").addEventListener("click",multiCompare,true);
  $("#clearResultFiltersButton").addEventListener("click",()=>{$("#searchInput").value="";$("#vendorFilter").value="";$("#validityFilter").value="";resultPage=1;renderResults();});
  $("#exportXlsxButton").addEventListener("click",async()=>{try{await exportManagedBinary("xlsx");}catch(error){toast(error.message);}});
  $("#exportFullXlsxButton").addEventListener("click",async()=>{try{await exportFullWorkbook();}catch(error){UiFeedback?.showError(error);toast(error.message||"Не удалось сформировать полный XLSX.");}});
  $("#exportAllDevicesButton").addEventListener("click",async()=>{try{await exportAllDevices();}catch(error){UiFeedback?.showError(error);toast(error.message||"Не удалось выгрузить все устройства.");}});
  $("#exportFullJsonButton").addEventListener("click",async()=>{try{await exportFullJson();}catch(error){UiFeedback?.showError(error);toast(error.message||"Не удалось сформировать полный JSON.");}});
  $("#exportPdfButton").addEventListener("click",async()=>{try{await exportManagedBinary("pdf");}catch(error){toast(error.message);}});
  $("#globalSearchForm").addEventListener("submit",(event)=>{event.preventDefault();runGlobalSearch();});
  $("#exportMenu").addEventListener("click",(event)=>{const action=event.target.closest("[data-export-action]")?.dataset.exportAction;if(!action)return;event.preventDefault();const target=document.getElementById(action);if(target)target.click();$("#exportMenu").removeAttribute("open");});
  $("#comparisonFilters").addEventListener("click",(e)=>{const filter=e.target.dataset.comparisonFilter;if(!filter)return;$$("[data-comparison-filter]").forEach((button)=>button.classList.toggle("active-filter",button.dataset.comparisonFilter===filter));const types={added:"Добавлено",removed:"Удалено",modified:"Изменено"};$$("#comparisonBody tr").forEach((row)=>{const type=row.children[1]?.textContent;row.hidden=filter!=="all"&&type!==types[filter];});});
  $("#historyBody").addEventListener("click",async(e)=>{
    const id=e.target.dataset.loadSnapshot||e.target.dataset.localSnapshot;if(!id)return;
    try{
      let opened;
      if(e.target.dataset.localSnapshot){
        const localSnapshot=(state.snapshots||[]).find((entry)=>entry.id===id);if(!localSnapshot)throw new Error("Локальный снимок не найден.");
        clearResultReference();
        if(localSnapshot.browserStored&&BrowserSnapshots?.page){
          const localPage=await BrowserSnapshots.page(id,{offset:0,limit:resultPageSize});
          opened={resultPage:localPage,devices:localPage?.items||[],invalid:[],lastAnalysis:localSnapshot.createdAt||new Date().toISOString()};
          state.resultBrowserSnapshotId=id;state.resultBrowserSnapshotDirty=false;state.resultDeviceCount=Number(localPage?.metadata?.deviceCount||localPage?.summary?.devices||0);state.resultInvalidCount=Number(localPage?.metadata?.invalidCount||localPage?.summary?.invalid||0);state.resultSummary=localPage?.summary||null;
        }else{
          const stored=await loadLocalSnapshotRecord(localSnapshot);opened={devices:stored?.devices||[],invalid:stored?.invalid||[],lastAnalysis:stored?.createdAt||localSnapshot.createdAt||new Date().toISOString()};
        }
      }else{
        clearResultReference();opened=await api("/snapshots/open",{method:"POST",body:JSON.stringify({id,snapshots:state.snapshots,compactResult:true,resultPageSize})});const reference=opened.resultReference||{};state.resultSnapshotId=String(reference.snapshotId||id);state.resultDeviceCount=Number(reference.deviceCount||0);state.resultInvalidCount=Number(reference.invalidCount||0);state.resultSummary=opened.resultSummary||opened.resultPage?.summary||null;
      }
      const openedItems=opened.resultPage?.items||opened.devices||[];state.devices=openedItems.filter((item)=>item?.valid!==false&&!item?.invalid);state.invalid=(opened.invalid||[]).concat(openedItems.filter((item)=>item?.valid===false||item?.invalid));state.lastAnalysis=opened.lastAnalysis||new Date().toISOString();resultPage=1;save();renderAll();view("workspace");toast("Снимок открыт.");
    }catch(error){toast(error.message);}
  });
  $("#historyBody").addEventListener("change",(event)=>{if(!event.target.matches("[data-snapshot-select]"))return;const boxes=$$("[data-snapshot-select]"),checked=boxes.filter((input)=>input.checked).length,all=$("#selectAllSnapshots");all.checked=boxes.length>0&&checked===boxes.length;all.indeterminate=checked>0&&checked<boxes.length;});
  $("#selectAllSnapshots").addEventListener("change",(event)=>{$$("[data-snapshot-select]").forEach((input)=>{input.checked=event.target.checked;});});
  $("#deleteSelectedSnapshotsButton").addEventListener("click",()=>deleteSelectedSnapshots().catch((error)=>toast(error.message)));
  $("#historySearchInput").addEventListener("input",debounce(renderHistory,250));
  $("#historyDateFrom").addEventListener("change",renderHistory);$("#historyDateTo").addEventListener("change",renderHistory);
  $("#clearHistoryFiltersButton").addEventListener("click",()=>{$("#historySearchInput").value="";$("#historyDateFrom").value="";$("#historyDateTo").value="";renderHistory();});
  $("#exportHistoryButton").addEventListener("click",async()=>{try{await exportHistory();}catch(error){toast(error.message);}});
  $("#applyMovementFiltersButton").addEventListener("click",renderMovementHistory);
  $("#movementSearchInput").addEventListener("keydown",(event)=>{if(event.key==="Enter")renderMovementHistory();});
  $("#movementSearchInput").addEventListener("input",debounce(renderMovementHistory,180));
  $$("#movementDateFrom,#movementDateTo").forEach((input)=>input.addEventListener("change",renderMovementHistory));
  $("#movementTypeFilter").addEventListener("change",renderMovementHistory);$("#movementFieldFilter").addEventListener("change",renderMovementHistory);
  $("#clearMovementFiltersButton").addEventListener("click",()=>{$$("#movementDateFrom,#movementDateTo,#movementSearchInput").forEach((input)=>{input.value="";});$("#movementTypeFilter").value="";$("#movementFieldFilter").value="";renderMovementHistory();});
  $("#exportMovementHistoryButton").addEventListener("click",()=>exportMovementHistory().catch((error)=>toast(error.message)));
  $("#deleteShownMovementsButton").addEventListener("click",deleteShownMovementHistory);
  $("#expandMovementGroupsButton").addEventListener("click",()=>setMovementGroupsExpanded(true));$("#collapseMovementGroupsButton").addEventListener("click",()=>setMovementGroupsExpanded(false));
  $("#localMovementBody").addEventListener("click",(event)=>{const button=event.target.closest("[data-toggle-movement-group]");if(!button)return;const mac=button.dataset.toggleMovementGroup,expanded=button.getAttribute("aria-expanded")!=="false";$$(`[data-movement-child="${mac}"]`).forEach((row)=>{row.hidden=expanded;});button.setAttribute("aria-expanded",expanded?"false":"true");button.textContent=expanded?"▸":"▾";button.title=expanded?"Развернуть группу":"Свернуть группу";});
  $("#movementColumnControls").addEventListener("change",(event)=>{if(event.target.matches("[data-movement-column-toggle],[data-movement-column-width]")){movementColumnSettings=readMovementColumnSettings();applyMovementColumnSettings();}});
  $("#optimizeMovementColumnsButton").addEventListener("click",optimizeMovementColumns);
  $("#resetMovementColumnsButton").addEventListener("click",()=>{movementColumnSettings={...movementColumnSettings,visible:["mac","count","dates","vendor","model","room","field","before","after","source"],widths:{mac:180,count:100,dates:170,vendor:160,model:160,room:120,field:120,before:240,after:240,source:160}};applyMovementColumnSettings();});
  $("#saveMovementColumnsButton").addEventListener("click",()=>saveMovementColumnSettings());
  $("#loadMovementColumnsButton").addEventListener("click",async()=>{try{const result=await api("/history/movements/columns");movementColumnSettings=result.settings;$("#movementColumnControls").innerHTML=movementColumnSettings.controlsHtml||"";applyMovementColumnSettings();toast("Колонки расширенной истории загружены.");}catch(error){toast(error.message);}});
  $("#enhancedMovementHeader").addEventListener("pointerdown",startMovementColumnResize);
  $("#clearHistoryButton").addEventListener("click",async()=>{if(!confirm("Очистить всю историю снимков из SQLite и локальные снимки браузера?"))return;let deleted=0;try{const result=await api("/database/snapshots/delete",{method:"POST",body:JSON.stringify({})});deleted=Number(result.deleted||0);}catch(error){if(!networkUnavailable(error))return toast(error.message);}await BrowserSnapshots?.prune?.([]).catch(()=>0);state.snapshots=[];state.movementHistory=[];state.devices=[];state.invalid=[];clearResultReference();save({immediate:true});await flushBrowserStateSave().catch(()=>{});renderAll();renderServices();toast(deleted?`Удалено снимков SQLite: ${deleted}. Локальная история очищена.`:"Локальная история снимков очищена.");});
  $("#learnVendorModelButton").addEventListener("click",async()=>{const settings=vendorModelLearnSettings();try{const result=await api("/vendor-model-history/learn",{method:"POST",body:JSON.stringify(settings)});await syncFromBackend();await renderMappings();applyLocalVendorModelMappings(state.devices);await applyBackendDetectionToCurrentResult();save();renderResults();renderAnalytics();renderHistory();toast("Изучено производителей: "+result.learned.vendors+", моделей: "+result.learned.models+". Правила применены к текущему результату.");}catch(error){const result=learnLocalVendorModelMappings(settings);applyLocalVendorModelMappings(state.devices);save();renderResults();renderAnalytics();renderHistory();toast("Локально изучено производителей: "+result.vendors+", моделей: "+result.models);}});
  $("#addVendorButton").addEventListener("click",async()=>{const oui=$("#vendorOuiInput").value.toUpperCase().replace(/[^0-9A-F]/g,""),name=$("#vendorNameInput").value.trim();if(oui.length<6||oui.length>10||!name){toast("Укажите OUI/MAC5 от 6 до 10 символов и производителя.");return;}try{await api("/mappings/vendors",{method:"POST",body:JSON.stringify({key:oui,value:name})});state.localVendorMappings[oui]=name;$("#vendorOuiInput").value="";$("#vendorNameInput").value="";await renderMappings();applyLocalVendorModelMappings(state.devices);await applyBackendDetectionToCurrentResult();save();renderResults();renderAnalytics();renderHistory();toast("Правило производителя сохранено и применено к текущему результату.");}catch(error){state.localVendorMappings[oui]=name;$("#vendorOuiInput").value="";$("#vendorNameInput").value="";applyLocalVendorModelMappings(state.devices);save();renderMappings();renderResults();renderAnalytics();renderHistory();toast("Правило производителя сохранено локально.");}});
  $("#addModelButton").addEventListener("click",async()=>{const p=$("#modelPrefixInput").value.toUpperCase().replace(/[^0-9A-F]/g,""),name=$("#modelNameInput").value.trim();if(p.length<6||p.length>10||!name){toast("Укажите префикс MAC от 6 до 10 символов и модель.");return;}try{await api("/mappings/models",{method:"POST",body:JSON.stringify({key:p,value:name})});state.localModelMappings[p]=name;$("#modelPrefixInput").value="";$("#modelNameInput").value="";await renderMappings();applyLocalVendorModelMappings(state.devices);await applyBackendDetectionToCurrentResult();save();renderResults();renderAnalytics();renderHistory();toast("Правило модели сохранено и применено к текущему результату.");}catch(error){state.localModelMappings[p]=name;$("#modelPrefixInput").value="";$("#modelNameInput").value="";applyLocalVendorModelMappings(state.devices);save();renderMappings();renderResults();renderAnalytics();renderHistory();toast("Правило модели сохранено локально.");}});
  $("#exportModelPrefixesButton").addEventListener("click",exportModelPrefixes);
  $("#settingsView").addEventListener("click",(e)=>{const model=e.target.dataset.modelPrefixes;if(model){e.preventDefault();e.stopImmediatePropagation();showModelAnalytics(model);}},true);
  $("#settingsView").addEventListener("click",async(e)=>{const v=e.target.dataset.removeVendor,m=e.target.dataset.removeModel,lv=e.target.dataset.localRemoveVendor,lm=e.target.dataset.localRemoveModel,model=e.target.dataset.modelPrefixes;if(model)return;if(lv||lm){if(lv)delete state.localVendorMappings[lv];if(lm)delete state.localModelMappings[lm];save();renderMappings();renderResults();toast("Локальное правило удалено.");return;}if(v||m){try{await api("/mappings/"+(v?"vendors/":"models/")+encodeURIComponent(v||m),{method:"DELETE"});await syncFromBackend();await renderMappings();toast("Правило удалено из SQLite.");}catch(error){toast(error.message);}}});
  $("#themeButton").addEventListener("click",showThemeSelection);
  $("#closeThemeDialog").addEventListener("click",()=>$("#themeDialog").close());
  $("#themeDialogCloseButton").addEventListener("click",()=>$("#themeDialog").close());
  $("#themeDialog").addEventListener("click",(e)=>{const theme=e.target.closest("[data-theme-dialog-choice]")?.dataset.themeDialogChoice;if(theme){saveThemePreference(theme);$("#themeDialog").close();}});
  $("#vendorDetectorThreshold")?.addEventListener("input",()=>{if($("#vendorDetectorThresholdLabel"))$("#vendorDetectorThresholdLabel").textContent=($("#vendorDetectorThreshold")?.value||60)+"%";});
  $("#saveVendorDetectorSettingsButton")?.addEventListener("click",saveVendorDetectorSettings);
  $("#importOuiReferenceButton")?.addEventListener("click",importOuiReference);
  $("#ouiReferenceFileInput")?.addEventListener("change",()=>{const file=$("#ouiReferenceFileInput")?.files?.[0];if(file&&$("#ouiReferenceStatus"))$("#ouiReferenceStatus").textContent=`Выбран: ${file.name} · ${(file.size/1024/1024).toFixed(2)} МБ`;});
  $("#saveHistoryEnrichmentSettingsButton")?.addEventListener("click",saveHistoryEnrichmentSettings);
  ["#engineeringLoginButton","#appModeButton","#brandModeButton","#modeContextAction"].forEach((selector)=>$(selector)?.addEventListener("click",(event)=>{event.preventDefault();engineeringSessionActive()?logoutEngineering():openEngineeringDialog();}));
  $("#closeEngineeringDialog")?.addEventListener("click",()=>$("#engineeringDialog")?.close());
  $("#cancelEngineeringLoginButton")?.addEventListener("click",()=>$("#engineeringDialog")?.close());
  $("#engineeringLoginForm")?.addEventListener("submit",async(event)=>{event.preventDefault();const result=$("#engineeringLoginResult"),submit=$("#submitEngineeringLoginButton");submit.disabled=true;result.className="engineering-login-result muted";result.textContent="Проверка пароля...";try{await loginEngineering($("#engineeringPasswordInput").value,Number($("#engineeringTtlInput").value||480));}catch(error){result.className="engineering-login-result error";result.textContent=error.status===401?"Неверный пароль инженерного режима.":error.message;}finally{submit.disabled=false;}});
  $("#settingsView").addEventListener("click",(e)=>{const theme=e.target.dataset.themeChoice;if(theme){saveThemePreference(theme);}});
  $("#refreshParityStatusButton").addEventListener("click",()=>{renderParityStatus();toast("Parity status обновлён.");});
  $("#exportParityReportButton").addEventListener("click",exportParityReport);
  $("#clearAllButton").addEventListener("click",()=>{if(confirm("Очистить текущие файлы и результаты? История сохранится.")){state.files=[];state.ddioFile=null;state.ddioOverlay={};state.ddioSummary=null;state.devices=[];state.invalid=[];sourceFilesById.clear();pruneStoredSourceFiles();clearResultReference();state.lastAnalysis=null;save();renderAll();}});
  $("#saveBackupButton").addEventListener("click",async()=>{try{const backup=await api("/backup/export",{method:"POST",body:JSON.stringify({state:compactAnalysisAutosaveState()})});download(backup.filename||"mac-analyzer-backup.json",backup.content||"{}","application/json");}catch(error){if(networkUnavailable(error))await createPortableDatabase();else toast(error.message);}});
  $("#saveAutosaveButton").addEventListener("click",async()=>{try{await persistAutosave("manual");toast("Autosave saved to SQLite.");}catch(error){if(!networkUnavailable(error))return toast(error.message);save({immediate:true});await flushBrowserStateSave();await flushPortableDatabaseSave().catch(()=>{});toast("Автосохранение выполнено локально.");}});
  $("#restoreAutosaveButton").addEventListener("click",async()=>{try{await restoreAutosave();toast("Autosave restored.");}catch(error){if(!networkUnavailable(error))return toast(error.message);const restored=await restoreBrowserStateFromIndexedDb();if(restored){renderAll();toast("Локальное автосохранение восстановлено.");}else toast("Локальное автосохранение отсутствует.");}});
  $("#deleteAutosaveButton").addEventListener("click",async()=>{try{await deleteAutosave();toast("Autosave deleted.");renderServices();}catch(error){if(!networkUnavailable(error))return toast(error.message);localStorage.removeItem(key);localStorage.removeItem(browserStateSavedAtKey);await deleteBrowserStateRecord().catch(()=>{});toast("Локальное автосохранение очищено.");}});
  $("#restoreBackupInput").addEventListener("change",async(e)=>{const file=e.target.files[0];e.target.value="";if(!file)return;try{const backup=await api("/backup/restore",{method:"POST",body:JSON.stringify({filename:file.name,contentBase64:await fileToBase64(file)})});state={...empty(),...(backup.state||{})};save();location.reload();}catch(error){if(!networkUnavailable(error))return toast("Не удалось восстановить резервную копию.");try{const payload=JSON.parse(await file.text()),restored=payload.state||payload;state=normalizeRestoredState(restored);save({immediate:true});await flushBrowserStateSave();renderAll();toast("Локальная JSON-копия восстановлена.");}catch{toast("Не удалось восстановить резервную копию.");}}});
  $("#addIpMappingButton").addEventListener("click",async()=>{const switchIp=$("#switchIpInput").value.trim(),address=$("#switchAddressInput").value.trim();if(!switchIp||!address)return toast("Укажите IP и адрес.");try{await api("/ip-mappings",{method:"POST",body:JSON.stringify({switchIp,address})});$("#switchIpInput").value="";$("#switchAddressInput").value="";renderServices();}catch(error){if(upsertLocalIpMapping(switchIp,address,"manual")){$("#switchIpInput").value="";$("#switchAddressInput").value="";renderLocalIpMappings();toast("IP-маппинг сохранён локально.");}else toast(error.message);}});
  $("#ipMappingImportInput").addEventListener("change",async(e)=>{const file=e.target.files[0];if(!file)return;try{const result=await api("/ip-mappings/import",{method:"POST",body:JSON.stringify({filename:file.name,contentBase64:await fileToBase64(file)})});renderServices();toast("Импортировано соответствий: "+result.imported+", пропущено: "+result.skipped);}catch(error){try{const result=await importLocalIpMappings(file);toast("Локально импортировано соответствий: "+result.imported+", пропущено: "+result.skipped);}catch(localError){toast("Импорт не выполнен: "+localError.message);}}e.target.value="";});
  $("#exportIpMappingsButton").addEventListener("click",async()=>{try{const data=await api("/ip-mappings/export");download(data.filename||"ip-address-mappings.csv","\uFEFF"+data.content,"text/csv");}catch(error){exportLocalIpMappings();toast("IP-маппинг экспортирован локально.");}});
  $("#autoDetectIpMappingsButton").addEventListener("click",async()=>{if(!currentDeviceCount())return toast("Нет результатов для автоопределения.");try{const result=await api("/ip-mappings/autodetect",{method:"POST",body:JSON.stringify(currentDevicePayload())});renderServices();toast("Автоопределено соответствий: "+result.imported);}catch(error){toast("Локально автоопределено соответствий: "+autodetectLocalIpMappings());}});
  $("#applyIpMappingsButton").addEventListener("click",async()=>{if(!currentDeviceCount())return toast("Нет результатов для применения.");if(state.resultBrowserSnapshotId){try{const result=await applyLocalIpMappings();save();renderResults();renderAnalytics();renderHistory();renderServices();toast("IP-маппинг применён к текущему результату: "+result.matched+" совпадений, обновлено "+result.filled);}catch(error){toast("IP-маппинг не применён: "+error.message);}return;}try{const result=await api("/ip-mappings/apply",{method:"POST",body:JSON.stringify(currentDevicePayload({compactResult:Boolean(state.resultSnapshotId),resultPageSize}))});state.devices=result.devices||[];if(result.resultReference?.snapshotId){state.resultSnapshotId=result.resultReference.snapshotId;state.resultDeviceCount=Number(result.resultReference.deviceCount||state.devices.length);state.resultInvalidCount=0;state.resultSummary=result.resultSummary||null;const index=state.snapshots.findIndex((item)=>String(item.id)===String(result.resultReference.snapshotId));if(index>=0&&result.snapshot)state.snapshots.splice(index,1,{...state.snapshots[index],...result.snapshot,devices:[],backendStored:true});}save();renderResults();renderAnalytics();renderHistory();renderServices();toast("IP-маппинг применён к текущему результату: "+(result.summary?.matched||0)+" совпадений, обновлено "+(result.summary?.filled||0));}catch(error){try{const result=await applyLocalIpMappings();toast("Локальный IP-маппинг применён: "+result.matched+" совпадений, обновлено "+result.filled);}catch(localError){toast("IP-маппинг не применён: "+localError.message);}}});
  $("#ipMappingList").addEventListener("click",async(e)=>{const value=e.target.dataset.removeIp,local=e.target.dataset.removeLocalIp;if(value){try{await api("/ip-mappings/"+encodeURIComponent(value),{method:"DELETE"});renderServices();}catch(error){toast(error.message);}}if(local){state.ipMappings=localIpMappingRows().filter((item)=>item.switchIp!==local);save();renderLocalIpMappings();toast("Локальный IP-маппинг удалён.");}});
  $("#addTaskButton").addEventListener("click",async()=>{const name=$("#taskNameInput").value.trim(),intervalMinutes=Number($("#taskIntervalInput").value);if(!name||intervalMinutes<1)return toast("Укажите имя и интервал.");try{await api("/tasks",{method:"POST",body:JSON.stringify({name,intervalMinutes,enabled:true})});$("#taskNameInput").value="";renderServices();}catch(error){toast(error.message);}});
  $("#queueCurrentFilesButton").addEventListener("click",async()=>{if(!state.files.length)return toast("Нет файлов для очереди.");try{const taskData=await api("/tasks"),task=(taskData.tasks||[])[0];if(!task)return toast("Сначала создайте задачу.");const result=await api("/tasks/queue",{method:"POST",body:JSON.stringify({taskId:task.id,files:sourceFilesPayload(true)})});renderServices();toast("Файлов добавлено в очередь: "+result.queued);}catch(error){toast(error.message);}});
  $("#runFirstTaskButton").addEventListener("click",async()=>{try{const taskData=await api("/tasks"),task=(taskData.tasks||[])[0];if(!task)return toast("Сначала создайте задачу.");const result=await api("/tasks/"+encodeURIComponent(task.id)+"/run",{method:"POST",body:JSON.stringify({})});renderServices();toast("Очередь обработана: "+result.done+" готово, "+result.errors+" ошибок.");}catch(error){toast(error.message);}});
  $("#taskList").addEventListener("click",async(e)=>{const id=e.target.dataset.removeTask;if(id){await api("/tasks/"+id,{method:"DELETE"});renderServices();}});
  $("#saveColumnsButton").addEventListener("click",async()=>{const columns=$$("#columnPreferenceList input[type=checkbox]:checked").map((input)=>input.value);if(!columns.length)return toast("Оставьте хотя бы одну колонку.");const order=$$("#columnPreferenceList [data-column-field]").map((item)=>item.dataset.columnField),custom=(state.customColumns||[]).map((key)=>({key,title:labels[key]||key,sourceIndex:state.customColumnMappings[key]}));try{const result=await api("/columns/preferences/results",{method:"POST",body:JSON.stringify({order,visible:columns,custom,widths:state.columnWidths})});applyColumnPreferences(result.preferences);toast("Колонки сохранены в SQLite.");}catch(error){toast(error.message);}});
  $("#resetColumnsButton").addEventListener("click",async()=>{try{const result=await api("/columns/preferences/results",{method:"DELETE"});applyColumnPreferences(result.preferences);toast("Колонки сброшены к стандартным.");}catch(error){toast(error.message);}});
  $("#addCustomColumnButton").addEventListener("click",async()=>{const name=$("#customColumnNameInput").value.trim(),column=$("#customColumnSource").value;if(!name||column==="")return toast("Укажите название и колонку файла.");const key="custom_"+name.toLowerCase().replace(/[^a-zа-я0-9]+/gi,"_").replace(/^_|_$/g,"");if((state.customColumns||[]).includes(key))return toast("Такое поле уже добавлено.");const nextCustom=[...(state.customColumns||[]),key],nextMappings={...(state.customColumnMappings||{}),[key]:Number(column)},nextLabels={...labels,[key]:name},nextOrder=[...(state.columnOrder||empty().columnOrder),key],nextVisible=[...(state.visibleColumns||empty().visibleColumns),key];try{const result=await api("/columns/preferences/results",{method:"POST",body:JSON.stringify(columnPreferencesPayload({order:nextOrder,visible:nextVisible,customKeys:nextCustom,customColumnMappings:nextMappings,labels:nextLabels}))});Object.assign(labels,nextLabels);$("#customColumnNameInput").value="";applyColumnPreferences(result.preferences);toast("Пользовательская колонка сохранена в SQLite.");}catch(error){toast(error.message);}});
  $("#columnPreferenceList").addEventListener("click",async(e)=>{const field=e.target.dataset.moveColumn,direction=e.target.dataset.direction;if(!field)return;try{const result=await api("/columns/preferences/results",{method:"POST",body:JSON.stringify({action:"move",column:field,direction})});applyColumnPreferences(result.preferences);toast("Порядок колонок сохранён в SQLite.");}catch(error){toast(error.message);}});
  $("#columnPreferenceList").addEventListener("click",async(e)=>{const field=e.target.dataset.removeCustomColumn;if(!field)return;const nextCustom=(state.customColumns||[]).filter((item)=>item!==field),nextMappings={...(state.customColumnMappings||{})},nextLabels={...labels},nextVisible=(state.visibleColumns||[]).filter((item)=>item!==field),nextOrder=(state.columnOrder||[]).filter((item)=>item!==field);delete nextMappings[field];delete nextLabels[field];try{const result=await api("/columns/preferences/results",{method:"POST",body:JSON.stringify(columnPreferencesPayload({order:nextOrder,visible:nextVisible,customKeys:nextCustom,customColumnMappings:nextMappings,labels:nextLabels}))});delete labels[field];state.devices.forEach((item)=>delete item[field]);applyColumnPreferences(result.preferences);toast("Пользовательская колонка удалена из SQLite.");}catch(error){toast(error.message);}});
  $("#columnPreferenceList").addEventListener("change",(event)=>{const column=event.target.dataset.columnWidth;if(!column)return;const width=Math.max(64,Math.min(600,Number(event.target.value)||150));state.columnWidths[column]=width;saveResultColumnWidths();});
  $("#optimizeColumnWidthsButton").addEventListener("click",optimizeResultColumnWidths);
  $("#resetColumnWidthsButton").addEventListener("click",resetResultColumnWidths);
  $("#saveColumnWidthsButton").addEventListener("click",()=>saveResultColumnWidths());
  $("#loadColumnWidthsButton").addEventListener("click",loadResultColumnWidths);
  $("#ouiLengthSelect").value=String(state.ouiLength||3);
  $("#ouiLengthSelect").addEventListener("change",(e)=>{saveOuiPreference({length:Number(e.target.value),style:state.ouiStyle});});
  $("#ouiStyleSelect").value=state.ouiStyle||"plain";
  $("#ouiStyleSelect").addEventListener("change",(e)=>{saveOuiPreference({length:state.ouiLength,style:e.target.value});});
  $("#saveNotificationButton").addEventListener("click",async()=>{try{await api("/notifications",{method:"POST",body:JSON.stringify({channel:$("#notificationChannel").value,configText:$("#notificationConfig").value,enabled:$("#notificationEnabled").checked})});toast("Настройки уведомлений сохранены.");}catch(error){toast("Проверьте JSON: "+error.message);}});
  $("#testNotificationButton").addEventListener("click",async()=>{try{const channel=$("#notificationChannel").value;await api("/notifications/test",{method:"POST",body:JSON.stringify({channel,configText:$("#notificationConfig").value})});toast("Тестовое уведомление отправлено.");}catch(error){toast("Тест не выполнен: "+error.message);}});
  $("#testAnalysisNotificationButton").addEventListener("click",async()=>{try{const result=await api("/notifications/event",{method:"POST",body:JSON.stringify(currentDevicePayload({type:"analysis_completed",invalid:state.invalid,source:"manual notification test"}))});toast("Событие анализа: отправлено "+result.sent+", ошибок "+result.errors+", пропущено "+result.skipped);}catch(error){toast("Событие не отправлено: "+error.message);}});
  $("#notificationChannel").addEventListener("change",()=>{renderServices();});
  $("#saveExternalApiSettingsButton").addEventListener("click",saveExternalApiSettings);
  $("#openApiSettingsDialogButton").addEventListener("click",showApiSettingsDialog);
  $("#closeApiSettingsDialog").addEventListener("click",()=>$("#apiSettingsDialog").close());
  $("#apiSettingsCancelButton").addEventListener("click",()=>$("#apiSettingsDialog").close());
  $("#apiSettingsSaveButton").addEventListener("click",saveApiSettingsDialog);
  $("#apiSettingsTestButton").addEventListener("click",testApiSettingsDialog);
  $("#apiSettingsTestMacInput").addEventListener("keydown",(event)=>{if(event.key==="Enter")testApiSettingsDialog();});
  $("#apiEnrichButton").addEventListener("click",async()=>{if(!state.devices.length)return toast("Нет устройств для API-обогащения.");const previousDevices=state.devices||[],sourceCreatedAt=state.lastAnalysis||primaryFileCreatedAt();try{if(!state.resultSnapshotId&&!backendAvailable&&state.devices.length>(MemoryGuard.limits.inlineComparisonRows||20000))throw new Error("Для API-обогащения большого автономного набора подключите backend.");const result=await api("/external-enrichment/run",{method:"POST",body:JSON.stringify(currentDevicePayload({createdAt:sourceCreatedAt,saveHistory:true,compactResult:true,resultPageSize:resultPageSize}))});state.devices=result.devices||[];state.lastAnalysis=sourceCreatedAt;if(result.resultReference?.snapshotId){state.resultSnapshotId=result.resultReference.snapshotId;state.resultDeviceCount=Number(result.resultReference.deviceCount||state.devices.length);state.resultInvalidCount=Number(result.resultReference.invalidCount||0);if(result.snapshot){state.snapshots.unshift({...result.snapshot,devices:[],backendStored:true});state.snapshots=state.snapshots.slice(0,25);}}recordLocalMovements(previousDevices,state.devices,"external-api-enrichment",state.lastAnalysis);save();persistAutosave("external-api-enrichment").catch(()=>{});renderAll();toast("API-обогащение: кандидатов "+result.summary.candidates+", обновлено "+result.summary.updated+", кэш "+result.summary.cached+", запросов "+result.summary.lookups);}catch(error){toast(error.message);}});
  $("#apiLookupButton").addEventListener("click",async()=>{const mac=$("#apiLookupMacInput").value.trim();if(!mac)return toast("Введите MAC-адрес.");try{const result=await api("/external-enrichment/test",{method:"POST",body:JSON.stringify({mac})});$("#apiLookupResult").textContent=(result.macFormatted||mac)+" · "+(result.vendor||"Unknown")+" · provider: "+result.provider+" · source: "+result.source;await refreshApiCacheStatus();}catch(error){$("#apiLookupResult").textContent="Ошибка API: "+error.message;}});
  $("#refreshApiCacheButton").addEventListener("click",()=>{refreshApiCacheStatus().catch((error)=>toast(error.message));});
  $("#clearApiCacheButton").addEventListener("click",clearApiCache);
  $("#databaseSearchButton").addEventListener("click",searchDatabase);
  $("#databaseImportButton").addEventListener("click",()=>$("#databaseImportInput").click());
  $("#databaseImportInput").addEventListener("change",(event)=>importDatabaseFile(event.target.files?.[0]));
  $("#databaseSearchInput").addEventListener("keydown",(event)=>{if(event.key==="Enter")searchDatabase();});
  $("#databaseSearchResults").addEventListener("dblclick",async(e)=>{const row=e.target.closest("[data-db-mac]");const mac=row?.dataset.dbMac,type=row?.dataset.dbType;if(!mac){toast(type==="ipMapping"?"IP mapping has no device MAC.":"No MAC in this database result.");return;}try{await openDatabaseDevice(mac);}catch(error){toast(error.message);}});
  $("#databaseHistoryFilterButton").addEventListener("click",loadDatabaseHistoryManagement);
  $("#reloadDatabaseHistoryButton").addEventListener("click",loadDatabaseHistoryManagement);
  $$("#dbHistoryMacFilter,#dbHistorySourceFilter,#dbHistoryVendorFilter,#dbHistoryModelFilter,#dbHistoryRoomFilter,#dbHistoryDateFrom,#dbHistoryDateTo").forEach((input)=>input.addEventListener("keydown",(event)=>{if(event.key==="Enter")loadDatabaseHistoryManagement();}));
  $("#clearDatabaseHistoryFiltersButton").addEventListener("click",()=>{$$("#dbHistoryMacFilter,#dbHistorySourceFilter,#dbHistoryVendorFilter,#dbHistoryModelFilter,#dbHistoryRoomFilter,#dbHistoryDateFrom,#dbHistoryDateTo").forEach((input)=>{input.value="";});loadDatabaseHistoryManagement();});
  $("#deleteSelectedDatabaseHistoryButton").addEventListener("click",()=>deleteDatabaseHistoryEntries(selectedDatabaseHistoryIds(),{}));
  $("#deleteFilteredDatabaseHistoryButton").addEventListener("click",()=>deleteDatabaseHistoryEntries([],databaseHistoryFilters()));
  $("#selectAllDatabaseHistory").addEventListener("change",(event)=>{$$('[data-db-history-select]').forEach((input)=>{input.checked=event.target.checked;});});
  $("#databaseHistoryBody").addEventListener("change",(event)=>{if(!event.target.matches("[data-db-history-select]"))return;const boxes=$$('[data-db-history-select]'),checked=boxes.filter((input)=>input.checked).length,selectAll=$("#selectAllDatabaseHistory");selectAll.checked=boxes.length>0&&checked===boxes.length;selectAll.indeterminate=checked>0&&checked<boxes.length;});
  $("#databaseHistoryBody").addEventListener("click",(event)=>{const button=event.target.closest("[data-delete-db-history-id]");if(button)deleteDatabaseHistoryEntries([Number(button.dataset.deleteDbHistoryId)],{});});
  $("#databaseHistoryBody").addEventListener("dblclick",async(event)=>{if(event.target.closest("button,input"))return;const row=event.target.closest("[data-db-history-mac]");if(!row)return;try{await openDatabaseDevice(row.dataset.dbHistoryMac);}catch(error){toast(error.message);}});
  $("#refreshDataButton").addEventListener("click",()=>{syncFromBackend();renderServices();loadDatabaseHistoryManagement();});
  $("#clearDatabaseSnapshotsButton").addEventListener("click",async()=>{if(!confirm("Удалить все сохранённые снимки/выгрузки из SQLite?"))return;try{const result=await api("/database/snapshots/delete",{method:"POST",body:JSON.stringify({})});state.snapshots=[];save();renderAll();renderServices();toast("Удалено снимков SQLite: "+result.deleted);}catch(error){toast(error.message);}});
  $("#clearDatabaseHistoryButton").addEventListener("click",async()=>{if(!confirm("Удалить всю историю устройств и перемещений из SQLite? Снимки браузера не будут удалены."))return;try{await api("/history",{method:"DELETE"});await loadDatabaseHistoryManagement();toast("История SQLite очищена.");}catch(error){toast(error.message);}});
  $("#databaseMaintenanceButton").addEventListener("click",async()=>{try{const result=await api("/database/maintenance",{method:"POST",body:JSON.stringify({integrity:true,optimize:true,vacuum:false})});renderServices();toast("SQLite integrity: "+result.integrity+", reclaimed "+Math.round((result.reclaimedBytes||0)/1024)+" KB");}catch(error){toast(error.message);}});
  $("#legacyImportButton").addEventListener("click",async()=>{try{const result=await api("/legacy/import",{method:"POST",body:JSON.stringify({dryRun:false})});renderServices();toast("Legacy SQLite: imported "+(result.summary?.imported||0)+", skipped "+(result.summary?.skipped||0));}catch(error){toast(error.message);}});
  $("#qualityAnalysisButton").addEventListener("click",()=>{analyzeQuality();toast("Анализ качества данных завершён.");});
  $("#refreshAnalyticsReportButton").addEventListener("click",refreshAnalyticsReport);
  $("#exportAnalyticsReportButton").addEventListener("click",exportAnalyticsReport);
  $("#dashboardVendorFilter").addEventListener("change",renderAnalytics);
  $("#dashboardSearchInput").addEventListener("input",debounce(renderAnalytics,180));
  $("#dashboardRoomFilter").addEventListener("change",renderAnalytics);
  $("#dashboardStatusFilter").addEventListener("change",renderAnalytics);
  $("#refreshDashboardButton").addEventListener("click",renderAnalytics);
  $$("[data-dashboard-status]").forEach((button)=>button.addEventListener("click",async()=>{const selected=button.dataset.dashboardStatus||"all",status=$("#dashboardStatusFilter");if(status)status.value=selected;await renderAnalytics();if(selected==="all")showDashboardDynamicsDialog();else if(selected==="changed")showDashboardChangesDialog("modified");else if(selected==="missing")showDashboardChangesDialog("removed");}));
  $("#dashboardChangeMode").addEventListener("change",()=>{const settings=readDashboardChangeControls();syncDashboardChangeControls(settings);});
  $("#applyDashboardChangeRangeButton").addEventListener("click",async()=>{readDashboardChangeControls();await renderAnalytics();showDashboardChangesDialog();});
  $("#openDashboardChangesButton").addEventListener("click",()=>showDashboardChangesDialog("all"));
  $("#dashboardChangeSeverityFilter").addEventListener("change",()=>{syncDashboardChangeTabState();renderDashboardChangesTable();});
  $("#dashboardChangeTypeFilter").addEventListener("change",()=>{syncDashboardChangeTabState();renderDashboardChangesTable();});
  $("#dashboardChangeSearch").addEventListener("input",debounce(renderDashboardChangesTable,180));
  $("#dashboardChangeMacSearch").addEventListener("input",debounce(renderDashboardChangesTable,120));
  $("#analyticsView").addEventListener("click",(event)=>{const expand=event.target.closest("[data-analytics-expand]"),collapse=event.target.closest("[data-analytics-collapse]");if(!expand&&!collapse)return;const panel=event.target.closest(".tool-panel");if(!panel)return;if(expand){panel.classList.toggle("analytics-panel-expanded");expand.setAttribute("aria-pressed",String(panel.classList.contains("analytics-panel-expanded")));}else{panel.classList.toggle("analytics-panel-collapsed");collapse.textContent=panel.classList.contains("analytics-panel-collapsed")?"+":"−";collapse.title=panel.classList.contains("analytics-panel-collapsed")?"Развернуть раздел":"Свернуть раздел";}});
  $$("[data-dashboard-change-type]").forEach((button)=>button.addEventListener("click",()=>selectDashboardChangeTab(button.dataset.dashboardChangeType||"all")));
  $(".dashboard-change-metrics").addEventListener("keydown",handleDashboardChangeTabKeydown);
  $("#dashboardChangesBody").addEventListener("click",(event)=>{const toggle=event.target.closest("[data-toggle-dashboard-change]");if(toggle){const id=toggle.dataset.toggleDashboardChange,expanded=toggle.getAttribute("aria-expanded")==="true";toggle.setAttribute("aria-expanded",expanded?"false":"true");toggle.textContent=expanded?"▸":"▾";$$(`[data-dashboard-change-child="${id}"]`).forEach((row)=>{row.hidden=expanded;});return;}const macButton=event.target.closest("[data-mac]");if(macButton)showDevice(macButton.dataset.mac);});
  $("#closeDashboardChangesDialog").addEventListener("click",()=>$("#dashboardChangesDialog").close());
  $("#closeDashboardDynamicsDialog").addEventListener("click",()=>$("#dashboardDynamicsDialog").close());
  $("#saveDashboardSettingsButton").addEventListener("click",showDashboardSettingsDialog);
  $$('[data-dashboard-settings-tab]').forEach((button)=>button.addEventListener("click",()=>selectDashboardSettingsTab(button.dataset.dashboardSettingsTab)));
  $("#applyDashboardSettingsButton").addEventListener("click",()=>saveDashboardSettings(dashboardDialogSettings()));
  $("#resetDashboardSettingsButton").addEventListener("click",()=>{const current=dashboardSettings();fillDashboardSettingsDialog({...current,visibleCards:{total:true,changed:true,missing:true,unchanged:true,vendors:true,rooms:true,changedRooms:true},visibleCharts:{dynamics:true,vendors:true,fields:true,missing:true},autoRefresh:true,refreshInterval:60});saveDashboardSettings(dashboardDialogSettings());});
  $("#closeDashboardSettingsDialog").addEventListener("click",()=>$("#dashboardSettingsDialog").close());
  $("#cancelDashboardSettingsButton").addEventListener("click",()=>$("#dashboardSettingsDialog").close());
  $("#exportDashboardButton").addEventListener("click",(event)=>{event.preventDefault();event.stopImmediatePropagation();exportDashboard();},true);
  $("#exportChartsSvgButton").addEventListener("click",exportChartsSvg);
  $("#exportTopologyButton").addEventListener("click",exportTopology);
  $("#exportClustersButton").addEventListener("click",exportClusters);
  window.addEventListener("pointermove",resizeResultColumn);window.addEventListener("pointerup",finishResultColumnResize);window.addEventListener("pointercancel",finishResultColumnResize);
  window.addEventListener("pointermove",resizeMovementColumn);window.addEventListener("pointerup",finishMovementColumnResize);window.addEventListener("pointercancel",finishMovementColumnResize);
  document.addEventListener("keydown",handleAppShortcut);
  setInterval(()=>{if(!browserOnlyMode)persistAutosave("interval").catch(()=>{});},60000);
  setInterval(()=>{if(state.engineeringMode&&!engineeringSessionActive()){clearEngineeringSession();renderEngineeringState();toast("Инженерная сессия завершена.");}},30000);
  window.addEventListener("beforeunload",()=>{save();if(!autonomousHtmlMode&&backendAvailable){const autosaveState=compactAnalysisAutosaveState();fetch("/api/autosave",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({slot:"main",reason:"beforeunload",state:autosaveState}),keepalive:true}).catch(()=>{});}});
  async function restoreInitialState(){
    await BrowserSnapshots?.pruneEnrichmentRows?.().catch(()=>0);
    const restored=await restoreBrowserStateFromIndexedDb();
    if(restored){applyTheme(state.theme);applyVendorDetectorSettings(state.vendorDetectorSettings||{});applyHistoryEnrichmentSettings(state.historyEnrichmentSettings||{});renderEngineeringState();renderAll();renderColumnPreferences();const status=$("#autosaveStatus");if(status)status.textContent="Последние данные отображены из локального кэша; проверяется постоянная база.";}
    const backendSynced=browserOnlyMode?false:await syncFromBackend();
    if(!backendSynced){
      const folderRestored=await restoreLocalFolderHandle({preferBrowserState:restored});
      if(!folderRestored&&!restored)await restorePortableDatabaseHandle();
    }
    const historicalSnapshots=(state.snapshots||[]).filter((item)=>item.browserStored).map((item)=>item.id).filter(Boolean).reverse();
    await BrowserSnapshots?.backfillDeviceHistory?.(historicalSnapshots).catch(()=>0);
    await restoreWorkspaceSourceFiles();
    await SmartroomUI?.autoLoad?.().catch((error)=>UiFeedback?.showError(error));
  }
  SmartroomUI?.initialize({
    getSnapshots:()=>finalDashboardSnapshots(),
    getCurrentDevices:()=>state.devices||[],
    getLastAnalysis:()=>state.lastAnalysis||"",
    getDdioOverlay:()=>state.ddioOverlay||{},
    hasDdioFile:()=>Boolean(state.ddioFile),
    streamSnapshot:(snapshot,onChunk)=>BrowserSnapshots?.streamSnapshot?BrowserSnapshots.streamSnapshot(snapshot.id,onChunk):Promise.resolve(null),
    loadSnapshot:async(snapshot)=>{if(snapshot?.browserStored)return loadLocalSnapshotRecord(snapshot);if(snapshot?.backendStored&&backendAvailable)try{return await api("/snapshots/open",{method:"POST",body:JSON.stringify({id:snapshot.id,snapshots:[]})});}catch{}return snapshot;},
    loadDdioFile,
    notify:toast,
  });
  VirtualTable?.initialize(document);
  queueMicrotask(()=>LazyTabs?.initialize(document.querySelectorAll(".view"),activeViewName()));
  initializeAnalyticsExpanders();applyTheme(state.theme);applyVendorDetectorSettings(state.vendorDetectorSettings||{});applyHistoryEnrichmentSettings(state.historyEnrichmentSettings||{});view(viewFromHash(),{updateHash:true,render:false});renderEngineeringState();renderAll();renderColumnPreferences();renderParityStatus();if(!browserOnlyMode){loadThemePreference();loadOuiPreference().then(()=>{renderResults();});loadVendorDetectorSettings();loadHistoryEnrichmentSettings();loadDashboardSettings();loadExternalApiSettings();refreshApiCacheStatus().catch(()=>{});}loadEngineeringSession();setBackendStatus(false,"Автономный режим · выберите локальную папку данных");restoreInitialState().finally(()=>{window.MacAnalyzerAppReady=true;document.documentElement.dataset.macAnalyzerApp="ready";scheduleViewContent(activeViewName());});
})();

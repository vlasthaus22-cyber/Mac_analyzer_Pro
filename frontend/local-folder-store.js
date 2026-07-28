(() => {
  "use strict";

  const handleDatabaseName = "mac-analyzer-local-folder-v1";
  const handleStoreName = "handles";
  const handleRecordId = "main";
  const databaseFileName = "mac-analyzer-data.madb";
  const folderNames = Object.freeze(["database", "imports", "exports", "settings", "logs", "backups"]);

  function openHandleDatabase() {
    return new Promise((resolve, reject) => {
      if (!("indexedDB" in window)) return reject(new Error("IndexedDB недоступна"));
      const request = indexedDB.open(handleDatabaseName, 1);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(handleStoreName)) {
          request.result.createObjectStore(handleStoreName, { keyPath: "id" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Не удалось открыть хранилище ссылки на папку"));
    });
  }

  async function saveHandle(handle) {
    if (!handle) return false;
    const database = await openHandleDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(handleStoreName, "readwrite");
      current.objectStore(handleStoreName).put({ id: handleRecordId, handle });
      current.oncomplete = () => { database.close(); resolve(true); };
      current.onerror = () => { const error = current.error; database.close(); reject(error); };
    });
  }

  async function loadHandle() {
    try {
      const database = await openHandleDatabase();
      return await new Promise((resolve, reject) => {
        const current = database.transaction(handleStoreName, "readonly");
        const request = current.objectStore(handleStoreName).get(handleRecordId);
        request.onsuccess = () => resolve(request.result?.handle || null);
        request.onerror = () => reject(request.error);
        current.oncomplete = () => database.close();
      });
    } catch {
      return null;
    }
  }

  async function permission(handle, mode = "read") {
    if (!handle?.queryPermission) return "unsupported";
    try { return await handle.queryPermission({ mode }); } catch { return "denied"; }
  }

  async function requestPermission(handle, mode = "readwrite") {
    const current = await permission(handle, mode);
    if (current === "granted" || current === "unsupported") return true;
    if (!handle?.requestPermission) return false;
    try { return await handle.requestPermission({ mode }) === "granted"; } catch { return false; }
  }

  async function chooseDirectoryHandle() {
    if (!("showDirectoryPicker" in window)) return null;
    const handle = await window.showDirectoryPicker({ id: "mac-analyzer-data", mode: "readwrite" });
    if (handle) await saveHandle(handle).catch(() => false);
    return handle || null;
  }

  async function ensureStructure(rootHandle) {
    if (!rootHandle?.getDirectoryHandle) throw new Error("Выбранная папка недоступна для записи");
    const directories = {};
    for (const name of folderNames) directories[name] = await rootHandle.getDirectoryHandle(name, { create: true });
    const databaseHandle = await directories.database.getFileHandle(databaseFileName, { create: true });
    return { rootHandle, directories, databaseHandle };
  }

  function safeFileName(value = "file") {
    const cleaned = String(value || "file").replace(/[<>:"/\\|?*\x00-\x1F]/g, "_").trim();
    return (cleaned || "file").slice(0, 180);
  }

  function stableFingerprint(value = "") {
    let hash = 2166136261;
    for (const character of String(value)) {
      hash ^= character.charCodeAt(0);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
  }

  function normalizedRelativePath(file) {
    return String(file?.webkitRelativePath || file?.relativePath || file?.name || "")
      .replace(/\\/g, "/")
      .replace(/^\/+/, "");
  }

  function findDatabaseFile(files = []) {
    const candidates = Array.from(files || [])
      .filter((file) => file instanceof Blob && /\.madb$/i.test(String(file.name || "")))
      .map((file) => {
        const path = normalizedRelativePath(file);
        const normalized = path.toLowerCase();
        let priority = 4;
        if (normalized.endsWith(`/database/${databaseFileName}`)) priority = 0;
        else if (normalized === databaseFileName || normalized.endsWith(`/${databaseFileName}`)) priority = 1;
        else if (normalized.includes("/database/")) priority = 2;
        else priority = 3;
        return { file, path, priority };
      })
      .sort((left, right) => left.priority - right.priority || right.file.size - left.file.size || left.path.localeCompare(right.path));
    if (!candidates.length) return null;
    const selected = candidates[0];
    const firstSegment = selected.path.split("/").filter(Boolean)[0] || "";
    return {
      file: selected.file,
      path: selected.path || selected.file.name,
      rootName: selected.path.includes("/") ? firstSegment : "",
      candidateCount: candidates.length,
    };
  }

  function inspectFolderFiles(files = []) {
    const list = Array.from(files || []).filter((file) => file instanceof Blob);
    const database = findDatabaseFile(list);
    return {
      fileCount: list.length,
      totalBytes: list.reduce((total, file) => total + Math.max(0, Number(file.size || 0)), 0),
      database,
      rootName: database?.rootName || normalizedRelativePath(list[0]).split("/").filter(Boolean)[0] || "",
    };
  }

  async function writeFile(handle, content) {
    const writable = await handle.createWritable({ keepExistingData: false });
    try {
      await writable.write(content);
      await writable.close();
      return true;
    } catch (error) {
      await writable.abort?.().catch(() => {});
      throw error;
    }
  }

  async function writeManifest(structure, extra = {}) {
    const file = await structure.directories.settings.getFileHandle("storage-manifest.json", { create: true });
    const manifest = {
      application: "MAC Analyzer Pro Web",
      format: "local-folder-v1",
      database: `database/${databaseFileName}`,
      folders: folderNames,
      updatedAt: new Date().toISOString(),
      ...extra,
    };
    await writeFile(file, JSON.stringify(manifest, null, 2));
    return manifest;
  }

  async function copyImport(structure, file, storageId = "") {
    if (!structure?.directories?.imports || !(file instanceof Blob)) return null;
    const identity = storageId || `${file.name||"source-file"}|${file.size||0}|${file.lastModified||0}`;
    const targetName = `${stableFingerprint(identity)}__${safeFileName(file.name || "source-file")}`;
    const target = await structure.directories.imports.getFileHandle(targetName, { create: true });
    await writeFile(target, file);
    const metadataHandle = await structure.directories.imports.getFileHandle(`${targetName}.json`, { create: true });
    await writeFile(metadataHandle, JSON.stringify({
      name: String(file.name || targetName),
      storedAs: targetName,
      storageId: String(storageId || ""),
      size: Number(file.size || 0),
      type: String(file.type || "application/octet-stream"),
      lastModified: Number(file.lastModified || 0),
      importedAt: new Date().toISOString(),
    }, null, 2));
    return targetName;
  }

  async function writeExport(structure, name, content) {
    if (!structure?.directories?.exports) return null;
    const targetName = safeFileName(name || `export-${Date.now()}.dat`);
    const target = await structure.directories.exports.getFileHandle(targetName, { create: true });
    await writeFile(target, content);
    return targetName;
  }

  async function writeLog(structure, event, details = {}) {
    if (!structure?.directories?.logs) return false;
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const target = await structure.directories.logs.getFileHandle(`${stamp}__${safeFileName(event)}.json`, { create: true });
    await writeFile(target, JSON.stringify({ event, createdAt: new Date().toISOString(), ...details }, null, 2));
    return true;
  }

  window.MacAnalyzerLocalFolderStore = Object.freeze({
    databaseFileName,
    folderNames,
    supportsDirectoryPicker: () => "showDirectoryPicker" in window,
    saveHandle,
    loadHandle,
    permission,
    requestPermission,
    chooseDirectoryHandle,
    ensureStructure,
    normalizedRelativePath,
    findDatabaseFile,
    inspectFolderFiles,
    writeManifest,
    copyImport,
    writeExport,
    writeLog,
  });
  document.documentElement.dataset.localFolderStore = "ready";
})();

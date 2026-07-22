(() => {
  "use strict";

  const format = "MAC_ANALYZER_PORTABLE_DB";
  const version = 1;
  const handleDatabaseName = "mac-analyzer-portable-file-v1";
  const handleStoreName = "handles";
  const handleRecordId = "main";
  const maximumDatabaseBytes = 1024 * 1024 * 1024;
  const writeBatchRows = 250;

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
      request.onerror = () => reject(request.error || new Error("Не удалось открыть хранилище файловой базы"));
    });
  }

  async function saveHandle(handle) {
    if (!handle) return false;
    const database = await openHandleDatabase();
    return new Promise((resolve, reject) => {
      const transaction = database.transaction(handleStoreName, "readwrite");
      transaction.objectStore(handleStoreName).put({ id: handleRecordId, handle });
      transaction.oncomplete = () => { database.close(); resolve(true); };
      transaction.onerror = () => { const error = transaction.error; database.close(); reject(error); };
    });
  }

  async function loadHandle() {
    try {
      const database = await openHandleDatabase();
      return await new Promise((resolve, reject) => {
        const transaction = database.transaction(handleStoreName, "readonly");
        const request = transaction.objectStore(handleStoreName).get(handleRecordId);
        request.onsuccess = () => resolve(request.result?.handle || null);
        request.onerror = () => reject(request.error);
        transaction.oncomplete = () => database.close();
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

  async function chooseOpenHandle() {
    if (!("showOpenFilePicker" in window)) return null;
    const [handle] = await window.showOpenFilePicker({
      multiple: false,
      types: [{ description: "MAC Analyzer database", accept: { "application/x-mac-analyzer-db": [".madb"] } }],
    });
    if (handle) await saveHandle(handle).catch(() => false);
    return handle || null;
  }

  async function chooseSaveHandle(suggestedName = "mac-analyzer-data.madb") {
    if (!("showSaveFilePicker" in window)) return null;
    const handle = await window.showSaveFilePicker({
      suggestedName,
      types: [{ description: "MAC Analyzer database", accept: { "application/x-mac-analyzer-db": [".madb"] } }],
    });
    if (handle) await saveHandle(handle).catch(() => false);
    return handle || null;
  }

  function normalizePayload(payload = {}) {
    const state = payload.state && typeof payload.state === "object" ? { ...payload.state } : {};
    delete state.devices;
    delete state.invalid;
    delete state.movementHistory;
    return {
      state,
      devices: Array.isArray(payload.devices) ? payload.devices : [],
      invalid: Array.isArray(payload.invalid) ? payload.invalid : [],
      deviceCount: Math.max(0, Number(payload.deviceCount ?? payload.devices?.length ?? 0) || 0),
      invalidCount: Math.max(0, Number(payload.invalidCount ?? payload.invalid?.length ?? 0) || 0),
      currentResultStreamer: typeof payload.currentResultStreamer === "function" ? payload.currentResultStreamer : null,
      movements: Array.isArray(payload.movements) ? payload.movements : [],
      snapshotMetadata: (Array.isArray(payload.snapshotMetadata) ? payload.snapshotMetadata : []).filter((item) => item?.id),
      snapshotLoader: typeof payload.snapshotLoader === "function" ? payload.snapshotLoader : null,
      snapshotStreamer: typeof payload.snapshotStreamer === "function" ? payload.snapshotStreamer : null,
      skipSnapshotId: String(payload.skipSnapshotId || ""),
    };
  }

  function headerFor(payload, savedAt) {
    return {
      format,
      version,
      savedAt,
      counts: {
        devices: payload.deviceCount,
        invalid: payload.invalidCount,
        movements: payload.movements.length,
        snapshots: payload.snapshotMetadata.length,
      },
    };
  }

  async function writeRows(write, type, rows, progress, completed, total) {
    let batch = "";
    let batchRows = 0;
    for (let index = 0; index < rows.length; index += 1) {
      batch += JSON.stringify({ type, value: rows[index] }) + "\n";
      batchRows += 1;
      if ((index + 1) % writeBatchRows === 0 || index + 1 === rows.length) {
        await write(batch);
        batch = "";
        completed.value += batchRows;
        batchRows = 0;
        progress(total ? Math.min(99, Math.round(completed.value / total * 100)) : 99, `Сохранено записей: ${completed.value.toLocaleString("ru-RU")} / ${total.toLocaleString("ru-RU")}`);
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
    }
  }

  async function writeToSink(write, payload, onProgress = () => {}) {
    const data = normalizePayload(payload);
    const savedAt = new Date().toISOString();
    const total = data.deviceCount + data.invalidCount + data.movements.length;
    const completed = { value: 0 };
    await write(JSON.stringify(headerFor(data, savedAt)) + "\n");
    await write(JSON.stringify({ type: "state", value: data.state }) + "\n");
    for (const metadata of data.snapshotMetadata) {
      if (String(metadata.id) === data.skipSnapshotId) {
        await write(JSON.stringify({ type: "snapshot-current", value: { ...metadata, devices: [], invalid: [] } }) + "\n");
        continue;
      }
      if (data.snapshotStreamer) {
        await write(JSON.stringify({ type: "snapshot-start", value: { ...metadata, devices: [], invalid: [] } }) + "\n");
        await data.snapshotStreamer(metadata, async (kind, rows) => {
          await writeRows(write, kind === "invalid" ? "snapshot-invalid" : "snapshot-device", Array.isArray(rows) ? rows : [], () => {}, { value: 0 }, 0);
        });
        await write(JSON.stringify({ type: "snapshot-end", value: { id: metadata.id } }) + "\n");
        onProgress(2, `Сохранён снимок: ${metadata.name || metadata.id}`);
      } else if (data.snapshotLoader) {
        const snapshot = await data.snapshotLoader(metadata);
        if (!snapshot) {
          await write(JSON.stringify({ type: "snapshot-start", value: { ...metadata, devices: [], invalid: [] } }) + "\n");
          await write(JSON.stringify({ type: "snapshot-end", value: { id: metadata.id } }) + "\n");
          continue;
        }
        const snapshotHeader = { ...metadata, ...snapshot, devices: [], invalid: [] };
        await write(JSON.stringify({ type: "snapshot-start", value: snapshotHeader }) + "\n");
        await writeRows(write, "snapshot-device", Array.isArray(snapshot.devices) ? snapshot.devices : [], () => {}, { value: 0 }, 0);
        await writeRows(write, "snapshot-invalid", Array.isArray(snapshot.invalid) ? snapshot.invalid : [], () => {}, { value: 0 }, 0);
        await write(JSON.stringify({ type: "snapshot-end", value: { id: metadata.id } }) + "\n");
        onProgress(2, `Сохранён снимок: ${metadata.name || metadata.id}`);
        await new Promise((resolve) => setTimeout(resolve, 0));
      } else {
        await write(JSON.stringify({ type: "snapshot-start", value: { ...metadata, devices: [], invalid: [] } }) + "\n");
        await write(JSON.stringify({ type: "snapshot-end", value: { id: metadata.id } }) + "\n");
      }
    }
    if (data.currentResultStreamer) {
      await data.currentResultStreamer(async (kind, rows) => {
        await writeRows(write, kind === "invalid" ? "invalid" : "device", Array.isArray(rows) ? rows : [], onProgress, completed, total);
      });
    } else {
      await writeRows(write, "device", data.devices, onProgress, completed, total);
      await writeRows(write, "invalid", data.invalid, onProgress, completed, total);
    }
    await writeRows(write, "movement", data.movements, onProgress, completed, total);
    onProgress(100, `Файловая база сохранена: ${data.deviceCount.toLocaleString("ru-RU")} устройств`);
    return { savedAt, counts: headerFor(data, savedAt).counts };
  }

  async function write(handle, payload, onProgress = () => {}) {
    if (!handle?.createWritable) throw new Error("Браузер не разрешил запись в файл базы");
    if (!(await requestPermission(handle, "readwrite"))) throw new Error("Нет разрешения на запись в файл базы");
    const writable = await handle.createWritable({ keepExistingData: false });
    try {
      const result = await writeToSink((chunk) => writable.write(chunk), payload, onProgress);
      await writable.close();
      return result;
    } catch (error) {
      await writable.abort?.().catch(() => {});
      throw error;
    }
  }

  async function createBlob(payload, onProgress = () => {}) {
    const chunks = [];
    await writeToSink(async (chunk) => { chunks.push(chunk); }, payload, onProgress);
    return new Blob(chunks, { type: "application/x-mac-analyzer-db" });
  }

  async function readLines(file, onLine, onProgress) {
    if (!file || file.size > maximumDatabaseBytes) throw new Error("Файл базы слишком большой или недоступен");
    const reader = file.stream().getReader();
    const decoder = new TextDecoder("utf-8");
    let pending = "";
    let processed = 0;
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      processed += chunk.value.byteLength;
      pending += decoder.decode(chunk.value, { stream: true });
      let newline;
      while ((newline = pending.indexOf("\n")) >= 0) {
        const line = pending.slice(0, newline).trim();
        pending = pending.slice(newline + 1);
        if (line) await onLine(line);
      }
      onProgress(file.size ? Math.min(99, Math.round(processed / file.size * 100)) : 50, `Прочитано: ${(processed / 1024 / 1024).toFixed(1)} МБ`);
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    pending += decoder.decode();
    if (pending.trim()) await onLine(pending.trim());
  }

  async function readFile(file, onProgress = () => {}, options = {}) {
    let header = null;
    let state = null;
    const devices = [];
    const invalid = [];
    const movements = [];
    const snapshots = [];
    const currentSnapshots = [];
    let activeSnapshot = null;
    await readLines(file, async (line) => {
      const record = JSON.parse(line);
      if (!header) {
        if (record.format !== format || Number(record.version) !== version) throw new Error("Это не файл базы MAC Analyzer или версия не поддерживается");
        header = record;
        return;
      }
      if (record.type === "state") state = record.value;
      else if (record.type === "snapshot-current") {
        const metadata = { ...(record.value || {}), devices: [], invalid: [], browserStored: true, backendStored: false, currentReference: true };
        currentSnapshots.push(metadata);
        snapshots.push(metadata);
      }
      else if (record.type === "snapshot-start") activeSnapshot = { ...(record.value || {}), devices: [], invalid: [] };
      else if (record.type === "snapshot-device" && activeSnapshot) activeSnapshot.devices.push(record.value);
      else if (record.type === "snapshot-invalid" && activeSnapshot) activeSnapshot.invalid.push(record.value);
      else if (record.type === "snapshot-end" && activeSnapshot) {
        const metadata = { ...activeSnapshot, devices: [], invalid: [], deviceCount: Number(activeSnapshot.deviceCount || activeSnapshot.devices.length), invalidCount: activeSnapshot.invalid.length, browserStored: true, backendStored: false };
        if (typeof options.onSnapshot === "function") await options.onSnapshot(activeSnapshot);
        snapshots.push(metadata);
        activeSnapshot = null;
      }
      else if (record.type === "device") devices.push(record.value);
      else if (record.type === "invalid") invalid.push(record.value);
      else if (record.type === "movement") movements.push(record.value);
    }, onProgress);
    if (!header || !state) throw new Error("Файл базы повреждён: отсутствует заголовок или состояние");
    const counts = header.counts || {};
    if (Number(counts.devices || 0) !== devices.length) throw new Error("Файл базы повреждён: количество устройств не совпадает");
    if (Number(counts.snapshots || 0) !== snapshots.length) throw new Error("Файл базы повреждён: количество снимков не совпадает");
    if (typeof options.onSnapshot === "function") {
      for (const metadata of currentSnapshots) {
        await options.onSnapshot({ ...metadata, devices, invalid });
      }
    }
    onProgress(100, `Восстановлено устройств: ${devices.length.toLocaleString("ru-RU")}`);
    return { header, state, devices, invalid, movements, snapshots };
  }

  async function read(handle, onProgress = () => {}, options = {}) {
    if (!handle?.getFile) throw new Error("Файл базы недоступен");
    if ((await permission(handle, "read")) !== "granted") throw new Error("Нет разрешения на чтение файла базы");
    return readFile(await handle.getFile(), onProgress, options);
  }

  async function readHeader(handle) {
    if (!handle?.getFile) return null;
    const file = await handle.getFile();
    if (!file?.size) return null;
    const prefix = await file.slice(0, Math.min(file.size, 64 * 1024)).text();
    const firstLine = prefix.split("\n", 1)[0].trim();
    if (!firstLine) return null;
    const header = JSON.parse(firstLine);
    if (header.format !== format || Number(header.version) !== version) throw new Error("Это не файл базы MAC Analyzer или версия не поддерживается");
    return header;
  }

  window.MacAnalyzerPortableDatabase = Object.freeze({
    format,
    version,
    supportsNativePicker: () => "showOpenFilePicker" in window && "showSaveFilePicker" in window,
    saveHandle,
    loadHandle,
    permission,
    requestPermission,
    chooseOpenHandle,
    chooseSaveHandle,
    write,
    createBlob,
    read,
    readFile,
    readHeader,
  });
  document.documentElement.dataset.portableDatabase = "ready";
})();

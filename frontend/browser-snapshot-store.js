(() => {
  "use strict";

  const databaseName = "mac-analyzer-browser-storage-v1";
  const databaseVersion = 6;
  const workspaceStore = "workspaces";
  const snapshotStore = "snapshots";
  const snapshotChunkStore = "snapshotChunks";
  const sourceFileStore = "sourceFiles";
  const enrichmentRowStore = "enrichmentRows";
  const deviceHistoryStore = "deviceHistory";
  const snapshotChunkRows = 1_000;

  function openDatabase() {
    return new Promise((resolve, reject) => {
      if (!("indexedDB" in window)) return reject(new Error("IndexedDB недоступна"));
      const request = indexedDB.open(databaseName, databaseVersion);
      request.onupgradeneeded = () => {
        const database = request.result;
        if (!database.objectStoreNames.contains(workspaceStore)) {
          database.createObjectStore(workspaceStore, { keyPath: "id" });
        }
        if (!database.objectStoreNames.contains(snapshotStore)) {
          database.createObjectStore(snapshotStore, { keyPath: "id" });
        }
        if (!database.objectStoreNames.contains(snapshotChunkStore)) {
          const chunks = database.createObjectStore(snapshotChunkStore, { keyPath: "key" });
          chunks.createIndex("snapshotId", "snapshotId", { unique: false });
        }
        if (!database.objectStoreNames.contains(sourceFileStore)) {
          database.createObjectStore(sourceFileStore, { keyPath: "id" });
        }
        if (!database.objectStoreNames.contains(enrichmentRowStore)) {
          const rows = database.createObjectStore(enrichmentRowStore, { keyPath: "key" });
          rows.createIndex("jobId", "jobId", { unique: false });
        }
        if (!database.objectStoreNames.contains(deviceHistoryStore)) {
          database.createObjectStore(deviceHistoryStore, { keyPath: "mac" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Не удалось открыть IndexedDB"));
    });
  }

  async function transaction(storeName, mode, action) {
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(storeName, mode);
      const store = current.objectStore(storeName);
      let result;
      try {
        result = action(store);
      } catch (error) {
        database.close();
        reject(error);
        return;
      }
      current.oncomplete = () => {
        database.close();
        resolve(result);
      };
      current.onerror = () => {
        const error = current.error;
        database.close();
        reject(error || new Error("Ошибка IndexedDB"));
      };
      current.onabort = current.onerror;
    });
  }

  function* chunkRows(rows, size = snapshotChunkRows) {
    const source = Array.isArray(rows) ? rows : [];
    const safeSize = Math.max(1, Number(size) || snapshotChunkRows);
    for (let offset = 0, index = 0; offset < source.length; offset += safeSize, index += 1) {
      yield { index, rows: source.slice(offset, offset + safeSize) };
    }
  }

  async function removeSnapshot(id) {
    const snapshotId = String(id || "");
    if (!snapshotId) return false;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction([snapshotStore, snapshotChunkStore], "readwrite");
      current.objectStore(snapshotStore).delete(snapshotId);
      const chunks = current.objectStore(snapshotChunkStore).index("snapshotId").openCursor(IDBKeyRange.only(snapshotId));
      chunks.onsuccess = () => {
        const cursor = chunks.result;
        if (!cursor) return;
        cursor.delete();
        cursor.continue();
      };
      chunks.onerror = () => reject(chunks.error || new Error("Не удалось удалить части локального снимка"));
      current.oncomplete = () => { database.close(); resolve(true); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Ошибка удаления локального снимка")); };
      current.onabort = current.onerror;
    });
  }

  async function save(snapshot, onProgress = () => {}) {
    if (!snapshot?.id) throw new Error("Снимок не содержит id");
    const snapshotId = String(snapshot.id);
    const devices = Array.isArray(snapshot.devices) ? snapshot.devices : [];
    const invalid = Array.isArray(snapshot.invalid) ? snapshot.invalid : [];
    const deviceChunks = Math.ceil(devices.length / snapshotChunkRows);
    const invalidChunks = Math.ceil(invalid.length / snapshotChunkRows);
    const metadata = {
      ...snapshot,
      id: snapshotId,
      devices: [],
      invalid: [],
      chunked: true,
      complete: false,
      chunkSize: snapshotChunkRows,
      deviceChunks,
      invalidChunks,
      deviceCount: Number(snapshot.deviceCount ?? devices.length),
      invalidCount: Number(snapshot.invalidCount ?? invalid.length),
    };
    await removeSnapshot(snapshotId);
    await transaction(snapshotStore, "readwrite", (store) => store.put(metadata));
    try {
      let completed = 0;
      const total = Math.max(1, deviceChunks + invalidChunks);
      for (const chunk of chunkRows(devices)) {
        await transaction(snapshotChunkStore, "readwrite", (store) => store.put({
          key: `${snapshotId}:device:${String(chunk.index).padStart(8, "0")}`,
          snapshotId,
          kind: "device",
          index: chunk.index,
          rows: chunk.rows,
        }));
        completed += 1;
        onProgress(Math.round(completed / total * 100), completed, total);
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
      for (const chunk of chunkRows(invalid)) {
        await transaction(snapshotChunkStore, "readwrite", (store) => store.put({
          key: `${snapshotId}:invalid:${String(chunk.index).padStart(8, "0")}`,
          snapshotId,
          kind: "invalid",
          index: chunk.index,
          rows: chunk.rows,
        }));
        completed += 1;
        onProgress(Math.round(completed / total * 100), completed, total);
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
      metadata.complete = true;
      await transaction(snapshotStore, "readwrite", (store) => store.put(metadata));
      onProgress(100, total, total);
      return metadata;
    } catch (error) {
      await removeSnapshot(snapshotId).catch(() => false);
      throw error;
    }
  }

  async function beginStreamedSnapshot(snapshot) {
    if (!snapshot?.id) throw new Error("Снимок не содержит id");
    const metadata = {
      ...snapshot,
      id: String(snapshot.id),
      devices: [],
      invalid: [],
      chunked: true,
      complete: false,
      chunkSize: snapshotChunkRows,
      deviceChunks: 0,
      invalidChunks: 0,
      deviceCount: 0,
      invalidCount: 0,
      browserStored: true,
      backendStored: false,
    };
    await removeSnapshot(metadata.id);
    await transaction(snapshotStore, "readwrite", (store) => store.put(metadata));
    return metadata;
  }

  async function appendStreamedSnapshotChunk(id, kind, index, rows) {
    const snapshotId = String(id || "");
    const rowKind = kind === "invalid" ? "invalid" : "device";
    const values = Array.isArray(rows) ? rows : [];
    if (!snapshotId || !values.length) return false;
    await transaction(snapshotChunkStore, "readwrite", (store) => store.put({
      key: `${snapshotId}:${rowKind}:${String(Math.max(0, Number(index) || 0)).padStart(8, "0")}`,
      snapshotId,
      kind: rowKind,
      index: Math.max(0, Number(index) || 0),
      rows: values,
    }));
    return true;
  }

  async function finishStreamedSnapshot(id, counts = {}) {
    const snapshotId = String(id || "");
    const metadata = await loadSnapshotMetadata(snapshotId);
    if (!metadata) throw new Error("Потоковый снимок не найден");
    const complete = {
      ...metadata,
      complete: true,
      deviceChunks: Math.max(0, Number(counts.deviceChunks || 0)),
      invalidChunks: Math.max(0, Number(counts.invalidChunks || 0)),
      deviceCount: Math.max(0, Number(counts.deviceCount || 0)),
      invalidCount: Math.max(0, Number(counts.invalidCount || 0)),
    };
    await transaction(snapshotStore, "readwrite", (store) => store.put(complete));
    return complete;
  }

  async function loadSnapshotMetadata(id) {
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(snapshotStore, "readonly");
      const request = current.objectStore(snapshotStore).get(String(id || ""));
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error || new Error("Не удалось прочитать локальный снимок"));
      current.oncomplete = () => database.close();
      current.onerror = () => {
        database.close();
        reject(current.error || new Error("Ошибка чтения IndexedDB"));
      };
    });
  }

  async function loadSnapshotChunkRecord(key) {
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(snapshotChunkStore, "readonly");
      const request = current.objectStore(snapshotChunkStore).get(key);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error || new Error("Не удалось прочитать части локального снимка"));
      current.oncomplete = () => database.close();
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Ошибка чтения частей IndexedDB")); };
    });
  }

  async function streamSnapshot(id, onChunk = async () => {}) {
    const metadata = await loadSnapshotMetadata(id);
    if (!metadata) return null;
    if (!metadata.chunked) {
      if (Array.isArray(metadata.devices) && metadata.devices.length) await onChunk("device", metadata.devices, 0);
      if (Array.isArray(metadata.invalid) && metadata.invalid.length) await onChunk("invalid", metadata.invalid, 0);
      return { ...metadata, devices: [], invalid: [] };
    }
    if (!metadata.complete) throw new Error("Локальный снимок записан не полностью");
    for (const [kind, count] of [["device", metadata.deviceChunks], ["invalid", metadata.invalidChunks]]) {
      for (let index = 0; index < Number(count || 0); index += 1) {
        const key = `${metadata.id}:${kind}:${String(index).padStart(8, "0")}`;
        const record = await loadSnapshotChunkRecord(key);
        if (!record) throw new Error(`Отсутствует часть локального снимка: ${key}`);
        const rows = Array.isArray(record.rows) ? record.rows : [];
        await onChunk(kind, rows, index);
        rows.length = 0;
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
    }
    return { ...metadata, devices: [], invalid: [] };
  }

  async function transformChunkRows(rows, transform, context = {}) {
    let changed = 0;
    const source = Array.isArray(rows) ? rows : [];
    const rowContext = { ...context, rowIndex: 0 };
    for (let index = 0; index < source.length; index += 1) {
      rowContext.rowIndex = index;
      if (await transform(source[index], rowContext)) changed += 1;
    }
    return changed;
  }

  async function copySnapshotWithTransform(sourceId, targetSnapshot, transform, onProgress = () => {}) {
    const sourceSnapshotId = String(sourceId || "");
    const targetSnapshotId = String(targetSnapshot?.id || "");
    if (!sourceSnapshotId || !targetSnapshotId) throw new Error("Для производного снимка нужны исходный и новый id");
    if (sourceSnapshotId === targetSnapshotId) throw new Error("Производный снимок должен иметь новый id");
    if (typeof transform !== "function") throw new Error("Преобразование снимка не задано");
    const source = await loadSnapshotMetadata(sourceSnapshotId);
    if (!source) throw new Error("Исходный локальный снимок не найден");
    if (source.chunked && !source.complete) throw new Error("Исходный локальный снимок записан не полностью");
    const totalChunks = Math.max(1, Number(source.deviceChunks || 0) + Number(source.invalidChunks || 0));
    await beginStreamedSnapshot({
      ...source,
      ...targetSnapshot,
      id: targetSnapshotId,
      signature: targetSnapshot.signature || "",
      derivedFrom: sourceSnapshotId,
      devices: [],
      invalid: [],
    });
    let changed = 0;
    let processed = 0;
    let deviceChunks = 0;
    let invalidChunks = 0;
    let deviceCount = 0;
    let invalidCount = 0;
    try {
      await streamSnapshot(sourceSnapshotId, async (kind, rows, index) => {
        if (kind === "device") {
          changed += await transformChunkRows(rows, transform, { kind, chunkIndex: index });
          deviceCount += rows.length;
          deviceChunks += 1;
        } else {
          invalidCount += rows.length;
          invalidChunks += 1;
        }
        await appendStreamedSnapshotChunk(targetSnapshotId, kind, index, rows);
        processed += 1;
        onProgress(Math.min(99, Math.round(processed / totalChunks * 100)), processed, totalChunks);
      });
      const metadata = await finishStreamedSnapshot(targetSnapshotId, {
        deviceChunks,
        invalidChunks,
        deviceCount,
        invalidCount,
      });
      onProgress(100, totalChunks, totalChunks);
      return { metadata, changed, processed: deviceCount };
    } catch (error) {
      await removeSnapshot(targetSnapshotId).catch(() => false);
      throw error;
    }
  }

  async function load(id) {
    const devices = [];
    const invalid = [];
    const metadata = await streamSnapshot(id, async (kind, rows) => {
      const target = kind === "invalid" ? invalid : devices;
      target.push(...rows);
    });
    return metadata ? { ...metadata, devices, invalid } : null;
  }

  function normalizedMac(value) {
    return String(value || "").toUpperCase().replace(/[^0-9A-F]/g, "").slice(0, 12);
  }

  async function findDevice(id, mac) {
    const snapshotId = String(id || "");
    const targetMac = normalizedMac(mac);
    if (!snapshotId || !targetMac) return null;
    const metadata = await loadSnapshotMetadata(snapshotId);
    if (!metadata) return null;
    if (!metadata.chunked) {
      return (metadata.devices || []).find((device) => (
        normalizedMac(device?.mac || device?.macFormatted || device?.mac_formatted) === targetMac
      )) || null;
    }
    if (!metadata.complete) throw new Error("Локальный снимок записан не полностью");
    for (let index = 0; index < Number(metadata.deviceChunks || 0); index += 1) {
      const key = `${snapshotId}:device:${String(index).padStart(8, "0")}`;
      const record = await loadSnapshotChunkRecord(key);
      if (!record) throw new Error(`Отсутствует часть локального снимка: ${key}`);
      const match = (record.rows || []).find((device) => (
        normalizedMac(device?.mac || device?.macFormatted || device?.mac_formatted) === targetMac
      ));
      if (match) return match;
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    return null;
  }

  async function clearEnrichment(jobId) {
    const id = String(jobId || "");
    if (!id) return false;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(enrichmentRowStore, "readwrite");
      const request = current.objectStore(enrichmentRowStore).index("jobId").openCursor(IDBKeyRange.only(id));
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        cursor.delete();
        cursor.continue();
      };
      request.onerror = () => reject(request.error || new Error("Unable to clear temporary enrichment rows"));
      current.oncomplete = () => { database.close(); resolve(true); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Temporary enrichment cleanup failed")); };
      current.onabort = current.onerror;
    });
  }

  async function pruneEnrichmentRows(maxAgeMs = 12 * 60 * 60 * 1000) {
    const cutoff = Date.now() - Math.max(60_000, Number(maxAgeMs) || 0);
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(enrichmentRowStore, "readwrite");
      const request = current.objectStore(enrichmentRowStore).openCursor();
      let removed = 0;
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        const updatedAt = Number(cursor.value?.updatedAt || 0);
        if (!updatedAt || updatedAt < cutoff) {
          cursor.delete();
          removed += 1;
        }
        cursor.continue();
      };
      request.onerror = () => reject(request.error || new Error("Unable to prune temporary enrichment rows"));
      current.oncomplete = () => { database.close(); resolve(removed); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Temporary enrichment prune failed")); };
      current.onabort = current.onerror;
    });
  }

  async function mergeEnrichmentRows(jobId, devices, options = {}) {
    const id = String(jobId || "");
    const rows = Array.isArray(devices) ? devices : [];
    const allowNew = options.allowNew !== false;
    if (!id || !rows.length) return 0;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(enrichmentRowStore, "readwrite");
      const store = current.objectStore(enrichmentRowStore);
      let written = 0;
      for (const device of rows) {
        const mac = String(device?.mac || "");
        if (!mac) continue;
        const key = `${id}:${mac}`;
        const request = store.get(key);
        request.onsuccess = () => {
          const previous = request.result?.device;
          if (!previous && !allowNew) return;
          const merged = previous ? { ...previous } : {};
          for (const [field, value] of Object.entries(device)) {
            if (value !== "" && value !== undefined) merged[field] = value;
          }
          store.put({ key, jobId: id, mac, device: merged, updatedAt: Date.now() });
          written += 1;
        };
        request.onerror = () => current.abort();
      }
      current.oncomplete = () => { database.close(); resolve(written); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Temporary enrichment merge failed")); };
      current.onabort = current.onerror;
    });
  }

  async function readEnrichmentPage(jobId, afterKey = "", limit = snapshotChunkRows) {
    const id = String(jobId || "");
    const prefix = `${id}:`;
    const upper = `${prefix}\uffff`;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const rows = [];
      let lastKey = "";
      const current = database.transaction(enrichmentRowStore, "readonly");
      const store = current.objectStore(enrichmentRowStore);
      const range = afterKey
        ? IDBKeyRange.bound(String(afterKey), upper, true, false)
        : IDBKeyRange.bound(prefix, upper, false, false);
      const request = store.openCursor(range);
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor || rows.length >= limit) return;
        rows.push(cursor.value?.device || {});
        lastKey = String(cursor.key);
        if (rows.length < limit) cursor.continue();
      };
      request.onerror = () => reject(request.error || new Error("Temporary enrichment read failed"));
      current.oncomplete = () => { database.close(); resolve({ rows, lastKey }); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Temporary enrichment read failed")); };
    });
  }

  async function streamEnrichmentRows(jobId, onChunk = async () => {}, chunkSize = snapshotChunkRows) {
    let afterKey = "";
    let count = 0;
    while (true) {
      const page = await readEnrichmentPage(jobId, afterKey, chunkSize);
      if (!page.rows.length) break;
      await onChunk(page.rows, count);
      count += page.rows.length;
      afterKey = page.lastKey;
      page.rows.length = 0;
      await new Promise((resolve) => setTimeout(resolve, 0));
      if (!afterKey) break;
    }
    return count;
  }

  async function countEnrichmentRows(jobId) {
    const id = String(jobId || "");
    if (!id) return 0;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(enrichmentRowStore, "readonly");
      const request = current.objectStore(enrichmentRowStore).index("jobId").count(IDBKeyRange.only(id));
      let count = 0;
      request.onsuccess = () => { count = Number(request.result || 0); };
      request.onerror = () => reject(request.error || new Error("Temporary enrichment count failed"));
      current.oncomplete = () => { database.close(); resolve(count); };
      current.onerror = () => {
        const error = current.error;
        database.close();
        reject(error || new Error("Temporary enrichment count failed"));
      };
    });
  }

  async function transformEnrichmentRows(jobId, transform) {
    let afterKey = "";
    let changed = 0;
    while (true) {
      const page = await readEnrichmentPage(jobId, afterKey, snapshotChunkRows);
      if (!page.rows.length) break;
      for (const device of page.rows) {
        if (await transform(device)) changed += 1;
      }
      await mergeEnrichmentRows(jobId, page.rows, { allowNew: true });
      afterKey = page.lastKey;
      page.rows.length = 0;
      await new Promise((resolve) => setTimeout(resolve, 0));
      if (!afterKey) break;
    }
    return changed;
  }

  const historyFields = ["vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort"];

  function normalizedHistoryValue(field, value) {
    const text = String(value ?? "").trim();
    if (field === "vendor" && ["unknown", "не определено"].includes(text.toLowerCase())) return "";
    return text;
  }

  async function mergeDeviceHistoryRows(rows, source = "browser-history") {
    const devices = Array.isArray(rows) ? rows : [];
    if (!devices.length) return 0;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(deviceHistoryStore, "readwrite");
      const store = current.objectStore(deviceHistoryStore);
      let updated = 0;
      for (const device of devices) {
        const mac = String(device?.mac || device?.macFormatted || "").toUpperCase().replace(/[^0-9A-F]/g, "");
        if (mac.length !== 12) continue;
        const request = store.get(mac);
        request.onsuccess = () => {
          const previous = request.result || { mac };
          const next = { ...previous, mac };
          let changed = !request.result;
          for (const field of historyFields) {
            const value = normalizedHistoryValue(field, device[field]);
            if (value && value !== next[field]) { next[field] = value; changed = true; }
          }
          if (changed) {
            next.source = String(source || device.source || "browser-history");
            next.updatedAt = new Date().toISOString();
            store.put(next);
            updated += 1;
          }
        };
        request.onerror = () => reject(request.error || new Error("Unable to read device history"));
      }
      current.oncomplete = () => { database.close(); resolve(updated); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Device history write failed")); };
      current.onabort = current.onerror;
    });
  }

  async function enrichDevicesFromHistory(rows) {
    const devices = Array.isArray(rows) ? rows : [];
    if (!devices.length) return 0;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(deviceHistoryStore, "readonly");
      const store = current.objectStore(deviceHistoryStore);
      let changed = 0;
      for (const device of devices) {
        const mac = String(device?.mac || device?.macFormatted || "").toUpperCase().replace(/[^0-9A-F]/g, "");
        if (mac.length !== 12) continue;
        const request = store.get(mac);
        request.onsuccess = () => {
          const history = request.result;
          if (!history) return;
          let rowChanged = false;
          for (const field of historyFields) {
            const currentValue = normalizedHistoryValue(field, device[field]);
            const historicalValue = normalizedHistoryValue(field, history[field]);
            if (!currentValue && historicalValue) { device[field] = historicalValue; rowChanged = true; }
          }
          if (rowChanged) changed += 1;
        };
        request.onerror = () => reject(request.error || new Error("Unable to read device history"));
      }
      current.oncomplete = () => { database.close(); resolve(changed); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Device history enrichment failed")); };
    });
  }

  async function enrichEnrichmentRowsFromHistory(jobId) {
    let afterKey = "";
    let changed = 0;
    while (true) {
      const page = await readEnrichmentPage(jobId, afterKey, snapshotChunkRows);
      if (!page.rows.length) break;
      const pageChanges = await enrichDevicesFromHistory(page.rows);
      if (pageChanges) await mergeEnrichmentRows(jobId, page.rows, { allowNew: true });
      changed += pageChanges;
      afterKey = page.lastKey;
      page.rows.length = 0;
      await new Promise((resolve) => setTimeout(resolve, 0));
      if (!afterKey) break;
    }
    return changed;
  }

  async function backfillDeviceHistory(snapshotIds = []) {
    const ids = [...new Set((snapshotIds || []).map(String).filter(Boolean))];
    if (!ids.length) return 0;
    const signature = ids.join("|");
    const database = await openDatabase();
    const previousSignature = await new Promise((resolve, reject) => {
      const current = database.transaction(deviceHistoryStore, "readonly");
      const request = current.objectStore(deviceHistoryStore).get("__snapshot_backfill__");
      request.onsuccess = () => resolve(String(request.result?.signature || ""));
      request.onerror = () => reject(request.error || new Error("Unable to read history migration state"));
      current.oncomplete = () => database.close();
      current.onerror = () => { database.close(); reject(current.error || new Error("History migration read failed")); };
    });
    if (previousSignature === signature) return 0;
    let merged = 0;
    for (const snapshotId of ids) {
      await streamSnapshot(snapshotId, async (kind, rows) => {
        if (kind === "device") merged += await mergeDeviceHistoryRows(rows, `snapshot:${snapshotId}`);
      });
    }
    await transaction(deviceHistoryStore, "readwrite", (store) => store.put({
      mac: "__snapshot_backfill__",
      signature,
      updatedAt: new Date().toISOString(),
    }));
    return merged;
  }

  async function saveEnrichmentSnapshot(jobId, snapshot, invalid = [], onProgress = () => {}) {
    if (!snapshot?.id) throw new Error("Snapshot id is required");
    const snapshotId = String(snapshot.id);
    await removeSnapshot(snapshotId);
    const metadata = {
      ...snapshot,
      id: snapshotId,
      devices: [],
      invalid: [],
      chunked: true,
      complete: false,
      chunkSize: snapshotChunkRows,
      deviceChunks: 0,
      invalidChunks: Math.ceil((Array.isArray(invalid) ? invalid.length : 0) / snapshotChunkRows),
      deviceCount: 0,
      invalidCount: Array.isArray(invalid) ? invalid.length : 0,
    };
    await transaction(snapshotStore, "readwrite", (store) => store.put(metadata));
    try {
      let chunkIndex = 0;
      await streamEnrichmentRows(jobId, async (rows, completedRows) => {
        await transaction(snapshotChunkStore, "readwrite", (store) => store.put({
          key: `${snapshotId}:device:${String(chunkIndex).padStart(8, "0")}`,
          snapshotId,
          kind: "device",
          index: chunkIndex,
          rows,
        }));
        chunkIndex += 1;
        metadata.deviceCount = completedRows + rows.length;
        onProgress(metadata.deviceCount);
      });
      metadata.deviceChunks = chunkIndex;
      for (const chunk of chunkRows(invalid)) {
        await transaction(snapshotChunkStore, "readwrite", (store) => store.put({
          key: `${snapshotId}:invalid:${String(chunk.index).padStart(8, "0")}`,
          snapshotId,
          kind: "invalid",
          index: chunk.index,
          rows: chunk.rows,
        }));
      }
      metadata.complete = true;
      await transaction(snapshotStore, "readwrite", (store) => store.put(metadata));
      return metadata;
    } catch (error) {
      await removeSnapshot(snapshotId).catch(() => false);
      throw error;
    }
  }

  function createPageCollector(options = {}) {
    const query = String(options.query || "").trim().toLowerCase();
    const vendor = String(options.vendor || "");
    const validity = String(options.validity || "").toLowerCase();
    const limit = Math.max(25, Math.min(Number(options.limit || options.pageSize || 250), 1000));
    const offset = Math.max(0, Number(options.offset || 0));
    const items = [];
    const vendors = new Set();
    let total = 0;
    let validCount = 0;
    let invalidCount = 0;
    let deviceCount = 0;
    let knownCount = 0;
    const matches = (row) => {
      if (vendor && String(row?.vendor || "") !== vendor) return false;
      if (!query) return true;
      return Object.values(row || {}).join(" ").toLowerCase().includes(query);
    };
    return {
      accept(kind, rows) {
        const isValid = kind !== "invalid";
        if (isValid && validity === "invalid") return;
        if (!isValid && validity === "valid") return;
        for (const row of Array.isArray(rows) ? rows : []) {
          if (isValid) {
            deviceCount += 1;
            const currentVendor = String(row?.vendor || "");
            if (currentVendor) vendors.add(currentVendor);
            if (currentVendor && currentVendor !== "Unknown" && currentVendor !== "Не определено") knownCount += 1;
          }
          if (!matches(row)) continue;
          if (isValid) validCount += 1;
          else invalidCount += 1;
          if (total >= offset && items.length < limit) items.push(row);
          total += 1;
        }
      },
      result() {
        const pages = Math.max(1, Math.ceil(total / limit));
        const page = Math.max(1, Math.min(Math.floor(offset / limit) + 1, pages));
        return {
          items,
          vendors: Array.from(vendors).sort(),
          pagination: { total, page, pages, limit, offset },
          summary: {
            devices: deviceCount,
            valid: validCount,
            invalid: invalidCount,
            vendors: vendors.size,
            knownPercent: deviceCount ? Math.round(knownCount / deviceCount * 100) : 0,
          },
        };
      },
    };
  }

  async function page(id, options = {}) {
    const collector = createPageCollector(options);
    const metadata = await streamSnapshot(id, async (kind, rows) => {
      collector.accept(kind, rows);
    });
    return metadata ? { ...collector.result(), metadata } : null;
  }

  function tallyRows(map, value) {
    const key = String(value || "").trim() || "Unknown";
    map.set(key, (map.get(key) || 0) + 1);
  }

  function tallyRowsBounded(map, value, limit = 20000) {
    const key = String(value || "").trim();
    if (!key) return;
    if (map.has(key)) {
      map.set(key, map.get(key) + 1);
      return;
    }
    if (map.size < limit) map.set(key, 1);
  }

  function rankedRows(map, limit = 50) {
    return Array.from(map.entries())
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
      .slice(0, Math.max(1, Number(limit) || 50))
      .map(([label, value]) => ({ label, value }));
  }

  function matchesDashboardFilter(device, options = {}) {
    const vendor = String(device?.vendor || "").trim();
    const room = String(device?.room || "").trim();
    const vendorFilter = String(options.vendor || "").trim();
    const roomFilter = String(options.room || "").trim();
    const query = String(options.query || "").trim().toLowerCase();
    const queryMac = query.replace(/[^0-9a-f]/gi, "").toUpperCase();
    const deviceMac = String(device?.mac || device?.macFormatted || device?.mac_formatted || "").replace(/[^0-9a-f]/gi, "").toUpperCase();
    const searchable = [device?.mac, device?.macFormatted, device?.vendor, device?.model, device?.ip, device?.address,
      device?.room, device?.smartroomId, device?.smartroom_id, device?.switchIp, device?.switch_ip,
      device?.switchPort, device?.switch_port, device?.source].map((value) => String(value || "")).join(" ").toLowerCase();
    const unknown = new Set(["", "unknown", "не определено", "неизвестный вендор", "unknown vendor"]);
    return (!vendorFilter || vendor === vendorFilter)
      && (!roomFilter || room === roomFilter)
      && (options.showUnknown !== false || !unknown.has(vendor.toLowerCase()))
      && (!query || searchable.includes(query) || (queryMac && deviceMac.includes(queryMac)));
  }

  async function aggregate(id, options = {}) {
    const vendors = new Map();
    const models = new Map();
    const rooms = new Map();
    const switchRows = new Map();
    const oui3Rows = new Map();
    const oui4Rows = new Map();
    const oui5Rows = new Map();
    const switches = new Set();
    let devices = 0;
    let known = 0;
    let withAddress = 0;
    let withRoom = 0;
    let withIp = 0;
    let withSwitch = 0;
    let withModel = 0;
    let autoVendors = 0;
    let autoModels = 0;
    const unknown = new Set(["", "unknown", "не определено", "неизвестный вендор", "unknown vendor"]);
    const metadata = await streamSnapshot(id, async (kind, rows) => {
      if (kind !== "device") return;
      for (const device of rows) {
        const vendor = String(device?.vendor || "").trim();
        const model = String(device?.model || "").trim();
        const room = String(device?.room || "").trim();
        if (!matchesDashboardFilter(device, options)) continue;
        devices += 1;
        const switchIp = String(device?.switchIp || device?.switch_ip || "").trim();
        const mac = String(device?.mac || device?.macFormatted || device?.mac_formatted || device?.oui || "").replace(/[^0-9a-f]/gi, "").toUpperCase();
        tallyRows(vendors, vendor);
        if (model) tallyRows(models, model);
        if (room) tallyRows(rooms, room);
        if (switchIp) tallyRowsBounded(switchRows, switchIp);
        if (mac.length >= 6) tallyRowsBounded(oui3Rows, mac.slice(0, 6));
        if (mac.length >= 8) tallyRowsBounded(oui4Rows, mac.slice(0, 8));
        if (mac.length >= 10) tallyRowsBounded(oui5Rows, mac.slice(0, 10));
        if (!unknown.has(vendor.toLowerCase())) known += 1;
        if (String(device?.address || "").trim()) withAddress += 1;
        if (room) withRoom += 1;
        if (String(device?.ip || "").trim()) withIp += 1;
        if (switchIp) { withSwitch += 1; switches.add(switchIp); }
        if (model) withModel += 1;
        if (!unknown.has(vendor.toLowerCase()) && (device?.vendorMatchedPrefix || !device?.vendorSource || !["file", "history"].includes(device.vendorSource))) autoVendors += 1;
        if (model && (device?.modelMatchedPrefix || !device?.modelSource || !["file", "history"].includes(device.modelSource))) autoModels += 1;
      }
    });
    if (!metadata) return null;
    const limit = Math.max(8, Math.min(200, Number(options.limit || 50)));
    return {
      snapshotId: String(id || ""),
      devices,
      invalid: Number(metadata.invalidCount || 0),
      uniqueMacs: devices,
      known,
      unknown: Math.max(0, devices - known),
      knownPercent: devices ? Math.round(known / devices * 100) : 0,
      uniqueVendors: Array.from(vendors.keys()).filter((value) => !unknown.has(value.toLowerCase())).length,
      uniqueModels: models.size,
      uniqueRooms: rooms.size,
      uniqueSwitches: switches.size,
      withAddress,
      withRoom,
      withIp,
      withSwitch,
      withModel,
      autoVendors,
      autoModels,
      uniqueOui3: oui3Rows.size,
      uniqueOui4: oui4Rows.size,
      uniqueOui5: oui5Rows.size,
      vendors: rankedRows(vendors, limit),
      models: rankedRows(models, limit),
      rooms: rankedRows(rooms, limit),
      switches: rankedRows(switchRows, limit),
      oui3: rankedRows(oui3Rows, limit),
      oui4: rankedRows(oui4Rows, limit),
      oui5: rankedRows(oui5Rows, limit),
      metadata: { ...metadata, devices: [], invalid: [] },
    };
  }

  async function aggregateSeries(snapshots, options = {}) {
    const rows = Array.isArray(snapshots) ? snapshots : [];
    const jobId = `snapshot-union-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const series = [];
    await clearEnrichment(jobId).catch(() => false);
    try {
      for (let index = 0; index < rows.length; index += 1) {
        const source = typeof rows[index] === "string" ? { id: rows[index] } : (rows[index] || {});
        const snapshotId = String(source.id || source.snapshotId || "");
        if (!snapshotId) continue;
        let currentCount = 0;
        const metadata = await streamSnapshot(snapshotId, async (kind, chunk) => {
          if (kind !== "device") return;
          const compact = chunk.filter((device) => matchesDashboardFilter(device, options)).map(compactComparisonDevice).filter((device) => device.mac).map((device) => ({ mac: device.mac }));
          currentCount += compact.length;
          await mergeEnrichmentRows(jobId, compact, { allowNew: true });
          compact.length = 0;
        });
        if (!metadata) continue;
        series.push({
          id: snapshotId,
          name: String(source.name || metadata.name || snapshotId),
          date: String(source.date || source.fileCreatedAt || source.createdAt || metadata.createdAt || metadata.savedAt || ""),
          count: currentCount,
          delta: currentCount - Number(series.at(-1)?.count || 0),
        });
        if (typeof options.onProgress === "function") options.onProgress(index + 1, rows.length);
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
      return {
        uniqueAcrossUploads: await countEnrichmentRows(jobId),
        latestCount: Number(series.at(-1)?.count || 0),
        series,
      };
    } finally {
      await clearEnrichment(jobId).catch(() => false);
    }
  }

  function compactComparisonDevice(device) {
    return {
      mac: String(device?.mac || device?.macFormatted || "").toUpperCase().replace(/[^0-9A-F]/g, ""),
      vendor: String(device?.vendor || ""),
      model: String(device?.model || ""),
      ip: String(device?.ip || ""),
      address: String(device?.address || ""),
      room: String(device?.room || ""),
      smartroomId: String(device?.smartroomId || device?.smartroom_id || ""),
      switchIp: String(device?.switchIp || device?.switch_ip || ""),
      switchPort: String(device?.switchPort || device?.switch_port || ""),
    };
  }

  async function compareCurrentChunk(jobId, rows, result, limit) {
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(enrichmentRowStore, "readwrite");
      const store = current.objectStore(enrichmentRowStore);
      for (const source of rows) {
        const device = compactComparisonDevice(source);
        if (!device.mac) continue;
        const key = `${jobId}:${device.mac}`;
        const request = store.get(key);
        request.onsuccess = () => {
          const previous = request.result?.device;
          if (!previous) {
            result.added += 1;
            result.changedDevices += 1;
            tallyRows(result.changedVendors, device.vendor);
            if (result.changes.length < limit) result.changes.push({
              mac: device.mac, type: "added", field: "device", before: "", after: device.vendor || "Устройство",
              beforeDevice: null, afterDevice: { ...device },
            });
            return;
          }
          let modified = false;
          const criticalMove = String(previous.switchIp || "") !== String(device.switchIp || "")
            && String(previous.ip || "") === String(device.ip || "")
            && String(previous.room || "") === String(device.room || "");
          for (const field of result.fields) {
            const before = String(previous[field] || "");
            const after = String(device[field] || "");
            if (before === after) continue;
            modified = true;
            result.modifiedFields += 1;
            result.fieldCounts.set(field, (result.fieldCounts.get(field) || 0) + 1);
            if (result.changes.length < limit) result.changes.push({
              mac: device.mac, type: "modified", field, before, after,
              beforeDevice: { ...previous }, afterDevice: { ...device },
            });
          }
          if (modified) {
            result.modifiedDevices += 1;
            result.changedDevices += 1;
            if (criticalMove) result.critical += 1;
            tallyRows(result.changedVendors, device.vendor);
          } else {
            result.unchanged += 1;
            tallyRows(result.unchangedVendors, device.vendor);
          }
          store.delete(key);
        };
        request.onerror = () => current.abort();
      }
      current.oncomplete = () => { database.close(); resolve(true); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Snapshot comparison failed")); };
      current.onabort = current.onerror;
    });
  }

  async function collectRemovedComparisonRows(jobId, result, limit) {
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(enrichmentRowStore, "readonly");
      const request = current.objectStore(enrichmentRowStore).index("jobId").openCursor(IDBKeyRange.only(jobId));
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        const previous = cursor.value?.device || {};
        result.removed += 1;
        tallyRows(result.missingVendors, previous.vendor);
        if (result.changes.length < limit) result.changes.push({
          mac: previous.mac || cursor.value?.mac || "", type: "removed", field: "device",
          before: previous.vendor || "Устройство", after: "", beforeDevice: { ...previous }, afterDevice: null,
        });
        cursor.continue();
      };
      request.onerror = () => reject(request.error || new Error("Snapshot comparison scan failed"));
      current.oncomplete = () => { database.close(); resolve(true); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Snapshot comparison scan failed")); };
    });
  }

  async function compareSnapshots(baselineId, comparisonId, options = {}) {
    const jobId = `snapshot-compare-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const limit = Math.max(100, Math.min(20000, Number(options.limit || 5000)));
    const result = {
      fields: ["vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort"],
      added: 0, removed: 0, modifiedDevices: 0, modifiedFields: 0, changedDevices: 0, unchanged: 0, critical: 0,
      changes: [], fieldCounts: new Map(), changedVendors: new Map(), unchangedVendors: new Map(), missingVendors: new Map(),
    };
    await clearEnrichment(jobId).catch(() => false);
    try {
      const baseline = await streamSnapshot(baselineId, async (kind, rows) => {
        if (kind !== "device") return;
        const compact = rows.map(compactComparisonDevice).filter((device) => device.mac);
        await mergeEnrichmentRows(jobId, compact, { allowNew: true });
        compact.length = 0;
      });
      if (!baseline) return null;
      const comparison = await streamSnapshot(comparisonId, async (kind, rows) => {
        if (kind === "device") await compareCurrentChunk(jobId, rows, result, limit);
      });
      if (!comparison) return null;
      await collectRemovedComparisonRows(jobId, result, limit);
      const changedAt = String(comparison.createdAt || comparison.savedAt || new Date().toISOString());
      result.changes.forEach((item) => { item.changedAt = changedAt; item.source = "snapshot"; });
      return {
        baselineSnapshotId: String(baselineId || ""),
        comparisonSnapshotId: String(comparisonId || ""),
        changedAt,
        summary: {
          added: result.added,
          removed: result.removed,
          modified: result.modifiedDevices,
          modifiedFields: result.modifiedFields,
          modifiedDevices: result.modifiedDevices,
          changedDevices: result.changedDevices,
          unchanged: result.unchanged,
          critical: result.critical,
          total: result.added + result.removed + result.modifiedDevices,
        },
        changes: result.changes.map((item) => ({ ...item })),
        fieldCounts: rankedRows(result.fieldCounts, 20),
        changedVendors: rankedRows(result.changedVendors, 20),
        unchangedVendors: rankedRows(result.unchangedVendors, 20),
        missingVendors: rankedRows(result.missingVendors, 20),
      };
    } finally {
      await clearEnrichment(jobId).catch(() => false);
      result.changes.length = 0;
      result.fieldCounts.clear();
      result.changedVendors.clear();
      result.unchangedVendors.clear();
      result.missingVendors.clear();
    }
  }

  async function prune(keepIds = []) {
    const keep = new Set(keepIds.map(String));
    const database = await openDatabase();
    const removeIds = await new Promise((resolve, reject) => {
      const ids = [];
      const current = database.transaction(snapshotStore, "readonly");
      const store = current.objectStore(snapshotStore);
      const request = store.openCursor();
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        if (!keep.has(String(cursor.key))) ids.push(String(cursor.key));
        cursor.continue();
      };
      request.onerror = () => reject(request.error || new Error("Не удалось очистить локальные снимки"));
      current.oncomplete = () => {
        database.close();
        resolve(ids);
      };
      current.onerror = () => {
        database.close();
        reject(current.error || new Error("Ошибка очистки IndexedDB"));
      };
    });
    for (const id of removeIds) {
      await removeSnapshot(id);
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    return true;
  }

  function removeLegacyWorkspace() {
    return transaction(workspaceStore, "readwrite", (store) => store.delete("main")).catch(() => false);
  }

  function saveSourceFile(id, file) {
    if (!id || !(file instanceof Blob)) return Promise.reject(new Error("Invalid source file"));
    return transaction(sourceFileStore, "readwrite", (store) => store.put({
      id: String(id),
      file,
      name: String(file.name || "source-file"),
      type: String(file.type || "application/octet-stream"),
      lastModified: Number(file.lastModified || 0),
      size: Number(file.size || 0),
      savedAt: new Date().toISOString(),
    }));
  }

  async function loadSourceFile(id) {
    if (!id) return null;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(sourceFileStore, "readonly");
      const request = current.objectStore(sourceFileStore).get(String(id));
      request.onsuccess = () => {
        const record = request.result;
        if (!record?.file) return resolve(null);
        if (record.file instanceof File) return resolve(record.file);
        resolve(new File([record.file], record.name || "source-file", {
          type: record.type || record.file.type || "application/octet-stream",
          lastModified: Number(record.lastModified || 0),
        }));
      };
      request.onerror = () => reject(request.error || new Error("Unable to read stored source file"));
      current.oncomplete = () => database.close();
      current.onerror = () => {
        database.close();
        reject(current.error || new Error("IndexedDB source file read error"));
      };
    });
  }

  function removeSourceFile(id) {
    if (!id) return Promise.resolve(false);
    return transaction(sourceFileStore, "readwrite", (store) => store.delete(String(id)));
  }

  async function pruneSourceFiles(keepIds = []) {
    const keep = new Set(keepIds.map(String));
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(sourceFileStore, "readwrite");
      const store = current.objectStore(sourceFileStore);
      const request = store.openCursor();
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        if (!keep.has(String(cursor.key))) cursor.delete();
        cursor.continue();
      };
      request.onerror = () => reject(request.error || new Error("Unable to prune stored source files"));
      current.oncomplete = () => {
        database.close();
        resolve(true);
      };
      current.onerror = () => {
        database.close();
        reject(current.error || new Error("IndexedDB source file prune error"));
      };
    });
  }

  window.MacAnalyzerBrowserSnapshots = Object.freeze({
    save,
    beginStreamedSnapshot,
    appendStreamedSnapshotChunk,
    finishStreamedSnapshot,
    load,
    prune,
    removeSnapshot,
    chunkRows,
    streamSnapshot,
    transformChunkRows,
    copySnapshotWithTransform,
    findDevice,
    page,
    aggregate,
    aggregateSeries,
    matchesDashboardFilter,
    compareSnapshots,
    createPageCollector,
    clearEnrichment,
    pruneEnrichmentRows,
    mergeEnrichmentRows,
    streamEnrichmentRows,
    transformEnrichmentRows,
    enrichEnrichmentRowsFromHistory,
    enrichDevicesFromHistory,
    mergeDeviceHistoryRows,
    backfillDeviceHistory,
    saveEnrichmentSnapshot,
    snapshotChunkRows,
    removeLegacyWorkspace,
    saveSourceFile,
    loadSourceFile,
    removeSourceFile,
    pruneSourceFiles,
  });
  document.documentElement.dataset.browserSnapshotStore = "ready";
})();

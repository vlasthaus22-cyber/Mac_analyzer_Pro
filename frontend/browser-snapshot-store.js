(() => {
  "use strict";

  const databaseName = "mac-analyzer-browser-storage-v1";
  const databaseVersion = 5;
  const workspaceStore = "workspaces";
  const snapshotStore = "snapshots";
  const snapshotChunkStore = "snapshotChunks";
  const sourceFileStore = "sourceFiles";
  const enrichmentRowStore = "enrichmentRows";
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

  async function load(id) {
    const devices = [];
    const invalid = [];
    const metadata = await streamSnapshot(id, async (kind, rows) => {
      const target = kind === "invalid" ? invalid : devices;
      target.push(...rows);
    });
    return metadata ? { ...metadata, devices, invalid } : null;
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
          store.put({ key, jobId: id, mac, device: merged });
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
    load,
    prune,
    removeSnapshot,
    chunkRows,
    streamSnapshot,
    page,
    createPageCollector,
    clearEnrichment,
    mergeEnrichmentRows,
    streamEnrichmentRows,
    transformEnrichmentRows,
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

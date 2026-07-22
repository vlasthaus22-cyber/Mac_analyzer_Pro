(() => {
  "use strict";

  const databaseName = "mac-analyzer-browser-storage-v1";
  const databaseVersion = 4;
  const workspaceStore = "workspaces";
  const snapshotStore = "snapshots";
  const snapshotChunkStore = "snapshotChunks";
  const sourceFileStore = "sourceFiles";
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
    snapshotChunkRows,
    removeLegacyWorkspace,
    saveSourceFile,
    loadSourceFile,
    removeSourceFile,
    pruneSourceFiles,
  });
  document.documentElement.dataset.browserSnapshotStore = "ready";
})();

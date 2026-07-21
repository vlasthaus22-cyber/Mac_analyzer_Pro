(() => {
  "use strict";

  const databaseName = "mac-analyzer-browser-storage-v1";
  const databaseVersion = 3;
  const workspaceStore = "workspaces";
  const snapshotStore = "snapshots";
  const sourceFileStore = "sourceFiles";

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

  function save(snapshot) {
    if (!snapshot?.id) return Promise.reject(new Error("Снимок не содержит id"));
    return transaction(snapshotStore, "readwrite", (store) => store.put(snapshot));
  }

  async function load(id) {
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

  async function prune(keepIds = []) {
    const keep = new Set(keepIds.map(String));
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(snapshotStore, "readwrite");
      const store = current.objectStore(snapshotStore);
      const request = store.openCursor();
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        if (!keep.has(String(cursor.key))) cursor.delete();
        cursor.continue();
      };
      request.onerror = () => reject(request.error || new Error("Не удалось очистить локальные снимки"));
      current.oncomplete = () => {
        database.close();
        resolve(true);
      };
      current.onerror = () => {
        database.close();
        reject(current.error || new Error("Ошибка очистки IndexedDB"));
      };
    });
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
    removeLegacyWorkspace,
    saveSourceFile,
    loadSourceFile,
    removeSourceFile,
    pruneSourceFiles,
  });
  document.documentElement.dataset.browserSnapshotStore = "ready";
})();

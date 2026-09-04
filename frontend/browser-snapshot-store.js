(() => {
  "use strict";

  const databaseName = "mac-analyzer-browser-storage-v1";
  const databaseVersion = 11;
  const workspaceStore = "workspaces";
  const snapshotStore = "snapshots";
  const snapshotChunkStore = "snapshotChunks";
  const sourceFileStore = "sourceFiles";
  const enrichmentRowStore = "enrichmentRows";
  const deviceHistoryStore = "deviceHistory";
  const resolvedDeviceStore = "DeviceInventory";
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
        let enrichmentRows;
        if (!database.objectStoreNames.contains(enrichmentRowStore)) {
          enrichmentRows = database.createObjectStore(enrichmentRowStore, { keyPath: "key" });
          enrichmentRows.createIndex("jobId", "jobId", { unique: false });
        } else enrichmentRows = request.transaction.objectStore(enrichmentRowStore);
        if (!enrichmentRows.indexNames.contains("aliases")) enrichmentRows.createIndex("aliases", "aliases", { unique: false, multiEntry: true });
        if (!database.objectStoreNames.contains(deviceHistoryStore)) {
          database.createObjectStore(deviceHistoryStore, { keyPath: "mac" });
        }
        let resolvedInventory;
        if (!database.objectStoreNames.contains(resolvedDeviceStore)) {
          const resolved = database.createObjectStore(resolvedDeviceStore, { keyPath: "internalDeviceId" });
          resolved.createIndex("by_mac", "mac", { unique: false });
          resolved.createIndex("by_serial", "serialKey", { unique: false });
          resolved.createIndex("by_device_id", "deviceIdKey", { unique: false });
          resolved.createIndex("by_updated_at", "updatedAt", { unique: false });
          resolvedInventory = resolved;
        } else resolvedInventory = request.transaction.objectStore(resolvedDeviceStore);
        for (const [name, keyPath] of [
          ["by_mac", "mac"],
          ["by_serial", "serialKey"],
          ["by_device_id", "deviceIdKey"],
          ["by_switch", "switchIp"],
          ["by_updated_at", "updatedAt"],
        ]) {
          if (!resolvedInventory.indexNames.contains(name)) resolvedInventory.createIndex(name, keyPath, { unique: false });
        }
        const legacyInventory = request.transaction.objectStore(deviceHistoryStore);
        legacyInventory.openCursor().onsuccess = (event) => {
          const cursor = event.target.result;
          if (!cursor) return;
          const item = cursor.value || {}, mac = String(item.mac || "").toUpperCase().replace(/[^0-9A-F]/g, "");
          if (mac.length === 12) resolvedInventory.put({ ...item, mac, internalDeviceId: item.internalDeviceId || `dev-mac-${mac}` });
          cursor.continue();
        };
        const equipment = database.objectStoreNames.contains("Equipment")
          ? request.transaction.objectStore("Equipment")
          : database.createObjectStore("Equipment", { keyPath: "id" });
        for (const [name, keyPath] of [["smartroom_id", "smartroom_id"], ["mac", "mac"], ["ip_switch", "ip_switch"], ["by_smartroom", "smartroom_id"], ["by_mac", "mac"], ["by_switch", "ip_switch"]]) {
          if (!equipment.indexNames.contains(name)) equipment.createIndex(name, keyPath, { unique: false });
        }
        const history = database.objectStoreNames.contains("History")
          ? request.transaction.objectStore("History")
          : database.createObjectStore("History", { keyPath: "id", autoIncrement: true });
        for (const [name, keyPath] of [["entity_type", "entity_type"], ["timestamp", "timestamp"], ["by_timestamp", "timestamp"], ["by_mac", "mac"], ["by_smartroom", "smartroom_id"]]) {
          if (!history.indexNames.contains(name)) history.createIndex(name, keyPath, { unique: false });
        }
        if (!database.objectStoreNames.contains("DDIO_Snapshot")) {
          database.createObjectStore("DDIO_Snapshot", { keyPath: "date" });
        }
        if (!database.objectStoreNames.contains("KnownModels")) {
          const known = database.createObjectStore("KnownModels", { keyPath: "mac" });
          known.createIndex("by_vendor", "vendor", { unique: false });
          known.createIndex("by_updated_at", "updatedAt", { unique: false });
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
      const quotaExceeded = error?.name === "QuotaExceededError";
      const failure = new Error(quotaExceeded
        ? "Недостаточно места в хранилище браузера для нового Final. Последний успешный Final сохранён без изменений. Освободите место или выгрузите базу и повторите обогащение."
        : `Не удалось атомарно сохранить новый Final: ${error?.message || error || "неизвестная ошибка"}`);
      failure.name = quotaExceeded ? "QuotaExceededError" : "EnrichmentSnapshotSaveError";
      failure.code = quotaExceeded ? "INDEXEDDB_QUOTA_EXCEEDED" : "FINAL_SNAPSHOT_SAVE_FAILED";
      failure.stage = "database-save";
      failure.cause = error;
      throw failure;
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

  async function replaceSnapshotFromTemporary(snapshotId, temporaryId, mutation = {}) {
    const targetId = String(snapshotId || "");
    const sourceId = String(temporaryId || "");
    if (!targetId || !sourceId || targetId === sourceId) throw new Error("Для замены снимка нужны разные исходный и временный id");
    const [original, transformed] = await Promise.all([
      loadSnapshotMetadata(targetId),
      loadSnapshotMetadata(sourceId),
    ]);
    if (!original || !transformed?.complete) throw new Error("Не удалось подготовить безопасное обновление текущего снимка");
    const metadata = {
      ...transformed,
      ...original,
      id: targetId,
      devices: [],
      invalid: [],
      chunked: true,
      complete: true,
      deviceChunks: Number(transformed.deviceChunks || 0),
      invalidChunks: Number(transformed.invalidChunks || 0),
      deviceCount: Number(transformed.deviceCount || 0),
      invalidCount: Number(transformed.invalidCount || 0),
      signature: "",
      updatedAt: new Date().toISOString(),
      lastMutationName: String(mutation.name || ""),
      lastMutationSource: String(mutation.source || ""),
    };
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction([snapshotStore, snapshotChunkStore], "readwrite");
      const snapshots = current.objectStore(snapshotStore);
      const chunks = current.objectStore(snapshotChunkStore);
      const chunkIndex = chunks.index("snapshotId");
      const removeCurrent = chunkIndex.openCursor(IDBKeyRange.only(targetId));
      const fail = (error) => reject(error || new Error("Не удалось заменить текущий локальный снимок"));
      removeCurrent.onerror = () => fail(removeCurrent.error);
      removeCurrent.onsuccess = () => {
        const cursor = removeCurrent.result;
        if (cursor) {
          cursor.delete();
          cursor.continue();
          return;
        }
        const moveTemporary = chunkIndex.openCursor(IDBKeyRange.only(sourceId));
        moveTemporary.onerror = () => fail(moveTemporary.error);
        moveTemporary.onsuccess = () => {
          const temporaryCursor = moveTemporary.result;
          if (!temporaryCursor) return;
          const record = temporaryCursor.value;
          chunks.put({
            ...record,
            key: `${targetId}:${record.kind}:${String(record.index).padStart(8, "0")}`,
            snapshotId: targetId,
          });
          temporaryCursor.delete();
          temporaryCursor.continue();
        };
      };
      snapshots.put(metadata);
      snapshots.delete(sourceId);
      current.oncomplete = () => { database.close(); resolve(metadata); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Ошибка обновления текущего локального снимка")); };
      current.onabort = current.onerror;
    });
  }

  async function updateSnapshotWithTransform(id, transform, onProgress = () => {}, mutation = {}) {
    const snapshotId = String(id || "");
    if (!snapshotId) throw new Error("Текущий локальный снимок не выбран");
    const temporaryId = `${snapshotId}:update:${Date.now().toString(36)}:${Math.random().toString(36).slice(2)}`;
    try {
      const result = await copySnapshotWithTransform(snapshotId, {
        id: temporaryId,
        updatedAt: new Date().toISOString(),
      }, transform, onProgress);
      if (!result.changed) {
        await removeSnapshot(temporaryId);
        return { ...result, metadata: await loadSnapshotMetadata(snapshotId), updated: false };
      }
      const metadata = await replaceSnapshotFromTemporary(snapshotId, temporaryId, mutation);
      return { ...result, metadata, updated: true };
    } catch (error) {
      await removeSnapshot(temporaryId).catch(() => false);
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
    const preferExisting = options.preferExisting === true;
    const stats = options.stats && typeof options.stats === "object" ? options.stats : null;
    if (!id || !rows.length) return 0;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(enrichmentRowStore, "readwrite");
      const store = current.objectStore(enrichmentRowStore);
      const identityApi = window.MacAnalyzerDeviceIdentity;
      const aliasesFor = (device) => (identityApi?.candidates?.(device) || []).map((alias) => `${id}:${alias}`);
      let written = 0, position = 0;
      const processNext = () => {
        if (position >= rows.length) return;
        const device = rows[position++], mac = String(device?.mac || ""), aliases = aliasesFor(device);
        const fallbackIdentity = String(device?.storageIdentity || device?.internalDeviceId || device?.identityKey || mac);
        if (!aliases.length && !fallbackIdentity) { if (stats) stats.invalidIdentity = (stats.invalidIdentity || 0) + 1; processNext(); return; }
        const matches = new Map(), aliasIndex = store.index("aliases");
        let pending = aliases.length;
        const finishLookup = () => {
          if (pending > 0) return;
          const records = Array.from(matches.values());
          const resolutionIndex = identityApi?.buildIndex?.(records.map((record) => record.device));
          const resolution = resolutionIndex ? identityApi.resolve(device, resolutionIndex) : { status: records.length > 1 ? "conflict" : records.length ? "matched" : "unmatched", match: records[0]?.device };
          let record = records.find((item) => item.device === resolution.match);
          if (resolution.status === "conflict") { record = null; if (stats) stats.conflicts = (stats.conflicts || 0) + 1; }
          const previous = record?.device;
          if (!previous && !allowNew) { if (stats) stats.skipped = (stats.skipped || 0) + 1; processNext(); return; }
          const merged = previous ? { ...previous } : {};
          const fieldSources = { ...(merged.fieldSources || {}) };
          const sourceFiles = Array.from(new Set([...(merged.sourceFiles || []), merged.source, device.source].filter(Boolean)));
          const sourceRoles = Array.from(new Set([...(merged.sourceRoles || []), device.sourceRole].filter(Boolean)));
          const conflicts = [...(merged.conflicts || [])];
          for (const [field, value] of Object.entries(device)) {
            if (["fieldSources", "sourceFiles", "sourceRoles", "conflicts"].includes(field)) continue;
            const hasExisting = merged[field] !== "" && merged[field] !== undefined && merged[field] !== null;
            if (hasExisting && value !== "" && value !== undefined && String(merged[field]) !== String(value)
              && ["vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort", "hostname", "serialNumber", "deviceId"].includes(field)) {
              const conflict = { field, selected: preferExisting ? merged[field] : value, selectedSource: preferExisting ? fieldSources[field] : device.source, alternative: preferExisting ? value : merged[field], alternativeSource: preferExisting ? device.source : fieldSources[field] };
              if (!conflicts.some((item) => JSON.stringify(item) === JSON.stringify(conflict))) conflicts.push(conflict);
            }
            if (value !== "" && value !== undefined && (!preferExisting || !hasExisting)) merged[field] = value;
            if (value !== "" && value !== undefined && (!preferExisting || !hasExisting) && device.source) fieldSources[field] = device.source;
          }
          merged.fieldSources = fieldSources;
          merged.sourceFiles = sourceFiles;
          merged.sourceRoles = sourceRoles;
          merged.conflicts = conflicts;
          merged.hasConflict = conflicts.length > 0;
          if (resolution.status === "conflict") {
            conflicts.push({ field: "identity", selected: device.internalDeviceId || fallbackIdentity, selectedSource: device.source || "", alternative: "Неоднозначное сопоставление потоковых записей", alternativeSource: "identity-resolver", confidence: "Conflict", evidence: resolution.evidence || [] });
            merged.conflicts = conflicts;
            merged.hasConflict = true;
            merged.matchConfidence = "Conflict";
          }
          merged.source = sourceFiles.length === 1 ? sourceFiles[0] : sourceFiles.join(" + ");
          let finalIdentity = String(device.internalDeviceId || fallbackIdentity);
          if (resolution.status === "conflict") {
            const conflictCandidate = { ...device };
            delete conflictCandidate.internalDeviceId;
            delete conflictCandidate.internal_device_id;
            finalIdentity = identityApi?.stableId?.(
              conflictCandidate,
              `primary-conflict:${device.source || ""}:${device.row || ""}`,
            ) || `${fallbackIdentity}:row:${device.row || position}`;
            merged.internalDeviceId = finalIdentity;
          }
          const storageIdentity = String(record?.key || `${id}:${finalIdentity}`);
          store.put({ key: storageIdentity, jobId: id, mac: String(merged.mac || mac), aliases: aliasesFor(merged), device: merged, updatedAt: Date.now() });
          if (stats) stats[previous ? "matched" : "created"] = (stats[previous ? "matched" : "created"] || 0) + 1;
          written += 1;
          processNext();
        };
        if (!pending) { finishLookup(); return; }
        for (const alias of aliases) {
          const request = aliasIndex.getAll(IDBKeyRange.only(alias));
          request.onsuccess = () => { for (const item of request.result || []) matches.set(item.key, item); pending -= 1; finishLookup(); };
          request.onerror = () => current.abort();
        }
      };
      processNext();
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

  const historyFields = [
    "vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort",
    "hostname", "serialNumber", "deviceId", "deviceName",
  ];

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
      const current = database.transaction([deviceHistoryStore, resolvedDeviceStore], "readwrite");
      const store = current.objectStore(deviceHistoryStore);
      const inventory = current.objectStore(resolvedDeviceStore);
      let updated = 0;
      const mergeKnown = (previous, device, identity) => {
        const next = { ...(previous || {}), internalDeviceId: identity };
        let changed = !previous;
        const mac = String(device?.mac || device?.macFormatted || "").toUpperCase().replace(/[^0-9A-F]/g, "");
        if (mac.length === 12 && next.mac !== mac) { next.mac = mac; changed = true; }
        for (const field of historyFields) {
          const value = field === "switchIp"
            ? normalizedSwitchIp(device[field] || device.switch_ip)
            : normalizedHistoryValue(field, device[field]);
          if (value && value !== next[field]) { next[field] = value; changed = true; }
        }
        if (changed) {
          next.source = String(source || device.source || "browser-history");
          next.updatedAt = new Date().toISOString();
          next.firstSeen ||= next.updatedAt;
          next.seenCount = Number(next.seenCount || 0) + 1;
        }
        next.serialKey = String(next.serialNumber || "").trim().toLowerCase();
        next.deviceIdKey = String(next.deviceId || "").trim().toLowerCase();
        return { next, changed, mac };
      };
      for (const device of devices) {
        const mac = String(device?.mac || device?.macFormatted || "").toUpperCase().replace(/[^0-9A-F]/g, "");
        const identity = String(device?.internalDeviceId || (mac.length === 12 ? `dev-mac-${mac}` : ""));
        if (!identity) continue;
        const inventoryRequest = inventory.get(identity);
        inventoryRequest.onsuccess = () => {
          const merged = mergeKnown(inventoryRequest.result, device, identity);
          if (merged.changed) { inventory.put(merged.next); updated += 1; }
        };
        inventoryRequest.onerror = () => reject(inventoryRequest.error || new Error("Unable to read device inventory"));
        if (mac.length === 12) {
          const legacyRequest = store.get(mac);
          legacyRequest.onsuccess = () => {
            const merged = mergeKnown(legacyRequest.result, device, identity);
            if (merged.changed) store.put({ ...merged.next, mac });
          };
          legacyRequest.onerror = () => reject(legacyRequest.error || new Error("Unable to read MAC history"));
        }
      }
      current.oncomplete = () => { database.close(); resolve(updated); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Device history write failed")); };
      current.onabort = current.onerror;
    });
  }

  async function readDeviceHistoryPage(afterMac = "", limit = snapshotChunkRows) {
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(resolvedDeviceStore, "readonly");
      const store = current.objectStore(resolvedDeviceStore);
      const range = afterMac ? IDBKeyRange.lowerBound(afterMac, true) : undefined;
      const request = store.openCursor(range);
      const rows = [];
      let lastMac = "";
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor || rows.length >= Math.max(1, Number(limit) || snapshotChunkRows)) return;
        lastMac = String(cursor.key || "");
        rows.push(cursor.value);
        cursor.continue();
      };
      request.onerror = () => reject(request.error || new Error("Unable to read device inventory"));
      current.oncomplete = () => { database.close(); resolve({ rows, lastMac }); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Device inventory read failed")); };
    });
  }

  async function streamDeviceHistory(onChunk, chunkSize = snapshotChunkRows) {
    let afterMac = "";
    let total = 0;
    while (true) {
      const page = await readDeviceHistoryPage(afterMac, chunkSize);
      if (!page.rows.length) break;
      await onChunk(page.rows, total);
      total += page.rows.length;
      afterMac = page.lastMac;
      if (!afterMac || page.rows.length < Math.max(1, Number(chunkSize) || snapshotChunkRows)) break;
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    return total;
  }

  async function countDeviceHistory() {
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(resolvedDeviceStore, "readonly");
      const store = current.objectStore(resolvedDeviceStore);
      const countRequest = store.count();
      let count = 0;
      countRequest.onsuccess = () => { count = Number(countRequest.result || 0); };
      current.oncomplete = () => { database.close(); resolve(Math.max(0, count)); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Device inventory count failed")); };
    });
  }

  function normalizedSwitchIp(value) {
    const match = String(value || "").trim().match(/\d{1,3}(?:\.\d{1,3}){3}/);
    if (!match) return "";
    const parts = match[0].split(".").map(Number);
    return parts.every((part) => part >= 0 && part <= 255) ? parts.join(".") : "";
  }

  async function switchAddressConsensus(switchIps, options = {}) {
    const targets = [...new Set((switchIps || []).map(normalizedSwitchIp).filter(Boolean))];
    const minimumConfidence = Math.max(0, Math.min(1, Number(options.minimumConfidence ?? 0.90)));
    const minimumObservations = Math.max(1, Number(options.minimumObservations ?? 2));
    const mappings = new Map();
    if (!targets.length) return mappings;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(resolvedDeviceStore, "readonly");
      const index = current.objectStore(resolvedDeviceStore).index("by_switch");
      const targetSet = new Set(targets), countsByIp = new Map();
      const finishSwitch = (switchIp, counts) => {
        const ranked = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
        const total = ranked.reduce((sum, item) => sum + item[1], 0);
        if (!ranked.length || total < minimumObservations) return;
        const [address, matchingObservations] = ranked[0];
        const confidence = matchingObservations / total;
        const tied = ranked.length > 1 && ranked[1][1] === matchingObservations;
        if (!tied && confidence + Number.EPSILON >= minimumConfidence) mappings.set(switchIp, {
          address,
          confidence,
          observations: total,
          matchingObservations,
          alternatives: ranked.slice(1).map((item) => item[0]),
          source: "indexeddb-switch-consensus",
        });
      };
      if (targets.length > 32) {
        // One ordered scan is substantially faster than opening thousands of
        // individual cursors for a large enrichment run.
        const request = index.openCursor();
        request.onsuccess = () => {
          const cursor = request.result;
          if (!cursor) { for (const [switchIp, counts] of countsByIp) finishSwitch(switchIp, counts); return; }
          const switchIp = normalizedSwitchIp(cursor.key);
          if (targetSet.has(switchIp)) {
            const address = String(cursor.value?.address || "").trim();
            if (address) {
              if (!countsByIp.has(switchIp)) countsByIp.set(switchIp, new Map());
              const counts = countsByIp.get(switchIp);
              counts.set(address, (counts.get(address) || 0) + 1);
            }
          }
          cursor.continue();
        };
        request.onerror = () => current.abort();
      } else {
        let position = 0;
        const processNext = () => {
          if (position >= targets.length) return;
          const switchIp = targets[position++], counts = new Map();
          const request = index.openCursor(IDBKeyRange.only(switchIp));
          request.onsuccess = () => {
            const cursor = request.result;
            if (cursor) {
              const address = String(cursor.value?.address || "").trim();
              if (address) counts.set(address, (counts.get(address) || 0) + 1);
              cursor.continue();
              return;
            }
            finishSwitch(switchIp, counts);
            processNext();
          };
          request.onerror = () => current.abort();
        };
        processNext();
      }
      current.oncomplete = () => { database.close(); resolve(mappings); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Switch address consensus failed")); };
      current.onabort = current.onerror;
    });
  }

  async function switchChangesFromHistory(rows) {
    const devices = Array.isArray(rows) ? rows : [];
    const changes = new Map();
    if (!devices.length) return changes;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(resolvedDeviceStore, "readonly");
      const store = current.objectStore(resolvedDeviceStore);
      for (const device of devices) {
        const mac = String(device?.mac || device?.macFormatted || "").toUpperCase().replace(/[^0-9A-F]/g, "");
        const internalId = String(device?.internalDeviceId || ""), deviceId = String(device?.deviceId || device?.device_id || "").trim().toLowerCase();
        const after = String(device?.switchIp || device?.switch_ip || "").trim();
        if (!after || (!internalId && mac.length !== 12 && !deviceId)) continue;
        const request = internalId ? store.get(internalId) : mac.length === 12 ? store.index("by_mac").getAll(mac) : store.index("by_device_id").getAll(deviceId);
        request.onsuccess = () => {
          const values = Array.isArray(request.result) ? request.result : request.result ? [request.result] : [];
          if (values.length !== 1) return;
          const before = String(values[0]?.switchIp || "").trim(), key = mac.length === 12 ? mac : `device-id:${deviceId}`;
          if (before && before !== after) changes.set(key, { before, after, currentIp: String(device?.ip || "").trim(), deviceId });
        };
        request.onerror = () => reject(request.error || new Error("Unable to compare switch history"));
      }
      current.oncomplete = () => { database.close(); resolve(changes); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Switch history comparison failed")); };
    });
  }

  async function enrichDevicesFromHistory(rows) {
    const devices = Array.isArray(rows) ? rows : [];
    if (!devices.length) return 0;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction([deviceHistoryStore, resolvedDeviceStore], "readonly");
      const store = current.objectStore(deviceHistoryStore);
      const inventory = current.objectStore(resolvedDeviceStore);
      let changed = 0;
      for (const device of devices) {
        const mac = String(device?.mac || device?.macFormatted || "").toUpperCase().replace(/[^0-9A-F]/g, "");
        const internalId = String(device?.internalDeviceId || ""), serialKey = String(device?.serialNumber || device?.serial_number || "").trim().toLowerCase(), deviceIdKey = String(device?.deviceId || device?.device_id || "").trim().toLowerCase();
        const requests = [];
        if (internalId) requests.push(inventory.get(internalId));
        if (mac.length === 12) requests.push(inventory.index("by_mac").getAll(mac));
        if (serialKey) requests.push(inventory.index("by_serial").getAll(serialKey));
        if (deviceIdKey) requests.push(inventory.index("by_device_id").getAll(deviceIdKey));
        if (!requests.length && mac.length === 12) requests.push(store.get(mac));
        if (!requests.length) continue;
        const matches = new Map(); let pending = requests.length;
        const finish = () => {
          pending -= 1;
          if (pending) return;
          if (matches.size !== 1) {
            if (matches.size > 1) { device.hasConflict = true; device.conflicts = [...(device.conflicts || []), { field: "identity", selected: "", alternative: "Неоднозначная локальная история", source: "IndexedDB" }]; }
            return;
          }
          const history = matches.values().next().value;
          let rowChanged = false;
          for (const field of historyFields) {
            const currentValue = normalizedHistoryValue(field, device[field]);
            const historicalValue = normalizedHistoryValue(field, history[field]);
            if (!currentValue && historicalValue) {
              device[field] = historicalValue;
              device.fieldSources = { ...(device.fieldSources || {}), [field]: "previous-final" };
              device.previousFinalMatched = true;
              rowChanged = true;
            }
          }
          if (history.internalDeviceId) device.internalDeviceId = history.internalDeviceId;
          if (rowChanged) changed += 1;
        };
        for (const request of requests) {
          request.onsuccess = () => {
            const values = Array.isArray(request.result) ? request.result : request.result ? [request.result] : [];
            for (const value of values) matches.set(String(value.internalDeviceId || value.mac), value);
            finish();
          };
          request.onerror = () => reject(request.error || new Error("Unable to read device history"));
        }
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

  async function promoteEnrichmentChunk(jobId, snapshotId, chunkIndex) {
    const id = String(jobId || ""), targetId = String(snapshotId || "");
    if (!id || !targetId) return 0;
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction([enrichmentRowStore, snapshotChunkStore], "readwrite");
      const source = current.objectStore(enrichmentRowStore);
      const target = current.objectStore(snapshotChunkStore);
      const request = source.index("jobId").openCursor(IDBKeyRange.only(id));
      const rows = [];
      let finalized = false;
      const finalize = () => {
        if (finalized) return;
        finalized = true;
        if (!rows.length) return;
        const write = target.put({
          key: `${targetId}:device:${String(chunkIndex).padStart(8, "0")}`,
          snapshotId: targetId,
          kind: "device",
          index: chunkIndex,
          rows,
        });
        write.onerror = () => current.abort();
      };
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor || rows.length >= snapshotChunkRows) { finalize(); return; }
        rows.push(cursor.value?.device || {});
        cursor.delete();
        if (rows.length >= snapshotChunkRows) finalize();
        else cursor.continue();
      };
      request.onerror = () => current.abort();
      current.oncomplete = () => { const count = rows.length; database.close(); resolve(count); };
      current.onerror = () => {
        const error = current.error;
        database.close();
        reject(error || new Error("Failed to promote enrichment rows to the final snapshot"));
      };
      current.onabort = current.onerror;
    });
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
      while (true) {
        const promoted = await promoteEnrichmentChunk(jobId, snapshotId, chunkIndex);
        if (!promoted) break;
        chunkIndex += 1;
        metadata.deviceCount += promoted;
        onProgress(metadata.deviceCount);
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
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
      const quotaExceeded = error?.name === "QuotaExceededError";
      const failure = new Error(quotaExceeded
        ? "Недостаточно места в хранилище браузера для нового Final. Последний успешный Final сохранён без изменений. Освободите место или выгрузите базу и повторите обогащение."
        : `Не удалось атомарно сохранить новый Final: ${error?.message || error || "неизвестная ошибка"}`);
      failure.name = quotaExceeded ? "QuotaExceededError" : "EnrichmentSnapshotSaveError";
      failure.code = quotaExceeded ? "INDEXEDDB_QUOTA_EXCEEDED" : "FINAL_SNAPSHOT_SAVE_FAILED";
      failure.stage = "database-save";
      failure.cause = error;
      throw failure;
    }
  }

  function createPageCollector(options = {}) {
    const query = String(options.query || "").trim().toLowerCase();
    const vendor = String(options.vendor || "");
    const validity = String(options.validity || "").toLowerCase();
    const limit = Math.max(25, Math.min(Number(options.limit || options.pageSize || 250), 1000));
    const offset = Math.max(0, Number(options.offset || 0));
    const sortField = String(options.sortField || "");
    const sortDirection = String(options.sortDirection || "").toLowerCase() === "desc" ? "desc" : "asc";
    const sortWindowLimit = 100_000;
    const retainedLimit = Math.min(sortWindowLimit, offset + limit);
    const items = [];
    const vendors = new Set();
    let total = 0;
    let validCount = 0;
    let invalidCount = 0;
    let deviceCount = 0;
    let knownCount = 0;
    let sequence = 0;
    const collator = new Intl.Collator("ru", { numeric: true, sensitivity: "base" });
    const valueForSort = (row) => {
      if (sortField === "macFormatted") return row?.macFormatted || row?.mac || "";
      if (sortField === "oui") return String(row?.oui || row?.mac || row?.macFormatted || "").replace(/[^0-9a-f]/gi, "");
      return row?.[sortField] ?? "";
    };
    const compareEntries = (left, right) => {
      const a = String(valueForSort(left.row) ?? "").trim(), b = String(valueForSort(right.row) ?? "").trim();
      if (!a || !b) return (!a && !b ? 0 : (!a ? 1 : -1)) || left.sequence - right.sequence;
      let compared = collator.compare(a, b);
      if (sortDirection === "desc") compared = -compared;
      return compared || left.sequence - right.sequence;
    };
    const siftWorstUp = (index) => {
      while (index > 0) { const parent = (index - 1) >>> 1; if (compareEntries(items[parent], items[index]) >= 0) break; [items[parent], items[index]] = [items[index], items[parent]]; index = parent; }
    };
    const siftWorstDown = (index) => {
      for (;;) { const left = index * 2 + 1, right = left + 1; if (left >= items.length) break; let worst = left; if (right < items.length && compareEntries(items[right], items[left]) > 0) worst = right; if (compareEntries(items[index], items[worst]) >= 0) break; [items[index], items[worst]] = [items[worst], items[index]]; index = worst; }
    };
    const retainSorted = (row) => {
      const entry = { row, sequence: sequence++ };
      if (items.length < retainedLimit) { items.push(entry); siftWorstUp(items.length - 1); }
      else if (items.length && compareEntries(entry, items[0]) < 0) { items[0] = entry; siftWorstDown(0); }
    };
    const matches = (row) => {
      if (vendor && String(row?.vendor || "") !== vendor) return false;
      if (!query) return true;
      const searchable = [row?.mac, row?.macFormatted, row?.vendor, row?.model, row?.ip, row?.address, row?.room,
        row?.smartroomId, row?.smartroom_id, row?.switchIp, row?.switch_ip, row?.switchPort, row?.switch_port,
        row?.hostname, row?.host_name, row?.serialNumber, row?.serial_number, row?.serial,
        row?.deviceId, row?.device_id, row?.deviceName, row?.device_name, row?.internalDeviceId,
        row?.source, row?.raw, row?.row].map((value) => String(value || "")).join(" ").toLowerCase();
      const queryMac = query.replace(/[^0-9a-f]/gi, ""), rowMac = String(row?.mac || row?.macFormatted || "").replace(/[^0-9a-f]/gi, "").toLowerCase();
      return searchable.includes(query) || (queryMac && rowMac.includes(queryMac));
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
          if (sortField) retainSorted(row);
          else if (total >= offset && items.length < limit) items.push(row);
          total += 1;
        }
      },
      result() {
        const pages = Math.max(1, Math.ceil(total / limit));
        const page = Math.max(1, Math.min(Math.floor(offset / limit) + 1, pages));
        return {
          items: sortField ? items.slice().sort(compareEntries).slice(Math.min(offset, items.length), Math.min(offset + limit, items.length)).map((entry) => entry.row) : items,
          vendors: Array.from(vendors).sort(),
          pagination: { total, page, pages, limit, offset, sortWindowLimit: sortField ? sortWindowLimit : 0 },
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
      device?.switchPort, device?.switch_port, device?.hostname, device?.host_name,
      device?.serialNumber, device?.serial_number, device?.serial, device?.deviceId, device?.device_id,
      device?.deviceName, device?.device_name, device?.internalDeviceId, device?.source]
      .map((value) => String(value || "")).join(" ").toLowerCase();
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
    const roomIdentities = new Set();
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
        const smartroomId = String(device?.smartroomId || device?.smartroom_id || "").trim();
        if (!matchesDashboardFilter(device, options)) continue;
        devices += 1;
        const switchIp = String(device?.switchIp || device?.switch_ip || "").trim();
        const mac = String(device?.mac || device?.macFormatted || device?.mac_formatted || device?.oui || "").replace(/[^0-9a-f]/gi, "").toUpperCase();
        tallyRows(vendors, vendor);
        if (model) tallyRows(models, model);
        if (room) tallyRows(rooms, room);
        if (smartroomId || room) roomIdentities.add(smartroomId || room);
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
      uniqueRooms: roomIdentities.size,
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
          const compact = chunk.filter((device) => matchesDashboardFilter(device, options)).map(compactComparisonDevice).filter((device) => comparisonIdentity(device)).map((device) => ({ storageIdentity: comparisonIdentity(device), internalDeviceId: device.internalDeviceId, mac: device.mac, serialNumber: device.serialNumber, deviceId: device.deviceId }));
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
      internalDeviceId: String(device?.internalDeviceId || device?.internal_device_id || ""),
      mac: String(device?.mac || device?.macFormatted || "").toUpperCase().replace(/[^0-9A-F]/g, ""),
      vendor: String(device?.vendor || ""),
      model: String(device?.model || ""),
      ip: String(device?.ip || ""),
      address: String(device?.address || ""),
      room: String(device?.room || ""),
      smartroomId: String(device?.smartroomId || device?.smartroom_id || ""),
      switchIp: String(device?.switchIp || device?.switch_ip || ""),
      switchPort: String(device?.switchPort || device?.switch_port || ""),
      hostname: String(device?.hostname || device?.host_name || ""),
      serialNumber: String(device?.serialNumber || device?.serial_number || device?.serial || ""),
      deviceId: String(device?.deviceId || device?.device_id || ""),
      deviceName: String(device?.deviceName || device?.device_name || device?.name || ""),
      ipSource: String(device?.ipSource || device?.fieldSources?.ip || ""),
      possibleIps: Array.from(new Set((Array.isArray(device?.possibleIps || device?.Possible_IPs) ? (device.possibleIps || device.Possible_IPs) : String(device?.possibleIps || device?.Possible_IPs || "").split(/[,;\s]+/)).map((value) => String(value || "").trim()).filter(Boolean))),
      hasConflict: Boolean(device?.hasConflict || (device?.conflicts || []).length),
    };
  }

  function comparisonAliases(device) {
    const compact = compactComparisonDevice(device);
    const internalId = compact.internalDeviceId.trim().toLowerCase();
    const mac = compact.mac;
    const serial = compact.serialNumber.trim().toLowerCase();
    const deviceId = compact.deviceId.trim().toLowerCase();
    const hostname = compact.hostname.trim().toLowerCase();
    return Array.from(new Set([
      internalId && `internal-id:${internalId}`,
      mac && `mac:${mac}`,
      serial && `serial:${serial}`,
      deviceId && `device:${deviceId}`,
      hostname && serial && `host-serial:${hostname}|${serial}`,
    ].filter(Boolean)));
  }

  function comparisonIdentity(device) {
    const internalId = String(device?.internalDeviceId || device?.internal_device_id || "").trim().toLowerCase();
    const mac = String(device?.mac || device?.macFormatted || "").toUpperCase().replace(/[^0-9A-F]/g, "");
    const serial = String(device?.serialNumber || device?.serial_number || device?.serial || "").trim().toLowerCase();
    const deviceId = String(device?.deviceId || device?.device_id || "").trim().toLowerCase();
    return internalId ? `internal-id:${internalId}` : mac ? `mac:${mac}` : serial ? `serial:${serial}` : deviceId ? `device:${deviceId}` : "";
  }

  function comparisonStorageKey(jobId, device) {
    const identity = comparisonIdentity(device);
    return identity ? `${String(jobId || "")}:${identity}` : "";
  }

  async function indexComparisonBaselineChunk(jobId, rows) {
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(enrichmentRowStore, "readwrite");
      const store = current.objectStore(enrichmentRowStore);
      let indexed = 0;
      for (const source of rows) {
        const device = compactComparisonDevice(source);
        const key = comparisonStorageKey(jobId, device);
        if (!key) continue;
        const aliases = comparisonAliases(device).map((alias) => `${jobId}:${alias}`);
        store.put({ key, jobId, mac: device.mac, aliases, device, matched: false, updatedAt: Date.now() });
        indexed += 1;
      }
      current.oncomplete = () => { database.close(); resolve(indexed); };
      current.onerror = () => { const error = current.error; database.close(); reject(error || new Error("Snapshot comparison baseline failed")); };
      current.onabort = current.onerror;
    });
  }

  async function compareCurrentChunk(jobId, rows, result, limit) {
    const database = await openDatabase();
    return new Promise((resolve, reject) => {
      const current = database.transaction(enrichmentRowStore, "readwrite");
      const store = current.objectStore(enrichmentRowStore);
      const aliasIndex = store.index("aliases");
      const sources = Array.from(rows || []);
      const recordChange = (source, records) => {
        const device = compactComparisonDevice(source);
        const identity = comparisonIdentity(device);
        if (!identity) return;
        const candidates = Array.from(new Map(records.filter((record) => record && !record.matched).map((record) => [record.key, record])).values());
        if (candidates.length > 1) {
          result.modifiedDevices += 1;
          result.changedDevices += 1;
          result.critical += 1;
          result.modifiedFields += 1;
          result.fieldCounts.set("identityConflict", (result.fieldCounts.get("identityConflict") || 0) + 1);
          tallyRows(result.changedVendors, device.vendor);
          if (result.changes.length < limit) result.changes.push({
            mac: device.mac, type: "modified", field: "identityConflict", before: "Несколько устройств предыдущего Final", after: "Требуется проверка идентификаторов",
            beforeDevice: null, afterDevice: { ...device },
          });
          return;
        }
        const matchedRecord = candidates[0];
        const previous = matchedRecord?.device;
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
          matchedRecord.matched = true;
          store.put(matchedRecord);
          let modified = false;
          const criticalMove = ["mac", "switchIp", "ip"].some((field) => {
            const before = String(previous[field] || "").trim();
            const after = String(device[field] || "").trim();
            return Boolean(before && after && before !== after);
          });
          for (const field of result.fields) {
            const before = String(previous[field] || "");
            const after = String(device[field] || "");
            if (before === after) continue;
            if (before && !after) continue;
            modified = true;
            result.modifiedFields += 1;
            result.fieldCounts.set(field, (result.fieldCounts.get(field) || 0) + 1);
            if (result.changes.length < limit) result.changes.push({
              mac: device.mac, type: "modified", field, before, after,
              beforeDevice: { ...previous }, afterDevice: { ...device },
            });
          }
          if (device.hasConflict) {
            modified = true;
            result.modifiedFields += 1;
            result.fieldCounts.set("identityConflict", (result.fieldCounts.get("identityConflict") || 0) + 1);
            if (result.changes.length < limit) result.changes.push({
              mac: device.mac, type: "modified", field: "identityConflict", before: "", after: "Обнаружен конфликт источников",
              beforeDevice: { ...previous }, afterDevice: { ...device },
            });
          }
          if (modified) {
            result.modifiedDevices += 1;
            result.changedDevices += 1;
            if (criticalMove || device.hasConflict) result.critical += 1;
            tallyRows(result.changedVendors, device.vendor);
          } else {
            result.unchanged += 1;
            tallyRows(result.unchangedVendors, device.vendor);
          }
      };
      const processRow = (rowIndex) => {
        if (rowIndex >= sources.length) return;
        const source = sources[rowIndex];
        const aliases = comparisonAliases(source).map((alias) => `${jobId}:${alias}`);
        if (!aliases.length) {
          processRow(rowIndex + 1);
          return;
        }
        const records = [];
        const readAlias = (aliasIndexNumber) => {
          if (aliasIndexNumber >= aliases.length) {
            recordChange(source, records);
            processRow(rowIndex + 1);
            return;
          }
          const request = aliasIndex.getAll(IDBKeyRange.only(aliases[aliasIndexNumber]));
          request.onsuccess = () => {
            records.push(...(request.result || []));
            readAlias(aliasIndexNumber + 1);
          };
          request.onerror = () => current.abort();
        };
        readAlias(0);
      };
      processRow(0);
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
        if (cursor.value?.matched) {
          cursor.continue();
          return;
        }
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
      fields: ["mac", "vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort", "hostname", "serialNumber", "deviceId", "deviceName"],
      added: 0, removed: 0, modifiedDevices: 0, modifiedFields: 0, changedDevices: 0, unchanged: 0, critical: 0,
      changes: [], fieldCounts: new Map(), changedVendors: new Map(), unchangedVendors: new Map(), missingVendors: new Map(),
    };
    await clearEnrichment(jobId).catch(() => false);
    try {
      const baseline = await streamSnapshot(baselineId, async (kind, rows) => {
        if (kind !== "device") return;
        await indexComparisonBaselineChunk(jobId, rows);
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
    updateSnapshotWithTransform,
    findDevice,
    page,
    aggregate,
    aggregateSeries,
    matchesDashboardFilter,
    comparisonIdentity,
    comparisonAliases,
    comparisonStorageKey,
    compareSnapshots,
    createPageCollector,
    clearEnrichment,
    pruneEnrichmentRows,
    mergeEnrichmentRows,
    countEnrichmentRows,
    streamEnrichmentRows,
    transformEnrichmentRows,
    enrichEnrichmentRowsFromHistory,
    enrichDevicesFromHistory,
    mergeDeviceHistoryRows,
    streamDeviceHistory,
    countDeviceHistory,
    switchAddressConsensus,
    switchChangesFromHistory,
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

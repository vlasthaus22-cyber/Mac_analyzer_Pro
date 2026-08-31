(() => {
  "use strict";

  const databaseName = "mac-analyzer-browser-storage-v1";
  // Keep every module that opens mac-analyzer-browser-storage-v1 on the same
  // schema version. Opening an older version after BrowserSnapshots upgraded
  // the database raises VersionError and breaks Analytics/Smartroom tabs.
  const databaseVersion = 11;
  const equipmentStore = "Equipment";
  const historyStore = "History";
  const ddioStore = "DDIO_Snapshot";
  const knownModelsStore = "KnownModels";
  const knownKey = "mac-analyzer-known-equipment-v1";
  const apiUrlKey = "mac-analyzer-ddio-api-url";
  const arpCache = new Map();

  function openDatabase() {
    return new Promise((resolve, reject) => {
      if (!("indexedDB" in window)) return reject(new Error("IndexedDB недоступна"));
      const request = indexedDB.open(databaseName, databaseVersion);
      request.onupgradeneeded = () => {
        const db = request.result;
        const equipment = db.objectStoreNames.contains(equipmentStore)
          ? request.transaction.objectStore(equipmentStore)
          : db.createObjectStore(equipmentStore, { keyPath: "id" });
        for (const [name, keyPath] of [
          ["smartroom_id", "smartroom_id"],
          ["mac", "mac"],
          ["ip_switch", "ip_switch"],
          ["by_smartroom", "smartroom_id"],
          ["by_mac", "mac"],
          ["by_switch", "ip_switch"],
        ]) {
          if (!equipment.indexNames.contains(name)) equipment.createIndex(name, keyPath, { unique: false });
        }
        const history = db.objectStoreNames.contains(historyStore)
          ? request.transaction.objectStore(historyStore)
          : db.createObjectStore(historyStore, { keyPath: "id", autoIncrement: true });
        for (const [name, keyPath] of [
          ["entity_type", "entity_type"],
          ["timestamp", "timestamp"],
          ["by_timestamp", "timestamp"],
          ["by_mac", "mac"],
          ["by_smartroom", "smartroom_id"],
        ]) {
          if (!history.indexNames.contains(name)) history.createIndex(name, keyPath, { unique: false });
        }
        if (!db.objectStoreNames.contains(ddioStore)) db.createObjectStore(ddioStore, { keyPath: "date" });
        if (!db.objectStoreNames.contains(knownModelsStore)) {
          const known = db.createObjectStore(knownModelsStore, { keyPath: "mac" });
          known.createIndex("by_vendor", "vendor", { unique: false });
          known.createIndex("by_updated_at", "updatedAt", { unique: false });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Не удалось открыть IndexedDB"));
      request.onblocked = () =>
        reject(new Error("IndexedDB занята другой вкладкой. Закройте старую вкладку программы и повторите."));
    });
  }

  async function transact(stores, mode, action) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(stores, mode);
      let result;
      try {
        result = action(tx);
      } catch (error) {
        db.close();
        reject(error);
        return;
      }
      tx.oncomplete = () => {
        db.close();
        resolve(result);
      };
      tx.onerror = () => {
        const error = tx.error;
        db.close();
        reject(error || new Error("Ошибка IndexedDB"));
      };
      tx.onabort = tx.onerror;
    });
  }

  function normalizeMac(value) {
    return String(value || "")
      .toUpperCase()
      .replace(/[^0-9A-F]/g, "")
      .slice(0, 12);
  }
  function text(value) {
    return String(value ?? "").trim();
  }
  let legacyMigration = null;

  async function migrateLegacyKnownEquipment() {
    if (legacyMigration) return legacyMigration;
    legacyMigration = (async () => {
      let legacy = {};
      try {
        legacy = JSON.parse(localStorage.getItem(knownKey) || "{}");
      } catch {
        legacy = {};
      }
      const entries = Object.entries(legacy || {}).filter(([mac]) => normalizeMac(mac));
      if (!entries.length) return 0;
      await transact([knownModelsStore], "readwrite", (tx) => {
        const store = tx.objectStore(knownModelsStore);
        for (const [macValue, item] of entries)
          store.put({
            mac: normalizeMac(macValue),
            vendor: text(item?.vendor),
            model: text(item?.model),
            address: text(item?.address),
            updatedAt: text(item?.updatedAt) || new Date().toISOString(),
          });
      });
      localStorage.removeItem(knownKey);
      return entries.length;
    })();
    return legacyMigration;
  }

  async function knownEquipment() {
    await migrateLegacyKnownEquipment();
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(knownModelsStore, "readonly"),
        request = tx.objectStore(knownModelsStore).getAll();
      request.onsuccess = () => resolve(Object.fromEntries((request.result || []).map((item) => [item.mac, item])));
      request.onerror = () => reject(request.error || new Error("Не удалось прочитать известные модели"));
      tx.oncomplete = () => db.close();
    });
  }

  async function saveKnownEquipment(value) {
    const rows = Object.entries(value || {}).filter(([mac]) => normalizeMac(mac));
    await transact([knownModelsStore], "readwrite", (tx) => {
      const store = tx.objectStore(knownModelsStore);
      for (const [macValue, item] of rows)
        store.put({
          mac: normalizeMac(macValue),
          vendor: text(item?.vendor),
          model: text(item?.model),
          address: text(item?.address),
          updatedAt: text(item?.updatedAt) || new Date().toISOString(),
        });
    });
    return rows.length;
  }

  function primeArpCache(rows = []) {
    for (const row of rows || []) {
      const ip = text(row.ip || row.ip_switch || row.switchIp);
      const mac = normalizeMac(row.mac || row.physical_address || row.physicalAddress);
      if (ip && mac) arpCache.set(ip, mac);
    }
    return arpCache.size;
  }

  function resolvePhysicalAddress(ip) {
    return arpCache.get(text(ip)) || "MAC не найден";
  }

  async function saveKnownModel(macValue, model, vendor = "") {
    const mac = normalizeMac(macValue),
      value = text(model);
    if (!mac || !value || /^unknown$/i.test(value)) throw new Error("Укажите корректные MAC и модель");
    const known = await knownEquipment(),
      previous = known[mac] || {};
    known[mac] = {
      ...previous,
      vendor: text(vendor) || previous.vendor || "",
      model: value,
      updatedAt: new Date().toISOString(),
    };
    await saveKnownEquipment(known);
    return known[mac];
  }

  async function syncEquipment(rows, timestamp = new Date().toISOString()) {
    const records = (rows || [])
      .map((row, index) => {
        const mac = normalizeMac(row.mac || row.macFormatted);
        const smartroomId = text(row.smartroomId || row.smartroom_id);
        if (!smartroomId) {
          console.warn(`[Smartroom] Запись ${index + 1} пропущена: Smartroom ID пустой или null`);
          return null;
        }
        return {
          id: `${smartroomId || "NO_ROOM"}:${mac || text(row.ip)}`,
          smartroom_id: smartroomId,
          ip_switch: text(row.switchIp || row.switch_ip || row.ip_switch),
          mac,
          model: text(row.model),
          manufacturer: text(row.vendor || row.manufacturer),
          date_added: text(row.date_added || timestamp),
          date_removed: text(row.date_removed),
          room: text(row.room),
          address: text(row.address),
          switch_port: text(row.switchPort || row.switch_port),
          ip: text(row.ip),
        };
      })
      .filter(Boolean);
    const known = await knownEquipment();
    for (const row of records)
      if (row.mac && row.model)
        known[row.mac] = {
          vendor: row.manufacturer || known[row.mac]?.vendor || "",
          model: row.model,
          address: row.address || known[row.mac]?.address || "",
          updatedAt: timestamp,
        };
    await saveKnownEquipment(known);
    await transact([equipmentStore], "readwrite", (tx) => {
      const store = tx.objectStore(equipmentStore),
        activeIds = new Set(records.map((row) => row.id));
      const cursorRequest = store.openCursor();
      cursorRequest.onsuccess = () => {
        const cursor = cursorRequest.result;
        if (!cursor) return;
        const old = cursor.value;
        if (!activeIds.has(old.id) && !old.date_removed) cursor.update({ ...old, date_removed: timestamp });
        cursor.continue();
      };
      for (const row of records) {
        const request = store.get(row.id);
        request.onsuccess = () =>
          store.put({ ...row, date_added: request.result?.date_added || row.date_added, date_removed: "" });
      }
    });
    return records.length;
  }

  async function appendHistory(events) {
    const rows = Array.from(events || []);
    await transact([historyStore], "readwrite", (tx) => {
      const store = tx.objectStore(historyStore);
      for (const event of rows) {
        const record = {
          entity_type: event.entity_type || "equipment",
          old_value: event.old_value ?? event.before ?? "",
          new_value: event.new_value ?? event.after ?? "",
          timestamp: event.timestamp || event.date || new Date().toISOString(),
          smartroom_id: event.smartroomId || event.smartroom_id || "",
          mac: normalizeMac(event.mac),
          field: event.field || "",
        };
        record.id = [
          record.entity_type,
          record.smartroom_id,
          record.mac,
          record.field,
          record.timestamp,
          record.old_value,
          record.new_value,
        ].join("|");
        store.put(record);
      }
    });
    return rows.length;
  }

  async function saveDdioSnapshot(devices, date = new Date().toISOString()) {
    const record = { date, devices: Array.from(devices || []) };
    await transact([ddioStore], "readwrite", (tx) => tx.objectStore(ddioStore).put(record));
    return record;
  }

  async function latestDdioSnapshot() {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(ddioStore, "readonly");
      const request = tx.objectStore(ddioStore).openCursor(null, "prev");
      request.onsuccess = () => resolve(request.result?.value || null);
      request.onerror = () => reject(request.error || new Error("Не удалось прочитать DDIO snapshot"));
      tx.oncomplete = () => db.close();
    });
  }

  function parseCsv(textValue) {
    const textData = String(textValue || "").replace(/^\uFEFF/, "");
    const delimiter =
      (textData.split(/\r?\n/, 1)[0].match(/;/g) || []).length >
      (textData.split(/\r?\n/, 1)[0].match(/,/g) || []).length
        ? ";"
        : ",";
    const rows = [];
    let row = [],
      cell = "",
      quoted = false;
    for (let index = 0; index < textData.length; index += 1) {
      const char = textData[index];
      if (char === '"') {
        if (quoted && textData[index + 1] === '"') {
          cell += '"';
          index += 1;
        } else quoted = !quoted;
      } else if (char === delimiter && !quoted) {
        row.push(cell);
        cell = "";
      } else if ((char === "\n" || char === "\r") && !quoted) {
        if (char === "\r" && textData[index + 1] === "\n") index += 1;
        row.push(cell);
        if (row.some((value) => value !== "")) rows.push(row);
        row = [];
        cell = "";
      } else cell += char;
    }
    row.push(cell);
    if (row.some((value) => value !== "")) rows.push(row);
    const headers = rows.shift() || [];
    return rows.map((values) =>
      Object.fromEntries(headers.map((header, index) => [text(header), values[index] ?? ""])),
    );
  }

  function parseDownload(textValue, contentType = "") {
    if (/json/i.test(contentType) || /^[\s\uFEFF]*[\[{]/.test(textValue)) {
      const parsed = JSON.parse(textValue);
      if (Array.isArray(parsed)) return parsed;
      for (const key of ["devices", "items", "results", "data"]) if (Array.isArray(parsed?.[key])) return parsed[key];
      throw new Error("JSON не содержит массива устройств");
    }
    return parseCsv(textValue);
  }

  async function fetchDdio(url) {
    const target = text(url);
    if (!target) throw new Error("Ссылка DDIO не указана");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(target, { cache: "no-store", signal: controller.signal });
      if (!response.ok) throw new Error(`DDIO URL вернул HTTP ${response.status}`);
      return parseDownload(await response.text(), response.headers.get("content-type") || "");
    } catch (error) {
      if (error?.name === "AbortError") throw new Error("Превышено время ожидания DDIO (30 секунд)");
      throw new Error(`Не удалось загрузить DDIO: ${error.message || error}`);
    } finally {
      clearTimeout(timeout);
    }
  }

  async function enrichData(devices, options = {}) {
    primeArpCache(options.arpRows || []);
    const arp = new Map((options.arpRows || []).map((row) => [text(row.ip || row.ip_switch || row.switchIp), row]));
    const known = await knownEquipment();
    const registry = options.registry || window.MacAnalyzerIeeeRegistry;
    const enriched = [];
    for (const source of devices || []) {
      const row = { ...source };
      const switchIp = text(row.switchIp || row.switch_ip || row.ip_switch);
      const arpRow = arp.get(switchIp) || {};
      const resolvedMac = resolvePhysicalAddress(switchIp);
      row.mac = normalizeMac(
        row.mac ||
          row.macFormatted ||
          arpRow.mac ||
          arpRow.physical_address ||
          (resolvedMac === "MAC не найден" ? "" : resolvedMac),
      );
      row.physicalAddress = row.mac || "MAC не найден";
      if (!row.address) row.address = text(arpRow.address || arpRow.physical_address_name);
      const saved = known[row.mac] || {};
      if (!row.vendor || /^(unknown|не определено)$/i.test(row.vendor))
        row.vendor = text(saved.vendor || registry?.lookup?.(row.mac)?.vendor || "Unknown");
      if (!row.model) row.model = text(saved.model || "Unknown");
      if (row.mac && row.model && !/^unknown$/i.test(row.model))
        known[row.mac] = {
          vendor: row.vendor || saved.vendor || "",
          model: row.model,
          address: row.address || saved.address || "",
          updatedAt: new Date().toISOString(),
        };
      enriched.push(row);
      if (enriched.length % 1000 === 0) await new Promise((resolve) => setTimeout(resolve, 0));
    }
    await saveKnownEquipment(known);
    return enriched;
  }

  function apiUrl() {
    return localStorage.getItem(apiUrlKey) || String(window.MAC_ANALYZER_API_URL || "");
  }
  function saveApiUrl(url) {
    localStorage.setItem(apiUrlKey, text(url));
    return text(url);
  }

  window.MacAnalyzerSmartroomStore = Object.freeze({
    syncEquipment,
    appendHistory,
    saveDdioSnapshot,
    latestDdioSnapshot,
    fetchDdio,
    enrichData,
    primeArpCache,
    resolvePhysicalAddress,
    saveKnownModel,
    apiUrl,
    saveApiUrl,
    parseDownload,
    stores: {
      Equipment: equipmentStore,
      History: historyStore,
      DDIO_Snapshot: ddioStore,
      KnownModels: knownModelsStore,
    },
  });
})();

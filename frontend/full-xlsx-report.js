(() => {
  "use strict";

  const defaultMaximumRows = 1_048_575;
  const deviceColumns = Object.freeze([
    { key: "row", title: "№" },
    { key: "macFormatted", title: "MAC-адрес" },
    { key: "oui3", title: "OUI 3 байта" },
    { key: "oui4", title: "OUI 4 байта" },
    { key: "oui5", title: "OUI 5 байт" },
    { key: "vendor", title: "Производитель" },
    { key: "model", title: "Модель" },
    { key: "ip", title: "IP устройства" },
    { key: "address", title: "Адрес помещения" },
    { key: "room", title: "Помещение" },
    { key: "switchIp", title: "IP коммутатора" },
    { key: "switchPort", title: "Порт" },
    { key: "source", title: "Источник" },
    { key: "vendorSource", title: "Источник производителя" },
    { key: "vendorConfidence", title: "Уверенность производителя" },
    { key: "vendorMatchedPrefix", title: "Префикс производителя" },
    { key: "modelSource", title: "Источник модели" },
    { key: "modelConfidence", title: "Уверенность модели" },
    { key: "modelMatchedPrefix", title: "Префикс модели" },
    { key: "valid", title: "Корректная запись" },
  ]);

  function defaultFormatMac(value) {
    const normalized = String(value || "").toUpperCase().replace(/[^0-9A-F]/g, "");
    return normalized.length === 12 ? normalized.match(/.{2}/g).join(":") : String(value || "");
  }

  function defaultFormatOui(value, length) {
    return String(value || "").toUpperCase().replace(/[^0-9A-F]/g, "").slice(0, Number(length || 3) * 2);
  }

  function valueFor(device, key, index, helpers) {
    if (key === "row") return index + 1;
    if (key === "macFormatted") return device.macFormatted || helpers.formatMac(device.mac);
    if (key === "oui3") return helpers.formatOuiValue(device.mac || device.macFormatted || device.oui, 3, "plain");
    if (key === "oui4") return helpers.formatOuiValue(device.mac || device.macFormatted || device.oui, 4, "plain");
    if (key === "oui5") return helpers.formatOuiValue(device.mac || device.macFormatted || device.oui, 5, "plain");
    if (key === "valid") return device.valid === false || device.invalid ? "Нет" : "Да";
    const snakeKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
    return device[key] ?? device[snakeKey] ?? "";
  }

  function snapshotDate(snapshot) {
    return snapshot.fileCreatedAt || snapshot.createdAt || snapshot.created_at || snapshot.savedAt || "";
  }

  function availableSnapshotRows(snapshot) {
    return snapshot.browserStored
      ? Math.max(0, Number(snapshot.deviceCount || 0))
      : Math.max(0, (snapshot.devices || []).length);
  }

  function historyGroups(snapshots, maximumRows = defaultMaximumRows) {
    const groups = [];
    let current = [];
    let rows = 0;
    for (const snapshot of snapshots) {
      const count = availableSnapshotRows(snapshot);
      if (count > maximumRows) {
        throw new Error(`Выгрузка «${snapshot.name || snapshot.id || "snapshot"}» превышает лимит листа Excel`);
      }
      if (current.length && rows + count > maximumRows) {
        groups.push({ snapshots: current, totalRows: rows });
        current = [];
        rows = 0;
      }
      current.push(snapshot);
      rows += count;
    }
    if (current.length || !groups.length) groups.push({ snapshots: current, totalRows: rows });
    return groups;
  }

  function summaryRows(payload, state, snapshots, historyRowCount) {
    const metrics = payload.metrics || {};
    const metricLabels = {
      devices: "Устройств в последней выгрузке",
      knownDevices: "Определён производитель",
      unknownVendor: "Производитель не определён",
      knownPercent: "Определено производителей, %",
      vendors: "Уникальных производителей",
      models: "Уникальных моделей",
      rooms: "Уникальных помещений",
      switches: "Уникальных коммутаторов",
      invalid: "Ошибочных записей",
      withAddress: "Заполнен адрес помещения",
      withRoom: "Заполнено помещение",
      withIp: "Заполнен IP устройства",
      withSwitch: "Заполнен IP коммутатора",
      withModel: "Определена модель",
      autoVendors: "Автоопределено производителей",
      autoModels: "Автоопределено моделей",
      uniqueOui3: "Уникальных OUI 3 байта",
      uniqueOui4: "Уникальных OUI 4 байта",
      uniqueOui5: "Уникальных OUI 5 байт",
    };
    return [
      ["Отчёт", "Полный отчёт MAC Analyzer Pro", ""],
      ["Дата экспорта", new Date().toISOString(), ""],
      ["Выгрузок", snapshots.length, "Все сохранённые точки истории"],
      ["Строк в хронологии MAC", historyRowCount, "Появления устройств во всех доступных выгрузках"],
      ["Записей изменений", (state.movementHistory || []).length, "Сохранённая расширенная история"],
      ...Object.entries(metricLabels).map(([key, label]) => [label, metrics[key] ?? 0, key === "knownPercent" ? "Процент" : ""]),
    ];
  }

  function analyticsRows(payload) {
    const metrics = payload.metrics || {};
    const total = Math.max(1, Number(metrics.devices || 0));
    const labels = {
      vendors: "Производитель",
      models: "Модель",
      rooms: "Помещение",
      switches: "IP коммутатора",
      oui3: "OUI 3 байта",
      oui4: "OUI 4 байта",
      oui5: "OUI 5 байт",
    };
    const rows = [];
    for (const [key, label] of Object.entries(labels)) {
      for (const item of payload.distributions?.[key] || []) {
        const count = Number(item.value ?? item.count ?? 0);
        rows.push([label, item.label || "", count, Number((count / total * 100).toFixed(2))]);
      }
    }
    return rows;
  }

  function compactDevice(device) {
    if (!device || typeof device !== "object") return null;
    return {
      vendor: String(device.vendor || ""),
      model: String(device.model || ""),
      ip: String(device.ip || ""),
      address: String(device.address || ""),
      room: String(device.room || ""),
      switchIp: String(device.switchIp || device.switch_ip || ""),
      switchPort: String(device.switchPort || device.switch_port || ""),
    };
  }

  function movementType(item) {
    const before = String(item.before ?? item.from_value ?? "");
    const after = String(item.after ?? item.to_value ?? "");
    return !before && after ? "added" : before && !after ? "removed" : "modified";
  }

  function movementRow(item, helpers) {
    const device = helpers.compactDevice(item.afterDevice) || helpers.compactDevice(item.beforeDevice) || {};
    return [
      item.changedAt || item.changed_at || item.date_str || "",
      helpers.formatMac(item.mac) || item.mac || "",
      item.type || item.change_type || helpers.movementType(item),
      item.field || item.field_name || "",
      item.before ?? item.from_value ?? item.old_value ?? "",
      item.after ?? item.to_value ?? item.new_value ?? "",
      device.vendor || "",
      device.model || "",
      device.ip || "",
      device.address || "",
      device.room || "",
      device.switchIp || "",
      device.switchPort || "",
      item.source || item.file_name || "",
    ];
  }

  function referenceRows(state) {
    const rows = [];
    Object.entries(state.localVendorMappings || {}).sort().forEach(([prefix, value]) => rows.push(["Производитель", prefix, value, ""]));
    Object.entries(state.localModelMappings || {}).sort().forEach(([prefix, value]) => rows.push(["Модель", prefix, value, ""]));
    for (const item of state.ipMappings || []) {
      const key = item.switchIp || item.switch_ip || item.ip || item.key || "";
      rows.push(["IP коммутатора", key, item.address || item.value || "", item.room || ""]);
    }
    return rows;
  }

  function settingsRows(state) {
    return [
      ["Тема", state.theme || "light"],
      ["Режим OUI", `${state.ouiLength || 3} байта / ${state.ouiStyle || "plain"}`],
      ["Автоопределение vendor/model", JSON.stringify(state.vendorDetectorSettings || {})],
      ["Историческое обогащение", JSON.stringify(state.historyEnrichmentSettings || {})],
      ["Настройки dashboard", JSON.stringify(state.dashboardSettings || {})],
      ["Пользовательские колонки", JSON.stringify(state.customColumns || [])],
      ["Порядок колонок", JSON.stringify(state.columnOrder || [])],
      ["Видимые колонки", JSON.stringify(state.visibleColumns || [])],
    ];
  }

  async function buildReport(options = {}) {
    const state = options.state || {};
    const helpers = {
      formatMac: options.formatMac || defaultFormatMac,
      formatOuiValue: options.formatOuiValue || defaultFormatOui,
      compactDevice: options.compactDevice || compactDevice,
      movementType: options.movementType || movementType,
    };
    const streamCurrentRows = options.streamCurrentRows || (async (accept) => accept(state.devices || []));
    const streamInvalidRows = options.streamInvalidRows || (async (accept) => accept(state.invalid || []));
    const streamSnapshotRows = options.streamSnapshotRows || (async (snapshot, accept) => accept(snapshot.devices || []));
    const currentDeviceCount = Math.max(0, Number(options.currentDeviceCount ?? (state.devices || []).length));
    const currentInvalidCount = Math.max(0, Number(options.currentInvalidCount ?? (state.invalid || []).length));
    const snapshots = (state.snapshots || []).slice().sort(
      (left, right) => (Date.parse(snapshotDate(left)) || 0) - (Date.parse(snapshotDate(right)) || 0),
    );
    const groups = historyGroups(snapshots, options.maximumRows || defaultMaximumRows);
    const historyRowCount = groups.reduce((sum, group) => sum + group.totalRows, 0);
    const analytics = await options.analyticsPayload();
    const columns = deviceColumns;
    const sheets = [
      { sheetName: "Сводка", columns: ["Показатель", "Значение", "Примечание"], rows: summaryRows(analytics, state, snapshots, historyRowCount) },
      {
        sheetName: "Устройства",
        columns: columns.map((column) => column.title),
        totalRows: currentDeviceCount,
        streamRows: streamCurrentRows,
        rowMapper: (device, index) => columns.map((column) => valueFor(device, column.key, index, helpers)),
      },
      { sheetName: "Аналитика", columns: ["Разрез", "Значение", "Количество", "Доля от устройств, %"], rows: analyticsRows(analytics) },
      {
        sheetName: "Выгрузки",
        columns: ["ID", "Название", "Дата файла", "Сохранено", "Источник", "Тип", "Устройств", "Ошибок", "Полнота"],
        rows: snapshots.map((snapshot) => [
          snapshot.id || "", snapshot.name || "", snapshotDate(snapshot), snapshot.savedAt || "", snapshot.source || "", snapshot.kind || "",
          snapshot.deviceCount ?? (snapshot.devices || []).length, snapshot.invalidCount ?? (snapshot.invalid || []).length,
          snapshot.browserStored ? "Полная IndexedDB" : "Доступные строки",
        ]),
      },
      {
        sheetName: "Изменения",
        columns: ["Дата", "MAC-адрес", "Тип", "Поле", "Было", "Стало", "Производитель", "Модель", "IP устройства", "Адрес помещения", "Помещение", "IP коммутатора", "Порт", "Источник"],
        rows: state.movementHistory || [],
        rowMapper: (item) => movementRow(item, helpers),
      },
      {
        sheetName: "Ошибки",
        columns: ["Строка", "Источник", "Ошибка", "Исходные данные"],
        totalRows: currentInvalidCount,
        streamRows: streamInvalidRows,
        rowMapper: (item) => [item.row || "", item.source || "", item.error || item.message || "Некорректный MAC", item.raw || item.value || ""],
      },
      {
        sheetName: "Исходные файлы",
        columns: ["ID", "Имя", "Роль", "Лист", "Строк", "Размер, байт", "Дата файла", "Статус"],
        rows: (state.files || []).map((file) => [
          file.id || "", file.name || "", file.role || "", file.sheet || file.sheetName || "", file.rowCount ?? (file.rows || []).length,
          file.sourceBytes || file.size || 0, file.fileCreatedAt || file.lastModified || "", file.consumedAt ? "Обработан" : "Загружен",
        ]),
      },
      { sheetName: "Справочники", columns: ["Тип", "Ключ", "Значение", "Дополнительно"], rows: referenceRows(state) },
      { sheetName: "Настройки", columns: ["Параметр", "Значение"], rows: settingsRows(state) },
    ];

    groups.forEach((group, index) => {
      sheets.splice(4 + index, 0, {
        sheetName: groups.length === 1 ? "История MAC" : `История MAC ${index + 1}`,
        columns: ["Дата выгрузки", "Снимок", "Источник выгрузки", ...columns.slice(1).map((column) => column.title)],
        totalRows: group.totalRows,
        streamRows: async (acceptRows) => {
          for (const snapshot of group.snapshots) {
            await streamSnapshotRows(snapshot, async (rows) => {
              const prefix = [snapshotDate(snapshot), snapshot.name || snapshot.id || "", snapshot.source || ""];
              await acceptRows(rows.map((device, rowIndex) => [
                ...prefix,
                ...columns.slice(1).map((column) => valueFor(device, column.key, rowIndex, helpers)),
              ]));
            });
          }
        },
      });
    });

    return { sheets, snapshots, historyRowCount, analytics };
  }

  window.MacAnalyzerFullXlsxReport = Object.freeze({
    buildReport,
    deviceColumns,
    snapshotDate,
    availableSnapshotRows,
    historyGroups,
  });
  if (typeof document !== "undefined") document.documentElement.dataset.fullXlsxReport = "ready";
})();

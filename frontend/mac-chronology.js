(() => {
  "use strict";

  const fieldLabels = Object.freeze({
    snapshot: "Выгрузка",
    history: "Запись истории",
    vendor: "Производитель",
    model: "Модель",
    ip: "IP устройства",
    address: "Адрес помещения",
    room: "Помещение",
    smartroomId: "Smartroom ID",
    smartroom_id: "Smartroom ID",
    switchIp: "IP коммутатора",
    switch_ip: "IP коммутатора",
    switchPort: "Порт",
    switch_port: "Порт",
    device: "Устройство",
    "-": "Устройство",
  });

  function normalizeMac(value) {
    return String(value || "").toUpperCase().replace(/[^0-9A-F]/g, "").slice(0, 12);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function snapshotDate(snapshot) {
    return snapshot?.fileCreatedAt || snapshot?.createdAt || snapshot?.created_at || snapshot?.savedAt || "";
  }

  function deviceValue(device, ...keys) {
    for (const key of keys) {
      const value = String(device?.[key] ?? "").trim();
      if (value) return value;
    }
    return "";
  }

  function compactDevice(device) {
    if (!device || typeof device !== "object") return {};
    return {
      mac: normalizeMac(device.mac || device.macFormatted || device.mac_formatted),
      vendor: deviceValue(device, "vendor"),
      model: deviceValue(device, "model"),
      ip: deviceValue(device, "ip"),
      address: deviceValue(device, "address"),
      room: deviceValue(device, "room"),
      smartroomId: deviceValue(device, "smartroomId", "smartroom_id"),
      switchIp: deviceValue(device, "switchIp", "switch_ip"),
      switchPort: deviceValue(device, "switchPort", "switch_port"),
      source: deviceValue(device, "source", "source_file"),
    };
  }

  function findInlineDevice(snapshot, mac) {
    return (Array.isArray(snapshot?.devices) ? snapshot.devices : [])
      .find((device) => normalizeMac(device?.mac || device?.macFormatted || device?.mac_formatted) === mac) || null;
  }

  async function collectAppearances(options = {}) {
    const mac = normalizeMac(options.mac);
    if (!mac) return [];
    const findSnapshotDevice = typeof options.findSnapshotDevice === "function"
      ? options.findSnapshotDevice
      : async () => null;
    const snapshots = (Array.isArray(options.snapshots) ? options.snapshots : []).slice().sort(
      (left, right) => (Date.parse(snapshotDate(left)) || 0) - (Date.parse(snapshotDate(right)) || 0),
    );
    const appearances = [];
    for (const snapshot of snapshots) {
      let device = findInlineDevice(snapshot, mac);
      if (!device && (snapshot?.browserStored || snapshot?.backendStored)) {
        device = await findSnapshotDevice(snapshot, mac);
      }
      if (!device) continue;
      appearances.push({
        snapshotId: snapshot.id || "",
        snapshotName: snapshot.name || snapshot.id || "Выгрузка",
        source: snapshot.source || device.source || snapshot.name || "",
        createdAt: snapshotDate(snapshot),
        device: compactDevice(device),
      });
    }
    return appearances;
  }

  function appearanceKey(item) {
    const device = compactDevice(item?.device || item);
    return [
      item?.snapshotId || "",
      item?.createdAt || item?.date || "",
      item?.snapshotName || "",
      item?.source || "",
      device.mac,
    ].join("|");
  }

  function mergeAppearances(...groups) {
    const merged = new Map();
    for (const item of groups.flat()) {
      if (!item || typeof item !== "object") continue;
      const normalized = { ...item, device: compactDevice(item.device || item) };
      const key = appearanceKey(normalized);
      const existing = merged.get(key);
      if (!existing) {
        merged.set(key, normalized);
        continue;
      }
      const device = { ...existing.device };
      for (const [field, value] of Object.entries(normalized.device)) {
        if (String(value || "").trim() || !String(device[field] || "").trim()) device[field] = value;
      }
      merged.set(key, { ...existing, ...normalized, device });
    }
    return Array.from(merged.values()).sort(
      (left, right) => (Date.parse(left.createdAt || "") || 0) - (Date.parse(right.createdAt || "") || 0),
    );
  }

  function normalizeMovement(item) {
    const field = String(item?.field || item?.field_name || "device");
    const beforeDevice = compactDevice(item?.beforeDevice || item?.before_device);
    const afterDevice = compactDevice(item?.afterDevice || item?.after_device);
    return {
      type: "movement",
      event: String(item?.event || item?.type || item?.change_type || "Изменение поля"),
      date: item?.date || item?.changedAt || item?.changed_at || "",
      field,
      fieldLabel: fieldLabels[field] || field,
      before: item?.before ?? item?.from_value ?? item?.old_value ?? "",
      after: item?.after ?? item?.to_value ?? item?.new_value ?? "",
      source: item?.source || item?.source_file || "История изменений",
      device: Object.keys(afterDevice).length ? afterDevice : beforeDevice,
    };
  }

  function normalizeHistory(item) {
    const device = compactDevice(item);
    return {
      type: "history",
      event: "Запись истории",
      date: item?.date || item?.recorded_at || item?.recordedAt || "",
      field: "history",
      fieldLabel: fieldLabels.history,
      before: "",
      after: [device.vendor, device.model, device.ip, device.address, device.room].filter(Boolean).join(" · "),
      source: item?.source || item?.source_file || "История",
      device,
    };
  }

  function normalizeAppearance(item) {
    const device = compactDevice(item?.device || item);
    return {
      type: "snapshot",
      event: "Появление в выгрузке",
      date: item?.createdAt || item?.date || "",
      field: "snapshot",
      fieldLabel: fieldLabels.snapshot,
      before: "",
      after: [device.vendor, device.model, device.ip].filter(Boolean).join(" · "),
      source: item?.snapshotName || item?.source || device.source || "Выгрузка",
      snapshotId: item?.snapshotId || "",
      device,
    };
  }

  function appearanceChanges(appearances) {
    const ordered = (appearances || []).slice().sort(
      (left, right) => (Date.parse(left.createdAt || "") || 0) - (Date.parse(right.createdAt || "") || 0),
    );
    const fields = ["vendor", "model", "ip", "address", "room", "smartroomId", "switchIp", "switchPort"];
    const events = [];
    for (let index = 1; index < ordered.length; index += 1) {
      const previous = compactDevice(ordered[index - 1].device);
      const current = compactDevice(ordered[index].device);
      for (const field of fields) {
        if (String(previous[field] || "") === String(current[field] || "")) continue;
        events.push({
          type: "movement",
          event: "Изменение между финальными выгрузками",
          date: ordered[index].createdAt || "",
          field,
          fieldLabel: fieldLabels[field] || field,
          before: previous[field] || "",
          after: current[field] || "",
          source: `${ordered[index - 1].snapshotName || "Выгрузка"} → ${ordered[index].snapshotName || "Выгрузка"}`,
          device: current,
        });
      }
    }
    return events;
  }

  function eventKey(item) {
    return [
      item.type, item.date, item.field, item.before, item.after, item.source,
      item.device?.mac, item.snapshotId,
    ].map((value) => String(value || "")).join("|");
  }

  function buildEvents(options = {}) {
    const events = [
      ...(options.appearances || []).map(normalizeAppearance),
      ...appearanceChanges(options.appearances || []),
      ...(options.history || []).map(normalizeHistory),
      ...(options.movements || []).map(normalizeMovement),
      ...(options.events || []).map((item) => {
        if (item?.type === "snapshot") return normalizeAppearance(item);
        if (item?.type === "history") return normalizeHistory(item);
        return normalizeMovement(item);
      }),
    ];
    const unique = new Map();
    for (const event of events) unique.set(eventKey(event), event);
    return Array.from(unique.values()).sort(
      (left, right) => (Date.parse(right.date || "") || 0) - (Date.parse(left.date || "") || 0),
    );
  }

  async function getMacHistory(options = {}) {
    const collected = await collectAppearances(options);
    const appearances = mergeAppearances(collected, options.appearances || []);
    return buildEvents({
      appearances,
      history: options.history || [],
      movements: options.movements || [],
      events: options.events || [],
    }).slice().reverse();
  }

  function displayDate(value, formatter) {
    if (typeof formatter === "function") return formatter(value);
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value || "Дата не указана") : date.toLocaleString("ru-RU");
  }

  function eventTone(event) {
    if (event.type === "snapshot") return "snapshot";
    if (event.type === "history") return "history";
    const text = `${event.event} ${event.field}`.toLowerCase();
    if (text.includes("удален") || text.includes("removed")) return "removed";
    if (text.includes("добав") || text.includes("added")) return "added";
    return "changed";
  }

  function contextHtml(device) {
    const items = [
      ["Производитель", device.vendor],
      ["Модель", device.model],
      ["IP устройства", device.ip],
      ["Адрес", device.address],
      ["Помещение", device.room],
      ["Smartroom ID", device.smartroomId],
      ["Коммутатор", device.switchIp],
      ["Порт", device.switchPort],
    ].filter(([, value]) => value);
    if (!items.length) return "";
    return `<dl class="mac-timeline-context">${items.map(([label, value]) => (
      `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`
    )).join("")}</dl>`;
  }

  function renderTimeline(events, options = {}) {
    if (!events.length) {
      return '<div class="mac-timeline-empty"><strong>Хронология пока пуста</strong><span>Для этого MAC ещё нет сохранённых появлений или изменений.</span></div>';
    }
    return events.slice(0, Math.max(1, Number(options.limit || 1000))).map((event) => {
      const tone = eventTone(event);
      const hasChange = String(event.before || "") || String(event.after || "");
      const change = hasChange ? (
        `<div class="mac-timeline-change"><span class="mac-value-before">${escapeHtml(event.before || "Не заполнено")}</span>` +
        '<span class="mac-change-arrow" aria-hidden="true">→</span>' +
        `<span class="mac-value-after">${escapeHtml(event.after || "Не заполнено")}</span></div>`
      ) : "";
      return `<article class="mac-timeline-item mac-timeline-${tone}">` +
        `<div class="mac-timeline-marker" aria-hidden="true"></div>` +
        `<div class="mac-timeline-card"><header><time>${escapeHtml(displayDate(event.date, options.formatDate))}</time>` +
        `<span class="mac-event-badge">${escapeHtml(event.event)}</span></header>` +
        `<div class="mac-timeline-title"><strong>${escapeHtml(event.fieldLabel || fieldLabels[event.field] || event.field || "Событие")}</strong>` +
        `<span>${escapeHtml(event.source || "Источник не указан")}</span></div>` +
        change + contextHtml(event.device || {}) +
        "</div></article>";
    }).join("");
  }

  function renderSummary(events, appearances) {
    const dates = events.map((item) => Date.parse(item.date || "")).filter(Number.isFinite).sort((a, b) => a - b);
    const sources = new Set(events.map((item) => String(item.source || "").trim()).filter(Boolean));
    const metrics = [
      ["Событий", events.length],
      ["Выгрузок", appearances.length],
      ["Изменений", events.filter((item) => item.type === "movement").length],
      ["Источников", sources.size],
      ["Первое появление", dates.length ? new Date(dates[0]).toLocaleDateString("ru-RU") : "—"],
      ["Последнее появление", dates.length ? new Date(dates[dates.length - 1]).toLocaleDateString("ru-RU") : "—"],
    ];
    return metrics.map(([label, value]) => (
      `<div class="mac-summary-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`
    )).join("");
  }

  function appearancesRowsHtml(appearances, options = {}) {
    if (!appearances.length) return '<tr><td colspan="8" class="empty-state">История появлений MAC пока пуста.</td></tr>';
    return appearances.slice().reverse().map((item) => {
      const device = compactDevice(item.device);
      return "<tr>" +
        `<td>${escapeHtml(displayDate(item.createdAt, options.formatDate))}</td>` +
        `<td>${escapeHtml(item.snapshotName || item.source || "Выгрузка")}</td>` +
        `<td>${escapeHtml(device.vendor || "—")}</td>` +
        `<td>${escapeHtml(device.model || "—")}</td>` +
        `<td>${escapeHtml(device.ip || "—")}</td>` +
        `<td>${escapeHtml(device.address || "—")}</td>` +
        `<td>${escapeHtml(device.room || "—")}</td>` +
        `<td>${escapeHtml(device.smartroomId || "—")}</td>` +
        "</tr>";
    }).join("");
  }

  window.MacAnalyzerMacChronology = Object.freeze({
    normalizeMac,
    compactDevice,
    collectAppearances,
    mergeAppearances,
    getMacHistory,
    buildEvents,
    renderTimeline,
    renderSummary,
    appearancesRowsHtml,
  });
  if (typeof document !== "undefined") document.documentElement.dataset.macChronology = "ready";
})();

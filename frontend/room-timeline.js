(() => {
  "use strict";

  const text = (value) => String(value ?? "").trim();
  const normalizeMac = (value) => {
    const normalized = text(value)
      .toUpperCase()
      .replace(/[^0-9A-F]/g, "");
    return normalized.length === 12 ? normalized : "";
  };
  const Time =
    (typeof window !== "undefined" && window.MacAnalyzerTime) ||
    (typeof require === "function" ? require("./time-utils.js") : null);

  const value = (device, ...keys) => {
    for (const key of keys) {
      const candidate = text(device?.[key]);
      if (candidate) return candidate;
    }
    return "";
  };

  function deviceIdentity(device, index = 0) {
    const mac = normalizeMac(device?.mac || device?.macFormatted || device?.mac_formatted);
    if (mac) return `mac:${mac}`;
    const deviceId = value(device, "deviceId", "device_id").toLowerCase();
    if (deviceId) return `device:${deviceId}`;
    const serial = value(device, "serialNumber", "serial_number", "serial").toUpperCase();
    if (serial) return `serial:${serial}`;
    const hostname = value(device, "hostname", "host_name").toLowerCase();
    if (hostname) return `host:${hostname}`;
    return `unidentified:${index}`;
  }

  function deviceMap(devices) {
    const result = new Map();
    (devices || []).forEach((device, index) => {
      const baseKey = deviceIdentity(device, index);
      const existing = result.get(baseKey);
      if (!existing) {
        result.set(baseKey, device);
        return;
      }
      const merged = { ...existing };
      for (const [field, fieldValue] of Object.entries(device || {})) {
        if (text(fieldValue)) merged[field] = fieldValue;
      }
      result.set(baseKey, merged);
    });
    return result;
  }

  const trackedFields = Object.freeze([
    ["switchIp", ["switchIp", "switch_ip", "ip_switch"], "IP коммутатора"],
    ["switchPort", ["switchPort", "switch_port", "port"], "Порт"],
    ["ip", ["ip", "deviceIp", "device_ip"], "IP устройства"],
    ["model", ["model"], "Модель"],
    ["vendor", ["vendor", "manufacturer"], "Производитель"],
    ["tb", ["tb", "territorialBank", "territorial_bank"], "ТБ"],
    ["city", ["city", "city_name"], "Город"],
    ["site", ["site", "siteName", "site_name"], "Площадка"],
    ["floor", ["floor", "floorName", "floor_name"], "Этаж"],
    ["room", ["room", "room_name"], "Помещение"],
    ["address", ["address", "physicalAddress"], "Адрес"],
  ]);

  function changedValues(before, after) {
    const changes = [];
    for (const [field, keys, label] of trackedFields) {
      const oldValue = value(before, ...keys);
      const newValue = value(after, ...keys);
      if (!newValue || oldValue === newValue) continue;
      changes.push({ field, label, before: oldValue, after: newValue });
    }
    return changes;
  }

  function compareLatest(room) {
    const history = Array.from(room?.history || []).filter((item) => item && typeof item === "object");
    const previousObservation = history.at(-2) || null;
    const currentObservation = history.at(-1) || null;
    const previous = deviceMap(previousObservation?.devices || []);
    const current = deviceMap(currentObservation?.devices || []);
    const identities = new Set([...previous.keys(), ...current.keys()]);
    const entries = [];
    for (const identity of identities) {
      const beforeDevice = previous.get(identity) || null;
      const device = current.get(identity) || null;
      const changes = beforeDevice && device ? changedValues(beforeDevice, device) : [];
      const moved = changes.some((change) => change.field === "switchIp" || change.field === "switchPort");
      let status = "Без изменений";
      if (!beforeDevice) status = "Добавлен";
      else if (!device) status = "Удален";
      else if (moved) status = "Перемещен";
      else if (changes.length) status = "Изменен";
      entries.push({
        identity,
        mac: normalizeMac(device?.mac || beforeDevice?.mac),
        model: text(device?.model || beforeDevice?.model) || "Unknown",
        status,
        changes,
        beforeDevice,
        device: device || beforeDevice || {},
      });
    }
    const changed = entries.filter((item) => item.status !== "Без изменений");
    return {
      previousDate: Time.toUtcIso(previousObservation?.date),
      currentDate: Time.toUtcIso(currentObservation?.date),
      total: entries.length,
      changed: changed.length,
      unchanged: entries.length - changed.length,
      allChanged: entries.length > 0 && changed.length === entries.length,
      entries,
    };
  }

  function events(room) {
    const result = [];
    let previous = new Map();
    for (const observation of room?.history || []) {
      const current = deviceMap(observation.devices || []);
      for (const [identity, device] of previous) {
        if (!current.has(identity))
          result.push({
            date: observation.date,
            mac: normalizeMac(device.mac),
            model: text(device.model) || "Unknown",
            vendor: text(device.vendor) || "Unknown",
            status: "Удален",
            device,
          });
      }
      for (const [identity, device] of current) {
        if (!previous.has(identity)) {
          result.push({
            date: observation.date,
            mac: normalizeMac(device.mac),
            model: text(device.model) || "Unknown",
            vendor: text(device.vendor) || "Unknown",
            status: "Добавлен",
            device,
          });
          continue;
        }
        const beforeDevice = previous.get(identity);
        const changes = changedValues(beforeDevice, device);
        if (!changes.length) continue;
        const moved = changes.some((change) => change.field === "switchIp" || change.field === "switchPort");
        result.push({
          date: observation.date,
          mac: normalizeMac(device.mac || beforeDevice.mac),
          model: text(device.model || beforeDevice.model) || "Unknown",
          vendor: text(device.vendor || beforeDevice.vendor) || "Unknown",
          status: moved ? "Перемещен" : "Изменен",
          changes,
          beforeDevice,
          device,
        });
      }
      previous = current;
    }
    result.sort(
      (left, right) =>
        (Time.timestamp(left.date) ?? Number.MAX_SAFE_INTEGER) -
        (Time.timestamp(right.date) ?? Number.MAX_SAFE_INTEGER),
    );
    return result.map((item, index) => ({
      ...item,
      date: Time.toUtcIso(item.date),
      elapsedMs: index ? Time.difference(result[index - 1].date, item.date) : null,
    }));
  }

  function statusTone(status) {
    if (status === "Добавлен") return "added";
    if (status === "Удален") return "removed";
    if (status === "Перемещен") return "moved";
    return "changed";
  }

  function changesHtml(item, escapeHtml) {
    if (!item.changes?.length) return "";
    return `<div class="room-timeline-changes">${item.changes
      .map(
        (change) =>
          `<span><b>${escapeHtml(change.label)}:</b> ${escapeHtml(change.before || "Не заполнено")} → ${escapeHtml(change.after)}</span>`,
      )
      .join("")}</div>`;
  }

  function render(room, helpers = {}) {
    const escapeHtml = helpers.escapeHtml || ((value) => text(value));
    const formatDate = helpers.formatDate || Time.formatUtc;
    const formatMac = helpers.formatMac || text;
    const rows = events(room);
    if (!rows.length)
      return {
        rows,
        tableHtml: '<tr><td colspan="4" class="empty-state">Изменений оборудования не найдено.</td></tr>',
        timelineHtml: '<p class="empty-state">История помещения отсутствует.</p>',
      };
    const rowHtml = rows
      .slice()
      .reverse()
      .map((item) => {
        const model = escapeHtml(item.model || "Unknown");
        const manual = /^unknown$/i.test(item.model)
          ? ` <button type="button" class="link-button" data-add-known-model="${escapeHtml(item.mac)}" data-known-vendor="${escapeHtml(item.vendor)}">Указать модель</button>`
          : "";
        const interval = item.elapsedMs === null ? "Первое событие" : `Через ${Time.formatDuration(item.elapsedMs)}`;
        return `<tr><td>${escapeHtml(formatDate(item.date))}<small class="timeline-duration">${escapeHtml(interval)}</small></td><td>${escapeHtml(formatMac(item.mac) || "—")}</td><td>${model}${changesHtml(item, escapeHtml)}${manual}</td><td><span class="room-status room-status-${statusTone(item.status)}">${escapeHtml(item.status)}</span></td></tr>`;
      })
      .join("");
    const timelineHtml = rows
      .map(
        (item, index) =>
          `<article class="room-timeline-event room-timeline-${statusTone(item.status)}">${index ? '<span class="room-timeline-arrow" aria-hidden="true">→</span>' : ""}<time>${escapeHtml(formatDate(item.date))}</time><small class="timeline-duration">${escapeHtml(item.elapsedMs === null ? "Первое событие" : `Через ${Time.formatDuration(item.elapsedMs)}`)}</small><strong>${escapeHtml(item.status)}</strong><span>${escapeHtml(formatMac(item.mac) || "—")}</span><small>${escapeHtml(item.model || "Unknown")}</small>${changesHtml(item, escapeHtml)}</article>`,
      )
      .join("");
    return { rows, tableHtml: rowHtml, timelineHtml };
  }

  window.MacAnalyzerRoomTimeline = Object.freeze({ events, compareLatest, render });
})();

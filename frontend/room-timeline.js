(() => {
  "use strict";

  const text = (value) => String(value ?? "").trim();
  const normalizeMac = (value) => text(value).toUpperCase().replace(/[^0-9A-F]/g, "").slice(0, 12);

  function events(room) {
    const result = [];
    let previous = new Map();
    for (const observation of room?.history || []) {
      const current = new Map((observation.devices || []).map((device) => [normalizeMac(device.mac), device]));
      for (const [mac, device] of previous) {
        if (!current.has(mac)) result.push({ date: observation.date, mac, model: text(device.model) || "Unknown", vendor: text(device.vendor) || "Unknown", status: "Удален", device });
      }
      for (const [mac, device] of current) {
        if (!previous.has(mac)) result.push({ date: observation.date, mac, model: text(device.model) || "Unknown", vendor: text(device.vendor) || "Unknown", status: "Добавлен", device });
      }
      previous = current;
    }
    return result.sort((left, right) => (Date.parse(left.date) || 0) - (Date.parse(right.date) || 0));
  }

  function render(room, helpers = {}) {
    const escapeHtml = helpers.escapeHtml || ((value) => text(value));
    const formatDate = helpers.formatDate || text;
    const formatMac = helpers.formatMac || text;
    const rows = events(room);
    if (!rows.length) return { rows, tableHtml: '<tr><td colspan="4" class="empty-state">Изменений оборудования не найдено.</td></tr>', timelineHtml: '<p class="empty-state">История помещения отсутствует.</p>' };
    const rowHtml = rows.slice().reverse().map((item) => {
      const model = escapeHtml(item.model || "Unknown");
      const manual = /^unknown$/i.test(item.model) ? ` <button type="button" class="link-button" data-add-known-model="${escapeHtml(item.mac)}" data-known-vendor="${escapeHtml(item.vendor)}">Указать модель</button>` : "";
      return `<tr><td>${escapeHtml(formatDate(item.date))}</td><td>${escapeHtml(formatMac(item.mac) || "—")}</td><td>${model}${manual}</td><td><span class="room-status room-status-${item.status === "Добавлен" ? "added" : "removed"}">${escapeHtml(item.status)}</span></td></tr>`;
    }).join("");
    const timelineHtml = rows.map((item, index) => `<article class="room-timeline-event room-timeline-${item.status === "Добавлен" ? "added" : "removed"}">${index ? '<span class="room-timeline-arrow" aria-hidden="true">→</span>' : ""}<time>${escapeHtml(formatDate(item.date))}</time><strong>${escapeHtml(item.status)}</strong><span>${escapeHtml(formatMac(item.mac) || "—")}</span><small>${escapeHtml(item.model || "Unknown")}</small></article>`).join("");
    return { rows, tableHtml: rowHtml, timelineHtml };
  }

  window.MacAnalyzerRoomTimeline = Object.freeze({ events, render });
})();

(() => {
  "use strict";

  const text = (value) => String(value ?? "").trim();
  const normalizeMac = (value) =>
    text(value)
      .toUpperCase()
      .replace(/[^0-9A-F]/g, "")
      .slice(0, 12);
  const Time =
    (typeof window !== "undefined" && window.MacAnalyzerTime) ||
    (typeof require === "function" ? require("./time-utils.js") : null);

  function events(room) {
    const result = [];
    let previous = new Map();
    for (const observation of room?.history || []) {
      const current = new Map((observation.devices || []).map((device) => [normalizeMac(device.mac), device]));
      for (const [mac, device] of previous) {
        if (!current.has(mac))
          result.push({
            date: observation.date,
            mac,
            model: text(device.model) || "Unknown",
            vendor: text(device.vendor) || "Unknown",
            status: "Удален",
            device,
          });
      }
      for (const [mac, device] of current) {
        if (!previous.has(mac))
          result.push({
            date: observation.date,
            mac,
            model: text(device.model) || "Unknown",
            vendor: text(device.vendor) || "Unknown",
            status: "Добавлен",
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
        return `<tr><td>${escapeHtml(formatDate(item.date))}<small class="timeline-duration">${escapeHtml(interval)}</small></td><td>${escapeHtml(formatMac(item.mac) || "—")}</td><td>${model}${manual}</td><td><span class="room-status room-status-${item.status === "Добавлен" ? "added" : "removed"}">${escapeHtml(item.status)}</span></td></tr>`;
      })
      .join("");
    const timelineHtml = rows
      .map(
        (item, index) =>
          `<article class="room-timeline-event room-timeline-${item.status === "Добавлен" ? "added" : "removed"}">${index ? '<span class="room-timeline-arrow" aria-hidden="true">→</span>' : ""}<time>${escapeHtml(formatDate(item.date))}</time><small class="timeline-duration">${escapeHtml(item.elapsedMs === null ? "Первое событие" : `Через ${Time.formatDuration(item.elapsedMs)}`)}</small><strong>${escapeHtml(item.status)}</strong><span>${escapeHtml(formatMac(item.mac) || "—")}</span><small>${escapeHtml(item.model || "Unknown")}</small></article>`,
      )
      .join("");
    return { rows, tableHtml: rowHtml, timelineHtml };
  }

  window.MacAnalyzerRoomTimeline = Object.freeze({ events, render });
})();

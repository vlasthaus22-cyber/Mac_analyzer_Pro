(() => {
  "use strict";

  function timestamp(value) {
    if (value === null || value === undefined || String(value).trim() === "") return null;
    const milliseconds =
      typeof value === "number" ? value : value instanceof Date ? value.getTime() : Date.parse(value);
    return Number.isFinite(milliseconds) ? milliseconds : null;
  }

  function toUtcIso(value) {
    const milliseconds = timestamp(value);
    return milliseconds === null ? "" : new Date(milliseconds).toISOString();
  }

  function difference(left, right) {
    const start = timestamp(left);
    const end = timestamp(right);
    return start === null || end === null ? null : Math.max(0, end - start);
  }

  function formatDuration(milliseconds) {
    if (!Number.isFinite(milliseconds) || milliseconds < 0) return "—";
    const seconds = Math.floor(milliseconds / 1000);
    if (seconds < 60) return `${seconds} сек.`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} мин.`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} ч ${minutes % 60} мин.`;
    const days = Math.floor(hours / 24);
    return `${days} дн. ${hours % 24} ч`;
  }

  function formatUtc(value, locale = "ru-RU") {
    const milliseconds = timestamp(value);
    if (milliseconds === null) return "Дата не указана";
    return `${new Intl.DateTimeFormat(locale, {
      dateStyle: "short",
      timeStyle: "medium",
      timeZone: "UTC",
    }).format(milliseconds)} UTC`;
  }

  const api = Object.freeze({ difference, formatDuration, formatUtc, timestamp, toUtcIso });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.MacAnalyzerTime = api;
})();

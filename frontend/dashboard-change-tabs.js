(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.MacAnalyzerDashboardChangeTabs = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const tabs = Object.freeze(["all", "critical", "added", "removed", "modified"]);

  function normalizeTab(value) {
    const tab = String(value || "all");
    return tabs.includes(tab) ? tab : "all";
  }

  function filtersForTab(value) {
    const tab = normalizeTab(value);
    return tab === "critical" ? { severity: "critical", type: "all" } : { severity: "all", type: tab };
  }

  function tabForFilters(severity, type) {
    const normalizedSeverity = String(severity || "all");
    const normalizedType = String(type || "all");
    if (normalizedSeverity === "critical" && normalizedType === "all") return "critical";
    if (normalizedSeverity === "all" && tabs.includes(normalizedType) && normalizedType !== "critical") return normalizedType;
    return "";
  }

  function nextTab(current, key) {
    const index = Math.max(0, tabs.indexOf(normalizeTab(current)));
    if (key === "Home") return tabs[0];
    if (key === "End") return tabs[tabs.length - 1];
    if (key === "ArrowRight") return tabs[(index + 1) % tabs.length];
    if (key === "ArrowLeft") return tabs[(index - 1 + tabs.length) % tabs.length];
    return normalizeTab(current);
  }

  return { tabs, normalizeTab, filtersForTab, tabForFilters, nextTab };
});

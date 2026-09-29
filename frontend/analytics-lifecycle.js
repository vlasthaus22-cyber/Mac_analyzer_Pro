(() => {
  "use strict";

  function durable(state = {}) {
    return Boolean(state.resultSnapshotId || state.resultBrowserSnapshotId);
  }

  function total(state = {}) {
    const stored = Number(state.resultDeviceCount || 0);
    return durable(state) && stored > 0 ? stored : Array.isArray(state.devices) ? state.devices.length : 0;
  }

  function previewCount(state = {}) {
    return Array.isArray(state.devices) ? state.devices.length : 0;
  }

  function partialPreview(state = {}) {
    return durable(state) && total(state) > previewCount(state);
  }

  function sourceKey(state = {}, settings = {}) {
    return JSON.stringify({
      backend: String(state.resultSnapshotId || ""),
      browser: String(state.resultBrowserSnapshotId || ""),
      total: total(state),
      settings: settings && typeof settings === "object" ? settings : {},
    });
  }

  function fallbackMode(state = {}, cache = null, key = "") {
    if (cache?.key === key && cache.data) return "cached";
    if (partialPreview(state)) return "preserve";
    return "local";
  }

  window.MacAnalyzerAnalyticsLifecycle = Object.freeze({
    durable,
    total,
    previewCount,
    partialPreview,
    sourceKey,
    fallbackMode,
  });
})();

(() => {
  "use strict";

  function durable(state = {}) {
    const stored = Number(state.resultDeviceCount || 0);
    const preview = previewCount(state);
    return Boolean(state.resultSnapshotId || state.resultBrowserSnapshotId || stored > preview);
  }

  function total(state = {}) {
    const stored = Number(state.resultDeviceCount || 0);
    return stored > previewCount(state) ? stored : Array.isArray(state.devices) ? state.devices.length : stored;
  }

  function previewCount(state = {}) {
    return Array.isArray(state.devices) ? state.devices.length : 0;
  }

  function partialPreview(state = {}) {
    return total(state) > previewCount(state);
  }

  function activeStorage(state = {}) {
    if (state.resultBrowserSnapshotId) return "browser";
    if (state.resultSnapshotId) return "backend";
    return "";
  }

  function isFinalSnapshot(snapshot = {}) {
    const kind = String(snapshot.kind || "").toLowerCase();
    const name = String(snapshot.name || "").toLowerCase();
    return kind === "analysis" || name.startsWith("анализ:") || name.startsWith("analysis:");
  }

  function snapshotTime(snapshot = {}) {
    return Date.parse(snapshot.savedAt || snapshot.createdAt || snapshot.fileCreatedAt || snapshot.date || "") || 0;
  }

  function finalCandidates(state = {}) {
    return (Array.isArray(state.snapshots) ? state.snapshots : [])
      .filter(isFinalSnapshot)
      .slice()
      .sort((left, right) => {
        const leftTime = snapshotTime(left);
        const rightTime = snapshotTime(right);
        if (leftTime && rightTime && leftTime !== rightTime) return rightTime - leftTime;
        return Number(right.snapshotOrder || 0) - Number(left.snapshotOrder || 0) || rightTime - leftTime;
      });
  }

  function restoredReferences(restored = {}) {
    const backend = String(restored.resultSnapshotId || "");
    const browser = String(restored.resultBrowserSnapshotId || "");
    const snapshots = Array.isArray(restored.snapshots) ? restored.snapshots : [];
    if (browser) return { backend: "", browser };
    if (backend) {
      const metadata = snapshots.find((item) => String(item?.id || item?.snapshotId || "") === backend);
      if (metadata?.browserStored && !metadata?.backendStored) return { backend: "", browser: backend };
      return { backend, browser: "" };
    }
    const active = String(restored.activeSnapshotId || "");
    if (!active) return { backend: "", browser: "" };
    const storage = String(restored.activeSnapshotStorage || "").toLowerCase();
    const metadata = snapshots.find((item) => String(item?.id || item?.snapshotId || "") === active);
    if (storage === "browser" || (metadata?.browserStored && !metadata?.backendStored)) {
      return { backend: "", browser: active };
    }
    if (storage === "backend" || metadata?.backendStored) return { backend: active, browser: "" };
    // Старые autosave не указывали тип хранилища. Не угадываем: приложение
    // проверит фактическое наличие снимка в IndexedDB/SQLite.
    return { backend: "", browser: "" };
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
    activeStorage,
    finalCandidates,
    restoredReferences,
  });
})();

(() => {
  "use strict";

  const list = (value) => (Array.isArray(value) ? value : []);
  const workspacePreviewRows = 101;
  const maxInlineResultRows = 20_000;

  function cloneSafe(value, seen = new WeakSet(), depth = 0) {
    if (value === null || value === undefined || ["string", "number", "boolean"].includes(typeof value)) return value;
    if (["function", "symbol"].includes(typeof value)) return undefined;
    if (typeof value === "bigint") return String(value);
    if (value instanceof Date) return Number.isFinite(value.valueOf()) ? value.toISOString() : "";
    if (typeof Blob !== "undefined" && value instanceof Blob) return value;
    if (typeof value !== "object" || depth > 10 || seen.has(value)) return undefined;
    seen.add(value);
    if (Array.isArray(value)) return value.map((item) => cloneSafe(item, seen, depth + 1)).filter((item) => item !== undefined);
    const result = {};
    for (const [key, item] of Object.entries(value)) {
      const safe = cloneSafe(item, seen, depth + 1);
      if (safe !== undefined) result[key] = safe;
    }
    return result;
  }

  function compactTransientState(source = {}) {
    return {
      ...source,
      // The complete DDIO result is already stored in the Final device rows and the
      // original DDIO file is kept in sourceFiles. Persisting this derived index in
      // the workspace record duplicates it and can make a single structured clone
      // hundreds of megabytes large.
      ddioOverlay: {},
      dashboardFleetCache: null,
    };
  }

  function compactFiles(files, preserveBrowserRows) {
    return list(files).map((file) => ({
      ...file,
      rows: preserveBrowserRows && !file.fileToken ? list(file.rows).slice(0, workspacePreviewRows) : [],
    }));
  }

  function compactSnapshots(snapshots) {
    // A workspace record is metadata, not a second snapshot database. Older
    // workspaces may still contain inline rows, so always remove them before
    // IndexedDB performs the structured clone. Complete rows live in the
    // chunked snapshot store (or SQLite).
    return list(snapshots).slice(0, 25).map((snapshot) => ({
      ...snapshot,
      deviceCount: Math.max(0, Number(snapshot?.deviceCount ?? snapshot?.devices?.length ?? 0) || 0),
      invalidCount: Math.max(0, Number(snapshot?.invalidCount ?? snapshot?.invalid?.length ?? 0) || 0),
      devices: [],
      invalid: [],
    }));
  }

  function compactLocalState(source = {}) {
    return cloneSafe({
      ...compactTransientState(source),
      browserStateInIndexedDb: true,
      files: compactFiles(source.files, false),
      ddioFile: source.ddioFile ? {...source.ddioFile, rows: []} : null,
      devices: [],
      invalid: [],
      snapshots: compactSnapshots(source.snapshots),
      movementHistory: list(source.movementHistory).slice(0, 100),
    });
  }

  function compactIndexedState(source = {}) {
    const snapshotBackedResult = Boolean(
      source.resultSnapshotId
      || (source.resultBrowserSnapshotId && source.resultBrowserSnapshotDirty !== true),
    );
    const resultRows = list(source.devices);
    const invalidRows = list(source.invalid);
    const inlineResult = !snapshotBackedResult
      && resultRows.length + invalidRows.length <= maxInlineResultRows;
    return cloneSafe({
      ...compactTransientState(source),
      browserStateInIndexedDb: true,
      files: compactFiles(source.files, true),
      ddioFile: source.ddioFile ? {...source.ddioFile, rows: list(source.ddioFile.rows).slice(0, workspacePreviewRows)} : null,
      devices: inlineResult ? resultRows : [],
      invalid: inlineResult ? invalidRows : [],
      resultPersistenceTruncated: !snapshotBackedResult && !inlineResult,
      snapshots: compactSnapshots(source.snapshots),
      movementHistory: list(source.movementHistory).slice(0, 100),
    });
  }

  window.MacAnalyzerStatePersistence = Object.freeze({
    compactIndexedState,
    compactLocalState,
    maxInlineResultRows,
  });
  document.documentElement.dataset.statePersistence = "ready";
})();

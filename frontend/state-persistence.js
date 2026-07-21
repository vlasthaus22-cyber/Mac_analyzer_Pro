(() => {
  "use strict";

  const list = (value) => (Array.isArray(value) ? value : []);
  const workspacePreviewRows = 101;

  function compactFiles(files, preserveBrowserRows) {
    return list(files).map((file) => ({
      ...file,
      rows: preserveBrowserRows && !file.fileToken ? list(file.rows).slice(0, workspacePreviewRows) : [],
    }));
  }

  function compactSnapshots(snapshots) {
    return list(snapshots).slice(0, 25).map((snapshot) => (
      snapshot.backendStored || snapshot.browserStored ? { ...snapshot, devices: [] } : snapshot
    ));
  }

  function compactLocalState(source = {}) {
    return {
      ...source,
      browserStateInIndexedDb: true,
      files: compactFiles(source.files, false),
      devices: [],
      invalid: [],
      snapshots: list(source.snapshots).slice(0, 25).map((snapshot) => ({ ...snapshot, devices: [] })),
      movementHistory: list(source.movementHistory).slice(0, 100),
    };
  }

  function compactIndexedState(source = {}) {
    const snapshotBackedResult = Boolean(
      source.resultSnapshotId
      || (source.resultBrowserSnapshotId && source.resultBrowserSnapshotDirty !== true),
    );
    return {
      ...source,
      browserStateInIndexedDb: true,
      files: compactFiles(source.files, true),
      devices: snapshotBackedResult ? [] : list(source.devices),
      invalid: snapshotBackedResult ? [] : list(source.invalid),
      snapshots: compactSnapshots(source.snapshots),
      movementHistory: list(source.movementHistory).slice(0, 100),
    };
  }

  window.MacAnalyzerStatePersistence = Object.freeze({
    compactIndexedState,
    compactLocalState,
  });
  document.documentElement.dataset.statePersistence = "ready";
})();

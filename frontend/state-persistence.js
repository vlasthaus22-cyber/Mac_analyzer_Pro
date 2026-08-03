(() => {
  "use strict";

  const list = (value) => (Array.isArray(value) ? value : []);
  const workspacePreviewRows = 101;
  const maxInlineResultRows = 20_000;

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
      ddioFile: source.ddioFile ? {...source.ddioFile, rows: []} : null,
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
    const resultRows = list(source.devices);
    const invalidRows = list(source.invalid);
    const inlineResult = !snapshotBackedResult
      && resultRows.length + invalidRows.length <= maxInlineResultRows;
    return {
      ...source,
      browserStateInIndexedDb: true,
      files: compactFiles(source.files, true),
      ddioFile: source.ddioFile ? {...source.ddioFile, rows: list(source.ddioFile.rows).slice(0, workspacePreviewRows)} : null,
      devices: inlineResult ? resultRows : [],
      invalid: inlineResult ? invalidRows : [],
      resultPersistenceTruncated: !snapshotBackedResult && !inlineResult,
      snapshots: compactSnapshots(source.snapshots),
      movementHistory: list(source.movementHistory).slice(0, 100),
    };
  }

  window.MacAnalyzerStatePersistence = Object.freeze({
    compactIndexedState,
    compactLocalState,
    maxInlineResultRows,
  });
  document.documentElement.dataset.statePersistence = "ready";
})();

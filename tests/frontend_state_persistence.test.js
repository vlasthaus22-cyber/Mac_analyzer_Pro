"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/state-persistence.js");

const persistence = global.MacAnalyzerStatePersistence;
assert.ok(persistence, "state persistence module must be exported");
assert.equal(document.documentElement.dataset.statePersistence, "ready");

const serverRows = [["MAC"], ["001122334455"], ["001122334466"]];
const browserRows = [["MAC"], ["AABBCCDDEEFF"]];
const source = {
  resultSnapshotId: "snapshot-1",
  files: [
    { name: "server.xlsx", fileToken: "token-1", rows: serverRows },
    { name: "standalone.xlsx", fileToken: "", rows: browserRows },
  ],
  devices: [{ mac: "001122334455" }],
  invalid: [{ row: 9 }],
  snapshots: [
    { id: "snapshot-1", backendStored: true, devices: [{ mac: "001122334455" }] },
    { id: "snapshot-2", browserStored: true, devices: [{ mac: "AABBCCDDEEFF" }] },
  ],
  movementHistory: Array.from({ length: 130 }, (_, index) => ({ index })),
};

const indexed = persistence.compactIndexedState(source);
assert.deepEqual(indexed.files[0].rows, [], "server-cached rows must not be cloned into IndexedDB");
assert.deepEqual(indexed.files[1].rows, browserRows, "standalone rows must remain available without backend");
assert.deepEqual(indexed.devices, [], "SQLite-backed result page must not be cloned into IndexedDB");
assert.deepEqual(indexed.invalid, []);
assert.deepEqual(indexed.snapshots[0].devices, []);
assert.deepEqual(indexed.snapshots[1].devices, [], "browser snapshot rows must live in the dedicated IndexedDB store");
assert.equal(indexed.movementHistory.length, 100);
assert.equal(source.files[0].rows.length, 3, "compaction must not mutate live workspace state");

const standalone = persistence.compactIndexedState({ ...source, resultSnapshotId: "", files: [source.files[1]] });
assert.deepEqual(standalone.files[0].rows, browserRows);
assert.deepEqual(standalone.devices, source.devices, "browser-only results must remain available");

const browserSnapshot = persistence.compactIndexedState({
  ...source,
  resultSnapshotId: "",
  resultBrowserSnapshotId: "snapshot-2",
  resultBrowserSnapshotDirty: false,
  files: [source.files[1]],
});
assert.deepEqual(browserSnapshot.devices, [], "snapshot-backed browser results must not be cloned twice");
assert.deepEqual(browserSnapshot.invalid, []);

const dirtyBrowserSnapshot = persistence.compactIndexedState({
  ...source,
  resultSnapshotId: "",
  resultBrowserSnapshotId: "snapshot-2",
  resultBrowserSnapshotDirty: true,
  files: [source.files[1]],
});
assert.deepEqual(dirtyBrowserSnapshot.devices, source.devices, "manually changed browser results must remain recoverable");

const local = persistence.compactLocalState(source);
assert.deepEqual(local.files.map((file) => file.rows), [[], []]);
assert.deepEqual(local.devices, []);
assert.deepEqual(local.invalid, []);

console.log("frontend state persistence test passed");

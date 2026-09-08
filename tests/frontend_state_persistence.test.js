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
    { id: "legacy-inline", devices: Array.from({ length: 25000 }, (_, index) => ({ mac: `001122${index.toString(16).padStart(6, "0")}` })), invalid: [{ row: 4 }] },
  ],
  movementHistory: Array.from({ length: 130 }, (_, index) => ({ index })),
  ddioOverlay: Object.fromEntries(Array.from({ length: 1000 }, (_, index) => [`MAC-${index}`, { possibleIps: ["192.0.2.1"] }])),
  dashboardFleetCache: { rows: Array.from({ length: 1000 }, (_, index) => index) },
};

const indexed = persistence.compactIndexedState(source);
assert.deepEqual(indexed.files[0].rows, [], "server-cached rows must not be cloned into IndexedDB");
assert.deepEqual(indexed.files[1].rows, browserRows, "standalone rows must remain available without backend");
assert.deepEqual(indexed.devices, [], "SQLite-backed result page must not be cloned into IndexedDB");
assert.deepEqual(indexed.invalid, []);
assert.deepEqual(indexed.snapshots[0].devices, []);
assert.deepEqual(indexed.snapshots[1].devices, [], "browser snapshot rows must live in the dedicated IndexedDB store");
assert.deepEqual(indexed.snapshots[2].devices, [], "legacy inline snapshot rows must never be cloned into the workspace record");
assert.deepEqual(indexed.snapshots[2].invalid, []);
assert.equal(indexed.snapshots[2].deviceCount, 25000);
assert.equal(indexed.movementHistory.length, 100);
assert.equal(source.files[0].rows.length, 3, "compaction must not mutate live workspace state");
assert.deepEqual(indexed.ddioOverlay, {}, "derived DDIO index must not be cloned into the workspace record");
assert.equal(indexed.dashboardFleetCache, null, "derived dashboard cache must be rebuilt instead of persisted");
assert.equal(Object.keys(source.ddioOverlay).length, 1000, "workspace compaction must not mutate the live DDIO index");
const cyclic = {}; cyclic.self = cyclic;
const cloneSafeState = persistence.compactIndexedState({ files: [], snapshots: [{ id: "safe", callback: () => true }], rogue: cyclic });
assert.equal("callback" in cloneSafeState.snapshots[0], false, "non-cloneable callback metadata must be removed");
assert.equal("self" in cloneSafeState.rogue, false, "cyclic metadata must not break autosave");

const standalone = persistence.compactIndexedState({ ...source, resultSnapshotId: "", files: [source.files[1]] });
assert.deepEqual(standalone.files[0].rows, browserRows);
assert.deepEqual(standalone.devices, source.devices, "browser-only results must remain available");
assert.equal(standalone.resultPersistenceTruncated, false);

const oversizedFallbackDevices = Array.from(
  { length: persistence.maxInlineResultRows + 1 },
  (_, index) => ({ mac: `AABBCC${index.toString(16).padStart(6, "0")}` }),
);
const oversizedFallback = persistence.compactIndexedState({
  resultSnapshotId: "",
  resultBrowserSnapshotId: "",
  devices: oversizedFallbackDevices,
  invalid: [],
});
assert.deepEqual(oversizedFallback.devices, [], "failed snapshot fallback must not clone a huge result");
assert.equal(oversizedFallback.resultPersistenceTruncated, true);
assert.equal(oversizedFallbackDevices.length, persistence.maxInlineResultRows + 1, "live result must stay intact");

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

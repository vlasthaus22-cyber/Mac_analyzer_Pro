"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
require("../frontend/analytics-lifecycle.js");

const lifecycle = global.MacAnalyzerAnalyticsLifecycle;
assert.ok(lifecycle);

const fullReference = {
  resultSnapshotId: "final-24",
  resultDeviceCount: 12_237,
  devices: Array.from({ length: 50 }, (_, index) => ({ id: index })),
};
const key = lifecycle.sourceKey(fullReference, { status: "all" });

assert.equal(lifecycle.total(fullReference), 12_237);
assert.equal(lifecycle.previewCount(fullReference), 50);
assert.equal(lifecycle.partialPreview(fullReference), true);
assert.equal(
  lifecycle.fallbackMode(fullReference, null, key),
  "preserve",
  "a 50-row preview must never replace analytics for the full Final",
);
assert.equal(
  lifecycle.fallbackMode(fullReference, { key, data: { metrics: { total: 12_237 } } }, key),
  "cached",
  "the last complete payload must survive a transient refresh failure",
);
assert.equal(
  lifecycle.fallbackMode({ devices: [{}, {}] }, null, "local"),
  "local",
  "an in-memory complete result may use local analytics",
);

const lostReference = {
  resultDeviceCount: 12_249,
  devices: Array.from({ length: 50 }, (_, index) => ({ id: index })),
  snapshots: [
    { id: "older", kind: "analysis", snapshotOrder: 13, browserStored: true, deviceCount: 11_573 },
    { id: "latest", kind: "analysis", snapshotOrder: 14, browserStored: true, deviceCount: 12_249 },
  ],
};
assert.equal(lifecycle.durable(lostReference), true, "a lost reference must not turn a preview into a complete result");
assert.equal(lifecycle.total(lostReference), 12_249);
assert.equal(lifecycle.partialPreview(lostReference), true);
assert.equal(lifecycle.fallbackMode(lostReference, null, "lost"), "preserve");
assert.equal(lifecycle.finalCandidates(lostReference)[0].id, "latest");

assert.deepEqual(
  lifecycle.restoredReferences({
    activeSnapshotId: "browser-final",
    activeSnapshotStorage: "browser",
  }),
  { backend: "", browser: "browser-final" },
);
assert.deepEqual(
  lifecycle.restoredReferences({
    activeSnapshotId: "legacy-unknown",
  }),
  { backend: "", browser: "" },
  "an old untyped autosave must not be misclassified as a backend snapshot",
);
assert.deepEqual(
  lifecycle.restoredReferences({
    resultSnapshotId: "misclassified-browser-final",
    snapshots: [{ id: "misclassified-browser-final", browserStored: true, backendStored: false }],
  }),
  { backend: "", browser: "misclassified-browser-final" },
  "a legacy browser snapshot stored in resultSnapshotId must be repaired",
);

console.log("frontend analytics lifecycle test passed");

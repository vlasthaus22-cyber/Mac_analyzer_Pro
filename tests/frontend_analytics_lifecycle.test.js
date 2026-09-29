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

console.log("frontend analytics lifecycle test passed");

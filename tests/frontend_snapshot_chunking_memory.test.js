"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/browser-snapshot-store.js");

const snapshots = global.MacAnalyzerBrowserSnapshots;
assert.ok(snapshots);
assert.equal(snapshots.snapshotChunkRows, 1_000);

const devices = Array.from({ length: 120_000 }, (_, index) => ({
  mac: `A1B2C3${index.toString(16).padStart(6, "0").toUpperCase()}`,
  vendor: "Stress Vendor",
  model: `Model ${index % 20}`,
  room: String(100 + index % 500),
}));

for (let round = 0; round < 4; round += 1) {
  let chunks = 0;
  let rows = 0;
  for (const chunk of snapshots.chunkRows(devices)) {
    chunks += 1;
    rows += chunk.rows.length;
    assert.ok(chunk.rows.length <= 1_000);
    assert.notStrictEqual(chunk.rows, devices);
  }
  assert.equal(chunks, 120);
  assert.equal(rows, devices.length);
}

const collector = snapshots.createPageCollector({ offset: 75_000, limit: 250, query: "stress vendor" });
for (const chunk of snapshots.chunkRows(devices)) collector.accept("device", chunk.rows);
const page = collector.result();
assert.equal(page.items.length, 250);
assert.equal(page.pagination.total, 120_000);
assert.equal(page.pagination.page, 301);
assert.equal(page.summary.devices, 120_000);
assert.equal(page.summary.vendors, 1);
assert.ok(page.items.length < devices.length / 100);

console.log("frontend snapshot chunking memory test passed");

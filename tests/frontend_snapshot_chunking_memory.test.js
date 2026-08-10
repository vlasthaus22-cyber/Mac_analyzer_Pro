"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/browser-snapshot-store.js");

const snapshots = global.MacAnalyzerBrowserSnapshots;
assert.ok(snapshots);
assert.equal(snapshots.snapshotChunkRows, 1_000);
assert.equal(typeof snapshots.beginStreamedSnapshot, "function");
assert.equal(typeof snapshots.appendStreamedSnapshotChunk, "function");
assert.equal(typeof snapshots.finishStreamedSnapshot, "function");
assert.equal(typeof snapshots.copySnapshotWithTransform, "function");
assert.equal(typeof snapshots.updateSnapshotWithTransform, "function");
assert.equal(typeof snapshots.transformChunkRows, "function");
assert.equal(typeof snapshots.matchesDashboardFilter, "function");
assert.equal(snapshots.matchesDashboardFilter({ vendor: "Cisco", room: "101" }, { room: "101" }), true);
assert.equal(snapshots.matchesDashboardFilter({ vendor: "Cisco", room: "101" }, { room: "202" }), false);
assert.equal(snapshots.matchesDashboardFilter({ vendor: "Cisco", room: "101" }, { vendor: "Cisco", room: "101" }), true);
assert.equal(snapshots.matchesDashboardFilter({ vendor: "Unknown", room: "101" }, { showUnknown: false }), false);
assert.equal(snapshots.matchesDashboardFilter({ mac: "AA:BB:CC:00:00:01", smartroomId: "SR-101", address: "Building A" }, { query: "sr-101" }), true);
assert.equal(snapshots.matchesDashboardFilter({ mac: "AA:BB:CC:00:00:01", smartroomId: "SR-101" }, { query: "aabbcc000001" }), true);
assert.equal(snapshots.matchesDashboardFilter({ mac: "AA:BB:CC:00:00:01", smartroomId: "SR-101" }, { query: "SR-999" }), false);

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

const sortedCollector = snapshots.createPageCollector({ offset: 0, limit: 25, query: "stress vendor", sortField: "model", sortDirection: "desc" });
for (const chunk of snapshots.chunkRows(devices)) sortedCollector.accept("device", chunk.rows);
const sortedPage = sortedCollector.result();
assert.equal(sortedPage.items.length, 25);
assert.equal(sortedPage.pagination.sortWindowLimit, 100_000);
assert.ok(sortedPage.items.every((item) => item.model === "Model 19"));

(async () => {
  const chunk = devices.slice(0, 1_000);
  const changed = await snapshots.transformChunkRows(chunk, (device) => {
    if (device.room !== "100") return false;
    device.address = "Корпус 1";
    return true;
  });
  assert.equal(changed, 2);
  assert.equal(chunk.filter((device) => device.address === "Корпус 1").length, 2);
  assert.ok(chunk.length <= snapshots.snapshotChunkRows);
  console.log("frontend snapshot chunking memory test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

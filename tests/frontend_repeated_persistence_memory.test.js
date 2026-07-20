"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/state-persistence.js");

const persistence = global.MacAnalyzerStatePersistence;
const count = 100_000;
const rows = [["MAC", "Vendor", "Model"]];
const devices = [];
for (let index = 0; index < count; index += 1) {
  const suffix = index.toString(16).toUpperCase().padStart(6, "0");
  rows.push([`A1B2C3${suffix}`, "Stress Vendor", `Model ${index % 20}`]);
  devices.push({ mac: `A1B2C3${suffix}`, vendor: "Stress Vendor", model: `Model ${index % 20}` });
}

const source = {
  resultSnapshotId: "",
  resultBrowserSnapshotId: "browser-stress-snapshot",
  resultBrowserSnapshotDirty: false,
  files: [{ id: "primary", name: "stress.xlsx", fileToken: "", rows, headers: rows[0] }],
  devices,
  invalid: [],
  snapshots: [{ id: "browser-stress-snapshot", browserStored: true, devices }],
  movementHistory: [],
};

for (let round = 0; round < 4; round += 1) {
  const indexed = persistence.compactIndexedState(source);
  assert.equal(indexed.devices.length, 0, `round ${round + 1}: result rows must stay in snapshot-store only`);
  assert.strictEqual(indexed.files[0].rows, rows, `round ${round + 1}: source rows must not be copied in JavaScript`);
  assert.equal(indexed.snapshots[0].devices.length, 0, `round ${round + 1}: snapshot metadata must stay compact`);

  const local = persistence.compactLocalState(source);
  assert.equal(local.devices.length, 0);
  assert.equal(local.files[0].rows.length, 0);
  assert.ok(JSON.stringify(local).length < 10_000, "localStorage payload must remain bounded");
}

console.log("frontend repeated persistence memory test passed");

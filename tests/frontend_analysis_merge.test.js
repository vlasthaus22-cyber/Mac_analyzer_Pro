const assert = require("assert");
const fs = require("fs");
const path = require("path");

const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
const match = app.match(/function mergeAnalysisDevice[\s\S]*?\r?\n  }\r?\n  async function visitLocalRowsForAnalysis/);
assert(match, "mergeAnalysisDevice must remain available to browser enrichment");
const definition = match[0].replace(/\r?\n  async function visitLocalRowsForAnalysis$/, "");
const DeviceIdentity = require("../frontend/device-identity.js");
const mergeAnalysisDevice = Function("DeviceIdentity", `"use strict"; ${definition}; return mergeAnalysisDevice;`)(DeviceIdentity);

const current = {
  mac: "001A11223344",
  model: "Apple TV 4K",
  switchPort: "Gi1/0/10",
  address: "",
  source: "current.csv",
};
const historicalEnrichment = {
  mac: "001A11223344",
  model: "Apple TV",
  switchPort: "Gi1/0/8",
  address: "Building A",
  source: "previous.csv",
};

const merged = mergeAnalysisDevice(current, historicalEnrichment, { preferExisting: true });
assert.strictEqual(merged.model, "Apple TV 4K");
assert.strictEqual(merged.switchPort, "Gi1/0/10");
assert.strictEqual(merged.address, "Building A");
assert.strictEqual(merged.source, "current.csv + previous.csv");
assert.strictEqual(merged.hasConflict, true);
assert.ok(merged.conflicts.some((item) => item.field === "model" && item.alternative === "Apple TV"));

assert.strictEqual(
  mergeAnalysisDevice(current, { model: "Apple TV 5K" }, { preferExisting: false }).model,
  "Apple TV 5K",
  "a later row in the primary file may update its own value",
);

console.log("frontend_analysis_merge.test.js: ok");

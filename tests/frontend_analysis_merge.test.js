const assert = require("assert");
const fs = require("fs");
const path = require("path");

const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
const match = app.match(/function mergeAnalysisDevice[\s\S]*?\r?\n  }\r?\n  async function visitLocalRowsForAnalysis/);
assert(match, "mergeAnalysisDevice must remain available to browser enrichment");
const definition = match[0].replace(/\r?\n  async function visitLocalRowsForAnalysis$/, "");
const mergeAnalysisDevice = Function(`"use strict"; ${definition}; return mergeAnalysisDevice;`)();

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

assert.deepStrictEqual(
  mergeAnalysisDevice(current, historicalEnrichment, { preferExisting: true }),
  {
    mac: "001A11223344",
    model: "Apple TV 4K",
    switchPort: "Gi1/0/10",
    address: "Building A",
    source: "current.csv",
  },
  "enrichment fills blanks but never overwrites current final values",
);

assert.strictEqual(
  mergeAnalysisDevice(current, { model: "Apple TV 5K" }, { preferExisting: false }).model,
  "Apple TV 5K",
  "a later row in the primary file may update its own value",
);

console.log("frontend_analysis_merge.test.js: ok");

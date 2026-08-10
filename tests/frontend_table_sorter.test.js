"use strict";

const assert = require("node:assert/strict");
global.window = globalThis;
require("../frontend/table-sorter.js");

const sorter = global.MacAnalyzerTableSorter;
assert.ok(sorter);
assert.equal(sorter.compareValues("2", "10") < 0, true);
assert.equal(sorter.compareValues("10.2.0.9", "10.2.0.10") < 0, true);
assert.equal(sorter.compareValues("02.08.2026 10:00", "10.08.2026 09:00") < 0, true);
assert.equal(sorter.compareValues("", "Cisco") > 0, true);
assert.equal(typeof sorter.sortTable, "function");
console.log("frontend table sorter test passed");

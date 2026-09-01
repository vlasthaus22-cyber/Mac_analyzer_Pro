"use strict";

const assert = require("node:assert/strict");
const validation = require("../frontend/record-validation.js");

assert.equal(validation.isEmptyRow(["", "  ", null]), true);
assert.equal(validation.isEmptyRow(["", "device"]), false);

const invalidMac = validation.invalidIdentity({
  row: ["GG:11", "room"],
  rowNumber: 7,
  source: "main.xlsx",
  sourceRole: "primary",
  rawMac: "GG:11",
  macColumn: 0,
});
assert.equal(invalidMac.errorCode, "INVALID_MAC");
assert.equal(invalidMac.macHexLength, 2);
assert.match(invalidMac.explanation, /2 из 12/);
assert.match(invalidMac.suggestion, /Исправьте MAC/);

const missing = validation.invalidIdentity({ row: ["", "Room 1"], rowNumber: 3 });
assert.equal(missing.errorCode, "MISSING_IDENTITY");
assert.match(missing.explanation, /не заполнены MAC/);

console.log("frontend record validation test passed");

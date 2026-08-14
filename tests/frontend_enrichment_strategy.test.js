"use strict";

const assert = require("node:assert/strict");
const identity = require("../frontend/device-identity.js");
const strategy = require("../frontend/enrichment-strategy.js");

function merge(previous, incoming, { preferExisting = false } = {}) {
  const result = { ...(previous || {}) };
  for (const [field, value] of Object.entries(incoming || {})) {
    if (value === "" || value === undefined || value === null) continue;
    if (preferExisting && result[field] !== "" && result[field] !== undefined && result[field] !== null) continue;
    result[field] = value;
  }
  result.sourceRoles = [...new Set([...(previous?.sourceRoles || []), incoming.sourceRole].filter(Boolean))];
  result.internalDeviceId = previous?.internalDeviceId || identity.stableId(result);
  return result;
}

function run(mode) {
  const devices = [], index = identity.buildIndex(), diagnostics = { decisions: [] };
  const resolve = (candidate) => strategy.resolveOrCreate({
    candidate, index, devices, identityApi: identity, merge, strategy: mode,
    sourceRole: candidate.sourceRole, diagnostics,
  });
  resolve({ mac: "001122334455", source: "main.csv", sourceRole: "primary", row: 2 });
  resolve({ mac: "001122334455", room: "Room A", source: "smartroom.csv", sourceRole: "smartroom", row: 2 });
  resolve({ mac: "001122334466", room: "Room B", source: "smartroom.csv", sourceRole: "smartroom", row: 3 });
  return { devices, diagnostics };
}

const noExpansion = run(strategy.NO_EXPANSION);
assert.equal(noExpansion.devices.length, 1);
assert.equal(noExpansion.devices[0].room, "Room A");
assert.equal(noExpansion.diagnostics.decisions[0].code, "NOT_CREATED_FROM_SMARTROOM");

const expansion = run(strategy.ALLOW_EXPANSION);
assert.equal(expansion.devices.length, 2);
assert.equal(expansion.diagnostics.decisions[0].code, "CREATED_FROM_SMARTROOM");

assert.equal(strategy.allowsCreation("ddio", strategy.ALLOW_EXPANSION), false);
assert.equal(strategy.normalize("primary"), strategy.ALLOW_EXPANSION);
assert.equal(strategy.normalize("unexpected"), strategy.NO_EXPANSION);

console.log("frontend enrichment strategy test passed");

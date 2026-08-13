const assert = require("assert");
const Identity = require("../frontend/device-identity.js");

const oldDevice = { mac: "00:11:22:33:44:55", smartroomId: "SR-OLD", hostname: "Codec-1" };
const newDevice = { mac: "001122334455", smartroomId: "SR-NEW", hostname: "codec-1" };
assert.strictEqual(Identity.comparisonKey(oldDevice), Identity.comparisonKey(newDevice));
const index = Identity.buildIndex([oldDevice]);
assert.strictEqual(Identity.find(newDevice, index), oldDevice);
assert.strictEqual(Identity.normalizeMac("00-11-22-33-44-55"), "001122334455");
const paired = Identity.pairSets(
  [{ mac: "001122334455", serialNumber: "SERIAL-1", switchIp: "10.0.0.1" }],
  [{ mac: "AABBCCDDEEFF", serialNumber: " serial-1 ", switchIp: "10.0.0.2" }],
);
assert.strictEqual(paired.pairs.length, 1, "serial number must retain identity when MAC changes");
assert.strictEqual(paired.added.length, 0);
assert.strictEqual(paired.removed.length, 0);
console.log("frontend_device_identity.test.js: ok");

const assert = require("assert");
const Churn = require("../frontend/presence-churn.js");
const d = (mac, extra = {}) => ({ mac, ...extra });
const result = Churn.analyze([
  { id: "1", devices: [d("00:11:22:33:44:55"), d("AA:BB:CC:DD:EE:FF")] },
  { id: "2", devices: [d("AA:BB:CC:DD:EE:FF")] },
  { id: "3", devices: [d("00:11:22:33:44:55", { model: "Cisco" }), d("AA:BB:CC:DD:EE:FF")] },
  { id: "4", devices: [d("AA:BB:CC:DD:EE:FF")] },
  { id: "5", devices: [d("00:11:22:33:44:55", { model: "Cisco" })] },
]);
assert.strictEqual(result.total, 1);
assert.strictEqual(result.items[0].disappearances, 2);
assert.strictEqual(result.items[0].reappearances, 2);
assert.strictEqual(result.items[0].transitionCount, 4);
assert.strictEqual(result.items[0].model, "Cisco");
console.log("frontend presence churn tests passed");

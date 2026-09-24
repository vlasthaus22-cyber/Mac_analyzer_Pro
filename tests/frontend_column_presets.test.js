const assert = require("assert");
const Presets = require("../frontend/column-presets.js");

const main = ["CallingStarionID", "NasIP", "NasPortID", "B_ReceiptTime"];
assert.deepStrictEqual(Presets.mappingForRole(main, "primary"), {
  ...Presets.emptyMapping(), mac: 0, switchIp: 1, switchPort: 2, authenticationTime: 3
});

const smartroom = ["MAC", "IP адрес", "Производитель", "Модель", "Тип модели", "Адрес комнаты", "Название комнаты", "ID комнаты"];
const smart = Presets.mappingForRole(smartroom, "smartroom");
assert.strictEqual(smart.mac, 0);
assert.strictEqual(smart.ip, 1);
assert.strictEqual(smart.vendor, 2);
assert.strictEqual(smart.model, 3);
assert.strictEqual(smart.deviceType, 4);
assert.strictEqual(smart.address, 5);
assert.strictEqual(smart.room, 6);
assert.strictEqual(smart.smartroomId, 7);

assert.deepStrictEqual(Presets.mappingForRole(["Column1", "Column2", "Column3", "Column9", "Column10"], "ddio"), {
  reservationMac: 2, reservationIp: 1, leaseMac: 4, leaseIp: 3
});

console.log("frontend column preset tests passed");

const assert = require("assert");
const vm = require("vm");

global.window = global;
global.Blob = class FakeBlob { constructor(parts) { this.source = parts.join(""); } };
global.URL = { createObjectURL(blob) { return blob.source; } };
global.Worker = class FakeWorker {
  constructor(source) {
    const owner = this;
    const self = {
      onmessage: null,
      postMessage(data) { queueMicrotask(() => owner.onmessage?.({ data })); },
    };
    vm.runInNewContext(source, { self, Map, Set, Array, Object, String, Date, Error });
    this.workerSelf = self;
  }
  postMessage(data) { queueMicrotask(() => this.workerSelf.onmessage({ data })); }
};

require("../frontend/smartroom-worker.js");

(async () => {
  const first = Array.from({ length: 1001 }, (_value, index) => ({
    mac: `001122${index.toString(16).padStart(6, "0")}`,
    smartroomId: index ? "ROOM-BULK" : "ROOM-1",
    room: index ? "Bulk" : "Переговорная 1",
    switchIp: "10.0.0.1",
    switchPort: `Gi${index}`,
  }));
  const second = [{ mac: first[0].mac, smartroomId: "ROOM-1", room: "Переговорная 1", city: "Москва", address: "Ленина 1", switchIp: "10.0.0.2", switchPort: "Gi9" }];
  const report = await global.MacAnalyzerSmartroomWorker.build([
    { id: "before", createdAt: "2026-08-01T00:00:00Z", devices: first },
    { id: "after", createdAt: "2026-08-02T00:00:00Z", devices: second },
  ], { ddioOverlay: { [first[0].mac]: { ip: "192.168.1.20", possibleIps: ["192.168.1.20", "192.168.1.30"] } } });

  assert.strictEqual(report.snapshots[0].total, 1001, "chunks must remain one logical snapshot");
  assert.strictEqual(report.criticalSwitchChanges.length, 1);
  assert.deepStrictEqual(Array.from(report.criticalSwitchChanges[0].possibleIps), ["192.168.1.20", "192.168.1.30"]);
  assert.strictEqual(report.criticalSwitchChanges[0].source, "DDIO");
  assert.strictEqual(report.macTimelines[first[0].mac].length, 2, "the full MAC chain is retained");
  assert.strictEqual(report.rooms.find((room) => room.smartroomId === "ROOM-BULK").missing.length, 1000);
  assert.strictEqual(report.rooms.find((room) => room.smartroomId === "ROOM-1").city, "Москва");

  const large = Array.from({ length: 10000 }, (_value, index) => ({ mac: `AABBCC${index.toString(16).padStart(6, "0")}`, smartroomId: `ROOM-${index}`, switchIp: "10.1.0.1" }));
  large.push({ mac: large[0].mac, smartroomId: "ROOM-DUPLICATE", switchIp: "10.1.0.1" });
  large.push({ mac: "AABBCCDDEEFF", smartroomId: null, switchIp: "10.1.0.1" });
  const startedAt = performance.now();
  const performanceReport = await global.MacAnalyzerSmartroomWorker.build([{ id: "large", createdAt: "2026-08-03T00:00:00Z", devices: large }]);
  const elapsed = performance.now() - startedAt;
  assert.strictEqual(performanceReport.snapshots[0].total, 10001, "strong MAC identity prevents duplicates when Smartroom changes");
  assert.strictEqual(performanceReport.skipped, 0, "a valid device is retained even without Smartroom ID");
  assert.ok(elapsed < 500, `10k aggregation must stay below 500 ms (actual ${elapsed.toFixed(1)} ms)`);
  console.log(`smartroom 10k aggregation: ${elapsed.toFixed(1)} ms`);
  console.log("frontend smartroom worker test passed");
})().catch((error) => { console.error(error); process.exitCode = 1; });

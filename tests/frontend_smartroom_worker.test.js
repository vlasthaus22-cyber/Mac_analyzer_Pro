const assert = require("assert");
const vm = require("vm");

global.window = global;
global.Blob = class FakeBlob {
  constructor(parts) {
    this.source = parts.join("");
  }
};
global.URL = {
  createObjectURL(blob) {
    return blob.source;
  },
};
global.Worker = class FakeWorker {
  constructor(source) {
    const owner = this;
    const self = {
      onmessage: null,
      postMessage(data) {
        queueMicrotask(() => owner.onmessage?.({ data }));
      },
    };
    vm.runInNewContext(source, { self, Map, Set, Array, Object, String, Date, Error });
    this.workerSelf = self;
  }
  postMessage(data) {
    queueMicrotask(() => this.workerSelf.onmessage({ data }));
  }
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
  const second = [
    {
      mac: first[0].mac,
      smartroomId: "ROOM-1",
      room: "Переговорная 1",
      address: "ЦБ, Москва, Центральная, 5, Переговорная 1",
      switchIp: "10.0.0.2",
      switchPort: "Gi9",
    },
  ];
  first.push({ ...first[0], model: "Merged model" });
  const report = await global.MacAnalyzerSmartroomWorker.build(
    [
      { id: "before", createdAt: "2026-08-01T00:00:00Z", devices: first },
      { id: "after", createdAt: "2026-08-02T00:00:00Z", devices: second },
    ],
    { ddioOverlay: { [first[0].mac]: { ip: "192.168.1.20", possibleIps: ["192.168.1.20", "192.168.1.30"] } } },
  );

  assert.strictEqual(
    report.snapshots[0].total,
    1001,
    "chunks and duplicate source rows must remain one logical snapshot",
  );
  assert.strictEqual(report.criticalSwitchChanges.length, 1);
  assert.deepStrictEqual(Array.from(report.criticalSwitchChanges[0].possibleIps), ["192.168.1.20", "192.168.1.30"]);
  assert.strictEqual(report.criticalSwitchChanges[0].source, "DDIO");
  assert.strictEqual(report.macTimelines[first[0].mac].length, 2, "the full MAC chain is retained");
  assert.strictEqual(report.rooms.find((room) => room.smartroomId === "ROOM-BULK").missing.length, 1000);
  assert.strictEqual(report.rooms.find((room) => room.smartroomId === "ROOM-1").city, "Москва");
  assert.strictEqual(report.rooms.find((room) => room.smartroomId === "ROOM-1").tb, "ЦБ");
  assert.strictEqual(report.rooms.find((room) => room.smartroomId === "ROOM-1").site, "Центральная");
  assert.strictEqual(report.rooms.find((room) => room.smartroomId === "ROOM-1").floor, "5");
  assert.strictEqual(report.rooms.find((room) => room.smartroomId === "ROOM-1").history[0].devices.length, 1);
  assert.strictEqual(report.charts.at(-1).changes, 1, "a confirmed switch change must be visible in charts");
  assert.ok(report.charts.at(-1).changedRooms.includes("ROOM-1"));
  assert.ok(report.charts.at(-1).changedRooms.includes("ROOM-BULK"), "a removed room must be counted as changed");
  assert.ok(report.charts.at(-1).changedMacs.includes(first[0].mac));
  assert.ok(
    report.charts.at(-1).changedMacs.includes(first[1].mac),
    "removed MACs must be represented in chart details",
  );

  const roomPathReport = await global.MacAnalyzerSmartroomWorker.build([
    {
      id: "room-path",
      createdAt: "2026-08-02T00:30:00Z",
      devices: [
        {
          mac: "102030405060",
          smartroomId: "ROOM-PATH",
          room: "ЦА, Москва, Кутузовский проспект, 3 этаж, Переговорная 5",
        },
      ],
    },
  ]);
  assert.strictEqual(roomPathReport.rooms[0].tb, "ЦА");
  assert.strictEqual(roomPathReport.rooms[0].city, "Москва");
  assert.strictEqual(roomPathReport.rooms[0].site, "Кутузовский проспект");
  assert.strictEqual(roomPathReport.rooms[0].floor, "3 этаж");
  assert.strictEqual(roomPathReport.rooms[0].room, "Переговорная 5");

  const switchWithoutDeviceId = await global.MacAnalyzerSmartroomWorker.build(
    [
      {
        id: "switch-before",
        createdAt: "2026-08-02T00:40:00Z",
        devices: [{ mac: "ABCDEF123456", smartroomId: "ROOM-NO-ID", switchIp: "10.0.0.1" }],
      },
      {
        id: "switch-after",
        createdAt: "2026-08-02T00:50:00Z",
        devices: [{ mac: "ABCDEF123456", smartroomId: "ROOM-NO-ID", switchIp: "10.0.0.2" }],
      },
    ],
    { ddioOverlay: { ABCDEF123456: { possibleIps: ["192.0.2.44"] } } },
  );
  assert.strictEqual(
    switchWithoutDeviceId.criticalSwitchChanges.length,
    1,
    "a missing Device ID must not break room chronology when switch IP changes",
  );
  assert.deepStrictEqual(Array.from(switchWithoutDeviceId.criticalSwitchChanges[0].possibleIps), ["192.0.2.44"]);

  const invalidReport = await global.MacAnalyzerSmartroomWorker.build([
    {
      id: "invalid",
      createdAt: "2026-08-02T00:00:00Z",
      devices: [
        { mac: "not-a-mac", smartroomId: "ROOM-INVALID", model: "Codec" },
        { mac: "also-bad", smartroomId: "" },
      ],
    },
  ]);
  assert.strictEqual(invalidReport.invalidMacRows, 2);
  assert.strictEqual(invalidReport.skipped, 1);
  assert.strictEqual(
    invalidReport.snapshots[0].total,
    1,
    "room identity may retain a row but malformed MAC must not become a MAC identity",
  );

  const serialReport = await global.MacAnalyzerSmartroomWorker.build([
    {
      id: "serials",
      createdAt: "2026-08-02T01:00:00Z",
      devices: [
        { smartroomId: "ROOM-SERIAL", serialNumber: "SERIAL-1", model: "Codec" },
        { smartroomId: "ROOM-SERIAL", serialNumber: "SERIAL-2", model: "Panel" },
      ],
    },
  ]);
  assert.strictEqual(serialReport.snapshots[0].total, 2, "serial numbers must keep distinct room devices without MAC");
  assert.strictEqual(serialReport.rooms[0].history[0].devices.length, 2);

  const large = Array.from({ length: 10000 }, (_value, index) => ({
    mac: `AABBCC${index.toString(16).padStart(6, "0")}`,
    smartroomId: `ROOM-${index}`,
    switchIp: "10.1.0.1",
  }));
  large.push({ mac: large[0].mac, smartroomId: "ROOM-DUPLICATE", switchIp: "10.1.0.1" });
  large.push({ mac: "AABBCCDDEEFF", smartroomId: null, switchIp: "10.1.0.1" });
  const startedAt = performance.now();
  const performanceReport = await global.MacAnalyzerSmartroomWorker.build([
    { id: "large", createdAt: "2026-08-03T00:00:00Z", devices: large },
  ]);
  const elapsed = performance.now() - startedAt;
  assert.strictEqual(
    performanceReport.snapshots[0].total,
    10001,
    "strong MAC identity prevents duplicates when Smartroom changes",
  );
  assert.strictEqual(performanceReport.skipped, 0, "a valid device is retained even without Smartroom ID");
  assert.ok(elapsed < 500, `10k aggregation must stay below 500 ms (actual ${elapsed.toFixed(1)} ms)`);
  console.log(`smartroom 10k aggregation: ${elapsed.toFixed(1)} ms`);
  console.log("frontend smartroom worker test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

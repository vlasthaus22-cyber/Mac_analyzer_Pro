"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
require("../frontend/full-json-report.js");

const reportBuilder = global.MacAnalyzerFullJsonReport;

(async () => {
  assert.ok(reportBuilder, "full JSON report module must be exported");
  const current = [
    { mac: "001122334455", room: "101", smartroomId: "SR-101" },
    { mac: "AABBCCDDEEFF", room: "102", smartroomId: "SR-102" },
  ];
  const snapshot = {
    id: "final-1",
    name: "Анализ: devices.xlsx",
    kind: "analysis",
    createdAt: "2026-07-29T08:00:00Z",
    devices: current,
  };
  const result = await reportBuilder.createReport({
    state: {
      files: [{ id: "file-1", name: "devices.xlsx", role: "primary", rowCount: 2 }],
      snapshots: [snapshot],
      movementHistory: [{ mac: current[0].mac, field: "room", before: "100", after: "101" }],
      dashboardSettings: { room: "101" },
    },
    analyticsPayload: async () => ({ metrics: { devices: 2, changedRooms: 1 } }),
    streamCurrentRows: async (accept) => accept(current),
    streamInventoryRows: async (accept) => accept([...current, { mac: "112233445566", room: "архив" }]),
    streamInvalidRows: async (accept) => accept([]),
    streamSnapshotRows: async (item, accept) => accept(item.devices),
    maxChunkBytes: 96,
  });
  assert.ok(result.chunks > 1, "small chunks exercise bounded JSON assembly");
  assert.equal(result.currentRows, 2);
  assert.equal(result.snapshotRows, 2);
  assert.equal(result.inventoryRows, 3);
  const reportText = await result.blob.text();
  assert.ok(reportText.split("\n").length > 20, "full JSON must be human-readable, not one line");
  const payload = JSON.parse(reportText);
  assert.equal(payload.format, "mac-analyzer-full-json");
  assert.equal(payload.currentDevices[0].smartroomId, "SR-101");
  assert.equal(payload.snapshots[0].devices[1].smartroomId, "SR-102");
  assert.equal(payload.movementHistory.length, 1);
  assert.equal(payload.allDevices.length, 3, "full JSON must include MAC addresses absent from the current export");
  const devicesOnly = await reportBuilder.createDeviceExport({
    streamRows: async (accept) => accept(current),
    maxChunkBytes: 64,
  });
  const devicesPayload = JSON.parse(await devicesOnly.blob.text());
  assert.equal(devicesOnly.rows, 2);
  assert.equal(devicesPayload.devices[1].mac, "AABBCCDDEEFF");
  assert.ok((await devicesOnly.blob.text()).includes("\n    {"), "device JSON must be formatted across lines");
  console.log("frontend full JSON report test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

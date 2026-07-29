"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/local-analytics.js");

const analytics = global.MacAnalyzerLocalAnalytics;
assert.ok(analytics);
assert.equal(global.document.documentElement.dataset.localAnalytics, "ready");

const devices = [
  { mac: "001122000001", vendor: "Cisco", model: "C9300", ip: "192.0.2.1", address: "Корпус 1", room: "101", smartroomId: "SR-101", switchIp: "10.0.0.1", switchPort: "Gi1/0/1" },
  { mac: "001122000002", vendor: "Cisco", model: "C9300", ip: "192.0.2.2", address: "Корпус 1", room: "101", smartroomId: "SR-101", switchIp: "10.0.0.1", switchPort: "Gi1/0/2" },
  { mac: "AABBCC000003", vendor: "Apple", model: "iPad", room: "202", smartroomId: "SR-202", switchIp: "10.0.0.2", switchPort: "7" },
  { mac: "DDEEFF000004", vendor: "Unknown", model: "", room: "", smartroomId: "", switchIp: "", switchPort: "" },
];

const payload = analytics.build(devices, { invalidCount: 2 });
assert.deepEqual(payload.summary, {
  devices: 4,
  knownVendors: 3,
  unknownVendors: 1,
  uniqueVendors: 2,
  uniqueModels: 2,
  uniqueRooms: 2,
  uniqueSmartrooms: 2,
  uniqueSwitches: 2,
  withIp: 2,
  withRoom: 3,
  withAddress: 2,
  withSwitch: 3,
  withModel: 3,
  invalid: 2,
});
assert.equal(payload.charts.vendors[0].label, "Cisco");
assert.equal(payload.charts.vendors[0].value, 2);
assert.equal(payload.clusters.summary.devices, 4);
assert.equal(payload.clusters.items[0].count, 2);
assert.equal(payload.topology.summary.switches, 2);
assert.equal(payload.topology.summary.ports, 3);
assert.equal(payload.topology.summary.linkedDevices, 3);
assert.equal(payload.topology.summary.unassignedDevices, 1);
assert.equal(payload.topology.nodes[0].switchIp, "10.0.0.1");
assert.equal(payload.topology.nodes[0].ports.length, 2);

const filtered = analytics.build(devices, { vendor: "Cisco", room: "101" });
assert.equal(filtered.summary.devices, 2);
assert.equal(filtered.summary.uniqueVendors, 1);
assert.equal(filtered.summary.uniqueRooms, 1);
assert.equal(filtered.topology.summary.linkedDevices, 2);
const withoutUnknown = analytics.build(devices, { showUnknown: false });
assert.equal(withoutUnknown.summary.devices, 3);
assert.equal(withoutUnknown.summary.unknownVendors, 0);

assert.match(analytics.renderOverview(payload), /Smartroom ID/);
assert.match(analytics.renderClusters(payload), /Cisco · 101 · 10\.0\.0\.1/);
assert.match(analytics.renderTopology(payload), /Gi1\/0\/1/);
assert.match(analytics.clustersCsv(payload), /^\uFEFFПроизводитель;Помещение;IP коммутатора;Устройств/);
assert.match(analytics.topologyDocument(payload), /Топология MAC Analyzer/);
assert.match(analytics.topologyDocument(payload), /10\.0\.0\.1/);
assert.match(analytics.chartsSvg(payload), /^<svg/);
assert.match(analytics.chartsSvg(payload), /Производители/);

const snapshots = [
  { id: "one", name: "Первый", createdAt: "2026-01-01T00:00:00Z", deviceCount: 2 },
  { id: "two", name: "Второй", createdAt: "2026-02-01T00:00:00Z", deviceCount: 4 },
];
assert.match(analytics.renderStatistics(snapshots, 4, 3), /Финальных выгрузок/);
assert.match(analytics.renderTemporal(snapshots), /Второй/);

const collector = analytics.createCollector({ clusterLimit: 100, switchLimit: 100, portLimit: 32 });
for (let chunk = 0; chunk < 20; chunk += 1) {
  collector.accept(Array.from({ length: 1_000 }, (_, index) => ({
    mac: `A1B2C3${(chunk * 1_000 + index).toString(16).padStart(6, "0")}`,
    vendor: `Vendor ${index % 5}`,
    model: `Model ${index % 10}`,
    room: String(100 + index % 20),
    smartroomId: `SR-${100 + index % 20}`,
    switchIp: `10.0.0.${1 + index % 10}`,
    switchPort: String(1 + index % 48),
  })));
}
const streamed = collector.finish();
assert.equal(streamed.summary.devices, 20_000);
assert.equal(streamed.summary.uniqueVendors, 5);
assert.equal(streamed.summary.uniqueRooms, 20);
assert.equal(streamed.summary.uniqueSmartrooms, 20);
assert.equal(streamed.summary.uniqueSwitches, 10);
assert.ok(streamed.clusters.items.length <= 100);
assert.ok(streamed.topology.nodes.every((node) => node.sampleMacs.length <= 12));
assert.ok(streamed.topology.nodes.every((node) => node.ports.every((port) => port.sampleMacs.length <= 8)));

console.log("frontend local analytics test passed");

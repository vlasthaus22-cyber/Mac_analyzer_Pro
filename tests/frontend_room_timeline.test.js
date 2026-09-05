"use strict";

const assert = require("node:assert/strict");
global.window = globalThis;
require("../frontend/room-timeline.js");

const timeline = global.MacAnalyzerRoomTimeline;
const room = {
  smartroomId: "ROOM-1",
  history: [
    {
      date: "2026-01-01T00:00:00Z",
      devices: [{ mac: "001122334455", model: "Unknown", vendor: "Cisco", switchIp: "10.0.0.1", switchPort: "Gi1" }],
    },
    { date: "2026-01-10T00:00:00Z", devices: [{ mac: "AABBCCDDEEFF", model: "Room Kit", vendor: "Cisco" }] },
    {
      date: "2026-01-20T00:00:00Z",
      devices: [{ mac: "AABBCCDDEEFF", model: "Room Kit", vendor: "Cisco", switchIp: "10.0.0.2", switchPort: "Gi9" }],
    },
  ],
};

const events = timeline.events(room);
assert.deepEqual(
  events.map((item) => item.status),
  ["Добавлен", "Удален", "Добавлен", "Перемещен"],
);
assert.equal(events[0].elapsedMs, null);
assert.equal(events[1].elapsedMs, 9 * 24 * 60 * 60 * 1000);
assert.equal(timeline.events({ history: [{ devices: [{ mac: "001122334455" }] }] })[0].date, "");
const rendered = timeline.render(room, { escapeHtml: String, formatDate: String, formatMac: String });
assert.match(rendered.tableHtml, /001122334455/);
assert.match(rendered.tableHtml, /Указать модель/);
assert.match(rendered.timelineHtml, /room-timeline-event/);
assert.match(rendered.timelineHtml, /Через 9 дн\./);
assert.match(rendered.timelineHtml, /Перемещен/);
assert.match(rendered.timelineHtml, /10\.0\.0\.2/);
assert.match(rendered.tableHtml, /IP коммутатора/);

const idOnly = timeline.events({
  history: [
    { date: "2026-01-01T00:00:00Z", devices: [{ deviceId: "unit-1", model: "A" }] },
    { date: "2026-01-02T00:00:00Z", devices: [{ deviceId: "unit-1", model: "B" }] },
  ],
});
assert.deepEqual(
  idOnly.map((item) => item.status),
  ["Добавлен", "Изменен"],
);

const duplicateRows = timeline.events({
  history: [
    {
      date: "2026-01-01T00:00:00Z",
      devices: [
        { mac: "001122334455", model: "Codec" },
        { mac: "00:11:22:33:44:55", vendor: "Cisco" },
      ],
    },
  ],
});
assert.equal(duplicateRows.length, 1, "duplicate source rows must remain one room device event");

const coverage = timeline.compareLatest({
  history: [
    {
      date: "2026-02-01T00:00:00Z",
      devices: [
        { mac: "001122334455", model: "Old" },
        { mac: "AABBCCDDEEFF", model: "Stable" },
      ],
    },
    {
      date: "2026-03-01T00:00:00Z",
      devices: [
        { mac: "001122334455", model: "New" },
        { mac: "AABBCCDDEEFF", model: "Stable" },
      ],
    },
  ],
});
assert.equal(coverage.total, 2);
assert.equal(coverage.changed, 1);
assert.equal(coverage.allChanged, false);
assert.equal(coverage.entries.find((item) => item.mac === "001122334455").status, "Изменен");

const allChanged = timeline.compareLatest({
  history: [
    { date: "2026-02-01T00:00:00Z", devices: [{ mac: "001122334455" }] },
    { date: "2026-03-01T00:00:00Z", devices: [{ mac: "AABBCCDDEEFF" }] },
  ],
});
assert.equal(allChanged.allChanged, true, "replacement means every room device changed between adjacent finals");

const changedMac = timeline.compareLatest({
  history: [
    {
      date: "2026-04-01T00:00:00Z",
      devices: [{ deviceId: "ROOM-CODEC-1", mac: "001122334455", model: "Codec", room: "101" }],
    },
    {
      date: "2026-05-01T00:00:00Z",
      devices: [{ deviceId: "room-codec-1", mac: "AABBCCDDEEFF", model: "Codec", room: "101" }],
    },
  ],
});
assert.equal(changedMac.total, 1, "stable Device ID must pair a device whose MAC changed");
assert.equal(changedMac.changed, 1);
assert.equal(changedMac.entries[0].status, "Изменен");
assert.equal(changedMac.entries[0].changes[0].label, "MAC / физический адрес");

const sparseLegacy = timeline.compareLatest({
  history: [
    { date: "2026-03-01T00:00:00Z", devices: [{ mac: "001122334455", model: "Known model" }] },
    { date: "2026-04-01T00:00:00Z", devices: [{ mac: "001122334455", model: "" }] },
    { date: "2026-05-01T00:00:00Z", devices: [{ mac: "001122334455", model: "Known model" }] },
  ],
});
assert.equal(sparseLegacy.changed, 0, "an empty legacy value must not create a false empty-to-known change");

const absentThenSparse = timeline.events({
  history: [
    { date: "2026-06-01T00:00:00Z", devices: [{ mac: "001122334455", model: "Known model", switchIp: "10.0.0.1" }] },
    { date: "2026-07-01T00:00:00Z", devices: [] },
    { date: "2026-08-01T00:00:00Z", devices: [{ mac: "001122334455", model: "", switchIp: "10.0.0.1" }] },
  ],
});
assert.equal(
  absentThenSparse.some((item) => item.changes?.some((change) => change.label === "Модель")),
  false,
  "a temporary absence must not erase a previously known value and create a false empty-to-known change",
);
console.log("frontend room timeline test passed");

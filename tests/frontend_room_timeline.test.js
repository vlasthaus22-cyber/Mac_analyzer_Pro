"use strict";

const assert = require("node:assert/strict");
global.window = globalThis;
require("../frontend/room-timeline.js");

const timeline = global.MacAnalyzerRoomTimeline;
const room = {
  smartroomId: "ROOM-1",
  history: [
    { date: "2026-01-01T00:00:00Z", devices: [{ mac: "001122334455", model: "Unknown", vendor: "Cisco" }] },
    { date: "2026-01-10T00:00:00Z", devices: [{ mac: "AABBCCDDEEFF", model: "Room Kit", vendor: "Cisco" }] },
  ],
};

const events = timeline.events(room);
assert.deepEqual(
  events.map((item) => item.status),
  ["Добавлен", "Удален", "Добавлен"],
);
assert.equal(events[0].elapsedMs, null);
assert.equal(events[1].elapsedMs, 9 * 24 * 60 * 60 * 1000);
assert.equal(timeline.events({ history: [{ devices: [{ mac: "001122334455" }] }] })[0].date, "");
const rendered = timeline.render(room, { escapeHtml: String, formatDate: String, formatMac: String });
assert.match(rendered.tableHtml, /001122334455/);
assert.match(rendered.tableHtml, /Указать модель/);
assert.match(rendered.timelineHtml, /room-timeline-event/);
assert.match(rendered.timelineHtml, /Через 9 дн\./);
console.log("frontend room timeline test passed");

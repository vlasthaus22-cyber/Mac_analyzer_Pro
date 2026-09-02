"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/mac-chronology.js");

const chronology = global.MacAnalyzerMacChronology;

(async () => {
  assert.ok(chronology, "MAC chronology module must be exported");
  assert.equal(document.documentElement.dataset.macChronology, "ready");
  assert.equal(
    chronology.normalizeMac("00112233445566"),
    "",
    "overlong MAC values must not be truncated into valid devices",
  );

  const requested = "00:11:22:33:44:55";
  const snapshots = [
    {
      id: "old",
      name: "Первая выгрузка",
      source: "first.xlsx",
      createdAt: "2026-07-01T08:00:00Z",
      browserStored: true,
      devices: [],
    },
    {
      id: "new",
      name: "Вторая выгрузка",
      source: "second.xlsx",
      createdAt: "2026-07-02T08:00:00Z",
      browserStored: true,
      devices: [],
    },
  ];
  const stored = new Map([
    [
      "old",
      { mac: requested, vendor: "Cisco", model: "C2960", ip: "10.0.0.10", address: "Главный корпус", room: "101" },
    ],
    [
      "new",
      { mac: requested, vendor: "Cisco", model: "C3560", ip: "10.0.0.10", address: "Главный корпус", room: "202" },
    ],
  ]);
  const calls = [];
  const appearances = await chronology.collectAppearances({
    mac: requested,
    snapshots,
    findSnapshotDevice: async (snapshot, mac) => {
      calls.push([snapshot.id, mac]);
      return stored.get(snapshot.id);
    },
  });

  assert.deepEqual(
    calls.map((item) => item[0]),
    ["old", "new"],
  );
  assert.equal(appearances.length, 2, "browserStored snapshots must contribute to MAC chronology");
  assert.equal(appearances[1].device.room, "202");

  const merged = chronology.mergeAppearances(
    [{ ...appearances[0], device: { ...appearances[0].device, model: "C2960", address: "Корпус A" } }],
    [{ ...appearances[0], device: { ...appearances[0].device, model: "", address: "" } }],
  );
  assert.equal(merged[0].device.model, "C2960", "a sparse duplicate must not erase the old final value");
  assert.equal(merged[0].device.address, "Корпус A");

  const backendAndBrowser = chronology.mergeAppearances(
    [{ ...appearances[0], source: "backend" }],
    [{ ...appearances[0], source: "browser" }],
  );
  assert.equal(
    backendAndBrowser.length,
    1,
    "the same snapshot must not appear twice when backend and browser sources differ",
  );

  const events = chronology.buildEvents({
    appearances,
    movements: [
      {
        mac: requested,
        changedAt: "2026-07-02T08:00:00Z",
        field: "room",
        before: "101",
        after: "202",
        source: "Первая выгрузка → Вторая выгрузка",
        beforeDevice: stored.get("old"),
        afterDevice: stored.get("new"),
      },
    ],
  });
  assert.equal(
    events.length,
    4,
    "chronology must derive sequential snapshot changes without relying on movement history",
  );
  assert.equal(events.find((item) => item.field === "room").fieldLabel, "Помещение");
  assert.ok(events.some((item) => item.field === "model" && item.before === "C2960" && item.after === "C3560"));
  assert.match(events.find((item) => item.field === "model").source, /Final «Первая выгрузка» → Final «Вторая выгрузка»/);

  const sparseEvents = chronology.buildEvents({
    appearances: [appearances[0], { ...appearances[1], device: { ...appearances[1].device, model: "" } }],
  });
  assert.ok(!sparseEvents.some((item) => item.field === "model"), "a missing new value must not create a false change");

  const fullChain = await chronology.getMacHistory({
    mac: requested,
    snapshots,
    findSnapshotDevice: async (snapshot) => stored.get(snapshot.id),
  });
  assert.equal(fullChain.length, 4, "getMacHistory must return the complete chain rather than the last event");
  assert.equal(fullChain[0].date, "2026-07-01T08:00:00Z", "the chain starts with the first appearance");
  assert.equal(fullChain.at(-1).date, "2026-07-02T08:00:00Z", "the chain ends at the current state");

  const timeline = chronology.renderTimeline(events, { formatDate: (value) => value.slice(0, 10) });
  assert.match(timeline, /mac-timeline-item/);
  assert.match(timeline, /Первая выгрузка/);
  assert.match(timeline, /Вторая выгрузка/);
  assert.match(timeline, /Главный корпус/);
  assert.match(timeline, /101/);
  assert.match(timeline, /202/);
  assert.ok(
    timeline.indexOf("Первая выгрузка") < timeline.indexOf("Вторая выгрузка"),
    "visible chronology must run from first appearance to current state",
  );

  const summary = chronology.renderSummary(events, appearances);
  assert.match(summary, /Событий/);
  assert.match(summary, /Выгрузок/);
  assert.match(summary, /Изменений/);
  assert.doesNotMatch(summary, /Дата не указана/);
  assert.match(summary, /01\.07\.2026/);

  console.log("frontend MAC chronology test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

"use strict";

const assert = require("node:assert/strict");

const elements = new Map();
const makeCanvas = (id) => ({ id, hidden: false, getContext: () => ({}) });
for (const id of ["smartroomChangesChart", "smartroomAddedRemovedChart", "smartroomTotalChart"]) {
  elements.set(id, makeCanvas(id));
  elements.set(`state:${id}`, { hidden: true, textContent: "", classList: { toggle() {} } });
}
global.window = global;
global.document = {
  documentElement: {},
  getElementById: (id) => elements.get(id) || null,
  querySelector: (selector) => elements.get(`state:${selector.match(/"(.+)"/)?.[1]}`) || null,
};
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.requestAnimationFrame = (callback) => callback();
global.Chart = class FakeChart {
  constructor(_context, config) {
    this.config = config;
    FakeChart.instances.push(this);
  }
  destroy() {
    this.destroyed = true;
  }
  static getChart() {
    return null;
  }
};
global.Chart.instances = [];

require("../frontend/smartroom-charts.js");

(async () => {
  const charts = global.MacAnalyzerSmartroomCharts;
  assert.deepEqual(charts.normalizeRows({ charts: [{ date: "2026-08-12", changes: "2", total: "4" }] }), [
    { date: "2026-08-12", changes: 2, added: 0, removed: 0, total: 4 },
  ]);
  const monthly = charts.monthlyRows({
    charts: [
      { date: "2026-01-02", changes: 2, total: 4, changedRooms: ["R1"], changedMacs: ["M1"] },
      { date: "2026-01-20", changes: 3, total: 5, changedRooms: ["R1", "R2"], changedMacs: ["M2"] },
      { date: "2026-03-01", changes: 1, total: 6, changedRooms: ["R3"], changedMacs: ["M3"] },
    ],
  });
  assert.equal(monthly.length, 3, "missing months from the first through last export must be present");
  assert.equal(monthly[0].changes, 5, "exports from the same month must be summed");
  assert.equal(monthly[0].total, 5, "the final device count for a month comes from its latest export");
  assert.deepEqual(monthly[0].changedRooms.sort(), ["R1", "R2"]);
  assert.equal(monthly[1].changes, 0);
  assert.deepEqual(
    charts
      .snapshotRows({
        snapshotChanges: [
          { name: "Final 1", date: "2026-01-01", total: 100, added: 100, removed: 0 },
          { name: "Final 2", date: "2026-02-01", total: 98, added: 3, removed: 5 },
        ],
      })
      .map((row) => [row.added, row.removed, row.total]),
    [
      [0, 0, 100],
      [3, 5, 98],
    ],
  );
  assert.equal(await charts.render({ charts: [] }), false);
  assert.equal(elements.get("state:smartroomChangesChart").hidden, false);
  assert.equal(
    await charts.render({
      charts: [
        { date: "2026-07-12", changes: 0, total: 3 },
        { date: "2026-08-12", changes: 1, total: 2, changedRooms: ["R1"], changedMacs: ["M1"] },
      ],
      snapshotChanges: [
        { name: "Final 1", date: "2026-07-12", total: 3, added: 3, removed: 0 },
        { name: "Final 2", date: "2026-08-12", total: 2, added: 1, removed: 2 },
      ],
    }),
    true,
  );
  assert.equal(global.Chart.instances.length, 3);
  assert.notEqual(global.Chart.instances[0].config.options.parsing, false, "numeric arrays must be parsed by Chart.js");
  assert.match(
    global.Chart.instances[0].config.options.plugins.tooltip.callbacks.afterLabel({ dataIndex: 1 }),
    /Переговорных: 1 · MAC-адресов: 1/,
  );
  assert.equal(elements.get("smartroomChangesChart").hidden, false);
  const additions = global.Chart.instances[1].config;
  assert.deepEqual(additions.data.labels, ["Final 2"], "the first Final must be excluded from added/missing changes");
  assert.deepEqual(additions.data.datasets[0].data, [1]);
  assert.deepEqual(additions.data.datasets[1].data, [-2], "missing values must be plotted below zero");
  assert.equal(additions.data.datasets[1].label, "Отсутствовало");
  const totals = global.Chart.instances[2].config;
  assert.deepEqual(totals.data.labels, ["Final 1", "Final 2"], "total chart must include every Final");
  assert.deepEqual(totals.data.datasets[0].data, [3, 2]);
  console.log("frontend smartroom charts test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

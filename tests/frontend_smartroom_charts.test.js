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
  assert.equal(await charts.render({ charts: [] }), false);
  assert.equal(elements.get("state:smartroomChangesChart").hidden, false);
  assert.equal(
    await charts.render({
      charts: [{ date: "2026-08-12", changes: 1, total: 2, changedRooms: ["R1"], changedMacs: ["M1"] }],
    }),
    true,
  );
  assert.equal(global.Chart.instances.length, 3);
  assert.notEqual(global.Chart.instances[0].config.options.parsing, false, "numeric arrays must be parsed by Chart.js");
  assert.match(
    global.Chart.instances[0].config.options.plugins.tooltip.callbacks.afterLabel({ dataIndex: 0 }),
    /Переговорных: 1 · MAC-адресов: 1/,
  );
  assert.equal(elements.get("smartroomChangesChart").hidden, false);
  console.log("frontend smartroom charts test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

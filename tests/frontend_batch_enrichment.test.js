const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync("frontend/batch-enrichment.js", "utf8"), context);
const Batch = context.window.MacAnalyzerBatchEnrichment;

function item(id, role, date, name = `${id}.csv`) {
  return { id, role, date, dateSource: "filename", name, file: { name } };
}

async function main() {
  assert.equal(Batch.isSupportedFile({ name: "main.csv" }), true);
  assert.equal(Batch.isSupportedFile({ name: "main.xlsx" }), true);
  assert.equal(Batch.isSupportedFile({ name: "main.exe" }), false);

  const nearest = Batch.buildPlan([
    item("p1", "primary", "2026-01-01T23:00:00Z"),
    item("s1", "smartroom", "2026-01-02T02:00:00Z"),
    item("d1", "ddio", "2026-01-02T03:00:00Z"),
  ], { mode: "nearest", toleranceHours: 24 });
  assert.equal(nearest.groups.length, 1);
  assert.equal(nearest.groups[0].smartroom.id, "s1");
  assert.equal(nearest.groups[0].ddio.id, "d1");

  const exact = Batch.buildPlan([
    item("p1", "primary", "2026-01-01T08:00:00Z"),
    item("s1", "smartroom", "2026-01-02T08:00:00Z"),
  ], { mode: "exact", toleranceHours: 24 });
  assert.equal(exact.groups[0].smartroom, null);
  assert.equal(exact.unmatched[0].id, "s1");

  const sameDaySeparate = Batch.buildPlan([
    item("p1", "primary", "2026-01-03T08:00:00Z"),
    item("p2", "primary", "2026-01-03T18:00:00Z"),
    item("s1", "smartroom", "2026-01-03T08:20:00Z"),
    item("s2", "smartroom", "2026-01-03T18:20:00Z"),
  ], { mode: "nearest", toleranceHours: 24 });
  assert.equal(sameDaySeparate.groups.length, 2);
  assert.equal(sameDaySeparate.groups[0].smartroom.id, "s1");
  assert.equal(sameDaySeparate.groups[1].smartroom.id, "s2");

  const closestWins = Batch.buildPlan([
    item("p1", "primary", "2026-01-04T00:00:00Z"),
    item("p2", "primary", "2026-01-04T10:00:00Z"),
    item("s1", "smartroom", "2026-01-04T09:00:00Z"),
  ], { mode: "nearest", toleranceHours: 24 });
  assert.equal(closestWins.groups[0].smartroom, null);
  assert.equal(closestWins.groups[1].smartroom.id, "s1");

  const zeroTolerance = Batch.buildPlan([
    item("p1", "primary", "2026-01-05T08:00:00Z"),
    item("s1", "smartroom", "2026-01-05T09:00:00Z"),
  ], { mode: "nearest", toleranceHours: 0 });
  assert.equal(zeroTolerance.groups[0].smartroom, null);

  Batch.reassign(sameDaySeparate, sameDaySeparate.groups[0].id, "smartroom", "s2");
  assert.equal(sameDaySeparate.groups[0].smartroom.id, "s2");
  assert.equal(sameDaySeparate.groups[1].smartroom, null);

  const described = await Batch.describeFiles([
    { name: "devices_2026-02-03.csv", size: 10, lastModified: 1, webkitRelativePath: "main/devices_2026-02-03.csv" },
  ], "primary", async () => ({ date: "2026-02-03T00:00:00.000Z", source: "filename" }));
  assert.equal(described[0].dateSource, "filename");
  assert.equal(described[0].relativePath, "main/devices_2026-02-03.csv");

  let active = 0;
  let peak = 0;
  const many = Array.from({ length: 20 }, (_, index) => ({ name: `f-${index}.csv`, size: index, lastModified: index }));
  const concurrent = await Batch.describeFiles(many, "primary", async (file) => {
    active += 1;
    peak = Math.max(peak, active);
    await new Promise((resolve) => setTimeout(resolve, 2));
    active -= 1;
    return { date: `2026-02-${String((Number(file.size) % 20) + 1).padStart(2, "0")}T00:00:00Z`, source: "test" };
  });
  assert.equal(concurrent.length, 20);
  assert.equal(peak > 1 && peak <= 8, true);
  console.log("frontend batch enrichment test passed");
}

main().catch((error) => { console.error(error); process.exitCode = 1; });

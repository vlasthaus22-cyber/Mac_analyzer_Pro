"use strict";
const assert = require("node:assert/strict");
require("fake-indexeddb/auto");
global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/browser-snapshot-store.js");
const store = global.MacAnalyzerBrowserSnapshots;
const device = (model, extra = {}) => ({ mac: "001122334455", deviceId: "codec-1", model, ...extra });
assert.deepEqual(
  store.comparisonHistoryIds([null, undefined, { id: "baseline", kind: "analysis" }], "baseline", "current"),
  [],
);
assert.deepEqual(store.comparisonHistoryIds(null, "baseline", "current"), []);

(async () => {
  const sourceFile = new File(["MAC,IP\n001122334455,10.0.0.1"], "primary.csv", {
    type: "text/csv",
    lastModified: 1234,
  });
  await store.saveSourceFile("primary.csv|32|1234", sourceFile);
  const restoredSource = await store.loadSourceFile("primary.csv|32|1234");
  assert.equal(restoredSource.name, "primary.csv");
  assert.equal(restoredSource.lastModified, 1234);
  assert.equal(await restoredSource.text(), await sourceFile.text());

  const snapshots = [
    {
      id: "first",
      kind: "analysis",
      devices: [device("Old", { address: "Building A" }), { mac: "AABBCCDDEEFF", model: "History only" }],
    },
    { id: "nearest", kind: "analysis", devices: [device("Known", { address: "Building B" })] },
    { id: "mapping", kind: "analysis", source: "ip-mapping-apply", devices: [device("Wrong")] },
    { id: "baseline", kind: "analysis", devices: [device("", { address: "  " })] },
    { id: "current", kind: "analysis", devices: [device("Known", { address: "Building B" })] },
    { id: "future", kind: "analysis", devices: [device("Future")] },
  ];
  for (const snapshot of snapshots) await store.save(snapshot);
  assert.deepEqual(store.comparisonHistoryIds(snapshots, "baseline", "current"), ["nearest", "first"]);
  const options = { historySnapshots: snapshots };
  for (let run = 0; run < 3; run++) {
    const comparison = await store.compareSnapshots("baseline", "current", options);
    assert.equal(comparison.summary.modified, 0, "blank baseline values inherit the nearest earlier Final");
    assert.equal(comparison.summary.unchanged, 1);
    assert.equal(comparison.summary.added, 0);
    assert.equal(comparison.summary.removed, 0, "history-only devices must not enter the baseline");
  }
  assert.equal((await store.load("baseline")).devices[0].model, "", "stored snapshots must remain immutable");
  await store.save({ id: "current", kind: "analysis", devices: [device("Changed", { address: "Building C" })] });
  const changed = await store.compareSnapshots("baseline", "current", options);
  const model = changed.changes.find((item) => item.field === "model");
  assert.equal(model.before, "Known");
  assert.equal(model.after, "Changed");
  assert.equal(model.beforeSnapshotId, "nearest");
  assert.equal(model.beforeDevice.address, "Building B");

  // A known baseline value is authoritative even if earlier history disagrees.
  await store.save({ id: "baseline", kind: "analysis", devices: [device("Baseline")] });
  assert.equal(
    (await store.compareSnapshots("baseline", "current", options)).changes.find((item) => item.field === "model")
      .before,
    "Baseline",
  );

  // Conflicting rows in the same historical snapshot cannot be resolved by row order.
  await store.save({ id: "ambiguous", kind: "analysis", devices: [device("One"), device("Two")] });
  await store.save({ id: "baseline", kind: "analysis", devices: [device("")] });
  const ambiguous = await store.compareSnapshots("baseline", "current", {
    historySnapshots: [
      { id: "ambiguous", kind: "analysis" },
      { id: "baseline", kind: "analysis" },
    ],
  });
  assert.equal(ambiguous.changes.find((item) => item.field === "model").before, "");

  // Reused MAC with conflicting serial/device ID is not reliable historical evidence.
  await store.save({ id: "ambiguous", kind: "analysis", devices: [device("Other device", { deviceId: "different" })] });
  const conflict = await store.compareSnapshots("baseline", "current", {
    historySnapshots: [
      { id: "ambiguous", kind: "analysis" },
      { id: "baseline", kind: "analysis" },
    ],
  });
  assert.equal(conflict.changes.find((item) => item.field === "model").before, "");
  await store.save({ id: "nearest", kind: "analysis", devices: [device("Known", { address: "" })] });
  await store.save({ id: "baseline", kind: "analysis", devices: [device("", { mac: "" })] });
  await store.save({ id: "current", kind: "analysis", devices: [device("Known", { address: "Building A" })] });
  assert.equal(
    (await store.compareSnapshots("baseline", "current", options)).summary.modified,
    0,
    "restoring a MAC must not lose the baseline key while visiting older snapshots",
  );

  const many = Array.from({ length: 1005 }, (_, index) => ({
    mac: `001122${index.toString(16).padStart(6, "0")}`,
    model: "Known",
    deviceId: `large-${index}`,
  }));
  await store.save({ id: "large-old", kind: "analysis", devices: many });
  await store.save({ id: "large-base", kind: "analysis", devices: many.map((item) => ({ ...item, model: "" })) });
  await store.save({ id: "large-new", kind: "analysis", devices: many });
  const large = await store.compareSnapshots("large-base", "large-new", {
    historySnapshots: [
      { id: "large-old", kind: "analysis" },
      { id: "large-base", kind: "analysis" },
    ],
  });
  assert.equal(large.summary.unchanged, 1005, "restoration crosses IndexedDB chunk boundaries");
  assert.equal(large.summary.modified, 0);
  await store.beginStreamedSnapshot({ id: "incomplete", kind: "analysis" });
  await assert.rejects(
    store.compareSnapshots("baseline", "current", {
      historySnapshots: [
        { id: "incomplete", kind: "analysis" },
        { id: "baseline", kind: "analysis" },
      ],
    }),
    /не полностью/,
  );
  assert.equal((await store.load("baseline")).devices[0].model, "", "failed history reads must not damage snapshots");
  assert.equal(
    (await store.compareSnapshots("baseline", "current", options)).summary.modified,
    0,
    "a successful comparison remains possible after an interrupted restoration",
  );
  await store.save({ id: "conflict-base", kind: "analysis", devices: [device("Known", { hasConflict: true })] });
  await store.save({
    id: "conflict-current",
    kind: "analysis",
    devices: [device("Known", { hasConflict: true, conflicts: [{ field: "source", alternative: "DDIO" }] })],
  });
  const sourceConflict = await store.compareSnapshots("conflict-base", "conflict-current");
  assert.equal(sourceConflict.summary.modified, 0, "source metadata conflicts are diagnostics, not physical changes");
  assert.equal(sourceConflict.summary.total, 0);
  console.log("frontend IndexedDB snapshot history tests passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

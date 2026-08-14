"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/memory-guard.js");

const guard = global.MacAnalyzerMemoryGuard;
assert.ok(guard, "memory guard module must be exported");
assert.equal(global.memoryGuard, guard, "legacy memoryGuard alias must use the same API");
assert.equal(document.documentElement.dataset.memoryGuard, "ready");

const rows = Array.from({ length: 100_000 }, (_, index) => ({ index, vendor: index % 2 ? "Cisco" : "Dell" }));
const page = guard.collectPage(rows, (item) => item.vendor === "Cisco", 100, 25);
assert.equal(page.total, 50_000);
assert.equal(page.page, 100);
assert.equal(page.pages, 2_000);
assert.equal(page.items.length, 25);
assert.equal(page.items[0].index, 4_951);

const normalize = (value) => String(value || "").replace(/[^0-9A-F]/gi, "").toUpperCase();
const first = [{ mac: "00:11:22:33:44:55", vendor: "Cisco" }, { mac: "AA:BB:CC:DD:EE:FF", vendor: "Dell" }];
const second = [first[1], first[0]];
assert.equal(guard.datasetSignature(first, ["vendor"], normalize), guard.datasetSignature(second, ["vendor"], normalize));

assert.throws(
  () => guard.assertTableCapacity(guard.limits.browserRows + 1, 1),
  (error) => error.code === "BROWSER_MEMORY_LIMIT" && /без переполнения памяти/.test(error.message),
);

assert.throws(
  () => guard.assertLocalExportCapacity(guard.limits.localExportRows + 1, 1),
  (error) => error.code === "BROWSER_MEMORY_LIMIT",
);
assert.doesNotThrow(() => guard.assertLocalExportCapacity(100, 1_000));

const aggregate = guard.assertEnrichmentCapacity([
  { rowCount: 100_000, headers: ["mac", "vendor", "room"] },
  { rowCount: 100_000, headers: ["mac", "ip", "switch"] },
]);
assert.deepEqual(aggregate, { rows: 200_000, cells: 600_000, textBytes: 0 });
assert.deepEqual(guard.effectiveEnrichmentLimits({ deviceMemory: 4 }), {
  rows: 110_000,
  cells: 1_100_000,
  textBytes: 32 * 1024 * 1024,
  deviceMemory: 4,
});
assert.throws(
  () => guard.assertEnrichmentCapacity([
    { rowCount: 60_000, headers: ["mac", "vendor"] },
    { rowCount: 60_000, headers: ["mac", "room"] },
  ], null, { deviceMemory: 4 }),
  (error) => error.code === "BROWSER_MEMORY_LIMIT" && /операция остановлена/.test(error.message),
);

assert.deepEqual(
  guard.streamingEnrichmentSize([
    { rowCount: 100_000, rows: [["MAC", "Vendor"]] },
    { rowCount: 100_000, rows: [["MAC", "Room"]] },
  ], "NO_EXPANSION"),
  { rows: 100_000, cells: 800_000, textBytes: 32 },
);
assert.doesNotThrow(() => guard.assertStreamingEnrichmentCapacity([
  { rowCount: 100_000, rows: [["MAC", "Vendor"]] },
  { rowCount: 100_000, rows: [["MAC", "Room"]] },
], "NO_EXPANSION", null, { deviceMemory: 4 }));
assert.throws(
  () => guard.assertStreamingEnrichmentCapacity([
    { rowCount: 100_000, rows: [["MAC", "Vendor"]] },
    { rowCount: 100_000, rows: [["MAC", "Room"]] },
  ], "ALLOW_EXPANSION", null, { deviceMemory: 4 }),
  (error) => error.code === "BROWSER_MEMORY_LIMIT",
);
assert.deepEqual(
  guard.enrichmentSize([{ rows: [["MAC", "Vendor"], ["001122334455", "Cisco"]], headers: ["MAC", "Vendor"] }]),
  { rows: 2, cells: 4, textBytes: 52 },
);
assert.throws(
  () => guard.assertEnrichmentCapacity(
    [{ rowCount: 1, headers: ["mac"] }],
    { jsHeapSizeLimit: 100 * 1024 * 1024, usedJSHeapSize: 20 * 1024 * 1024 },
  ),
  (error) => error.code === "BROWSER_MEMORY_LIMIT" && /свободной памяти/.test(error.message),
);
assert.throws(
  () => guard.assertEnrichmentCapacity([
    { rowCount: 110_001, headers: ["mac"] },
    { rowCount: 110_001, headers: ["mac"] },
  ]),
  (error) => error.code === "BROWSER_MEMORY_LIMIT" && /всех файлах обогащения/.test(error.message),
);

assert.deepEqual(
  guard.assertImportCapacity({ size: 8 * 1024 * 1024 }, [{ sourceBytes: 16 * 1024 * 1024 }], null),
  { fileBytes: 8 * 1024 * 1024, batchBytes: 24 * 1024 * 1024 },
);
assert.throws(
  () => guard.assertImportCapacity({ size: guard.limits.browserInputFileBytes + 1 }),
  (error) => error.code === "BROWSER_MEMORY_LIMIT",
);
assert.throws(
  () => guard.assertImportCapacity(
    { size: 40 * 1024 * 1024 },
    [{ sourceBytes: 60 * 1024 * 1024 }],
  ),
  (error) => error.code === "BROWSER_MEMORY_LIMIT",
);
assert.deepEqual(
  guard.assertZipDirectoryCapacity(new Map([
    ["xl/workbook.xml", { uncompressedSize: 1024 }],
    ["xl/worksheets/sheet1.xml", { uncompressedSize: 2048 }],
  ]), null),
  { entries: 2, expandedBytes: 3072 },
);
assert.throws(
  () => guard.assertZipDirectoryCapacity([
    { uncompressedSize: guard.limits.browserZipExpandedBytes + 1 },
  ]),
  (error) => error.code === "BROWSER_MEMORY_LIMIT",
);
assert.throws(
  () => guard.assertImportCapacity(
    { size: 16 * 1024 * 1024 },
    [],
    { jsHeapSizeLimit: 160 * 1024 * 1024, usedJSHeapSize: 80 * 1024 * 1024 },
  ),
  (error) => error.code === "BROWSER_MEMORY_LIMIT",
);

console.log("frontend memory guard test passed");

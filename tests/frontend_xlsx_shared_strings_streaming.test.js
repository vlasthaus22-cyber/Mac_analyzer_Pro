"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/memory-guard.js");
require("../frontend/file-readers.js");

const readers = global.MacAnalyzerFileReaders;
const itemCount = 120_000;
const xml = `<sst>${Array.from({ length: itemCount }, (_, index) => `<si><t>Vendor ${index}</t></si>`).join("")}</sst>`;
const bytes = new TextEncoder().encode(xml);
const directory = {
  bytes,
  entries: new Map([["xl/sharedStrings.xml", {
    method: 0,
    size: bytes.byteLength,
    uncompressedSize: bytes.byteLength,
    start: 0,
  }]]),
};

(async () => {
  if (global.gc) global.gc();
  const baselineHeap = process.memoryUsage().heapUsed;
  for (let round = 0; round < 3; round += 1) {
    const strings = await readers.xlsxSharedStringsFromDirectory(directory);
    assert.equal(strings.length, itemCount);
    assert.equal(strings[0], "Vendor 0");
    assert.equal(strings[itemCount - 1], `Vendor ${itemCount - 1}`);
    strings.length = 0;
  }
  let retainedBytes = 0;
  if (global.gc) {
    global.gc();
    retainedBytes = Math.max(0, process.memoryUsage().heapUsed - baselineHeap);
    assert.ok(retainedBytes < 32 * 1024 * 1024, `shared strings retained ${retainedBytes} bytes`);
  }
  console.log(`XLSX shared strings streaming test passed; retained ${(retainedBytes / 1024 / 1024).toFixed(1)} MB`);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

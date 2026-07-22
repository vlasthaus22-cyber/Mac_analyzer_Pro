"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/memory-guard.js");
require("../frontend/file-readers.js");

const readers = global.MacAnalyzerFileReaders;
const workbookPath = path.join(__dirname, "..", "data", "imports", "oom-browser-test.xlsx");
const workbookBytes = fs.readFileSync(workbookPath);
const workbookBuffer = workbookBytes.buffer.slice(
  workbookBytes.byteOffset,
  workbookBytes.byteOffset + workbookBytes.byteLength,
);

(async () => {
  const directory = readers.clientZipDirectory(workbookBuffer);
  const sharedStringBytes = await readers.clientZipEntryBytes(directory, "xl/sharedStrings.xml");
  const sharedStrings = sharedStringBytes
    ? readers.xlsxSharedStringsFromXml(new TextDecoder("utf-8").decode(sharedStringBytes))
    : [];
  const sheetPath = [...directory.entries.keys()]
    .find((name) => /^xl\/worksheets\/sheet\d+\.xml$/i.test(name));
  assert.ok(sheetPath, "real XLSX must contain a worksheet");
  if (global.gc) global.gc();
  const baselineHeap = process.memoryUsage().heapUsed;
  let retainedBytes = 0;

  for (let round = 0; round < 3; round += 1) {
    let visited = 0;
    const rows = await readers.xlsxWorksheetRows(
      directory,
      sheetPath,
      sharedStrings,
      () => {},
      { collectRows: false, onRow: () => { visited += 1; } },
    );
    assert.equal(visited, 100_001, `round ${round + 1} must process the complete workbook`);
    assert.equal(rows.parsedRowCount, 100_001);
    assert.equal(rows.length, 0, "processed XLSX rows must not remain in a retained result array");
  }

  if (global.gc) {
    global.gc();
    retainedBytes = Math.max(0, process.memoryUsage().heapUsed - baselineHeap);
    assert.ok(retainedBytes < 64 * 1024 * 1024, `repeated XLSX reads retained ${retainedBytes} bytes`);
  }

  console.log(`real XLSX repeated enrichment memory test passed; retained ${(retainedBytes / 1024 / 1024).toFixed(1)} MB`);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

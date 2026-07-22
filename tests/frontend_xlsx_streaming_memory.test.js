"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/memory-guard.js");
require("../frontend/file-readers.js");

const readers = global.MacAnalyzerFileReaders;
const dataRows = 100_000;
const xml = [
  `<worksheet><dimension ref="A1:B${dataRows + 1}"/><sheetData>`,
  '<row r="1"><c r="A1" t="inlineStr"><is><t>MAC</t></is></c><c r="B1" t="inlineStr"><is><t>Room</t></is></c></row>',
  ...Array.from({ length: dataRows }, (_, index) => {
    const row = index + 2;
    return `<row r="${row}"><c r="A${row}" t="inlineStr"><is><t>AABBCC${index.toString(16).padStart(6, "0")}</t></is></c><c r="B${row}"><v>${index % 500}</v></c></row>`;
  }),
  "</sheetData></worksheet>",
].join("");
const bytes = new TextEncoder().encode(xml);

function directory() {
  return {
    bytes,
    entries: new Map([["xl/worksheets/sheet1.xml", {
      method: 0,
      size: bytes.byteLength,
      uncompressedSize: bytes.byteLength,
      start: 0,
    }]]),
  };
}

(async () => {
  for (let round = 0; round < 3; round += 1) {
    let visited = 0;
    const rows = await readers.xlsxWorksheetRows(
      directory(),
      "xl/worksheets/sheet1.xml",
      [],
      () => {},
      {
        collectRows: false,
        onRow: (_row, index) => {
          visited += 1;
          assert.equal(index, visited - 1);
        },
      },
    );
    assert.equal(rows.length, 0, "streaming mode must not retain worksheet rows");
    assert.equal(rows.parsedRowCount, dataRows + 1);
    assert.equal(rows.declaredRowCount, dataRows + 1);
    assert.equal(visited, dataRows + 1);
  }

  let previewVisited = 0;
  const preview = await readers.xlsxWorksheetRows(
    directory(),
    "xl/worksheets/sheet1.xml",
    [],
    () => {},
    { collectRows: false, maxRows: 101, onRow: () => { previewVisited += 1; } },
  );
  assert.equal(preview.length, 0);
  assert.equal(previewVisited, 101);
  assert.equal(preview.truncated, true);
  assert.equal(await readers.xlsxWorksheetRowCount(directory(), "xl/worksheets/sheet1.xml"), dataRows + 1);

  console.log("frontend XLSX streaming memory test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

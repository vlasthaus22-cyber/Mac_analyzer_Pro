"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/memory-guard.js");
require("../frontend/file-readers.js");
require("../frontend/xlsx-exporter.js");

const exporter = global.MacAnalyzerXlsxExporter;
const readers = global.MacAnalyzerFileReaders;

(async () => {
  assert.ok(exporter, "XLSX exporter module must be exported");
  assert.equal(document.documentElement.dataset.xlsxExporter, "ready");

  const sourceBatches = [
    [
      { mac: "00:11:22:33:44:55", vendor: "Cisco & Systems", room: "101" },
      { mac: "AA:BB:CC:DD:EE:FF", vendor: "Vendor <B>", room: " 202 " },
    ],
    [{ mac: "10:20:30:40:50:60", vendor: "Производитель", room: "303" }],
  ];
  const progress = [];
  const result = await exporter.createWorkbook({
    columns: ["MAC", "Производитель", "Помещение"],
    totalRows: 3,
    sheetName: 'MAC "Analyzer"',
    streamRows: async (accept) => {
      for (const batch of sourceBatches) await accept(batch);
    },
    rowMapper: (device) => [device.mac, device.vendor, device.room],
    onProgress: (percent) => progress.push(percent),
  });

  assert.equal(result.rows, 3);
  assert.equal(result.mimeType, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
  assert.ok(result.blob.size > 1000, "generated XLSX must contain a complete workbook");
  assert.equal(progress.at(-1), 100);

  const buffer = await result.blob.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  assert.deepEqual([...bytes.slice(0, 4)], [0x50, 0x4b, 0x03, 0x04], "XLSX must be a ZIP file");
  const directory = readers.clientZipDirectory(buffer);
  assert.deepEqual(
    [...directory.entries.keys()].sort(),
    [
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/_rels/workbook.xml.rels",
    "xl/styles.xml",
    "xl/workbook.xml",
      "xl/worksheets/sheet1.xml",
    ].sort(),
  );

  const sheet = new TextDecoder().decode(
    await readers.clientZipEntryBytes(directory, "xl/worksheets/sheet1.xml"),
  );
  assert.equal((sheet.match(/<row\b/g) || []).length, 4, "header and every streamed row must be exported");
  assert.match(sheet, /Cisco &amp; Systems/);
  assert.match(sheet, /Vendor &lt;B&gt;/);
  assert.match(sheet, /Производитель/);

  const workbook = new TextDecoder().decode(
    await readers.clientZipEntryBytes(directory, "xl/workbook.xml"),
  );
  assert.match(workbook, /name="MAC &quot;Analyzer&quot;"/);

  const multiSheet = await exporter.createWorkbook({
    sheets: [
      {
        sheetName: "Сводка/аналитика",
        columns: ["Показатель", "Значение"],
        rows: [["Устройств", 3], ["Выгрузок", 2]],
      },
      {
        sheetName: "Сводка:аналитика",
        columns: ["Дата", "MAC", "Изменение"],
        totalRows: 2,
        streamRows: async (accept) => {
          await accept([
            ["2026-07-27", "00:11:22:33:44:55", "Добавлено"],
            ["2026-07-28", "00:11:22:33:44:55", "Изменена модель"],
          ]);
        },
      },
    ],
  });
  assert.equal(multiSheet.sheets.length, 2);
  assert.equal(multiSheet.rows, 4);
  assert.deepEqual(multiSheet.sheets.map((sheet) => sheet.rows), [2, 2]);
  const multiBuffer = await multiSheet.blob.arrayBuffer();
  const multiDirectory = readers.clientZipDirectory(multiBuffer);
  assert.ok(multiDirectory.entries.has("xl/worksheets/sheet1.xml"));
  assert.ok(multiDirectory.entries.has("xl/worksheets/sheet2.xml"));
  const multiWorkbook = new TextDecoder().decode(
    await readers.clientZipEntryBytes(multiDirectory, "xl/workbook.xml"),
  );
  assert.match(multiWorkbook, /name="Сводка аналитика"/);
  assert.match(multiWorkbook, /name="Сводка аналитика 2"/);
  const secondSheet = new TextDecoder().decode(
    await readers.clientZipEntryBytes(multiDirectory, "xl/worksheets/sheet2.xml"),
  );
  assert.match(secondSheet, /Изменена модель/);
  assert.equal((secondSheet.match(/<row\b/g) || []).length, 3);

  console.log("frontend XLSX exporter test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

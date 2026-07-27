"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/memory-guard.js");
require("../frontend/file-readers.js");
require("../frontend/xlsx-exporter.js");
require("../frontend/full-xlsx-report.js");

const reportBuilder = global.MacAnalyzerFullXlsxReport;
const exporter = global.MacAnalyzerXlsxExporter;
const readers = global.MacAnalyzerFileReaders;

(async () => {
  assert.ok(reportBuilder, "full XLSX report module must be exported");
  assert.equal(document.documentElement.dataset.fullXlsxReport, "ready");

  const firstDevice = {
    mac: "001122334455",
    vendor: "Cisco",
    model: "Catalyst 2960",
    ip: "10.0.0.10",
    address: "Main",
    room: "101",
    switchIp: "10.0.0.1",
    switchPort: "Gi1/0/1",
    source: "first.csv",
  };
  const secondDevice = {
    ...firstDevice,
    model: "Catalyst 3560",
    room: "202",
    source: "second.csv",
  };
  const otherDevice = {
    mac: "AABBCCDDEEFF",
    vendor: "Example",
    model: "AP-1",
    room: "203",
    source: "second.csv",
  };
  const state = {
    devices: [secondDevice, otherDevice],
    invalid: [{ row: 4, source: "second.csv", error: "Bad MAC", raw: "broken" }],
    snapshots: [
      { id: "new", name: "Second", source: "second.csv", createdAt: "2026-07-28T10:00:00Z", devices: [secondDevice, otherDevice] },
      { id: "old", name: "First", source: "first.csv", createdAt: "2026-07-27T10:00:00Z", devices: [firstDevice] },
    ],
    movementHistory: [{
      changedAt: "2026-07-28T10:00:00Z",
      mac: firstDevice.mac,
      type: "Изменено",
      field: "Модель",
      before: firstDevice.model,
      after: secondDevice.model,
      beforeDevice: firstDevice,
      afterDevice: secondDevice,
      source: "first.csv -> second.csv",
    }],
    files: [{ id: "source-1", name: "second.csv", role: "primary", rowCount: 2, size: 1024 }],
    localVendorMappings: { "001122": "Cisco" },
    localModelMappings: { "00112233": "Catalyst" },
    ipMappings: [{ switchIp: "10.0.0.1", address: "Main", room: "101" }],
    theme: "light",
  };
  const analytics = {
    metrics: { devices: 2, knownDevices: 2, vendors: 2, models: 2, rooms: 2, switches: 1, withRoom: 2 },
    distributions: {
      vendors: [{ label: "Cisco", value: 1 }, { label: "Example", value: 1 }],
      models: [{ label: "Catalyst 3560", value: 1 }, { label: "AP-1", value: 1 }],
      rooms: [{ label: "202", value: 1 }, { label: "203", value: 1 }],
      switches: [{ label: "10.0.0.1", value: 1 }],
      oui3: [{ label: "001122", value: 1 }],
      oui4: [{ label: "00112233", value: 1 }],
      oui5: [{ label: "0011223344", value: 1 }],
    },
  };

  const report = await reportBuilder.buildReport({
    state,
    currentDeviceCount: 2,
    currentInvalidCount: 1,
    maximumRows: exporter.maximumRows,
    analyticsPayload: async () => analytics,
  });
  assert.equal(report.historyRowCount, 3);
  assert.equal(report.sheets.length, 10);
  assert.deepEqual(
    report.sheets.map((sheet) => sheet.sheetName),
    ["Сводка", "Устройства", "Аналитика", "Выгрузки", "История MAC", "Изменения", "Ошибки", "Исходные файлы", "Справочники", "Настройки"],
  );
  assert.deepEqual(report.snapshots.map((snapshot) => snapshot.id), ["old", "new"]);
  assert.equal(reportBuilder.historyGroups(report.snapshots, 2).length, 2);

  const workbook = await exporter.createWorkbook({ sheets: report.sheets });
  assert.equal(workbook.sheets.length, 10);
  assert.equal(workbook.sheets.find((sheet) => sheet.name === "История MAC").rows, 3);
  assert.equal(workbook.sheets.find((sheet) => sheet.name === "Изменения").rows, 1);
  const buffer = await workbook.blob.arrayBuffer();
  const directory = readers.clientZipDirectory(buffer);
  assert.ok(directory.entries.has("xl/worksheets/sheet10.xml"));

  const historySheet = new TextDecoder().decode(
    await readers.clientZipEntryBytes(directory, "xl/worksheets/sheet5.xml"),
  );
  assert.equal((historySheet.match(/<row\b/g) || []).length, 4);
  assert.match(historySheet, /Catalyst 2960/);
  assert.match(historySheet, /Catalyst 3560/);
  assert.match(historySheet, /AP-1/);

  const changesSheet = new TextDecoder().decode(
    await readers.clientZipEntryBytes(directory, "xl/worksheets/sheet6.xml"),
  );
  assert.match(changesSheet, /Catalyst 2960/);
  assert.match(changesSheet, /Catalyst 3560/);
  assert.match(changesSheet, /first.csv -&gt; second.csv/);

  console.log("frontend full XLSX report test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

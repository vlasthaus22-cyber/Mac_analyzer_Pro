"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/memory-guard.js");
require("../frontend/file-readers.js");

const readers = global.MacAnalyzerFileReaders;
assert.ok(readers, "file reader module must be exported");
assert.equal(document.documentElement.dataset.fileReaders, "ready");
assert.deepEqual(
  readers.clientTableRows('MAC,Vendor\n"00:11:22:33:44:55","Cisco, Inc."\n', ","),
  [["MAC", "Vendor"], ["00:11:22:33:44:55", "Cisco, Inc."]],
);
assert.deepEqual(
  readers.clientJsonTable('[{"MAC":"00:11:22:33:44:55","Vendor":"Cisco"}]'),
  { headers: ["MAC", "Vendor"], rows: [["00:11:22:33:44:55", "Cisco"]] },
);
assert.equal(readers.clientDelimiter("MAC;Vendor\n001122;Cisco", "sample.csv"), ";");
assert.equal(readers.dateFromFilename("DDIO_2026-09-13_14-25-30.xlsx"), "2026-09-13T14:25:30.000Z");
assert.equal(readers.dateFromFilename("Final 13.09.2026.xlsx"), "2026-09-13T00:00:00.000Z");
assert.equal(readers.dateFromFilename("main_20260913.csv"), "2026-09-13T00:00:00.000Z");
assert.equal(readers.dateFromFilename("smartroom_13092026_142530.csv"), "2026-09-13T14:25:30.000Z");
assert.equal(readers.dateFromFilename("Final 31.02.2026.xlsx"), "", "invalid calendar dates must be rejected");
const utf8Csv = "MAC,Address\n00:11:22:33:44:55,Ленина 1\n";
const utf8Bytes = new TextEncoder().encode(utf8Csv);
const decodedUtf8 = readers.readClientTextFile({
  arrayBuffer: async () => utf8Bytes.buffer,
});
assert.deepEqual(
  readers.xlsxSharedStringsFromXml('<sst><si><t>Cisco &amp; Systems</t></si><si><r><t>Room</t></r><r><t> 12</t></r></si></sst>'),
  ["Cisco & Systems", "Room 12"],
);
assert.deepEqual(
  readers.xlsxRowFromXml('<row r="2"><c r="A2" t="s"><v>0</v></c><c r="C2" t="inlineStr"><is><t>10.0.0.1</t></is></c></row>', ["AABBCC000001"]),
  { values: ["AABBCC000001", "", "10.0.0.1"], cellCount: 2, populated: true },
);
assert.deepEqual(readers.xlsxDimensionSize("A1:N250"), { columns: 14, rows: 250 });
assert.equal(
  readers.xlsxRowFromXml('<row r="2"><c r="N2" t="inlineStr"><is><t>192.168.1.50</t></is></c></row>', []).values.length,
  14,
  "XLSX columns after H must remain addressable",
);

Promise.all([decodedUtf8, readers.clientFileObservationDate({ name: "DDIO_20260913.csv", lastModified: 1 })]).then(([text, csvDate]) => {
  assert.equal(text, utf8Csv);
  assert.deepEqual(csvDate, { date: "2026-09-13T00:00:00.000Z", source: "filename" });
  console.log("frontend file readers test passed");
}).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

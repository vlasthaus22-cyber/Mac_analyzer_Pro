(() => {
  "use strict";

  const mimeType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  const maximumRows = 1_048_575;
  const maximumColumns = 16_384;
  const maximumWorksheetBytes = 512 * 1024 * 1024;
  const encoder = new TextEncoder();
  const crcTable = new Uint32Array(256);

  for (let index = 0; index < 256; index += 1) {
    let value = index;
    for (let bit = 0; bit < 8; bit += 1) value = (value >>> 1) ^ (0xedb88320 & -(value & 1));
    crcTable[index] = value >>> 0;
  }

  function xmlText(value) {
    return String(value ?? "")
      .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\ufffe\uffff]/g, " ")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function columnName(index) {
    let result = "";
    let value = Number(index) + 1;
    while (value > 0) {
      const remainder = (value - 1) % 26;
      result = String.fromCharCode(65 + remainder) + result;
      value = Math.floor((value - 1) / 26);
    }
    return result;
  }

  function updateCrc(state, bytes) {
    let crc = state >>> 0;
    for (let index = 0; index < bytes.length; index += 1) {
      crc = (crc >>> 8) ^ crcTable[(crc ^ bytes[index]) & 0xff];
    }
    return crc >>> 0;
  }

  function encodePart(value) {
    return value instanceof Uint8Array ? value : encoder.encode(String(value ?? ""));
  }

  function buildEntry(name, sourceParts) {
    const parts = [];
    let size = 0;
    let crcState = 0xffffffff;
    for (const source of sourceParts) {
      const bytes = encodePart(source);
      parts.push(bytes);
      size += bytes.byteLength;
      crcState = updateCrc(crcState, bytes);
    }
    return {
      name,
      nameBytes: encoder.encode(name),
      parts,
      size,
      crc: (crcState ^ 0xffffffff) >>> 0,
    };
  }

  function dosTimestamp(date = new Date()) {
    const year = Math.max(1980, date.getFullYear());
    return {
      time: ((date.getHours() & 31) << 11) | ((date.getMinutes() & 63) << 5) | (Math.floor(date.getSeconds() / 2) & 31),
      date: (((year - 1980) & 127) << 9) | (((date.getMonth() + 1) & 15) << 5) | (date.getDate() & 31),
    };
  }

  function localHeader(entry, timestamp) {
    const bytes = new Uint8Array(30 + entry.nameBytes.length);
    const view = new DataView(bytes.buffer);
    view.setUint32(0, 0x04034b50, true);
    view.setUint16(4, 20, true);
    view.setUint16(6, 0x0800, true);
    view.setUint16(8, 0, true);
    view.setUint16(10, timestamp.time, true);
    view.setUint16(12, timestamp.date, true);
    view.setUint32(14, entry.crc, true);
    view.setUint32(18, entry.size, true);
    view.setUint32(22, entry.size, true);
    view.setUint16(26, entry.nameBytes.length, true);
    view.setUint16(28, 0, true);
    bytes.set(entry.nameBytes, 30);
    return bytes;
  }

  function centralHeader(entry, offset, timestamp) {
    const bytes = new Uint8Array(46 + entry.nameBytes.length);
    const view = new DataView(bytes.buffer);
    view.setUint32(0, 0x02014b50, true);
    view.setUint16(4, 20, true);
    view.setUint16(6, 20, true);
    view.setUint16(8, 0x0800, true);
    view.setUint16(10, 0, true);
    view.setUint16(12, timestamp.time, true);
    view.setUint16(14, timestamp.date, true);
    view.setUint32(16, entry.crc, true);
    view.setUint32(20, entry.size, true);
    view.setUint32(24, entry.size, true);
    view.setUint16(28, entry.nameBytes.length, true);
    view.setUint16(30, 0, true);
    view.setUint16(32, 0, true);
    view.setUint16(34, 0, true);
    view.setUint16(36, 0, true);
    view.setUint32(38, 0, true);
    view.setUint32(42, offset, true);
    bytes.set(entry.nameBytes, 46);
    return bytes;
  }

  function endOfDirectory(entryCount, centralSize, centralOffset) {
    const bytes = new Uint8Array(22);
    const view = new DataView(bytes.buffer);
    view.setUint32(0, 0x06054b50, true);
    view.setUint16(4, 0, true);
    view.setUint16(6, 0, true);
    view.setUint16(8, entryCount, true);
    view.setUint16(10, entryCount, true);
    view.setUint32(12, centralSize, true);
    view.setUint32(16, centralOffset, true);
    view.setUint16(20, 0, true);
    return bytes;
  }

  function workbookEntries(sheetName, worksheetEntry) {
    const safeSheetName = xmlText(String(sheetName || "MAC Analyzer").slice(0, 31) || "MAC Analyzer");
    return [
      buildEntry("[Content_Types].xml", [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>',
        "</Types>",
      ]),
      buildEntry("_rels/.rels", [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>',
        "</Relationships>",
      ]),
      buildEntry("xl/workbook.xml", [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ',
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        `<sheets><sheet name="${safeSheetName}" sheetId="1" r:id="rId1"/></sheets></workbook>`,
      ]),
      buildEntry("xl/_rels/workbook.xml.rels", [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>',
        "</Relationships>",
      ]),
      worksheetEntry,
    ];
  }

  function workbookBlob(entries) {
    const timestamp = dosTimestamp();
    const parts = [];
    const central = [];
    let offset = 0;
    for (const entry of entries) {
      const header = localHeader(entry, timestamp);
      parts.push(header, ...entry.parts);
      central.push(centralHeader(entry, offset, timestamp));
      offset += header.byteLength + entry.size;
      if (offset > 0xffffffff) throw new Error("XLSX превышает лимит ZIP 4 ГБ");
    }
    const centralOffset = offset;
    const centralSize = central.reduce((total, item) => total + item.byteLength, 0);
    parts.push(...central, endOfDirectory(entries.length, centralSize, centralOffset));
    return new Blob(parts, { type: mimeType });
  }

  function rowXml(values, rowNumber) {
    const cells = Array.from(values || [], (value, columnIndex) => (
      `<c r="${columnName(columnIndex)}${rowNumber}" t="inlineStr"><is><t xml:space="preserve">${xmlText(value)}</t></is></c>`
    )).join("");
    return `<row r="${rowNumber}">${cells}</row>`;
  }

  async function createWorkbook(options = {}) {
    const columns = Array.isArray(options.columns) ? options.columns : [];
    const totalRows = Math.max(0, Number(options.totalRows || 0) || 0);
    const rowMapper = typeof options.rowMapper === "function" ? options.rowMapper : (row) => row;
    const streamRows = typeof options.streamRows === "function"
      ? options.streamRows
      : async (accept) => accept(Array.isArray(options.rows) ? options.rows : []);
    const onProgress = typeof options.onProgress === "function" ? options.onProgress : () => {};
    if (!columns.length) throw new Error("Для XLSX не выбраны колонки");
    if (columns.length > maximumColumns) throw new Error(`XLSX поддерживает не более ${maximumColumns} колонок`);
    if (totalRows > maximumRows) throw new Error(`XLSX поддерживает не более ${maximumRows.toLocaleString("ru-RU")} строк данных`);

    const worksheetParts = [];
    let worksheetBytes = 0;
    let crcState = 0xffffffff;
    let processedRows = 0;
    let batch = "";
    const appendBytes = (bytes) => {
      if (worksheetBytes + bytes.byteLength > maximumWorksheetBytes) {
        throw new Error("XLSX превысил безопасный лимит 512 МБ; разделите результат на несколько файлов");
      }
      worksheetParts.push(bytes);
      worksheetBytes += bytes.byteLength;
      crcState = updateCrc(crcState, bytes);
    };
    const append = (value) => appendBytes(encodePart(value));
    const flushBatch = () => {
      if (!batch) return;
      append(batch);
      batch = "";
    };

    append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>');
    append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">');
    append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetData>');
    append(rowXml(columns, 1));

    await streamRows(async (sourceRows) => {
      for (const sourceRow of Array.isArray(sourceRows) ? sourceRows : []) {
        if (processedRows >= maximumRows) throw new Error(`XLSX поддерживает не более ${maximumRows.toLocaleString("ru-RU")} строк данных`);
        batch += rowXml(rowMapper(sourceRow, processedRows), processedRows + 2);
        processedRows += 1;
        if (batch.length >= 256 * 1024) flushBatch();
      }
      flushBatch();
      const percent = totalRows ? Math.min(96, Math.round(processedRows / totalRows * 94) + 2) : 50;
      onProgress(percent, `XLSX: ${processedRows.toLocaleString("ru-RU")} / ${totalRows.toLocaleString("ru-RU")} строк`);
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    flushBatch();
    append("</sheetData></worksheet>");

    const worksheetEntry = {
      name: "xl/worksheets/sheet1.xml",
      nameBytes: encoder.encode("xl/worksheets/sheet1.xml"),
      parts: worksheetParts,
      size: worksheetBytes,
      crc: (crcState ^ 0xffffffff) >>> 0,
    };
    const blob = workbookBlob(workbookEntries(options.sheetName, worksheetEntry));
    onProgress(100, `XLSX готов: ${processedRows.toLocaleString("ru-RU")} строк`);
    return { blob, rows: processedRows, bytes: blob.size, mimeType };
  }

  window.MacAnalyzerXlsxExporter = Object.freeze({
    createWorkbook,
    mimeType,
    maximumRows,
    maximumColumns,
    xmlText,
    columnName,
  });
  if (typeof document !== "undefined") document.documentElement.dataset.xlsxExporter = "ready";
})();

(() => {
  "use strict";

  const mimeType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  const maximumRows = 1_048_575;
  const maximumColumns = 16_384;
  const maximumWorksheetBytes = 512 * 1024 * 1024;
  const maximumWorkbookBytes = 512 * 1024 * 1024;
  const maximumStyledRows = 50_000;
  const maximumSheets = 255;
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

  function safeSheetNames(sheets) {
    const used = new Set();
    return sheets.map((sheet, index) => {
      const base = String(sheet.sheetName || sheet.name || `Лист ${index + 1}`)
        .replace(/[\[\]:*?/\\]/g, " ")
        .trim() || `Лист ${index + 1}`;
      let name = base.slice(0, 31);
      let suffix = 1;
      while (used.has(name.toLocaleLowerCase())) {
        suffix += 1;
        const tail = ` ${suffix}`;
        name = base.slice(0, 31 - tail.length) + tail;
      }
      used.add(name.toLocaleLowerCase());
      return name;
    });
  }

  function workbookEntries(sheetNames, worksheetEntries) {
    const contentOverrides = worksheetEntries.map((_entry, index) => (
      `<Override PartName="/xl/worksheets/sheet${index + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`
    ));
    const workbookSheets = sheetNames.map((name, index) => (
      `<sheet name="${xmlText(name)}" sheetId="${index + 1}" r:id="rId${index + 1}"/>`
    ));
    const worksheetRelationships = worksheetEntries.map((_entry, index) => (
      `<Relationship Id="rId${index + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${index + 1}.xml"/>`
    ));
    return [
      buildEntry("[Content_Types].xml", [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        ...contentOverrides,
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
        "<sheets>",
        ...workbookSheets,
        "</sheets></workbook>",
      ]),
      buildEntry("xl/_rels/workbook.xml.rels", [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        ...worksheetRelationships,
        `<Relationship Id="rId${worksheetEntries.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>`,
        "</Relationships>",
      ]),
      buildEntry("xl/styles.xml", [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<fonts count="2"><font><sz val="10"/><name val="Segoe UI"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Segoe UI"/></font></fonts>',
        '<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF155E59"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE8F3F1"/><bgColor indexed="64"/></patternFill></fill></fills>',
        '<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFD8E2E1"/></left><right style="thin"><color rgb="FFD8E2E1"/></right><top style="thin"><color rgb="FFD8E2E1"/></top><bottom style="thin"><color rgb="FFD8E2E1"/></bottom><diagonal/></border></borders>',
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>',
        '<cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>',
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>',
        '<dxfs count="0"/><tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>',
        "</styleSheet>",
      ]),
      ...worksheetEntries,
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

  function rowXml(values, rowNumber, styleId = 0, height = 0) {
    const style = styleId ? ` s="${styleId}"` : "";
    const cells = Array.from(values || [], (value, columnIndex) => (
      `<c r="${columnName(columnIndex)}${rowNumber}"${style} t="inlineStr"><is><t xml:space="preserve">${xmlText(value)}</t></is></c>`
    )).join("");
    const rowHeight = height ? ` ht="${height}" customHeight="1"` : "";
    return `<row r="${rowNumber}"${rowHeight}>${cells}</row>`;
  }

  function columnWidthsXml(columns, requestedWidths) {
    const widths = Array.isArray(requestedWidths) ? requestedWidths : [];
    const definitions = columns.map((title, index) => {
      const fallback = Math.max(10, Math.min(32, String(title || "").length + 4));
      const width = Math.max(6, Math.min(80, Number(widths[index]) || fallback));
      return `<col min="${index + 1}" max="${index + 1}" width="${width}" customWidth="1"/>`;
    });
    return definitions.length ? `<cols>${definitions.join("")}</cols>` : "";
  }

  async function createWorksheet(sheet, sheetIndex, sheetCount, onProgress) {
    const columns = Array.isArray(sheet.columns) ? sheet.columns : [];
    const totalRows = Math.max(0, Number(sheet.totalRows ?? sheet.rows?.length ?? 0) || 0);
    const rowMapper = typeof sheet.rowMapper === "function" ? sheet.rowMapper : (row) => row;
    const streamRows = typeof sheet.streamRows === "function"
      ? sheet.streamRows
      : async (accept) => accept(Array.isArray(sheet.rows) ? sheet.rows : []);
    const sheetName = String(sheet.sheetName || sheet.name || `Лист ${sheetIndex + 1}`);
    if (!columns.length) throw new Error(`Для листа «${sheetName}» не выбраны колонки`);
    if (columns.length > maximumColumns) throw new Error(`XLSX поддерживает не более ${maximumColumns} колонок`);
    if (totalRows > maximumRows) throw new Error(`Лист «${sheetName}» содержит больше ${maximumRows.toLocaleString("ru-RU")} строк`);

    const worksheetParts = [];
    let worksheetBytes = 0;
    let crcState = 0xffffffff;
    let processedRows = 0;
    let batch = "";
    const appendBytes = (bytes) => {
      if (worksheetBytes + bytes.byteLength > maximumWorksheetBytes) {
        throw new Error(`Лист «${sheetName}» превысил безопасный лимит 512 МБ`);
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
    if (sheet.tabColor) append(`<sheetPr><tabColor rgb="${xmlText(String(sheet.tabColor).replace(/[^0-9A-F]/gi, "").slice(-8).padStart(8, "F"))}"/></sheetPr>`);
    append('<sheetViews><sheetView workbookViewId="0" showGridLines="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>');
    append('<sheetFormatPr defaultRowHeight="18"/>');
    append(columnWidthsXml(columns, sheet.columnWidths));
    append("<sheetData>");
    append(rowXml(columns, 1, 1, 28));

    await streamRows(async (sourceRows) => {
      for (const sourceRow of Array.isArray(sourceRows) ? sourceRows : []) {
        if (processedRows >= maximumRows) {
          throw new Error(`Лист «${sheetName}» содержит больше ${maximumRows.toLocaleString("ru-RU")} строк`);
        }
        const styleId = sheet.stripedRows && totalRows <= maximumStyledRows ? (processedRows % 2 ? 3 : 2) : 0;
        batch += rowXml(rowMapper(sourceRow, processedRows), processedRows + 2, styleId);
        processedRows += 1;
        if (batch.length >= 256 * 1024) flushBatch();
      }
      flushBatch();
      const localRatio = totalRows ? Math.min(1, processedRows / totalRows) : 0.5;
      const percent = Math.min(96, Math.round((sheetIndex + localRatio) / Math.max(1, sheetCount) * 94) + 2);
      onProgress(percent, `XLSX · ${sheetName}: ${processedRows.toLocaleString("ru-RU")} / ${totalRows.toLocaleString("ru-RU")} строк`);
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    flushBatch();
    append("</sheetData>");
    if (sheet.autoFilter !== false) {
      append(`<autoFilter ref="A1:${columnName(columns.length - 1)}${Math.max(1, processedRows + 1)}"/>`);
    }
    append("</worksheet>");

    const entryName = `xl/worksheets/sheet${sheetIndex + 1}.xml`;
    return {
      entry: {
        name: entryName,
        nameBytes: encoder.encode(entryName),
        parts: worksheetParts,
        size: worksheetBytes,
        crc: (crcState ^ 0xffffffff) >>> 0,
      },
      rows: processedRows,
      bytes: worksheetBytes,
    };
  }

  async function createWorkbook(options = {}) {
    const onProgress = typeof options.onProgress === "function" ? options.onProgress : () => {};
    const sourceSheets = Array.isArray(options.sheets) && options.sheets.length
      ? options.sheets
      : [{
        columns: options.columns,
        totalRows: options.totalRows,
        rows: options.rows,
        rowMapper: options.rowMapper,
        streamRows: options.streamRows,
        sheetName: options.sheetName,
      }];
    if (sourceSheets.length > maximumSheets) throw new Error(`XLSX поддерживает не более ${maximumSheets} листов в одном отчёте`);
    const sheetNames = safeSheetNames(sourceSheets);
    const worksheetEntries = [];
    const sheetResults = [];
    let worksheetBytes = 0;

    for (let index = 0; index < sourceSheets.length; index += 1) {
      const result = await createWorksheet(
        { ...sourceSheets[index], sheetName: sheetNames[index] },
        index,
        sourceSheets.length,
        onProgress,
      );
      worksheetBytes += result.bytes;
      if (worksheetBytes > maximumWorkbookBytes) {
        throw new Error("XLSX превысил безопасный лимит 512 МБ; сократите число сохраняемых выгрузок");
      }
      worksheetEntries.push(result.entry);
      sheetResults.push({ name: sheetNames[index], rows: result.rows, bytes: result.bytes });
      onProgress(
        Math.min(97, Math.round((index + 1) / sourceSheets.length * 94) + 2),
        `XLSX: лист «${sheetNames[index]}» готов`,
      );
      await new Promise((resolve) => setTimeout(resolve, 0));
    }

    const blob = workbookBlob(workbookEntries(sheetNames, worksheetEntries));
    const processedRows = sheetResults.reduce((total, sheet) => total + sheet.rows, 0);
    onProgress(100, `XLSX готов: ${sheetResults.length} листов, ${processedRows.toLocaleString("ru-RU")} строк`);
    return {
      blob,
      rows: sourceSheets.length === 1 ? sheetResults[0].rows : processedRows,
      bytes: blob.size,
      mimeType,
      sheets: sheetResults,
    };
  }

  window.MacAnalyzerXlsxExporter = Object.freeze({
    createWorkbook,
    mimeType,
    maximumRows,
    maximumColumns,
    maximumWorkbookBytes,
    xmlText,
    columnName,
  });
  if (typeof document !== "undefined") document.documentElement.dataset.xlsxExporter = "ready";
})();

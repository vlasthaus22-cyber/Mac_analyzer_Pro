(() => {
  "use strict";

  const MemoryGuard = window.MacAnalyzerMemoryGuard;
  if (!MemoryGuard) throw new Error("Модуль frontend/memory-guard.js не загружен");

  function textScore(text) {
    return [...text].reduce(
      (score, char) => score
        + (char.charCodeAt(0) > 31 || "\r\n\t".includes(char) ? 1 : -20)
        + (/[А-Яа-яЁё]/.test(char) ? 4 : 0)
        + (",;\t|".includes(char) ? 8 : 0),
      0,
    );
  }

  async function readClientTextFile(file) {
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    const bomEncoding = bytes[0] === 0xff && bytes[1] === 0xfe
      ? "utf-16le"
      : bytes[0] === 0xfe && bytes[1] === 0xff
        ? "utf-16be"
        : bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf
          ? "utf-8"
          : "";
    if (bomEncoding) {
      const text = new TextDecoder(bomEncoding).decode(buffer).replace(/\0/g, "");
      if (text.trim()) return text;
    }
    try {
      const utf8 = new TextDecoder("utf-8", { fatal: true }).decode(buffer);
      if (utf8.trim()) return utf8;
    } catch {
      // Invalid UTF-8 is scored against the supported legacy encodings below.
    }
    const encodings = ["windows-1251", "utf-16le", "utf-16be"];
    let best = { score: -Infinity, text: "" };
    for (const encoding of encodings) {
      try {
        const text = new TextDecoder(encoding).decode(buffer).replace(/\0/g, "");
        const score = textScore(text);
        if (text.trim() && score > best.score) best = { score, text };
      } catch {
        // Try the next supported encoding.
      }
    }
    if (!best.text.trim()) throw new Error("Файл пустой или кодировка не распознана");
    return best.text;
  }

  function clientDelimiter(text, filename) {
    if (/\.tsv$/i.test(filename)) return "\t";
    const sample = text.split(/\r?\n/).slice(0, 20).join("\n");
    const counts = [",", ";", "\t", "|"].map((delimiter) => [
      delimiter,
      sample.split(delimiter).length - 1,
    ]);
    const best = counts.sort((left, right) => right[1] - left[1])[0];
    return best[1] ? best[0] : ",";
  }

  function clientTableRows(text, delimiter) {
    const rows = [];
    let row = [];
    let cell = "";
    let quoted = false;
    for (let index = 0; index < text.length; index += 1) {
      const char = text[index];
      const next = text[index + 1];
      if (char === '"' && quoted && next === '"') {
        cell += '"';
        index += 1;
      } else if (char === '"') {
        quoted = !quoted;
      } else if (char === delimiter && !quoted) {
        row.push(cell.trim());
        cell = "";
      } else if ((char === "\n" || char === "\r") && !quoted) {
        if (char === "\r" && next === "\n") index += 1;
        row.push(cell.trim());
        if (row.some(Boolean)) rows.push(row);
        row = [];
        cell = "";
      } else {
        cell += char;
      }
    }
    row.push(cell.trim());
    if (row.some(Boolean)) rows.push(row);
    return rows;
  }

  function clientJsonTable(text) {
    const data = JSON.parse(text);
    const items = Array.isArray(data) ? data : (data.devices || data.rows || data.data || []);
    if (!Array.isArray(items) || !items.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      throw new Error("JSON должен содержать массив объектов или devices/rows/data");
    }
    const headers = [...new Set(items.flatMap((item) => Object.keys(item)))];
    return { headers, rows: items.map((item) => headers.map((header) => item[header] ?? "")) };
  }

  async function inflateRaw(bytes) {
    if (!("DecompressionStream" in window)) {
      throw new Error("Браузер не поддерживает распаковку XLSX");
    }
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  function clientZipDirectory(buffer) {
    const bytes = new Uint8Array(buffer);
    const view = new DataView(buffer);
    let endOfDirectory = -1;
    for (let index = bytes.length - 22; index >= Math.max(0, bytes.length - 66000); index -= 1) {
      if (view.getUint32(index, true) === 0x06054b50) {
        endOfDirectory = index;
        break;
      }
    }
    if (endOfDirectory < 0) throw new Error("XLSX не содержит ZIP-каталог");

    const total = view.getUint16(endOfDirectory + 10, true);
    const offset = view.getUint32(endOfDirectory + 16, true);
    const entries = new Map();
    let position = offset;
    for (let index = 0; index < total; index += 1) {
      if (view.getUint32(position, true) !== 0x02014b50) break;
      const method = view.getUint16(position + 10, true);
      const size = view.getUint32(position + 20, true);
      const uncompressedSize = view.getUint32(position + 24, true);
      const nameLength = view.getUint16(position + 28, true);
      const extraLength = view.getUint16(position + 30, true);
      const commentLength = view.getUint16(position + 32, true);
      const localOffset = view.getUint32(position + 42, true);
      const name = new TextDecoder()
        .decode(bytes.slice(position + 46, position + 46 + nameLength))
        .replace(/\\/g, "/");
      const localNameLength = view.getUint16(localOffset + 26, true);
      const localExtraLength = view.getUint16(localOffset + 28, true);
      const start = localOffset + 30 + localNameLength + localExtraLength;
      entries.set(name, { method, size, uncompressedSize, start });
      position += 46 + nameLength + extraLength + commentLength;
    }
    MemoryGuard.assertZipDirectoryCapacity(entries);
    return { bytes, entries };
  }

  async function clientZipFileDirectory(file) {
    if (!file || typeof file.slice !== "function") {
      throw new Error("XLSX file does not support streamed reads");
    }
    const fileSize = Math.max(0, Number(file.size || 0));
    const tailOffset = Math.max(0, fileSize - 66000);
    const tailBuffer = await file.slice(tailOffset, fileSize).arrayBuffer();
    const tailBytes = new Uint8Array(tailBuffer);
    const tailView = new DataView(tailBuffer);
    let endOfDirectory = -1;
    for (let index = tailBytes.length - 22; index >= 0; index -= 1) {
      if (tailView.getUint32(index, true) === 0x06054b50) {
        endOfDirectory = index;
        break;
      }
    }
    if (endOfDirectory < 0) throw new Error("XLSX does not contain a ZIP directory");

    const total = tailView.getUint16(endOfDirectory + 10, true);
    const centralSize = tailView.getUint32(endOfDirectory + 12, true);
    const centralOffset = tailView.getUint32(endOfDirectory + 16, true);
    if (centralOffset === 0xffffffff || centralSize === 0xffffffff) {
      throw new Error("ZIP64 XLSX is not supported in autonomous browser mode");
    }
    if (centralOffset + centralSize > fileSize) throw new Error("XLSX ZIP directory is damaged");

    const centralBuffer = await file.slice(centralOffset, centralOffset + centralSize).arrayBuffer();
    const centralBytes = new Uint8Array(centralBuffer);
    const centralView = new DataView(centralBuffer);
    const pendingEntries = [];
    let position = 0;
    for (let index = 0; index < total; index += 1) {
      if (position + 46 > centralBytes.length || centralView.getUint32(position, true) !== 0x02014b50) break;
      const method = centralView.getUint16(position + 10, true);
      const size = centralView.getUint32(position + 20, true);
      const uncompressedSize = centralView.getUint32(position + 24, true);
      const nameLength = centralView.getUint16(position + 28, true);
      const extraLength = centralView.getUint16(position + 30, true);
      const commentLength = centralView.getUint16(position + 32, true);
      const localOffset = centralView.getUint32(position + 42, true);
      const nextPosition = position + 46 + nameLength + extraLength + commentLength;
      if (nextPosition > centralBytes.length) throw new Error("XLSX ZIP directory is damaged");
      const name = new TextDecoder()
        .decode(centralBytes.slice(position + 46, position + 46 + nameLength))
        .replace(/\\/g, "/");
      pendingEntries.push({ name, method, size, uncompressedSize, localOffset });
      position = nextPosition;
    }

    const entries = new Map();
    for (const item of pendingEntries) {
      const localBuffer = await file.slice(item.localOffset, item.localOffset + 30).arrayBuffer();
      if (localBuffer.byteLength < 30 || new DataView(localBuffer).getUint32(0, true) !== 0x04034b50) {
        throw new Error(`XLSX ZIP entry is damaged (${item.name})`);
      }
      const localView = new DataView(localBuffer);
      const localNameLength = localView.getUint16(26, true);
      const localExtraLength = localView.getUint16(28, true);
      const start = item.localOffset + 30 + localNameLength + localExtraLength;
      if (start + item.size > fileSize) throw new Error(`XLSX ZIP entry is truncated (${item.name})`);
      entries.set(item.name, {
        method: item.method,
        size: item.size,
        uncompressedSize: item.uncompressedSize,
        start,
      });
    }
    MemoryGuard.assertZipDirectoryCapacity(entries);
    return { file, entries };
  }

  async function clientZipEntryBytes(directory, path, maximumBytes = MemoryGuard.limits.worksheetBytes) {
    const entry = directory.entries.get(path);
    if (!entry) return null;
    MemoryGuard.assertEntryCapacity(`Слишком большой раздел XLSX (${path})`, entry.uncompressedSize, maximumBytes);
    if (directory.file) {
      return new Uint8Array(await new Response(zipEntryStream(directory, entry)).arrayBuffer());
    }
    const compressed = directory.bytes.subarray(entry.start, entry.start + entry.size);
    if (entry.method === 0) return compressed;
    if (entry.method === 8) return inflateRaw(compressed);
    throw new Error(`XLSX использует неподдерживаемый ZIP-метод ${entry.method}`);
  }

  async function clientZipEntries(buffer, onProgress = () => {}) {
    const directory = clientZipDirectory(buffer);
    const entries = new Map();
    const names = [...directory.entries.keys()];
    for (let index = 0; index < names.length; index += 1) {
      const name = names[index];
      entries.set(name, await clientZipEntryBytes(directory, name));
      onProgress(names.length ? Math.round(((index + 1) / names.length) * 100) : 100, `Распаковка XLSX: ${index + 1} / ${names.length}`);
    }
    return entries;
  }

  function xlsxXml(entries, path) {
    const bytes = entries.get(path);
    if (!bytes) return null;
    return new DOMParser().parseFromString(new TextDecoder("utf-8").decode(bytes), "application/xml");
  }

  function xlsxSharedStrings(documentNode) {
    if (!documentNode) return [];
    return Array.from(documentNode.getElementsByTagName("si")).map((item) => (
      Array.from(item.getElementsByTagName("t")).map((text) => text.textContent || "").join("")
    ));
  }

  function decodeXmlText(value) {
    return String(value || "").replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (match, entity) => {
      if (entity === "amp") return "&";
      if (entity === "lt") return "<";
      if (entity === "gt") return ">";
      if (entity === "quot") return '"';
      if (entity === "apos") return "'";
      const numeric = entity.toLowerCase().startsWith("#x")
        ? Number.parseInt(entity.slice(2), 16)
        : Number.parseInt(entity.slice(1), 10);
      return Number.isFinite(numeric) ? String.fromCodePoint(numeric) : match;
    });
  }

  function xlsxSharedStringsFromXml(xml) {
    const strings = [];
    const itemPattern = /<si\b[^>]*>([\s\S]*?)<\/si>/gi;
    let itemMatch;
    while ((itemMatch = itemPattern.exec(xml))) {
      let value = "";
      const textPattern = /<t\b[^>]*>([\s\S]*?)<\/t>/gi;
      let textMatch;
      while ((textMatch = textPattern.exec(itemMatch[1]))) value += decodeXmlText(textMatch[1]);
      strings.push(value);
      if (strings.length > MemoryGuard.limits.sharedStrings) {
        throw MemoryGuard.capacityError("Слишком много общих строк XLSX", strings.length, MemoryGuard.limits.sharedStrings);
      }
    }
    return strings;
  }

  async function xlsxSharedStringsFromDirectory(directory, onProgress = () => {}) {
    const entry = directory.entries.get("xl/sharedStrings.xml");
    if (!entry) return [];
    MemoryGuard.assertEntryCapacity("Слишком большой раздел общих строк XLSX", entry.uncompressedSize, MemoryGuard.limits.sharedStringBytes);
    const reader = zipEntryStream(directory, entry).getReader();
    const decoder = new TextDecoder("utf-8");
    const strings = [];
    let pending = "";
    let processedBytes = 0;
    let lastYieldCount = 0;
    const drain = (final = false) => {
      while (true) {
        const start = pending.search(/<si\b/i);
        if (start < 0) {
          if (!final && pending.length > 8) pending = pending.slice(-8);
          return;
        }
        if (start > 0) pending = pending.slice(start);
        const end = pending.search(/<\/si\s*>/i);
        if (end < 0) return;
        const closing = pending.slice(end).match(/^<\/si\s*>/i)?.[0] || "</si>";
        const itemXml = pending.slice(0, end + closing.length);
        pending = pending.slice(end + closing.length);
        strings.push(xlsxSharedStringsFromXml(itemXml)[0] || "");
        if (strings.length > MemoryGuard.limits.sharedStrings) {
          throw MemoryGuard.capacityError("Слишком много общих строк XLSX", strings.length, MemoryGuard.limits.sharedStrings);
        }
      }
    };
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      processedBytes += chunk.value.byteLength;
      pending += decoder.decode(chunk.value, { stream: true });
      drain();
      if (strings.length - lastYieldCount >= 5_000) {
        lastYieldCount = strings.length;
        const ratio = entry.uncompressedSize ? Math.min(1, processedBytes / entry.uncompressedSize) : 0;
        onProgress(20 + ratio * 25, `Общие строки XLSX: ${strings.length.toLocaleString("ru-RU")}`);
        await MemoryGuard.yieldToMainThread();
      }
    }
    pending += decoder.decode();
    drain(true);
    return strings;
  }

  function xlsxColumnIndex(reference) {
    const letters = (String(reference || "").match(/[A-Z]+/i) || [""])[0].toUpperCase();
    let index = 0;
    for (const char of letters) index = index * 26 + char.charCodeAt(0) - 64;
    return Math.max(0, index - 1);
  }

  function xlsxDimensionSize(reference) {
    const finalCell = String(reference || "").split(":").pop() || "";
    const columnMatch = /^\$?([A-Z]+)/i.exec(finalCell);
    const rowMatch = /(\d+)$/.exec(finalCell);
    return {
      columns: columnMatch ? xlsxColumnIndex(columnMatch[1]) + 1 : 0,
      rows: rowMatch ? Math.max(0, Number(rowMatch[1]) || 0) : 0,
    };
  }

  function xlsxCellValue(cell, sharedStrings) {
    const type = cell.getAttribute("t") || "";
    const value = cell.getElementsByTagName("v")[0]?.textContent ?? "";
    if (type === "s") return sharedStrings[Number(value)] ?? "";
    if (type === "inlineStr") {
      return Array.from(cell.getElementsByTagName("t")).map((text) => text.textContent || "").join("");
    }
    if (type === "b") return value === "1" ? "TRUE" : "FALSE";
    return value;
  }

  function xlsxRowFromXml(rowXml, sharedStrings) {
    const row = [];
    const cellPattern = /<c\b([^>]*?)(?:\/\s*>|>([\s\S]*?)<\/c>)/gi;
    let cellMatch;
    let sequentialIndex = 0;
    let cellCount = 0;
    while ((cellMatch = cellPattern.exec(rowXml))) {
      const attributes = cellMatch[1] || "";
      const body = cellMatch[2] || "";
      const reference = /\br="([^"]+)"/i.exec(attributes)?.[1] || "";
      const type = /\bt="([^"]+)"/i.exec(attributes)?.[1] || "";
      const columnIndex = reference ? xlsxColumnIndex(reference) : sequentialIndex;
      const rawValue = /<v\b[^>]*>([\s\S]*?)<\/v>/i.exec(body)?.[1] ?? "";
      let value = decodeXmlText(rawValue);
      if (type === "s") value = sharedStrings[Number(rawValue)] ?? "";
      else if (type === "inlineStr") {
        value = "";
        const textPattern = /<t\b[^>]*>([\s\S]*?)<\/t>/gi;
        let textMatch;
        while ((textMatch = textPattern.exec(body))) value += decodeXmlText(textMatch[1]);
      } else if (type === "b") value = rawValue === "1" ? "TRUE" : "FALSE";
      row[columnIndex] = value;
      sequentialIndex = columnIndex + 1;
      cellCount += 1;
    }
    const values = Array.from({ length: row.length }, (_item, index) => row[index] ?? "");
    return { values, cellCount, populated: values.some((value) => String(value).trim()) };
  }

  function normalizedZipPath(path) {
    const parts = [];
    for (const part of String(path || "").replace(/\\/g, "/").split("/")) {
      if (!part || part === ".") continue;
      if (part === "..") parts.pop();
      else parts.push(part);
    }
    return parts.join("/");
  }

  function zipEntryStream(directory, entry) {
    const compressed = directory.file
      ? directory.file.slice(entry.start, entry.start + entry.size)
      : new Blob([directory.bytes.subarray(entry.start, entry.start + entry.size)]);
    let stream = compressed.stream();
    if (entry.method === 8) stream = stream.pipeThrough(new DecompressionStream("deflate-raw"));
    else if (entry.method !== 0) throw new Error(`XLSX использует неподдерживаемый ZIP-метод ${entry.method}`);
    return stream;
  }

  async function xlsxWorksheetRowCount(directory, sheetPath, onProgress = () => {}) {
    const entry = directory.entries.get(sheetPath);
    if (!entry) throw new Error("XLSX лист не найден");
    MemoryGuard.assertEntryCapacity("Слишком большой XML-лист XLSX", entry.uncompressedSize, MemoryGuard.limits.worksheetBytes);
    const reader = zipEntryStream(directory, entry).getReader();
    const decoder = new TextDecoder("utf-8");
    let pending = "";
    let processedBytes = 0;
    let lastYieldBytes = 0;
    let rowCount = 0;
    const countCompletePrefix = (final = false) => {
      const safeLength = final ? pending.length : pending.lastIndexOf("<");
      if (safeLength <= 0) return;
      const complete = pending.slice(0, safeLength);
      rowCount += (complete.match(/<row\b/gi) || []).length;
      pending = pending.slice(safeLength);
    };
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      processedBytes += chunk.value.byteLength;
      pending += decoder.decode(chunk.value, { stream: true });
      countCompletePrefix();
      if (processedBytes - lastYieldBytes >= 2 * 1024 * 1024) {
        lastYieldBytes = processedBytes;
        const ratio = entry.uncompressedSize ? Math.min(1, processedBytes / entry.uncompressedSize) : 0;
        onProgress(45 + ratio * 30, `Подсчёт строк XLSX: ${rowCount.toLocaleString("ru-RU")}`);
        await MemoryGuard.yieldToMainThread();
      }
    }
    pending += decoder.decode();
    countCompletePrefix(true);
    return rowCount;
  }

  async function xlsxWorksheetRows(directory, sheetPath, sharedStrings, onProgress = () => {}, options = {}) {
    const entry = directory.entries.get(sheetPath);
    if (!entry) throw new Error("XLSX лист не найден");
    MemoryGuard.assertEntryCapacity("Слишком большой XML-лист XLSX", entry.uncompressedSize, MemoryGuard.limits.worksheetBytes);
    const reader = zipEntryStream(directory, entry).getReader();
    const decoder = new TextDecoder("utf-8");
    const rows = [];
    const collectRows = options.collectRows !== false;
    const retainsRows = collectRows || options.retainedRows === true;
    const onRow = typeof options.onRow === "function" ? options.onRow : null;
    const maximumRows = Math.max(0, Number(options.maxRows || 0) || 0);
    let pending = "";
    let cellCount = 0;
    let processedBytes = 0;
    let rowCount = 0;
    let declaredRowCount = 0;
    let declaredColumnCount = 0;
    let observedColumnCount = 0;
    let stopped = false;
    let lastYieldRowCount = 0;
    const captureDimension = () => {
      if (declaredRowCount && declaredColumnCount) return;
      const reference = /<dimension\b[^>]*\bref="([^"]+)"/i.exec(pending)?.[1] || "";
      const size = xlsxDimensionSize(reference);
      if (size.rows) declaredRowCount = size.rows;
      if (size.columns) declaredColumnCount = size.columns;
    };
    const drainRows = async () => {
      while (!stopped) {
        const rowStart = pending.search(/<row\b/i);
        if (rowStart < 0) {
          if (pending.length > 32) pending = pending.slice(-32);
          return;
        }
        if (rowStart > 0) pending = pending.slice(rowStart);
        const rowEnd = pending.search(/<\/row\s*>/i);
        if (rowEnd < 0) return;
        const closing = pending.slice(rowEnd).match(/^<\/row\s*>/i)?.[0] || "</row>";
        const rowXml = pending.slice(0, rowEnd + closing.length);
        pending = pending.slice(rowEnd + closing.length);
        const parsed = xlsxRowFromXml(rowXml, sharedStrings);
        cellCount += parsed.cellCount;
        observedColumnCount = Math.max(observedColumnCount, parsed.values.length);
        if (parsed.populated) {
          const rowIndex = rowCount;
          rowCount += 1;
          if (collectRows) rows.push(parsed.values);
          if (onRow) await onRow(parsed.values, rowIndex);
          if (maximumRows && rowCount >= maximumRows) stopped = true;
        }
        if (retainsRows) MemoryGuard.assertTableCapacity(rowCount, cellCount);
        else if (rowCount > MemoryGuard.limits.browserEnrichmentRows) {
          throw MemoryGuard.capacityError("Слишком много строк в потоковом XLSX", rowCount, MemoryGuard.limits.browserEnrichmentRows);
        }
      }
    };
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      processedBytes += chunk.value.byteLength;
      pending += decoder.decode(chunk.value, { stream: true });
      captureDimension();
      await drainRows();
      if (stopped) {
        await reader.cancel().catch(() => {});
        break;
      }
      if (rowCount - lastYieldRowCount >= 2000) {
        lastYieldRowCount = rowCount;
        const ratio = entry.uncompressedSize ? Math.min(1, processedBytes / entry.uncompressedSize) : 0;
        onProgress(78 + ratio * 20, `Строки XLSX: ${rowCount.toLocaleString("ru-RU")}`);
        await MemoryGuard.yieldToMainThread();
      }
    }
    if (!stopped) {
      pending += decoder.decode();
      captureDimension();
      await drainRows();
    }
    Object.defineProperties(rows, {
      parsedRowCount: { value: rowCount, enumerable: false },
      declaredRowCount: { value: declaredRowCount, enumerable: false },
      declaredColumnCount: { value: declaredColumnCount, enumerable: false },
      observedColumnCount: { value: observedColumnCount, enumerable: false },
      truncated: { value: stopped, enumerable: false },
    });
    return rows;
  }

  async function clientXlsxTable(file, onProgress = () => {}, options = {}) {
    MemoryGuard.assertImportCapacity(file);
    onProgress(3, "Чтение XLSX с диска");
    onProgress(10, "Проверка структуры XLSX");
    const directory = await clientZipFileDirectory(file);
    onProgress(20, "Чтение структуры книги без распаковки лишних разделов");
    const workbookBytes = await clientZipEntryBytes(directory, "xl/workbook.xml", 16 * 1024 * 1024);
    const relationshipBytes = await clientZipEntryBytes(directory, "xl/_rels/workbook.xml.rels", 16 * 1024 * 1024);
    const workbook = workbookBytes ? new DOMParser().parseFromString(new TextDecoder("utf-8").decode(workbookBytes), "application/xml") : null;
    const relationships = relationshipBytes ? new DOMParser().parseFromString(new TextDecoder("utf-8").decode(relationshipBytes), "application/xml") : null;
    const sharedStrings = await xlsxSharedStringsFromDirectory(directory, onProgress);
    if (!workbook) throw new Error("XLSX workbook.xml не найден");
    const firstSheet = workbook.getElementsByTagName("sheet")[0];
    if (!firstSheet) throw new Error("XLSX не содержит листов");

    const relationshipId = firstSheet.getAttribute("r:id") || firstSheet.getAttribute("id");
    let target = "";
    if (relationships && relationshipId) {
      const relationship = Array.from(relationships.getElementsByTagName("Relationship"))
        .find((node) => node.getAttribute("Id") === relationshipId);
      target = relationship?.getAttribute("Target") || "";
    }
    let sheetPath = target ? normalizedZipPath(target.startsWith("/") ? target.slice(1) : `xl/${target}`) : "";
    if (!directory.entries.has(sheetPath)) {
      sheetPath = [...directory.entries.keys()].find((name) => /^xl\/worksheets\/sheet\d+\.xml$/i.test(name)) || "";
    }
    onProgress(78, `Чтение строк листа ${firstSheet.getAttribute("name") || "1"}`);
    let headers = null;
    let dataRowCount = 0;
    const collectedRows = [];
    const collectRows = options.collectRows !== false;
    const maximumDataRows = Math.max(0, Number(options.maxRows || 0) || 0);
    const rawRows = await xlsxWorksheetRows(directory, sheetPath, sharedStrings, onProgress, {
      collectRows: false,
      retainedRows: collectRows,
      maxRows: maximumDataRows ? maximumDataRows + 1 : 0,
      onRow: async (row, rawIndex) => {
        if (rawIndex === 0) {
          headers = row;
          return;
        }
        const dataIndex = dataRowCount;
        dataRowCount += 1;
        if (collectRows) collectedRows.push(row);
        if (typeof options.onRow === "function") await options.onRow(row, dataIndex);
      },
    });
    if (!headers) throw new Error("XLSX не содержит строк");
    if (!headers.some(Boolean)) throw new Error("Первая строка XLSX не содержит заголовков");
    const declaredColumns = Math.min(512, Math.max(0, Number(rawRows.declaredColumnCount || 0)));
    const columnCount = Math.max(headers.length, Number(rawRows.observedColumnCount || 0), declaredColumns);
    headers = Array.from({ length: columnCount }, (_value, index) => String(headers[index] || `Column ${index + 1}`));
    const declaredDataRows = Math.max(0, Number(rawRows.declaredRowCount || 0) - 1);
    const countedDataRows = maximumDataRows && rawRows.truncated && !declaredDataRows
      ? Math.max(0, (await xlsxWorksheetRowCount(directory, sheetPath, onProgress)) - 1)
      : 0;
    const rowCount = Math.max(dataRowCount, declaredDataRows, countedDataRows);
    onProgress(100, `XLSX прочитан: ${rowCount} строк`);
    return {
      headers,
      rows: collectedRows,
      rowCount,
      truncated: Boolean(rawRows.truncated || rowCount > collectedRows.length),
      sheet: firstSheet.getAttribute("name") || "",
    };
  }

  async function clientReadTable(file, onProgress = () => {}, options = {}) {
    if (/\.(xlsx|xlsm)$/i.test(file.name)) return clientXlsxTable(file, onProgress, options);
    MemoryGuard.assertImportCapacity(file);
    if (/\.xls$/i.test(file.name)) {
      throw new Error("Старый XLS не поддерживается в браузере, сохраните файл как XLSX");
    }
    onProgress(10, "Чтение текстового файла");
    const text = await readClientTextFile(file);
    onProgress(55, "Разбор строк и колонок");
    if (/\.json$/i.test(file.name) || text.trim().startsWith("[") || text.trim().startsWith("{")) {
      const table = clientJsonTable(text);
      onProgress(100, `JSON прочитан: ${table.rows.length} строк`);
      const rowCount = table.rows.length;
      const selectedRows = options.maxRows ? table.rows.slice(0, Math.max(0, Number(options.maxRows) || 0)) : table.rows;
      if (typeof options.onRow === "function") selectedRows.forEach((row, index) => options.onRow(row, index));
      return { ...table, rows: options.collectRows === false ? [] : selectedRows, rowCount, truncated: selectedRows.length < rowCount };
    }
    const rows = clientTableRows(text, clientDelimiter(text, file.name));
    if (!rows.length) throw new Error("Файл не содержит строк");
    if (!rows[0].some(Boolean)) throw new Error("Первая строка файла не содержит заголовков");
    onProgress(100, `Файл прочитан: ${Math.max(0, rows.length - 1)} строк`);
    const headers = rows.shift();
    const rowCount = rows.length;
    const selectedRows = options.maxRows ? rows.slice(0, Math.max(0, Number(options.maxRows) || 0)) : rows;
    if (typeof options.onRow === "function") selectedRows.forEach((row, index) => options.onRow(row, index));
    return { headers, rows: options.collectRows === false ? [] : selectedRows, rowCount, truncated: selectedRows.length < rowCount };
  }

  window.MacAnalyzerFileReaders = Object.freeze({
    readClientTextFile,
    clientDelimiter,
    clientTableRows,
    clientJsonTable,
    clientZipDirectory,
    clientZipFileDirectory,
    clientZipEntryBytes,
    clientZipEntries,
    xlsxSharedStringsFromXml,
    xlsxSharedStringsFromDirectory,
    xlsxRowFromXml,
    xlsxDimensionSize,
    xlsxWorksheetRows,
    xlsxWorksheetRowCount,
    clientXlsxTable,
    clientReadTable,
  });
  document.documentElement.dataset.fileReaders = "ready";
})();

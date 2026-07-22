(() => {
  "use strict";

  const limits = Object.freeze({
    browserRows: 150_000,
    browserCells: 1_500_000,
    browserEnrichmentRows: 220_000,
    browserEnrichmentCells: 2_200_000,
    browserEnrichmentTextBytes: 64 * 1024 * 1024,
    browserHeapReserveBytes: 64 * 1024 * 1024,
    browserInputFileBytes: 64 * 1024 * 1024,
    browserInputBatchBytes: 96 * 1024 * 1024,
    browserZipExpandedBytes: 192 * 1024 * 1024,
    browserZipEntries: 10_000,
    invalidRows: 5_000,
    movementRows: 5_000,
    inlineComparisonRows: 20_000,
    snapshotPreviewRows: 500,
    browserSnapshotRows: 1_000_000,
    localExportRows: 20_000,
    localExportCells: 250_000,
    worksheetBytes: 128 * 1024 * 1024,
    sharedStringBytes: 64 * 1024 * 1024,
    sharedStrings: 500_000,
  });

  function capacityError(kind, current, maximum) {
    const error = new Error(
      `${kind}: безопасный предел автономного HTML-режима ${maximum.toLocaleString("ru-RU")}, получено ${current.toLocaleString("ru-RU")}. Разделите данные на меньшие файлы или используйте backend; операция остановлена без переполнения памяти браузера.`,
    );
    error.code = "BROWSER_MEMORY_LIMIT";
    return error;
  }

  function assertTableCapacity(rowCount, cellCount) {
    if (rowCount > limits.browserRows) throw capacityError("Слишком много строк", rowCount, limits.browserRows);
    if (cellCount > limits.browserCells) throw capacityError("Слишком много ячеек", cellCount, limits.browserCells);
  }

  function enrichmentSize(files) {
    let rows = 0;
    let cells = 0;
    let textBytes = 0;
    for (const file of Array.isArray(files) ? files : []) {
      const fileRows = Math.max(0, Number(file?.rowCount ?? file?.rows?.length ?? 0) || 0);
      const columns = Math.max(1, Number(file?.headers?.length ?? file?.rows?.[0]?.length ?? 1) || 1);
      rows += fileRows;
      cells += fileRows * columns;
      for (const row of Array.isArray(file?.rows) ? file.rows : []) {
        for (const value of Array.isArray(row) ? row : []) {
          textBytes += typeof value === "string" ? value.length * 2 : 16;
        }
      }
    }
    return { rows, cells, textBytes };
  }

  function estimatedEnrichmentWorkingSet(size) {
    return limits.browserHeapReserveBytes
      + size.rows * 1_400
      + size.cells * 24
      + size.textBytes;
  }

  function assertHeapHeadroom(size, memoryInfo = globalThis.performance?.memory) {
    const heapLimit = Number(memoryInfo?.jsHeapSizeLimit || 0);
    const heapUsed = Number(memoryInfo?.usedJSHeapSize || 0);
    if (!Number.isFinite(heapLimit) || !Number.isFinite(heapUsed) || heapLimit <= 0 || heapUsed < 0) return;
    const safeFreeBytes = Math.max(0, Math.floor((heapLimit - heapUsed) * 0.75));
    const requiredBytes = estimatedEnrichmentWorkingSet(size);
    if (requiredBytes > safeFreeBytes) {
      throw capacityError("Недостаточно свободной памяти браузера для обогащения", requiredBytes, safeFreeBytes);
    }
  }

  function effectiveEnrichmentLimits(navigatorInfo = globalThis.navigator) {
    const deviceMemory = Number(navigatorInfo?.deviceMemory || 0);
    const ratio = deviceMemory > 0 && deviceMemory <= 2 ? 0.3
      : deviceMemory > 0 && deviceMemory <= 4 ? 0.5
        : deviceMemory > 0 && deviceMemory <= 8 ? 0.75
          : 1;
    return {
      rows: Math.floor(limits.browserEnrichmentRows * ratio),
      cells: Math.floor(limits.browserEnrichmentCells * ratio),
      textBytes: Math.floor(limits.browserEnrichmentTextBytes * ratio),
      deviceMemory,
    };
  }

  function assertEnrichmentCapacity(files, memoryInfo = globalThis.performance?.memory, navigatorInfo = globalThis.navigator) {
    const size = enrichmentSize(files);
    const effective = effectiveEnrichmentLimits(navigatorInfo);
    if (size.rows > effective.rows) throw capacityError("Слишком много строк во всех файлах обогащения", size.rows, effective.rows);
    if (size.cells > effective.cells) throw capacityError("Слишком много ячеек во всех файлах обогащения", size.cells, effective.cells);
    if (size.textBytes > effective.textBytes) throw capacityError("Слишком большой объём текста во всех файлах обогащения", size.textBytes, effective.textBytes);
    assertHeapHeadroom(size, memoryInfo);
    return size;
  }

  function streamingEnrichmentSize(files, strategy = "primary") {
    const source = Array.isArray(files) ? files : [];
    const rowCounts = source.map((file) => Math.max(0, Number(file?.rowCount ?? file?.rows?.length ?? 0) || 0));
    const primaryRows = rowCounts[0] || 0;
    const resultRows = strategy === "primary" ? primaryRows : rowCounts.reduce((total, rows) => total + rows, 0);
    const resultColumns = 8;
    let textBytes = 0;
    for (const file of source) {
      for (const row of Array.isArray(file?.rows) ? file.rows : []) {
        for (const value of Array.isArray(row) ? row : []) textBytes += typeof value === "string" ? value.length * 2 : 16;
      }
    }
    return { rows: resultRows, cells: resultRows * resultColumns, textBytes };
  }

  function assertStreamingEnrichmentCapacity(files, strategy = "primary", memoryInfo = globalThis.performance?.memory, navigatorInfo = globalThis.navigator) {
    const size = streamingEnrichmentSize(files, strategy);
    const effective = effectiveEnrichmentLimits(navigatorInfo);
    if (size.rows > effective.rows) throw capacityError("Слишком много результирующих устройств для потокового обогащения", size.rows, effective.rows);
    if (size.cells > effective.cells) throw capacityError("Слишком большой результирующий набор для потокового обогащения", size.cells, effective.cells);
    if (size.textBytes > effective.textBytes) throw capacityError("Слишком большой объём текста в предпросмотре файлов", size.textBytes, effective.textBytes);
    assertHeapHeadroom(size, memoryInfo);
    return size;
  }

  function sourceFileBytes(files) {
    return (Array.isArray(files) ? files : []).reduce(
      (total, file) => total + Math.max(0, Number(file?.sourceBytes ?? file?.size ?? 0) || 0),
      0,
    );
  }

  function assertImportCapacity(file, loadedFiles = [], memoryInfo = globalThis.performance?.memory) {
    const fileBytes = Math.max(0, Number(file?.size ?? file?.sourceBytes ?? file ?? 0) || 0);
    const batchBytes = sourceFileBytes(loadedFiles) + fileBytes;
    if (fileBytes > limits.browserInputFileBytes) {
      throw capacityError("Слишком большой исходный файл", fileBytes, limits.browserInputFileBytes);
    }
    if (batchBytes > limits.browserInputBatchBytes) {
      throw capacityError("Слишком большой суммарный размер файлов обогащения", batchBytes, limits.browserInputBatchBytes);
    }
    const heapLimit = Number(memoryInfo?.jsHeapSizeLimit || 0);
    const heapUsed = Number(memoryInfo?.usedJSHeapSize || 0);
    if (Number.isFinite(heapLimit) && Number.isFinite(heapUsed) && heapLimit > 0 && heapUsed >= 0) {
      const safeFreeBytes = Math.max(0, Math.floor((heapLimit - heapUsed) * 0.75));
      const requiredBytes = limits.browserHeapReserveBytes + fileBytes * 4;
      if (requiredBytes > safeFreeBytes) {
        throw capacityError("Недостаточно свободной памяти браузера для чтения файла", requiredBytes, safeFreeBytes);
      }
    }
    return { fileBytes, batchBytes };
  }

  function assertZipDirectoryCapacity(entries, memoryInfo = globalThis.performance?.memory) {
    const values = entries instanceof Map ? [...entries.values()] : Array.isArray(entries) ? entries : [];
    const expandedBytes = values.reduce(
      (total, entry) => total + Math.max(0, Number(entry?.uncompressedSize || 0) || 0),
      0,
    );
    if (values.length > limits.browserZipEntries) {
      throw capacityError("Слишком много разделов в XLSX", values.length, limits.browserZipEntries);
    }
    if (expandedBytes > limits.browserZipExpandedBytes) {
      throw capacityError("Слишком большой распакованный объём XLSX", expandedBytes, limits.browserZipExpandedBytes);
    }
    const heapLimit = Number(memoryInfo?.jsHeapSizeLimit || 0);
    const heapUsed = Number(memoryInfo?.usedJSHeapSize || 0);
    if (Number.isFinite(heapLimit) && Number.isFinite(heapUsed) && heapLimit > 0 && heapUsed >= 0) {
      const safeFreeBytes = Math.max(0, Math.floor((heapLimit - heapUsed) * 0.75));
      const requiredBytes = limits.browserHeapReserveBytes + expandedBytes;
      if (requiredBytes > safeFreeBytes) {
        throw capacityError("Недостаточно свободной памяти браузера для распаковки XLSX", requiredBytes, safeFreeBytes);
      }
    }
    return { entries: values.length, expandedBytes };
  }

  function assertEntryCapacity(kind, byteLength, maximum) {
    if (byteLength > maximum) throw capacityError(kind, byteLength, maximum);
  }

  function assertLocalExportCapacity(rowCount, cellCount) {
    if (rowCount > limits.localExportRows) throw capacityError("Слишком много строк для локального экспорта", rowCount, limits.localExportRows);
    if (cellCount > limits.localExportCells) throw capacityError("Слишком много ячеек для локального экспорта", cellCount, limits.localExportCells);
  }

  function hashText(value) {
    const text = String(value ?? "");
    let hash = 2166136261;
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function datasetSignature(devices, fields, normalizeMac) {
    const items = Array.isArray(devices) ? devices : [];
    let sum = 0;
    let xor = 0;
    for (const device of items) {
      let itemHash = hashText(normalizeMac(device?.mac || device?.macFormatted) || "");
      for (const field of fields) itemHash = Math.imul(itemHash ^ hashText(device?.[field] || ""), 16777619) >>> 0;
      sum = (sum + itemHash) >>> 0;
      xor = (xor ^ ((itemHash << (itemHash & 15)) | (itemHash >>> (32 - (itemHash & 15))))) >>> 0;
    }
    return `${items.length}:${sum.toString(16)}:${xor.toString(16)}`;
  }

  function collectPage(items, predicate, requestedPage, pageSize, onVisit = () => {}) {
    const source = Array.isArray(items) ? items : [];
    const size = Math.max(1, Number(pageSize) || 1);
    let page = Math.max(1, Number(requestedPage) || 1);
    let total = 0;
    let visible = [];
    const scan = () => {
      visible = [];
      total = 0;
      const start = (page - 1) * size;
      const end = start + size;
      for (const item of source) {
        onVisit(item);
        if (!predicate(item)) continue;
        if (total >= start && total < end) visible.push(item);
        total += 1;
      }
    };
    scan();
    const pages = Math.max(1, Math.ceil(total / size));
    if (page > pages) {
      page = pages;
      scan();
    }
    return { items: visible, total, page, pages };
  }

  function yieldToMainThread() {
    return new Promise((resolve) => setTimeout(resolve, 0));
  }

  const publicApi = Object.freeze({
    limits,
    capacityError,
    assertTableCapacity,
    enrichmentSize,
    estimatedEnrichmentWorkingSet,
    effectiveEnrichmentLimits,
    assertHeapHeadroom,
    assertEnrichmentCapacity,
    streamingEnrichmentSize,
    assertStreamingEnrichmentCapacity,
    sourceFileBytes,
    assertImportCapacity,
    assertZipDirectoryCapacity,
    assertEntryCapacity,
    assertLocalExportCapacity,
    datasetSignature,
    collectPage,
    yieldToMainThread,
  });
  window.MacAnalyzerMemoryGuard = publicApi;
  // Compatibility for frontend copies cached before the MemoryGuard rename.
  window.memoryGuard = publicApi;
  document.documentElement.dataset.memoryGuard = "ready";
})();

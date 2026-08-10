(() => {
  "use strict";

  const defaultChunkBytes = 512 * 1024;

  function createWriter(maxChunkBytes = defaultChunkBytes) {
    const chunks = [];
    let buffer = "";
    const flush = () => {
      if (!buffer) return;
      chunks.push(buffer);
      buffer = "";
    };
    const write = (value) => {
      const text = String(value ?? "");
      if (buffer.length + text.length > maxChunkBytes) flush();
      if (text.length > maxChunkBytes) chunks.push(text);
      else buffer += text;
    };
    return {
      write,
      finish(type = "application/json") {
        flush();
        return { blob: new Blob(chunks, { type }), chunks: chunks.length };
      },
    };
  }

  function safeState(state = {}) {
    return {
      files: (state.files || []).map((file) => ({
        id: file.id || "",
        name: file.name || "",
        role: file.role || "",
        sheet: file.sheet || "",
        createdAt: file.createdAt || "",
        rowCount: Number(file.rowCount || 0),
        mapping: file.mapping || {},
      })),
      ipMappings: state.ipMappings || [],
      localVendorMappings: state.localVendorMappings || {},
      localModelMappings: state.localModelMappings || {},
      dashboardSettings: state.dashboardSettings || {},
      vendorDetectorSettings: state.vendorDetectorSettings || {},
      historyEnrichmentSettings: state.historyEnrichmentSettings || {},
      visibleColumns: state.visibleColumns || [],
      columnOrder: state.columnOrder || [],
    };
  }

  function indentedJson(value, indent) {
    const serialized = JSON.stringify(value, null, 2);
    const padding = " ".repeat(Math.max(0, Number(indent) || 0));
    return String(serialized === undefined ? "null" : serialized).replace(/^/gm, padding);
  }

  async function writeArray(writer, streamRows, onProgress = () => {}, indent = 2) {
    let first = true;
    let count = 0;
    const padding = " ".repeat(Math.max(0, Number(indent) || 0));
    writer.write("[\n");
    await streamRows(async (rows) => {
      for (const row of Array.isArray(rows) ? rows : []) {
        writer.write((first ? "" : ",\n") + indentedJson(row, indent + 2));
        first = false;
        count += 1;
      }
      onProgress(count);
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    writer.write(`\n${padding}]`);
    return count;
  }

  async function createReport(options = {}) {
    const state = options.state || {};
    const writer = createWriter(options.maxChunkBytes);
    const snapshots = (state.snapshots || []).slice().sort(
      (left, right) => (Date.parse(left.fileCreatedAt || left.createdAt || left.savedAt || "") || 0)
        - (Date.parse(right.fileCreatedAt || right.createdAt || right.savedAt || "") || 0),
    );
    const analytics = await options.analyticsPayload();
    const progress = typeof options.onProgress === "function" ? options.onProgress : () => {};
    writer.write('{\n  "format": "mac-analyzer-full-json",\n  "version": 2,');
    writer.write(`\n  "exportedAt": ${JSON.stringify(new Date().toISOString())},`);
    writer.write(`\n  "analytics": ${indentedJson(analytics || {}, 2).trimStart()},`);
    writer.write(`\n  "workspace": ${indentedJson(safeState(state), 2).trimStart()},`);
    writer.write('\n  "currentDevices": ');
    const currentRows = await writeArray(writer, options.streamCurrentRows, (count) => progress(8, `Текущих устройств: ${count}`), 2);
    writer.write(',\n  "allDevices": ');
    const inventoryRows = await writeArray(writer, options.streamInventoryRows || options.streamCurrentRows, (count) => progress(18, `Устройств в накопительной базе: ${count}`), 2);
    writer.write(',\n  "invalidRows": ');
    const invalidRows = await writeArray(writer, options.streamInvalidRows, (count) => progress(25, `Ошибочных строк: ${count}`), 2);
    writer.write(`,\n  "movementHistory": ${indentedJson(state.movementHistory || [], 2).trimStart()},\n  "snapshots": [\n`);
    let snapshotRows = 0;
    for (let index = 0; index < snapshots.length; index += 1) {
      const snapshot = snapshots[index];
      if (index) writer.write(",\n");
      const metadata = {
        id: snapshot.id || "",
        name: snapshot.name || "",
        source: snapshot.source || "",
        kind: snapshot.kind || "",
        fileCreatedAt: snapshot.fileCreatedAt || snapshot.createdAt || "",
        savedAt: snapshot.savedAt || "",
        deviceCount: Number(snapshot.deviceCount ?? (snapshot.devices || []).length),
        invalidCount: Number(snapshot.invalidCount ?? (snapshot.invalid || []).length),
      };
      writer.write(`    {\n      "metadata": ${indentedJson(metadata, 6).trimStart()},\n      "devices": `);
      snapshotRows += await writeArray(
        writer,
        (accept) => options.streamSnapshotRows(snapshot, accept),
        () => progress(30 + Math.round((index + 1) / Math.max(1, snapshots.length) * 65), `Выгрузка ${index + 1} из ${snapshots.length}`),
        6,
      );
      writer.write("\n    }");
    }
    writer.write("\n  ]\n}\n");
    const result = writer.finish();
    return { ...result, currentRows, inventoryRows, invalidRows, snapshotRows, snapshots: snapshots.length };
  }

  async function createDeviceExport(options = {}) {
    const writer = createWriter(options.maxChunkBytes);
    writer.write('{\n  "format": "mac-analyzer-devices-json",\n  "version": 2,');
    writer.write(`\n  "exportedAt": ${JSON.stringify(new Date().toISOString())},\n  "devices": `);
    const rows = await writeArray(writer, options.streamRows, options.onProgress, 2);
    writer.write("\n}\n");
    return { ...writer.finish(), rows };
  }

  window.MacAnalyzerFullJsonReport = Object.freeze({ createReport, createDeviceExport });
})();

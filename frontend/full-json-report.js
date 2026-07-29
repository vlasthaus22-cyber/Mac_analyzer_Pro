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

  async function writeArray(writer, streamRows, onProgress = () => {}) {
    let first = true;
    let count = 0;
    writer.write("[");
    await streamRows(async (rows) => {
      for (const row of Array.isArray(rows) ? rows : []) {
        writer.write((first ? "" : ",") + JSON.stringify(row));
        first = false;
        count += 1;
      }
      onProgress(count);
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    writer.write("]");
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
    writer.write('{"format":"mac-analyzer-full-json","version":1,');
    writer.write(`"exportedAt":${JSON.stringify(new Date().toISOString())},`);
    writer.write(`"analytics":${JSON.stringify(analytics || {})},`);
    writer.write(`"workspace":${JSON.stringify(safeState(state))},`);
    writer.write('"currentDevices":');
    const currentRows = await writeArray(writer, options.streamCurrentRows, (count) => progress(10, `Текущих устройств: ${count}`));
    writer.write(',"invalidRows":');
    const invalidRows = await writeArray(writer, options.streamInvalidRows, (count) => progress(25, `Ошибочных строк: ${count}`));
    writer.write(`,"movementHistory":${JSON.stringify(state.movementHistory || [])},"snapshots":[`);
    let snapshotRows = 0;
    for (let index = 0; index < snapshots.length; index += 1) {
      const snapshot = snapshots[index];
      if (index) writer.write(",");
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
      writer.write(`{"metadata":${JSON.stringify(metadata)},"devices":`);
      snapshotRows += await writeArray(
        writer,
        (accept) => options.streamSnapshotRows(snapshot, accept),
        () => progress(30 + Math.round((index + 1) / Math.max(1, snapshots.length) * 65), `Выгрузка ${index + 1} из ${snapshots.length}`),
      );
      writer.write("}");
    }
    writer.write("]}");
    const result = writer.finish();
    return { ...result, currentRows, invalidRows, snapshotRows, snapshots: snapshots.length };
  }

  async function createDeviceExport(options = {}) {
    const writer = createWriter(options.maxChunkBytes);
    writer.write('{"format":"mac-analyzer-devices-json","version":1,');
    writer.write(`"exportedAt":${JSON.stringify(new Date().toISOString())},"devices":`);
    const rows = await writeArray(writer, options.streamRows, options.onProgress);
    writer.write("}");
    return { ...writer.finish(), rows };
  }

  window.MacAnalyzerFullJsonReport = Object.freeze({ createReport, createDeviceExport });
})();

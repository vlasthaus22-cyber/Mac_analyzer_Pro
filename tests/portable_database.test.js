"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/portable-database.js");

const database = global.MacAnalyzerPortableDatabase;
assert.ok(database, "portable database module must be exported");
assert.equal(document.documentElement.dataset.portableDatabase, "ready");

class MemoryFileHandle {
  constructor(name = "stress.madb") {
    this.name = name;
    this.blob = new Blob([]);
    this.maximumChunkBytes = 0;
  }

  async queryPermission() { return "granted"; }
  async requestPermission() { return "granted"; }
  async getFile() { return this.blob; }

  async createWritable() {
    const chunks = [];
    return {
      write: async (chunk) => {
        chunks.push(chunk);
        this.maximumChunkBytes = Math.max(this.maximumChunkBytes, Buffer.byteLength(String(chunk), "utf8"));
      },
      close: async () => { this.blob = new Blob(chunks, { type: "application/x-mac-analyzer-db" }); },
      abort: async () => { chunks.length = 0; },
    };
  }
}

(async () => {
  const handle = new MemoryFileHandle();
  const devices = Array.from({ length: 60_000 }, (_, index) => ({
    mac: `AABBCC${index.toString(16).padStart(6, "0").toUpperCase()}`,
    vendor: "Stress Vendor",
    model: `Model ${index % 25}`,
    ip: `10.${Math.floor(index / 65536)}.${Math.floor(index / 256) % 256}.${index % 256}`,
    room: String(100 + (index % 200)),
  }));
  const payload = {
    state: { theme: "dark", localVendorMappings: { AABBCC: "Stress Vendor" } },
    devices,
    invalid: [{ row: 7, raw: "bad-mac" }],
    movements: Array.from({ length: 5_000 }, (_, index) => ({ mac: devices[index].mac, field: "room" })),
    snapshotMetadata: [
      { id: "snapshot-current", name: "Current enrichment", browserStored: true, deviceCount: devices.length },
      { id: "snapshot-before", name: "Before enrichment", browserStored: true, deviceCount: 1_000 },
    ],
    skipSnapshotId: "snapshot-current",
    snapshotStreamer: async (metadata, onChunk) => {
      if (metadata.id !== "snapshot-before") return;
      for (let offset = 0; offset < 1_000; offset += 250) {
        await onChunk("device", devices.slice(offset, offset + 250));
      }
    },
  };

  for (let round = 0; round < 3; round += 1) {
    devices[round].room = String(900 + round);
    const result = await database.write(handle, payload);
    assert.equal(result.counts.devices, 60_000);
  }

  const restoredSnapshots = [];
  const restored = await database.read(handle, () => {}, { onSnapshot: async (snapshot) => restoredSnapshots.push(snapshot) });
  assert.equal(restored.header.format, database.format);
  assert.equal(restored.devices.length, 60_000);
  assert.equal(restored.invalid.length, 1);
  assert.equal(restored.movements.length, 5_000);
  assert.equal(restored.devices[2].room, "902");
  assert.equal(restored.state.theme, "dark");
  assert.equal(restoredSnapshots.length, 2);
  assert.equal(restoredSnapshots.find((item) => item.id === "snapshot-before").devices.length, 1_000);
  assert.equal(restoredSnapshots.find((item) => item.id === "snapshot-current").devices.length, 60_000);
  assert.equal(restored.snapshots.find((item) => item.id === "snapshot-current").currentReference, true);
  assert.equal(restored.snapshots.length, 2);
  const headerOnly = await database.readHeader(handle);
  assert.equal(headerOnly.format, database.format);
  assert.equal(headerOnly.counts.devices, 60_000);
  assert.ok(handle.maximumChunkBytes < 512 * 1024, "database writer must use bounded chunks");

  const streamedHandle = new MemoryFileHandle("streamed-current.madb");
  const streamedPayload = {
    state: { theme: "light" },
    devices: [],
    invalid: [],
    deviceCount: devices.length,
    invalidCount: 1,
    movements: [],
    snapshotMetadata: [{ id: "snapshot-current", name: "Current enrichment", browserStored: true, deviceCount: devices.length }],
    skipSnapshotId: "snapshot-current",
    currentResultStreamer: async (onChunk) => {
      for (let offset = 0; offset < devices.length; offset += 1_000) {
        await onChunk("device", devices.slice(offset, offset + 1_000));
      }
      await onChunk("invalid", [{ row: 7, raw: "bad-mac" }]);
    },
    inventoryStreamer: async (onChunk) => {
      await onChunk(devices.slice(0, 750));
    },
  };
  const streamedResult = await database.write(streamedHandle, streamedPayload);
  assert.equal(streamedResult.counts.devices, 60_000);
  assert.equal(streamedResult.counts.invalid, 1);
  const streamedRestored = await database.read(streamedHandle);
  assert.equal(streamedRestored.devices.length, 60_000);
  assert.equal(streamedRestored.invalid.length, 1);
  assert.ok(streamedHandle.maximumChunkBytes < 512 * 1024, "current result streamer must keep writes bounded");

  const restoredChunks = [];
  const restoredStarts = [];
  const restoredEnds = [];
  const inventoryRows = [];
  const boundedRestore = await database.readFile(streamedHandle.blob, () => {}, {
    retainRows: false,
    previewLimit: 250,
    batchRows: 500,
    onSnapshotStart: async (metadata) => restoredStarts.push(metadata.id),
    onSnapshotChunk: async (metadata, kind, rows, index) => {
      restoredChunks.push({ id: metadata.id, kind, index, count: rows.length });
      assert.ok(rows.length <= 500);
    },
    onSnapshotEnd: async (metadata, counts) => restoredEnds.push({ id: metadata.id, counts }),
    onInventoryChunk: async (rows) => inventoryRows.push(...rows),
  });
  assert.equal(boundedRestore.deviceCount, 60_000);
  assert.equal(boundedRestore.devices.length, 250, "cross-browser restore must retain only one preview page");
  assert.equal(boundedRestore.invalidCount, 1);
  assert.equal(restoredStarts.length, 1);
  assert.equal(restoredEnds[0].counts.deviceCount, 60_000);
  assert.equal(restoredEnds[0].counts.deviceChunks, 120);
  assert.equal(restoredChunks.filter((item) => item.kind === "device").length, 120);
  assert.equal(inventoryRows.length, 750, "portable database must carry the cumulative device inventory");

  console.log("portable database streaming stress test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

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

  console.log("portable database streaming stress test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

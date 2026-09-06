"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/local-folder-store.js");

const store = global.MacAnalyzerLocalFolderStore;
assert.ok(store, "local folder store must be exported");
assert.equal(document.documentElement.dataset.localFolderStore, "ready");
assert.deepEqual(store.folderNames, ["database", "imports", "exports", "settings", "logs", "backups"]);

class MemoryFileHandle {
  constructor(name) {
    this.name = name;
    this.content = new Blob([]);
  }

  async createWritable() {
    const handle = this;
    const chunks = [];
    return {
      async write(value) { chunks.push(value); },
      async close() { handle.content = new Blob(chunks); },
      async abort() { chunks.length = 0; },
    };
  }

  async getFile() {
    return this.content;
  }
}

class MemoryDirectoryHandle {
  constructor(name) {
    this.name = name;
    this.directories = new Map();
    this.files = new Map();
  }

  async getDirectoryHandle(name, options = {}) {
    if (!this.directories.has(name) && options.create) this.directories.set(name, new MemoryDirectoryHandle(name));
    if (!this.directories.has(name)) throw new Error("directory not found");
    return this.directories.get(name);
  }

  async getFileHandle(name, options = {}) {
    if (!this.files.has(name) && options.create) this.files.set(name, new MemoryFileHandle(name));
    if (!this.files.has(name)) throw new Error("file not found");
    return this.files.get(name);
  }
}

(async () => {
  const root = new MemoryDirectoryHandle("MAC Analyzer Data");
  const structure = await store.ensureStructure(root);
  assert.equal(root.directories.size, 6);
  assert.equal(structure.databaseHandle.name, "mac-analyzer-data.madb");

  const manifest = await store.writeManifest(structure, { counts: { devices: 42 } });
  assert.equal(manifest.database, "database/mac-analyzer-data.madb");
  const manifestHandle = structure.directories.settings.files.get("storage-manifest.json");
  const manifestText = await (await manifestHandle.getFile()).text();
  assert.match(manifestText, /"devices": 42/);

  const source = new Blob(["MAC,IP\n001122334455,10.0.0.1"], { type: "text/csv" });
  Object.defineProperty(source, "name", { value: "source.csv" });
  Object.defineProperty(source, "lastModified", { value: 1234 });
  const importedName = await store.copyImport(structure, source, "source.csv|32|1234");
  assert.match(importedName, /__source\.csv$/);
  assert.ok(structure.directories.imports.files.has(importedName));
  assert.ok(structure.directories.imports.files.has(`${importedName}.json`));
  assert.equal(await store.copyImport(structure, source, "source.csv|32|1234"), importedName);
  assert.equal(structure.directories.imports.files.size, 2, "repeated import must replace the same archive pair");
  const restoredSource = await store.loadImport(structure, "source.csv|32|1234", "source.csv");
  assert.ok(restoredSource instanceof Blob);
  assert.equal(await restoredSource.text(), await source.text());

  const exportName = await store.writeExport(structure, "result.csv", new Blob(["MAC\n001122334455"]));
  assert.equal(exportName, "result.csv");
  assert.ok(structure.directories.exports.files.has("result.csv"));

  await store.writeLog(structure, "test-complete", { devices: 42 });
  assert.equal(structure.directories.logs.files.size, 1);

  const unrelated = new Blob(["not-a-database"]);
  Object.defineProperties(unrelated, {
    name: { value: "notes.txt" },
    webkitRelativePath: { value: "Shared MAC Data/settings/notes.txt" },
  });
  const preferred = new Blob(["portable-database"]);
  Object.defineProperties(preferred, {
    name: { value: "mac-analyzer-data.madb" },
    webkitRelativePath: { value: "Shared MAC Data/database/mac-analyzer-data.madb" },
  });
  const secondary = new Blob(["secondary"]);
  Object.defineProperties(secondary, {
    name: { value: "backup.madb" },
    webkitRelativePath: { value: "Shared MAC Data/backups/backup.madb" },
  });
  const inspected = store.inspectFolderFiles([unrelated, secondary, preferred]);
  assert.equal(inspected.database.file, preferred, "database/mac-analyzer-data.madb must win over backup files");
  assert.equal(inspected.database.path, "Shared MAC Data/database/mac-analyzer-data.madb");
  assert.equal(inspected.rootName, "Shared MAC Data");
  assert.equal(inspected.fileCount, 3);
  assert.equal(store.findDatabaseFile([unrelated]), null);
  console.log("local folder store test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

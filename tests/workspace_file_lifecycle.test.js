"use strict";

const assert = require("node:assert/strict");

global.window = globalThis;
global.document = { documentElement: { dataset: {} } };
require("../frontend/workspace-file-lifecycle.js");

const lifecycle = global.MacAnalyzerWorkspaceFileLifecycle;
const files = [
  { id: "primary", role: "primary", name: "main.xlsx" },
  { id: "old-1", role: "enrichment", name: "old-1.xlsx", consumedAt: "2026-07-20T10:00:00Z" },
  { id: "old-2", role: "enrichment", name: "old-2.xlsx", consumedAt: "2026-07-21T10:00:00Z" },
  { id: "pending", role: "enrichment", name: "pending.xlsx" },
];

const unchanged = lifecycle.selectForNextImport(files, "primary");
assert.strictEqual(unchanged.files, files);
assert.deepEqual(unchanged.removed, []);

const next = lifecycle.selectForNextImport(files, "enrichment");
assert.deepEqual(next.files.map((file) => file.id), ["primary", "pending"]);
assert.deepEqual(next.removed.map((file) => file.id), ["old-1", "old-2"]);
assert.equal(files.length, 4, "selection must not mutate the current workspace before commit");

assert.equal(lifecycle.markConsumed(next.files, "2026-07-22T10:00:00Z"), 1);
assert.equal(next.files[0].consumedAt, undefined);
assert.equal(next.files[1].consumedAt, "2026-07-22T10:00:00Z");
assert.equal(document.documentElement.dataset.workspaceFileLifecycle, "ready");

console.log("workspace file lifecycle test passed");

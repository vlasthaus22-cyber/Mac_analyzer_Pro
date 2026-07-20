const assert = require("assert");

require("../frontend/guide.js");

const Guide = globalThis.MacAnalyzerGuide;
assert.ok(Guide, "guide module must be exported");
assert.deepStrictEqual(Guide.tabNames, ["overview", "user", "engineer", "large-files"]);
assert.strictEqual(Guide.normalizeTab("engineer"), "engineer");
assert.strictEqual(Guide.normalizeTab("unknown"), "overview");

const user = Guide.modePresentation(false);
assert.strictEqual(user.mode, "user");
assert.strictEqual(user.label, "Пользовательский режим");
assert.match(user.summary, /поиск/);

const engineer = Guide.modePresentation(true, "2030-01-02T03:04:05Z");
assert.strictEqual(engineer.mode, "engineering");
assert.strictEqual(engineer.label, "Инженерный режим");
assert.match(engineer.summary, /Полный доступ/);
assert.match(engineer.summary, /до/);

console.log("frontend guide tests passed");

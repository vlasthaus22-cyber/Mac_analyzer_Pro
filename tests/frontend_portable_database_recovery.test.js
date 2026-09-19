"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
const start = source.indexOf("function isPortableFileSystemWriteError(");
const end = source.indexOf("function detachUnwritablePortableDatabase(", start);
assert.ok(start >= 0 && end > start, "portable filesystem recovery classifier must exist");
const classifier = new Function(`${source.slice(start, end)}; return isPortableFileSystemWriteError;`)();

assert.equal(
  classifier({
    name: "NoModificationAllowedError",
    message: "An attempt was made to write to a file or directory which could not be modified due to the state of the underlying filesystem.",
  }),
  true,
);
assert.equal(classifier({ name: "NotAllowedError", message: "Permission denied" }), true);
assert.equal(classifier({ name: "DataCloneError", message: "Data cannot be cloned" }), false);
assert.match(source, /persistPortableDatabase\(\{tolerateFileSystemFailure:false\}\)/);
assert.match(source, /Результат сохранён в IndexedDB/);

console.log("frontend portable database recovery test passed");

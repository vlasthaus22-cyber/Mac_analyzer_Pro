"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const html = fs.readFileSync(path.join(__dirname, "..", "mac_analyzer_standalone.html"), "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map((match) => match[1]);

assert.ok(scripts.length, "standalone HTML must contain inline JavaScript");
scripts.forEach((source, index) => {
  assert.doesNotThrow(
    () => new vm.Script(source, { filename: `mac-analyzer-standalone-inline-${index}.js` }),
    `standalone inline script ${index} must compile`,
  );
});

console.log("standalone inline JavaScript syntax test passed");

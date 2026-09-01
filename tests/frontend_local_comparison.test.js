const assert = require("assert");
const fs = require("fs");
const path = require("path");
const { performance } = require("perf_hooks");

const source = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
const start = source.indexOf("function localDeviceMap(devices=[])");
const end = source.indexOf("function recordLocalMovements(", start);
assert(start >= 0, "localDeviceMap must be defined in app.js");
assert(end > start, "local comparison implementation must be extractable");

const implementation = source.slice(start, end);
const build = new Function(
  "normalize",
  "formatMac",
  "compactDashboardDevice",
  "MemoryGuard",
  "labels",
  `${implementation}; return { localDeviceMap, localComparisonBetweenDevices };`,
);
const normalize = (value) => String(value || "").toUpperCase().replace(/[^0-9A-F]/g, "");
const api = build(
  normalize,
  (value) => normalize(value),
  (device) => ({ ...device }),
  { limits: { movementRows: 100000 } },
  {},
);

const before = [
  { mac: "AA:BB:CC:00:00:01", ip: "10.0.0.1", model: "A" },
  { mac: "AA:BB:CC:00:00:02", ip: "10.0.0.2", model: "B" },
];
const after = [
  { mac: "AA-BB-CC-00-00-01", ip: "10.0.0.10", model: "A" },
  { mac: "AA:BB:CC:00:00:03", ip: "10.0.0.3", model: "C" },
];
const changes = api.localComparisonBetweenDevices(before, after, ["ip", "model"]);
assert(changes.some((item) => item.type === "Изменено" && item.mac.endsWith("01") && item.field === "ip"));
assert(changes.some((item) => item.type === "Добавлено" && item.mac.endsWith("03")));
assert(changes.some((item) => item.type === "Удалено" && item.mac.endsWith("02")));

const largeBefore = Array.from({ length: 20000 }, (_item, index) => ({
  mac: index.toString(16).padStart(12, "0"),
  ip: `10.${(index >> 16) & 255}.${(index >> 8) & 255}.${index & 255}`,
}));
const largeAfter = largeBefore.map((item) => ({ ...item }));
const started = performance.now();
assert.deepStrictEqual(api.localComparisonBetweenDevices(largeBefore, largeAfter, ["ip"]), []);
const durationMs = performance.now() - started;
assert(durationMs < 1500, `20k local comparison took ${durationMs.toFixed(1)} ms`);

console.log(`frontend local comparison test passed; 20k rows ${durationMs.toFixed(1)} ms`);

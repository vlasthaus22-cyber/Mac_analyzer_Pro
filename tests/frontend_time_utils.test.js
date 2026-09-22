"use strict";

const assert = require("node:assert/strict");
const time = require("../frontend/time-utils.js");

assert.equal(time.toUtcIso("2026-08-12T03:00:00+03:00"), "2026-08-12T00:00:00.000Z");
assert.equal(time.toUtcIso(""), "");
assert.equal(time.difference("2026-08-12T00:00:00Z", "2026-08-12T00:00:05Z"), 5000);
assert.equal(time.difference(null, "2026-08-12T00:00:05Z"), null);
assert.equal(time.formatDuration(5000), "5 сек.");
assert.equal(time.formatUtc(null), "Дата не указана");
assert.equal(time.timestamp(1785589200000), 1785589200000);
assert.match(time.formatUtc(1785589200000), /2026/);
assert.equal(time.utcDayStart("2026-08-12"), Date.parse("2026-08-12T00:00:00.000Z"));
assert.equal(time.utcDayEnd("2026-08-12"), Date.parse("2026-08-12T23:59:59.999Z"));
assert.equal(time.utcDayStart("bad-date"), null);

console.log("frontend time utils test passed");

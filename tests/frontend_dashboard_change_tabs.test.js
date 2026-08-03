const assert = require("assert");
const Tabs = require("../frontend/dashboard-change-tabs.js");

assert.deepStrictEqual(Tabs.filtersForTab("critical"), { severity: "critical", type: "all" });
assert.deepStrictEqual(Tabs.filtersForTab("modified"), { severity: "all", type: "modified" });
assert.deepStrictEqual(Tabs.filtersForTab("unknown"), { severity: "all", type: "all" });
assert.strictEqual(Tabs.tabForFilters("critical", "all"), "critical");
assert.strictEqual(Tabs.tabForFilters("all", "removed"), "removed");
assert.strictEqual(Tabs.tabForFilters("high", "modified"), "");
assert.strictEqual(Tabs.nextTab("critical", "ArrowRight"), "added");
assert.strictEqual(Tabs.nextTab("all", "ArrowLeft"), "modified");
assert.strictEqual(Tabs.nextTab("removed", "Home"), "all");
assert.strictEqual(Tabs.nextTab("added", "End"), "modified");

console.log("frontend dashboard change tabs test passed");

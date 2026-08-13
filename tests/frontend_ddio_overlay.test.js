const assert = require("assert");
const DDIO = require("../frontend/ddio-overlay.js");

const headers = [
  { name: "IP Address", index: 0 },
  { name: "Reservation MAC Address", index: 1 },
  { name: "Lease MAC Address", index: 2 },
];
const mapping = DDIO.detectMapping(headers);
assert.deepStrictEqual(mapping, {
  deviceId: "",
  reservationMac: 1,
  reservationIp: "",
  leaseMac: 2,
  leaseIp: "",
  ip: 0,
});
assert.strictEqual(DDIO.validateMapping(mapping).valid, true);
assert.strictEqual(DDIO.ipVersion("192.168.1.1"), 4);
assert.strictEqual(DDIO.ipVersion("2001:db8::1"), 6);
assert.strictEqual(DDIO.ipVersion("999.1.1.1"), 0);
assert.strictEqual(DDIO.normalizeIp("not-an-ip"), "");

const wideHeaders = Array.from({ length: 14 }, (_value, index) => ({ name: `Column ${index + 1}`, index }));
wideHeaders[9].name = "Reservation MAC Address";
wideHeaders[10].name = "Reservation IP Address";
wideHeaders[12].name = "Lease MAC Address";
wideHeaders[13].name = "Lease IP Address";
const wideMapping = DDIO.detectMapping(wideHeaders);
assert.deepStrictEqual(wideMapping, {
  deviceId: "",
  reservationMac: 9,
  reservationIp: 10,
  leaseMac: 12,
  leaseIp: 13,
  ip: "",
});
assert.strictEqual(DDIO.validateMapping(wideMapping).reservationComplete, true);
assert.strictEqual(DDIO.validateMapping(wideMapping).leaseComplete, true);

const tracker = DDIO.createSwitchTracker();
DDIO.observeSwitch(tracker, 0, "00:11:22:33:44:55", "10.0.0.1", true);
DDIO.observeCurrentIp(tracker, "00:11:22:33:44:55", "192.168.1.10");
DDIO.observeSwitch(tracker, 0, "00:11:22:33:44:66", "10.0.0.8", true);
DDIO.observeSwitch(tracker, 1, "00:11:22:33:44:55", "10.0.0.2", true);
DDIO.observeSwitch(tracker, 1, "00:11:22:33:44:66", "10.0.0.8", true);

const changes = DDIO.switchChanges(tracker);
assert.strictEqual(changes.size, 0, "an enrichment file must not impersonate the previous database state");

const historicalTracker = DDIO.createSwitchTracker();
assert.strictEqual(
  DDIO.seedSwitchChange(historicalTracker, "00:11:22:33:44:55", "10.0.0.1", "10.0.0.9", "192.168.1.10"),
  true,
);
const historicalChanges = DDIO.switchChanges(historicalTracker);
assert.deepStrictEqual(historicalChanges.get("001122334455"), { before: "10.0.0.1", after: "10.0.0.9", deviceId: "" });

const candidates = new Map();
DDIO.collectCandidate(["192.168.1.20", "00-11-22-33-44-55", ""], mapping, historicalChanges, candidates);
DDIO.collectCandidate(["192.168.1.30", "", "00:11:22:33:44:55"], mapping, historicalChanges, candidates);
const overlay = DDIO.buildOverlay(historicalChanges, candidates, new Map([["001122334455", "192.168.1.10"]]));
assert.deepStrictEqual(overlay, {
  "001122334455": {
    ip: "192.168.1.30",
    possibleIps: ["192.168.1.20", "192.168.1.30"],
    match: "lease",
    source: "DDIO",
    previousSwitchIp: "10.0.0.1",
    currentSwitchIp: "10.0.0.9",
  },
});

const devices = [{ mac: "001122334455", ip: "192.168.1.10", switchIp: "10.0.0.2" }];
const before = JSON.stringify(devices);
DDIO.buildOverlay(historicalChanges, candidates, new Map());
assert.strictEqual(JSON.stringify(devices), before, "DDIO overlay must not mutate device data");

const sameIpOverlay = DDIO.buildOverlay(historicalChanges, candidates, new Map([["001122334455", "192.168.1.30"]]));
assert.deepStrictEqual(
  sameIpOverlay["001122334455"].possibleIps,
  ["192.168.1.20", "192.168.1.30"],
  "critical analytics retains every possible DDIO IP",
);

const fallbackDevices = [{ mac: "001122334455", ip: "" }];
const fallbackIndex = DDIO.buildPossibleIpIndex([["00:11:22:33:44:55", "192.168.1.60"]], { leaseMac: 0, leaseIp: 1 });
assert.strictEqual(DDIO.applyIpFallback(fallbackDevices, fallbackIndex), 1);
assert.strictEqual(fallbackDevices[0].ip, "192.168.1.60");
assert.strictEqual(fallbackDevices[0].ipSource, "ddio");

const wideRow = Array(14).fill("");
wideRow[9] = "00:11:22:33:44:55";
wideRow[10] = "192.168.1.40";
wideRow[12] = "00:11:22:33:44:55";
wideRow[13] = "192.168.1.50";
const wideCandidates = new Map();
DDIO.collectCandidate(wideRow, wideMapping, historicalChanges, wideCandidates);
assert.deepStrictEqual(wideCandidates.get("001122334455"), {
  ip: "192.168.1.50",
  match: "lease",
  possibleIps: ["192.168.1.40", "192.168.1.50"],
});

const deviceHeaders = [
  { name: "Device_ID", index: 0 },
  { name: "Reservation IP Address", index: 1 },
  { name: "Lease IP Address", index: 2 },
];
const deviceMapping = DDIO.detectMapping(deviceHeaders);
assert.deepStrictEqual(deviceMapping, {
  deviceId: 0,
  reservationMac: "",
  reservationIp: 1,
  leaseMac: "",
  leaseIp: 2,
  ip: "",
});
assert.strictEqual(DDIO.validateMapping(deviceMapping).deviceComplete, true);
const deviceIndex = DDIO.buildPossibleIpIndex(
  [
    ["SW-ROOM-1", "192.168.10.2", "192.168.10.3"],
    [" sw-room-1 ", "192.168.10.4", "192.168.10.3"],
    ["sw-room-1", "999.168.1.1", "not-an-ip"],
  ],
  deviceMapping,
);
assert.deepStrictEqual(deviceIndex.get("sw-room-1"), ["192.168.10.2", "192.168.10.3", "192.168.10.4"]);

const deviceTracker = DDIO.createSwitchTracker();
DDIO.seedSwitchChange(deviceTracker, "00:11:22:33:44:55", "10.0.0.1 ", " 10.0.0.2", "", "SW-ROOM-1");
const deviceChanges = DDIO.switchChanges(deviceTracker);
const deviceCandidates = new Map();
DDIO.collectCandidate(["sw-room-1", "192.168.10.2", "192.168.10.3"], deviceMapping, deviceChanges, deviceCandidates);
assert.deepStrictEqual(deviceCandidates.get("001122334455").possibleIps, ["192.168.10.2", "192.168.10.3"]);

console.log("frontend_ddio_overlay.test.js: ok");

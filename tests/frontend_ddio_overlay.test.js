const assert = require("assert");
const DDIO = require("../frontend/ddio-overlay.js");

const headers = [
  { name: "IP Address", index: 0 },
  { name: "Reservation MAC Address", index: 1 },
  { name: "Lease MAC Address", index: 2 },
];
const mapping = DDIO.detectMapping(headers);
assert.deepStrictEqual(mapping, { reservationMac: 1, reservationIp: "", leaseMac: 2, leaseIp: "", ip: 0 });
assert.strictEqual(DDIO.validateMapping(mapping).valid, true);

const wideHeaders = Array.from({ length: 14 }, (_value, index) => ({ name: `Column ${index + 1}`, index }));
wideHeaders[9].name = "Reservation MAC Address";
wideHeaders[10].name = "Reservation IP Address";
wideHeaders[12].name = "Lease MAC Address";
wideHeaders[13].name = "Lease IP Address";
const wideMapping = DDIO.detectMapping(wideHeaders);
assert.deepStrictEqual(wideMapping, {
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
assert.strictEqual(changes.size, 1, "only a real switch-IP change is eligible");

const candidates = new Map();
DDIO.collectCandidate(["192.168.1.20", "00-11-22-33-44-55", ""], mapping, changes, candidates);
DDIO.collectCandidate(["192.168.1.30", "", "00:11:22:33:44:55"], mapping, changes, candidates);
const overlay = DDIO.buildOverlay(changes, candidates, new Map([["001122334455", "192.168.1.10"]]));
assert.deepStrictEqual(overlay, {
  "001122334455": {
    ip: "192.168.1.30",
    match: "lease",
    previousSwitchIp: "10.0.0.1",
    currentSwitchIp: "10.0.0.2",
  },
});

const devices = [{ mac: "001122334455", ip: "192.168.1.10", switchIp: "10.0.0.2" }];
const before = JSON.stringify(devices);
DDIO.buildOverlay(changes, candidates, new Map());
assert.strictEqual(JSON.stringify(devices), before, "DDIO overlay must not mutate device data");

const sameIpOverlay = DDIO.buildOverlay(changes, candidates, new Map([["001122334455", "192.168.1.30"]]));
assert.deepStrictEqual(sameIpOverlay, {}, "an already stored IP is not a new DDIO hint");

const wideRow = Array(14).fill("");
wideRow[9] = "00:11:22:33:44:55";
wideRow[10] = "192.168.1.40";
wideRow[12] = "00:11:22:33:44:55";
wideRow[13] = "192.168.1.50";
const wideCandidates = new Map();
DDIO.collectCandidate(wideRow, wideMapping, changes, wideCandidates);
assert.deepStrictEqual(wideCandidates.get("001122334455"), { ip: "192.168.1.50", match: "lease" });

console.log("frontend_ddio_overlay.test.js: ok");

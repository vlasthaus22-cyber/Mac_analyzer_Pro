const assert = require("assert");
const DDIO = require("../frontend/ddio-overlay.js");

const headers = [
  { name: "IP Address", index: 0 },
  { name: "Reservation MAC Address", index: 1 },
  { name: "Lease MAC Address", index: 2 },
];
const mapping = DDIO.detectMapping(headers);
assert.deepStrictEqual(mapping, { reservationMac: 1, leaseMac: 2, ip: 0 });
assert.strictEqual(DDIO.validateMapping(mapping).valid, true);

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

console.log("frontend_ddio_overlay.test.js: ok");


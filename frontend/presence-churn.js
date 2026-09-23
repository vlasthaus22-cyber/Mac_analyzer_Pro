(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.MacAnalyzerPresenceChurn = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const normalizeMac = (value) => {
    const hex = String(value ?? "").toUpperCase().replace(/[^0-9A-F]/g, "");
    return hex.length === 12 ? hex : "";
  };
  const compact = (device = {}) => ({
    mac: normalizeMac(device.mac || device.macFormatted),
    macFormatted: normalizeMac(device.mac || device.macFormatted).replace(/(..)(?=.)/g, "$1:"),
    vendor: String(device.vendor || ""), model: String(device.model || ""), ip: String(device.ip || ""),
    room: String(device.room || ""), address: String(device.address || ""), smartroomId: String(device.smartroomId || device.smartroom_id || "")
  });

  function createTracker() {
    let previous = new Set(), snapshots = 0;
    const records = new Map();
    return {
      observe(snapshot = {}, devices = []) {
        const current = new Map();
        for (const raw of devices || []) { const device = compact(raw), mac = device.mac; if (mac && !current.has(mac)) current.set(mac, device); }
        for (const mac of previous) if (!current.has(mac)) {
          const item = records.get(mac); if (item && item.presentLast) { item.disappearances += 1; item.transitions.push({ type: "absent", snapshotId: String(snapshot.id || ""), name: String(snapshot.name || ""), date: String(snapshot.fileCreatedAt || snapshot.createdAt || snapshot.savedAt || "") }); item.presentLast = false; }
        }
        for (const [mac, device] of current) {
          let item = records.get(mac);
          if (!item) item = { mac, macFormatted: device.macFormatted, vendor: device.vendor, model: device.model, ip: device.ip, room: device.room, address: device.address, smartroomId: device.smartroomId, firstSeen: String(snapshot.fileCreatedAt || snapshot.createdAt || snapshot.savedAt || ""), lastSeen: "", presentCount: 0, disappearances: 0, reappearances: 0, transitions: [], presentLast: false, everSeen: false };
          if (item.everSeen && !item.presentLast) { item.reappearances += 1; item.transitions.push({ type: "present", snapshotId: String(snapshot.id || ""), name: String(snapshot.name || ""), date: String(snapshot.fileCreatedAt || snapshot.createdAt || snapshot.savedAt || "") }); }
          Object.assign(item, Object.fromEntries(Object.entries(device).filter(([, value]) => value)));
          item.presentCount += 1; item.lastSeen = String(snapshot.fileCreatedAt || snapshot.createdAt || snapshot.savedAt || ""); item.presentLast = true; item.everSeen = true; records.set(mac, item);
        }
        previous = new Set(current.keys()); snapshots += 1;
      },
      result(options = {}) {
        const query = String(options.query || "").trim().toLowerCase(), limit = Math.max(1, Number(options.limit || 500));
        const items = Array.from(records.values()).map((item) => ({ ...item, transitions: item.transitions.slice(), transitionCount: item.disappearances + item.reappearances, absentCount: Math.max(0, snapshots - item.presentCount) }))
          .filter((item) => item.disappearances > 0 && item.reappearances > 0)
          .filter((item) => !query || Object.values(item).join(" ").toLowerCase().includes(query))
          .sort((a, b) => b.transitionCount - a.transitionCount || b.reappearances - a.reappearances || a.mac.localeCompare(b.mac));
        return { snapshotCount: snapshots, total: items.length, items: items.slice(0, limit) };
      }
    };
  }
  function analyze(snapshots = [], options = {}) { const tracker = createTracker(); for (const snapshot of snapshots || []) tracker.observe(snapshot, snapshot.devices || []); return tracker.result(options); }
  return { normalizeMac, createTracker, analyze };
});

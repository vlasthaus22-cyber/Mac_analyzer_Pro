(() => {
  "use strict";

  const text = (value) => String(value ?? "").trim();
  const normalizeMac = (value) => {
    let mac = text(value).toUpperCase().replace(/[^0-9A-F]/g, "");
    if (mac.length === 10) mac = "00" + mac;
    if (mac.length === 11) mac = "0" + mac;
    if (mac.length === 8) mac = "0000" + mac;
    return mac.length === 12 ? mac : "";
  };
  const token = (value) => text(value).replace(/\s+/g, " ").toLowerCase();

  function candidates(device = {}) {
    const mac = normalizeMac(device.mac || device.macFormatted);
    const serial = token(device.serialNumber || device.serial_number || device.serial);
    const deviceId = token(device.deviceId || device.device_id || device.asset_id);
    const hostname = token(device.hostname || device.host_name);
    return [
      mac && `mac:${mac}`,
      serial && `serial:${serial}`,
      deviceId && `device:${deviceId}`,
      hostname && serial && `host-serial:${hostname}|${serial}`,
    ].filter(Boolean);
  }

  function key(device = {}) {
    return candidates(device)[0] || "";
  }

  function buildIndex(devices = []) {
    const index = new Map(), ambiguous = new Set();
    for (const device of devices || []) {
      for (const candidate of candidates(device)) {
        if (index.has(candidate) && index.get(candidate) !== device) ambiguous.add(candidate);
        else index.set(candidate, device);
      }
    }
    for (const candidate of ambiguous) index.delete(candidate);
    return index;
  }

  function find(device, index) {
    const matches = new Set(candidates(device).map((candidate) => index?.get(candidate)).filter(Boolean));
    return matches.size === 1 ? matches.values().next().value : null;
  }

  function comparisonKey(device = {}) {
    return key(device) || `room-mac:${token(device.smartroomId || device.smartroom_id)}|${normalizeMac(device.mac)}`;
  }

  function pairSets(previousDevices = [], currentDevices = []) {
    const previous = (previousDevices || []).filter((item) => item && typeof item === "object");
    const current = (currentDevices || []).filter((item) => item && typeof item === "object");
    const index = buildIndex(previous), used = new Set(), pairs = [], added = [];
    for (const device of current) {
      const match = find(device, index);
      if (!match || used.has(match)) added.push(device);
      else { used.add(match); pairs.push([match, device]); }
    }
    return { pairs, added, removed: previous.filter((device) => !used.has(device)) };
  }

  const api = Object.freeze({ buildIndex, candidates, comparisonKey, find, key, normalizeMac, pairSets, token });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.MacAnalyzerDeviceIdentity = api;
})();

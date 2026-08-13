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
    const internalId = token(device.internalDeviceId || device.internal_device_id);
    return [
      internalId && `internal-id:${internalId}`,
      mac && `mac:${mac}`,
      serial && `serial:${serial}`,
      deviceId && `device:${deviceId}`,
      hostname && serial && `host-serial:${hostname}|${serial}`,
    ].filter(Boolean);
  }

  function key(device = {}) {
    return candidates(device).find((candidate) => !candidate.startsWith("internal-id:")) || "";
  }

  function stableId(device = {}, namespace = "") {
    const existing = text(device.internalDeviceId || device.internal_device_id);
    if (existing) return existing;
    const strongest = key(device);
    if (!strongest) return "";
    const seed = [token(namespace), strongest].join("|");
    let hash = 2166136261;
    for (const byte of new TextEncoder().encode(seed)) {
      hash ^= byte;
      hash = Math.imul(hash, 16777619);
    }
    return `dev-${(hash >>> 0).toString(16).padStart(8, "0")}`;
  }

  function buildIndex(devices = []) {
    const index = new Map();
    index.ambiguousCandidates = new Set();
    for (const device of devices || []) addToIndex(index, device);
    return index;
  }

  function addToIndex(index, device) {
    if (!index.ambiguousCandidates) index.ambiguousCandidates = new Set();
    for (const candidate of candidates(device)) {
      if (index.ambiguousCandidates.has(candidate)) continue;
      if (index.has(candidate) && index.get(candidate) !== device) {
        index.delete(candidate);
        index.ambiguousCandidates.add(candidate);
      } else index.set(candidate, device);
    }
    return index;
  }

  function find(device, index) {
    return resolve(device, index).match;
  }

  function resolve(device, index, options = {}) {
    const scores = { "internal-id": 1, mac: 1, serial: 0.96, device: 0.95, "host-serial": 0.92 };
    const evidence = [], matches = new Set();
    const ambiguousEvidence = [];
    for (const candidate of candidates(device)) {
      if (index?.ambiguousCandidates?.has(candidate)) { ambiguousEvidence.push(candidate); continue; }
      const match = index?.get(candidate);
      if (!match) continue;
      const kind = candidate.split(":", 1)[0], score = scores[kind] || 0.75;
      evidence.push({ candidate, kind, score, confidence: score === 1 ? "Exact" : score >= 0.9 ? "High" : "Medium" });
      matches.add(match);
    }
    if (matches.size > 1) return { status: "conflict", match: null, confidence: "Conflict", score: 0, evidence };
    if (!matches.size && ambiguousEvidence.length) return { status: "conflict", match: null, confidence: "Conflict", score: 0, evidence: ambiguousEvidence.map((candidate) => ({ candidate, kind: candidate.split(":", 1)[0], confidence: "Conflict", score: 0 })) };
    if (!matches.size) return { status: "unmatched", match: null, confidence: "Low", score: 0, evidence: [] };
    const match = matches.values().next().value;
    const incomingMac = normalizeMac(device.mac || device.macFormatted), matchedMac = normalizeMac(match.mac || match.macFormatted);
    const exact = evidence.some((item) => item.kind === "internal-id" || item.kind === "mac");
    if (incomingMac && matchedMac && incomingMac !== matchedMac && !exact && options.allowIdentifierChanges !== true) return { status: "conflict", match: null, confidence: "Conflict", score: 0, evidence };
    const best = evidence.sort((left, right) => right.score - left.score)[0];
    return { status: "matched", match, confidence: best.confidence, score: best.score, evidence, ambiguousEvidence };
  }

  function comparisonKey(device = {}) {
    return key(device) || `room-mac:${token(device.smartroomId || device.smartroom_id)}|${normalizeMac(device.mac)}`;
  }

  function pairSets(previousDevices = [], currentDevices = []) {
    const previous = (previousDevices || []).filter((item) => item && typeof item === "object");
    const current = (currentDevices || []).filter((item) => item && typeof item === "object");
    const index = buildIndex(previous), used = new Set(), pairs = [], added = [];
    for (const device of current) {
      const match = resolve(device, index, { allowIdentifierChanges: true }).match;
      if (!match || used.has(match)) added.push(device);
      else { used.add(match); pairs.push([match, device]); }
    }
    return { pairs, added, removed: previous.filter((device) => !used.has(device)) };
  }

  const api = Object.freeze({ addToIndex, buildIndex, candidates, comparisonKey, find, key, normalizeMac, pairSets, resolve, stableId, token });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.MacAnalyzerDeviceIdentity = api;
})();

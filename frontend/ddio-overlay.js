(() => {
  "use strict";

  const text = (value) => String(value ?? "").trim();

  function ipVersion(value) {
    const candidate = text(value)
      .replace(/^\[|\]$/g, "")
      .split("%")[0];
    if (
      /^\d{1,3}(?:\.\d{1,3}){3}$/.test(candidate) &&
      candidate.split(".").every((part) => Number(part) >= 0 && Number(part) <= 255)
    )
      return 4;
    if (!candidate.includes(":") || !/^[0-9a-f:]+$/i.test(candidate) || (candidate.match(/::/g) || []).length > 1)
      return 0;
    const sides = candidate.split("::");
    const groups = sides.flatMap((side) => (side ? side.split(":") : [])).filter(Boolean);
    if (!groups.every((group) => /^[0-9a-f]{1,4}$/i.test(group))) return 0;
    return sides.length === 2 ? (groups.length < 8 ? 6 : 0) : groups.length === 8 ? 6 : 0;
  }

  function normalizeIp(value) {
    const candidate = text(value).replace(/^\[|\]$/g, "");
    return ipVersion(candidate) ? candidate : "";
  }

  function parsePossibleIps(value) {
    const values = Array.isArray(value) ? value : text(value).replace(/\r?\n/g, ";").replace(/,/g, ";").split(";");
    return Array.from(new Set(values.map(normalizeIp).filter(Boolean)));
  }

  function normalizeMac(value) {
    let normalized = text(value)
      .toUpperCase()
      .replace(/[^0-9A-F]/g, "");
    if (normalized.length === 10) normalized = "00" + normalized;
    if (normalized.length === 11) normalized = "0" + normalized;
    if (normalized.length === 8) normalized = "0000" + normalized;
    return normalized.length === 12 ? normalized : "";
  }

  function normalizeHeader(value) {
    return text(value)
      .toLowerCase()
      .replace(/ё/g, "е")
      .replace(/[_./\\()-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function headerValue(header) {
    return typeof header === "object" && header !== null ? header.name : header;
  }

  function headerIndex(header, fallback) {
    const value = typeof header === "object" && header !== null ? header.index : fallback;
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed >= 0 ? parsed : fallback;
  }

  function scoreHeader(header, field) {
    const normalized = normalizeHeader(header);
    const hasMac = /(^| )(mac|мак)( |$)/.test(normalized) || normalized.includes("hardware address");
    const reservation = /(reservation|reserved|fixed address|fixed mac|резервац|зарезерв)/.test(normalized);
    const lease = /(lease|leased|аренд|выдан)/.test(normalized);
    const ip = /(^| )(ip|ipv4)( |$)/.test(normalized) || /ip адрес|адрес ip/.test(normalized);
    if (field === "deviceId") {
      return /(device id|device identifier|идентификатор устройства|id устройства|устройство id)/.test(normalized)
        ? 40
        : -1;
    }
    if (field === "possibleIps") {
      return /(possible ips?|possible addresses|возможн.*ip|вариант.*ip)/.test(normalized) ? 45 : -1;
    }
    if (field === "reservationMac") {
      if (!hasMac) return -1;
      if (lease && !reservation) return -1;
      return 10 + (reservation ? 20 : 0) - (lease ? 8 : 0);
    }
    if (field === "leaseMac") {
      if (!hasMac) return -1;
      if (reservation && !lease) return -1;
      return 10 + (lease ? 20 : 0) - (reservation ? 8 : 0);
    }
    if (field === "reservationIp") {
      if (!ip || /switch|коммутатор|gateway|шлюз/.test(normalized) || !reservation) return -1;
      return 30 - (lease ? 8 : 0) + (/address|адрес/.test(normalized) ? 5 : 0);
    }
    if (field === "leaseIp") {
      if (!ip || /switch|коммутатор|gateway|шлюз/.test(normalized) || !lease) return -1;
      return 30 - (reservation ? 8 : 0) + (/address|адрес/.test(normalized) ? 5 : 0);
    }
    if (field === "ip") {
      if (!ip || /switch|коммутатор|gateway|шлюз/.test(normalized)) return -1;
      if (reservation || lease) return -1;
      return 10 + (/address|адрес/.test(normalized) ? 5 : 0);
    }
    return -1;
  }

  function detectMapping(headers = []) {
    const entries = headers.map((header, fallback) => ({
      name: headerValue(header),
      index: headerIndex(header, fallback),
    }));
    const pick = (field, excluded = new Set()) => {
      let best = { index: "", score: -1 };
      for (const entry of entries) {
        if (excluded.has(entry.index)) continue;
        const score = scoreHeader(entry.name, field);
        if (score > best.score) best = { index: entry.index, score };
      }
      return best.score >= 0 ? best.index : "";
    };
    const reservationMac = pick("reservationMac");
    const leaseMac = pick("leaseMac", new Set(reservationMac === "" ? [] : [reservationMac]));
    return {
      deviceId: pick("deviceId"),
      possibleIps: pick("possibleIps"),
      reservationMac,
      reservationIp: pick("reservationIp"),
      leaseMac,
      leaseIp: pick("leaseIp"),
      ip: pick("ip"),
    };
  }

  function compileMapping(mapping = {}) {
    const result = {};
    for (const field of ["deviceId", "reservationMac", "reservationIp", "leaseMac", "leaseIp", "ip", "possibleIps"]) {
      if (mapping[field] === "" || mapping[field] === undefined || mapping[field] === null) continue;
      const index = Number(mapping[field]);
      if (Number.isInteger(index) && index >= 0) result[field] = index;
    }
    return result;
  }

  function validateMapping(mapping = {}) {
    const compiled = compileMapping(mapping);
    const reservationComplete =
      compiled.reservationMac !== undefined && (compiled.reservationIp !== undefined || compiled.ip !== undefined);
    const leaseComplete =
      compiled.leaseMac !== undefined && (compiled.leaseIp !== undefined || compiled.ip !== undefined);
    const deviceComplete =
      compiled.deviceId !== undefined &&
      (compiled.reservationIp !== undefined ||
        compiled.leaseIp !== undefined ||
        compiled.ip !== undefined ||
        compiled.possibleIps !== undefined);
    return {
      valid: reservationComplete || leaseComplete || deviceComplete,
      hasIp: compiled.reservationIp !== undefined || compiled.leaseIp !== undefined || compiled.ip !== undefined,
      hasMac: compiled.reservationMac !== undefined || compiled.leaseMac !== undefined,
      reservationComplete,
      leaseComplete,
      deviceComplete,
      mapping: compiled,
    };
  }

  function createSwitchTracker() {
    return new Map();
  }

  function seedSwitchChange(tracker, macValue, beforeValue, afterValue, currentIpValue = "", deviceIdValue = "") {
    const mac = normalizeMac(macValue);
    const deviceId = text(deviceIdValue).toLowerCase();
    const identity = mac || (deviceId ? `device-id:${deviceId}` : "");
    const before = text(beforeValue);
    const after = text(afterValue);
    if (!identity || !before || !after || before === after || !(tracker instanceof Map)) return false;
    tracker.set(identity, { before, after, currentIp: text(currentIpValue), deviceId });
    return true;
  }

  function observeSwitch(tracker, fileIndex, macValue, switchIpValue, deviceIdValue = "") {
    const mac = normalizeMac(macValue);
    const switchIp = text(switchIpValue);
    if (!mac || !switchIp || !(tracker instanceof Map)) return false;
    if (fileIndex === 0) {
      tracker.set(mac, { before: switchIp, after: switchIp, deviceId: text(deviceIdValue).toLowerCase() });
      return true;
    }
    // Enrichment files are not an authoritative previous state. A real
    // transition is seeded later from the last value persisted in IndexedDB.
    return false;
  }

  function observeCurrentIp(tracker, macValue, ipValue) {
    const mac = normalizeMac(macValue);
    const ip = text(ipValue);
    const current = tracker instanceof Map ? tracker.get(mac) : null;
    if (!current || !ip) return false;
    current.currentIp = ip;
    return true;
  }

  function switchChanges(tracker) {
    const changes = new Map();
    const deviceIds = new Map();
    Object.defineProperty(changes, "deviceIds", { value: deviceIds, enumerable: false });
    if (!(tracker instanceof Map)) return changes;
    for (const [identity, item] of tracker.entries()) {
      const before = text(item?.before);
      const after = text(item?.after);
      if (before && after && before !== after) {
        const deviceId = text(item?.deviceId).toLowerCase();
        changes.set(identity, { before, after, deviceId });
        if (deviceId) {
          const macs = deviceIds.get(deviceId) || new Set();
          macs.add(identity);
          deviceIds.set(deviceId, macs);
        }
      }
    }
    return changes;
  }

  function collectCandidate(row, mapping, changes, candidates) {
    if (!Array.isArray(row) || !(changes instanceof Map) || !(candidates instanceof Map)) return 0;
    const compiled = compileMapping(mapping);
    let matched = 0;
    const deviceId = compiled.deviceId === undefined ? "" : text(row[compiled.deviceId]).toLowerCase();
    const deviceMacs = deviceId ? Array.from(changes.deviceIds?.get(deviceId) || []) : [];
    const reservationMac = compiled.reservationMac === undefined ? "" : normalizeMac(row[compiled.reservationMac]);
    const leaseMac = compiled.leaseMac === undefined ? "" : normalizeMac(row[compiled.leaseMac]);
    const reservationIpIndex = compiled.reservationIp ?? compiled.ip;
    const leaseIpIndex = compiled.leaseIp ?? compiled.ip;
    const reservationIp = reservationIpIndex === undefined ? "" : normalizeIp(row[reservationIpIndex]);
    const leaseIp = leaseIpIndex === undefined ? "" : normalizeIp(row[leaseIpIndex]);
    const explicitPossible = compiled.possibleIps === undefined ? [] : parsePossibleIps(row[compiled.possibleIps]);
    const addCandidate = (mac, ip, match) => {
      if (!mac || !ip || !changes.has(mac)) return;
      const existing = candidates.get(mac),
        possibleIps = Array.from(new Set([...(existing?.possibleIps || (existing?.ip ? [existing.ip] : [])), ip]));
      candidates.set(mac, { ip, match, possibleIps });
      matched += 1;
    };
    addCandidate(reservationMac, reservationIp, "reservation");
    addCandidate(leaseMac, leaseIp, "lease");
    for (const mac of deviceMacs) {
      addCandidate(mac, reservationIp, "device-id/reservation");
      addCandidate(mac, leaseIp, "device-id/lease");
    }
    const addPossible = (mac, match) => {
      if (!mac || !changes.has(mac) || !explicitPossible.length) return;
      const existing = candidates.get(mac) || { ip: "", match, possibleIps: [] };
      existing.possibleIps = Array.from(new Set([...(existing.possibleIps || []), ...explicitPossible]));
      if (!existing.match) existing.match = match;
      candidates.set(mac, existing);
      matched += 1;
    };
    addPossible(reservationMac, "reservation/possible-ips");
    addPossible(leaseMac, "lease/possible-ips");
    for (const mac of deviceMacs) addPossible(mac, "device-id/possible-ips");
    return matched;
  }

  function buildPossibleIpIndex(rows = [], mapping = {}) {
    const compiled = compileMapping(mapping),
      index = new Map();
    for (const row of rows || []) collectPossibleIp(row, compiled, index);
    return index;
  }

  function collectPossibleIp(row, mapping = {}, index = new Map()) {
    const compiled =
      mapping && Object.values(mapping).every((value) => Number.isInteger(value)) ? mapping : compileMapping(mapping);
    const add = (key, ip) => {
      const normalizedKey = text(key).toLowerCase(),
        normalizedIp = normalizeIp(ip);
      if (!normalizedKey || !normalizedIp) return;
      const values = index.get(normalizedKey) || [];
      if (!values.includes(normalizedIp)) values.push(normalizedIp);
      index.set(normalizedKey, values);
    };
    if (!Array.isArray(row)) return 0;
    const deviceId = compiled.deviceId === undefined ? "" : row[compiled.deviceId];
    const reservationMac = compiled.reservationMac === undefined ? "" : normalizeMac(row[compiled.reservationMac]);
    const leaseMac = compiled.leaseMac === undefined ? "" : normalizeMac(row[compiled.leaseMac]);
    const reservationIp = row[compiled.reservationIp ?? compiled.ip];
    const leaseIp = row[compiled.leaseIp ?? compiled.ip];
    add(deviceId, reservationIp);
    add(deviceId, leaseIp);
    add(reservationMac, reservationIp);
    add(leaseMac, leaseIp);
    // Possible IPs are intentionally excluded from the fallback index: they
    // are diagnostic alternatives and never become the current device IP.
    return index.size;
  }

  function applyIpFallback(devices = [], index = new Map()) {
    let updated = 0;
    for (const device of devices || []) {
      if (normalizeIp(device?.ip)) continue;
      const mac = normalizeMac(device?.mac || device?.macFormatted);
      const deviceId = text(device?.deviceId || device?.device_id).toLowerCase();
      const values = index.get(mac) || (deviceId ? index.get(deviceId) : null) || [];
      if (!values.length) continue;
      device.ip = values.at(-1);
      device.ipSource = "ddio";
      device.fieldSources = { ...(device.fieldSources || {}), ip: "DDIO" };
      device.possibleIps = [...values];
      updated += 1;
    }
    return updated;
  }

  function buildOverlay(changes, candidates, currentIpByMac = new Map()) {
    const overlay = {};
    if (!(changes instanceof Map) || !(candidates instanceof Map)) return overlay;
    for (const [mac, change] of changes.entries()) {
      const candidate = candidates.get(mac);
      if (!candidate || (!(candidate.possibleIps || []).length && !candidate.ip)) continue;
      const possibleIps = Array.from(
        new Set((candidate.possibleIps || [candidate.ip]).map(normalizeIp).filter(Boolean)),
      );
      if (!possibleIps.length) continue;
      overlay[mac] = {
        ip: possibleIps.includes(candidate.ip) ? candidate.ip : possibleIps[0],
        possibleIps,
        match: candidate.match,
        source: "DDIO",
        previousSwitchIp: text(change.before),
        currentSwitchIp: text(change.after),
      };
    }
    return overlay;
  }

  const api = Object.freeze({
    buildOverlay,
    buildPossibleIpIndex,
    collectPossibleIp,
    applyIpFallback,
    collectCandidate,
    compileMapping,
    createSwitchTracker,
    detectMapping,
    normalizeHeader,
    normalizeIp,
    parsePossibleIps,
    normalizeMac,
    ipVersion,
    observeCurrentIp,
    observeSwitch,
    seedSwitchChange,
    switchChanges,
    validateMapping,
  });

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") {
    window.MacAnalyzerDdioOverlay = api;
    document.documentElement.dataset.ddioOverlay = "ready";
  }
})();

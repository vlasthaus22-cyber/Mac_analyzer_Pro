(() => {
  "use strict";

  const text = (value) => String(value ?? "").trim();

  function normalizeMac(value) {
    let normalized = text(value).toUpperCase().replace(/[^0-9A-F]/g, "");
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
      reservationMac,
      reservationIp: pick("reservationIp"),
      leaseMac,
      leaseIp: pick("leaseIp"),
      ip: pick("ip"),
    };
  }

  function compileMapping(mapping = {}) {
    const result = {};
    for (const field of ["reservationMac", "reservationIp", "leaseMac", "leaseIp", "ip"]) {
      if (mapping[field] === "" || mapping[field] === undefined || mapping[field] === null) continue;
      const index = Number(mapping[field]);
      if (Number.isInteger(index) && index >= 0) result[field] = index;
    }
    return result;
  }

  function validateMapping(mapping = {}) {
    const compiled = compileMapping(mapping);
    const reservationComplete = compiled.reservationMac !== undefined
      && (compiled.reservationIp !== undefined || compiled.ip !== undefined);
    const leaseComplete = compiled.leaseMac !== undefined
      && (compiled.leaseIp !== undefined || compiled.ip !== undefined);
    return {
      valid: reservationComplete || leaseComplete,
      hasIp: compiled.reservationIp !== undefined || compiled.leaseIp !== undefined || compiled.ip !== undefined,
      hasMac: compiled.reservationMac !== undefined || compiled.leaseMac !== undefined,
      reservationComplete,
      leaseComplete,
      mapping: compiled,
    };
  }

  function createSwitchTracker() {
    return new Map();
  }

  function observeSwitch(tracker, fileIndex, macValue, switchIpValue, existedBeforeMerge = true) {
    const mac = normalizeMac(macValue);
    const switchIp = text(switchIpValue);
    if (!mac || !switchIp || !(tracker instanceof Map)) return false;
    if (fileIndex === 0) {
      tracker.set(mac, { before: switchIp, after: switchIp });
      return true;
    }
    const current = tracker.get(mac);
    if (!current || !existedBeforeMerge) return false;
    current.after = switchIp;
    return true;
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
    if (!(tracker instanceof Map)) return changes;
    for (const [mac, item] of tracker.entries()) {
      const before = text(item?.before);
      const after = text(item?.after);
      if (before && after && before !== after) changes.set(mac, { before, after });
    }
    return changes;
  }

  function collectCandidate(row, mapping, changes, candidates) {
    if (!Array.isArray(row) || !(changes instanceof Map) || !(candidates instanceof Map)) return 0;
    const compiled = compileMapping(mapping);
    let matched = 0;
    const reservationMac = compiled.reservationMac === undefined ? "" : normalizeMac(row[compiled.reservationMac]);
    const leaseMac = compiled.leaseMac === undefined ? "" : normalizeMac(row[compiled.leaseMac]);
    const reservationIpIndex = compiled.reservationIp ?? compiled.ip;
    const leaseIpIndex = compiled.leaseIp ?? compiled.ip;
    const reservationIp = reservationIpIndex === undefined ? "" : text(row[reservationIpIndex]);
    const leaseIp = leaseIpIndex === undefined ? "" : text(row[leaseIpIndex]);
    if (reservationMac && reservationIp && changes.has(reservationMac) && !candidates.has(reservationMac)) {
      candidates.set(reservationMac, { ip: reservationIp, match: "reservation" });
      matched++;
    }
    if (leaseMac && leaseIp && changes.has(leaseMac)) {
      candidates.set(leaseMac, { ip: leaseIp, match: "lease" });
      matched++;
    }
    return matched;
  }

  function buildOverlay(changes, candidates, currentIpByMac = new Map()) {
    const overlay = {};
    if (!(changes instanceof Map) || !(candidates instanceof Map)) return overlay;
    for (const [mac, change] of changes.entries()) {
      const candidate = candidates.get(mac);
      if (!candidate?.ip) continue;
      const currentIp = text(currentIpByMac instanceof Map ? currentIpByMac.get(mac) : currentIpByMac?.[mac]);
      if (currentIp && currentIp === candidate.ip) continue;
      overlay[mac] = {
        ip: candidate.ip,
        match: candidate.match,
        previousSwitchIp: text(change.before),
        currentSwitchIp: text(change.after),
      };
    }
    return overlay;
  }

  const api = Object.freeze({
    buildOverlay,
    collectCandidate,
    compileMapping,
    createSwitchTracker,
    detectMapping,
    normalizeHeader,
    normalizeMac,
    observeCurrentIp,
    observeSwitch,
    switchChanges,
    validateMapping,
  });

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") {
    window.MacAnalyzerDdioOverlay = api;
    document.documentElement.dataset.ddioOverlay = "ready";
  }
})();

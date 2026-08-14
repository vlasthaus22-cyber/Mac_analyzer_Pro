(() => {
  "use strict";

  const NO_EXPANSION = "NO_EXPANSION";
  const ALLOW_EXPANSION = "ALLOW_EXPANSION";
  const legacyExpansionAliases = new Set([
    "allow_expansion", "allow-expansion", "expand", "union", "merge", "primary",
  ]);

  function normalize(value) {
    return legacyExpansionAliases.has(String(value || "").trim().toLowerCase())
      ? ALLOW_EXPANSION
      : NO_EXPANSION;
  }

  function normalizeRole(value) {
    const role = String(value || "").trim().toLowerCase();
    if (["smartroom", "smart-room", "sr", "enrichment", "secondary"].includes(role)) return "smartroom";
    if (role === "ddio") return "ddio";
    if (role === "history" || role === "previous-final") return "history";
    return "primary";
  }

  function allowsCreation(sourceRole, strategy) {
    const role = normalizeRole(sourceRole);
    return role === "primary" || (role === "smartroom" && normalize(strategy) === ALLOW_EXPANSION);
  }

  function conflictStableId(identityApi, device) {
    const clone = { ...(device || {}) };
    delete clone.internalDeviceId;
    delete clone.internal_device_id;
    return identityApi.stableId(clone, `primary-conflict:${clone.source || ""}:${clone.row || ""}`);
  }

  function appendDecision(diagnostics, decision) {
    if (!diagnostics || !decision) return;
    diagnostics.decisions ||= [];
    diagnostics.decisionLimit ||= 5000;
    if (diagnostics.decisions.length < diagnostics.decisionLimit) diagnostics.decisions.push(decision);
    else diagnostics.decisionsTruncated = true;
  }

  function resolveOrCreate(options = {}) {
    const {
      candidate, index, devices, identityApi, merge, strategy,
      sourceRole = candidate?.sourceRole, diagnostics,
    } = options;
    if (!candidate || !index || !Array.isArray(devices) || !identityApi || typeof merge !== "function") {
      throw new TypeError("resolveOrCreateDevice requires candidate, identity index, device array and merge callback");
    }
    const role = normalizeRole(sourceRole);
    const normalizedStrategy = normalize(strategy);
    const resolution = identityApi.resolve(candidate, index);
    const baseDecision = {
      source: String(candidate.source || ""), sourceRole: role, row: candidate.row,
      strategy: normalizedStrategy, strongIdentifiers: identityApi.candidates(candidate),
      evidence: resolution.evidence || [],
    };
    if (resolution.status === "conflict") {
      if (role !== "primary") {
        const decision = { ...baseDecision, code: "NOT_CREATED_FROM_SMARTROOM_CONFLICT", reason: "ambiguous strong identifiers" };
        appendDecision(diagnostics, decision);
        return { status: "conflict-skipped", device: null, resolution, decision };
      }
      const created = merge(null, candidate, { preferExisting: false });
      created.internalDeviceId = conflictStableId(identityApi, created);
      created.conflicts = [...(created.conflicts || []), {
        field: "identity", selected: created.internalDeviceId, selectedSource: candidate.source || "",
        alternative: "Multiple main devices match strong identifiers", alternativeSource: "identity-resolver",
        confidence: "Conflict", evidence: resolution.evidence || [],
      }];
      created.hasConflict = true;
      created.matchConfidence = "Conflict";
      devices.push(created);
      identityApi.addToIndex(index, created);
      const decision = { ...baseDecision, code: "CREATED_FROM_MAIN_CONFLICT", reason: "main rows cannot be dropped on ambiguous identity" };
      appendDecision(diagnostics, decision);
      return { status: "created", device: created, resolution, decision };
    }
    if (resolution.match) {
      const existing = resolution.match;
      const merged = merge(existing, candidate, { preferExisting: true });
      merged.internalDeviceId = existing.internalDeviceId || identityApi.stableId(merged);
      merged.matchConfidence = resolution.confidence || "High";
      Object.keys(existing).forEach((key) => delete existing[key]);
      Object.assign(existing, merged);
      identityApi.addToIndex(index, existing);
      return { status: "matched", device: existing, resolution, decision: null };
    }
    if (!allowsCreation(role, normalizedStrategy)) {
      const code = role === "ddio" ? "NOT_CREATED_FROM_DDIO" : "NOT_CREATED_FROM_SMARTROOM";
      const decision = { ...baseDecision, code, reason: role === "ddio" ? "DDIO is enrichment-only" : "strategy=NO_EXPANSION" };
      appendDecision(diagnostics, decision);
      return { status: "unmatched-skipped", device: null, resolution, decision };
    }
    const created = merge(null, candidate, { preferExisting: false });
    created.internalDeviceId = identityApi.stableId(created);
    created.matchConfidence = created.mac ? "Exact" : "High";
    devices.push(created);
    identityApi.addToIndex(index, created);
    const decision = role === "smartroom"
      ? { ...baseDecision, code: "CREATED_FROM_SMARTROOM", reason: "unmatched strong identity and strategy=ALLOW_EXPANSION" }
      : null;
    appendDecision(diagnostics, decision);
    return { status: "created", device: created, resolution, decision };
  }

  const api = Object.freeze({
    ALLOW_EXPANSION, NO_EXPANSION, allowsCreation, normalize, normalizeRole, resolveOrCreate,
  });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.MacAnalyzerEnrichmentStrategy = api;
})();

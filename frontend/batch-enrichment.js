(function (global) {
  "use strict";

  const SUPPORTED_EXTENSIONS = new Set(["csv", "tsv", "txt", "json", "xlsx", "xlsm", "xls"]);
  const ROLES = new Set(["primary", "smartroom", "ddio"]);

  function extension(name) {
    const match = String(name || "").toLowerCase().match(/\.([^.]+)$/);
    return match ? match[1] : "";
  }

  function isSupportedFile(file) {
    return Boolean(file && SUPPORTED_EXTENSIONS.has(extension(file.name)));
  }

  function roleName(role) {
    return ROLES.has(String(role || "").toLowerCase()) ? String(role).toLowerCase() : "primary";
  }

  function timestamp(value) {
    const parsed = new Date(value || "").getTime();
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function calendarDay(value) {
    const parsed = new Date(value || "");
    if (!Number.isFinite(parsed.getTime())) return "";
    return [parsed.getUTCFullYear(), String(parsed.getUTCMonth() + 1).padStart(2, "0"), String(parsed.getUTCDate()).padStart(2, "0")].join("-");
  }

  function descriptorId(file, role, index) {
    return [roleName(role), index, file?.webkitRelativePath || file?.name || "file", Number(file?.size || 0), Number(file?.lastModified || 0)].join(":");
  }

  function toleranceHours(value) {
    const parsed = Number(value ?? 24);
    return Number.isFinite(parsed) ? Math.max(0, parsed) : 24;
  }

  async function describeFiles(files, role, dateResolver) {
    const normalizedRole = roleName(role);
    const accepted = Array.from(files || []).filter(isSupportedFile);
    const result = new Array(accepted.length);
    let cursor = 0;
    const worker = async () => {
      while (cursor < accepted.length) {
        const index = cursor++;
        const file = accepted[index];
        const info = await dateResolver(file);
        result[index] = {
        id: descriptorId(file, normalizedRole, index),
        role: normalizedRole,
        name: String(file.name || ""),
        relativePath: String(file.webkitRelativePath || file.name || ""),
        size: Number(file.size || 0),
        date: String(info?.date || ""),
        dateSource: String(info?.source || "file.lastModified"),
          file,
        };
      }
    };
    await Promise.all(Array.from({ length: Math.min(8, accepted.length) }, worker));
    return result.sort((left, right) => timestamp(left.date) - timestamp(right.date) || left.name.localeCompare(right.name, "ru"));
  }

  function allowedPair(anchor, candidate, options) {
    const mode = options.mode === "exact" ? "exact" : "nearest";
    const toleranceMs = toleranceHours(options.toleranceHours) * 60 * 60 * 1000;
    const anchorTime = timestamp(anchor.date);
    const anchorDay = calendarDay(anchor.date);
    const distanceMs = Math.abs(timestamp(candidate.date) - anchorTime);
    const sameDay = calendarDay(candidate.date) === anchorDay;
    return mode === "exact" ? sameDay : distanceMs <= toleranceMs
      ? { distanceMs }
      : null;
  }

  function closestAssignments(primaries, candidates, options) {
    const pairs = [];
    for (const primary of primaries) {
      for (const candidate of candidates) {
        const allowed = allowedPair(primary, candidate, options);
        if (allowed) pairs.push({ primary, candidate, distanceMs: Math.abs(timestamp(candidate.date) - timestamp(primary.date)) });
      }
    }
    pairs.sort((left, right) => left.distanceMs - right.distanceMs
      || timestamp(left.primary.date) - timestamp(right.primary.date)
      || left.primary.name.localeCompare(right.primary.name, "ru")
      || left.candidate.name.localeCompare(right.candidate.name, "ru"));
    const assignedPrimaries = new Set();
    const assignedCandidates = new Set();
    const matches = new Map();
    for (const pair of pairs) {
      if (assignedPrimaries.has(pair.primary.id) || assignedCandidates.has(pair.candidate.id)) continue;
      assignedPrimaries.add(pair.primary.id);
      assignedCandidates.add(pair.candidate.id);
      matches.set(pair.primary.id, pair);
    }
    return { matches, assignedCandidates };
  }

  function buildPlan(descriptors, options = {}) {
    const items = Array.from(descriptors || []).filter((item) => item && ROLES.has(item.role));
    const primaries = items.filter((item) => item.role === "primary");
    const smartrooms = items.filter((item) => item.role === "smartroom");
    const ddios = items.filter((item) => item.role === "ddio");
    const smartroomAssignments = closestAssignments(primaries, smartrooms, options);
    const ddioAssignments = closestAssignments(primaries, ddios, options);
    const groups = primaries.map((primary, index) => {
      const smartroomMatch = smartroomAssignments.matches.get(primary.id) || null;
      const ddioMatch = ddioAssignments.matches.get(primary.id) || null;
      return {
        id: `batch-${index + 1}-${primary.id}`,
        order: index + 1,
        active: true,
        primary,
        smartroom: smartroomMatch?.candidate || null,
        ddio: ddioMatch?.candidate || null,
        distances: {
          smartroomHours: smartroomMatch ? Number((smartroomMatch.distanceMs / 3600000).toFixed(2)) : null,
          ddioHours: ddioMatch ? Number((ddioMatch.distanceMs / 3600000).toFixed(2)) : null,
        },
      };
    });
    return {
      mode: options.mode === "exact" ? "exact" : "nearest",
      toleranceHours: toleranceHours(options.toleranceHours),
      groups,
      files: items,
      unmatched: [
        ...smartrooms.filter((item) => !smartroomAssignments.assignedCandidates.has(item.id)),
        ...ddios.filter((item) => !ddioAssignments.assignedCandidates.has(item.id)),
      ],
    };
  }

  function reassign(plan, groupId, role, fileId) {
    if (!plan || !["smartroom", "ddio"].includes(role)) return plan;
    const selected = plan.files.find((item) => item.id === fileId && item.role === role) || null;
    for (const group of plan.groups || []) {
      if (selected && group.id !== groupId && group[role]?.id === selected.id) group[role] = null;
      if (group.id === groupId) group[role] = selected;
    }
    const assigned = new Set((plan.groups || []).flatMap((group) => [group.smartroom?.id, group.ddio?.id]).filter(Boolean));
    plan.unmatched = plan.files.filter((item) => item.role !== "primary" && !assigned.has(item.id));
    return plan;
  }

  global.MacAnalyzerBatchEnrichment = Object.freeze({
    SUPPORTED_EXTENSIONS,
    isSupportedFile,
    describeFiles,
    buildPlan,
    reassign,
    calendarDay,
  });
})(window);

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

  async function describeFiles(files, role, dateResolver) {
    const normalizedRole = roleName(role);
    const accepted = Array.from(files || []).filter(isSupportedFile);
    const result = [];
    for (const [index, file] of accepted.entries()) {
      const info = await dateResolver(file);
      result.push({
        id: descriptorId(file, normalizedRole, index),
        role: normalizedRole,
        name: String(file.name || ""),
        relativePath: String(file.webkitRelativePath || file.name || ""),
        size: Number(file.size || 0),
        date: String(info?.date || ""),
        dateSource: String(info?.source || "file.lastModified"),
        file,
      });
    }
    return result.sort((left, right) => timestamp(left.date) - timestamp(right.date) || left.name.localeCompare(right.name, "ru"));
  }

  function nearestUnused(anchor, candidates, used, options) {
    const mode = options.mode === "exact" ? "exact" : "nearest";
    const toleranceMs = Math.max(0, Number(options.toleranceHours || 24)) * 60 * 60 * 1000;
    const anchorTime = timestamp(anchor.date);
    const anchorDay = calendarDay(anchor.date);
    return candidates
      .filter((candidate) => !used.has(candidate.id))
      .map((candidate) => ({
        candidate,
        distanceMs: Math.abs(timestamp(candidate.date) - anchorTime),
        sameDay: calendarDay(candidate.date) === anchorDay,
      }))
      .filter((item) => mode === "exact" ? item.sameDay : item.distanceMs <= toleranceMs)
      .sort((left, right) => left.distanceMs - right.distanceMs || left.candidate.name.localeCompare(right.candidate.name, "ru"))[0] || null;
  }

  function buildPlan(descriptors, options = {}) {
    const items = Array.from(descriptors || []).filter((item) => item && ROLES.has(item.role));
    const primaries = items.filter((item) => item.role === "primary");
    const smartrooms = items.filter((item) => item.role === "smartroom");
    const ddios = items.filter((item) => item.role === "ddio");
    const usedSmartrooms = new Set();
    const usedDdios = new Set();
    const groups = primaries.map((primary, index) => {
      const smartroomMatch = nearestUnused(primary, smartrooms, usedSmartrooms, options);
      const ddioMatch = nearestUnused(primary, ddios, usedDdios, options);
      if (smartroomMatch) usedSmartrooms.add(smartroomMatch.candidate.id);
      if (ddioMatch) usedDdios.add(ddioMatch.candidate.id);
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
      toleranceHours: Math.max(0, Number(options.toleranceHours || 24)),
      groups,
      files: items,
      unmatched: [
        ...smartrooms.filter((item) => !usedSmartrooms.has(item.id)),
        ...ddios.filter((item) => !usedDdios.has(item.id)),
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

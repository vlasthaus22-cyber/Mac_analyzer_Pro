(() => {
  "use strict";

  const list = (value) => (Array.isArray(value) ? value : []);

  function selectForNextImport(files, requestedRole = "auto") {
    const source = list(files);
    const primaryExists = source.some((file) => file?.role === "primary");
    const incomingIsEnrichment = requestedRole === "enrichment"
      || (requestedRole === "auto" && primaryExists);
    if (!incomingIsEnrichment) return { files: source, removed: [] };
    const removed = source.filter((file) => file?.role === "enrichment" && file?.consumedAt);
    if (!removed.length) return { files: source, removed };
    const removedIds = new Set(removed.map((file) => file.id));
    return { files: source.filter((file) => !removedIds.has(file.id)), removed };
  }

  function markConsumed(files, consumedAt = new Date().toISOString()) {
    let marked = 0;
    for (const file of list(files)) {
      if (file?.role !== "enrichment") continue;
      file.consumedAt = consumedAt;
      marked += 1;
    }
    return marked;
  }

  window.MacAnalyzerWorkspaceFileLifecycle = Object.freeze({
    selectForNextImport,
    markConsumed,
  });
  document.documentElement.dataset.workspaceFileLifecycle = "ready";
})();

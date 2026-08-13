(() => {
  "use strict";

  const list = (value) => (Array.isArray(value) ? value : []);

  function selectForNextImport(files, requestedRole = "auto") {
    const source = list(files);
    const primaryExists = source.some((file) => file?.role === "primary");
    const incomingIsSmartRoom = ["smartroom", "enrichment"].includes(requestedRole)
      || (requestedRole === "auto" && primaryExists);
    if (!incomingIsSmartRoom) return { files: source, removed: [] };
    const removed = source.filter((file) => ["smartroom", "enrichment"].includes(file?.role) && file?.consumedAt);
    if (!removed.length) return { files: source, removed };
    const removedIds = new Set(removed.map((file) => file.id));
    return { files: source.filter((file) => !removedIds.has(file.id)), removed };
  }

  function markConsumed(files, consumedAt = new Date().toISOString()) {
    let marked = 0;
    for (const file of list(files)) {
      if (!["smartroom", "enrichment"].includes(file?.role)) continue;
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

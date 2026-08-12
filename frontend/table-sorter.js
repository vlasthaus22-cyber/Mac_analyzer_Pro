(() => {
  "use strict";
  const collator = new Intl.Collator("ru", { numeric: true, sensitivity: "base" });
  function dateValue(value) {
    const text = String(value || "").trim();
    const match = text.match(/^(\d{1,2})[.\/-](\d{1,2})[.\/-](\d{4})(?:[,\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
    if (match) return Date.UTC(Number(match[3]), Number(match[2]) - 1, Number(match[1]), Number(match[4] || 0), Number(match[5] || 0), Number(match[6] || 0));
    const parsed = Date.parse(text);
    return Number.isFinite(parsed) && /\d{4}/.test(text) ? parsed : null;
  }
  function numericValue(value) {
    const text = String(value || "").trim().replace(/\s+/g, "").replace(",", ".").replace(/%$/, "");
    return /^[-+]?\d+(?:\.\d+)?$/.test(text) ? Number(text) : null;
  }
  function compareValues(left, right) {
    const a = String(left ?? "").trim(), b = String(right ?? "").trim();
    if (!a || !b) return !a && !b ? 0 : (!a ? 1 : -1);
    const numberA = numericValue(a), numberB = numericValue(b);
    if (numberA !== null && numberB !== null) return numberA - numberB;
    const dateA = dateValue(a), dateB = dateValue(b);
    if (dateA !== null && dateB !== null) return dateA - dateB;
    return collator.compare(a, b);
  }
  function updateHeader(table, header, direction) {
    table.querySelectorAll("thead th[aria-sort]").forEach((cell) => { if (cell !== header) { cell.setAttribute("aria-sort", "none"); cell.dataset.sortDirection = ""; const marker = cell.querySelector(".sort-indicator"); if (marker) marker.textContent = "↕"; } });
    header.setAttribute("aria-sort", direction === "desc" ? "descending" : "ascending");
    header.dataset.sortDirection = direction;
    const marker = header.querySelector(".sort-indicator"); if (marker) marker.textContent = direction === "desc" ? "▼" : "▲";
  }
  function sortTable(table, header, forcedDirection = "") {
    if (!table || !header || table.id === "enhancedMovementTable" || table.dataset.sortDisabled === "true") return false;
    const index = Array.from(header.parentElement?.children || []).indexOf(header);
    if (index < 0 || header.querySelector("input, select, button") || header.dataset.sortDisabled === "true") return false;
    const direction = forcedDirection || (header.dataset.sortDirection === "asc" ? "desc" : "asc");
    updateHeader(table, header, direction);
    const field = header.dataset.sortField || "";
    if (table.dataset.remoteSort === "true" || field) {
      table.dispatchEvent(new CustomEvent("table-sort-change", { bubbles: true, detail: { field, index, direction } }));
      return true;
    }
    const body = table.tBodies?.[0];
    if (!body) return false;
    const virtualTable = window.MacAnalyzerVirtualTable;
    const rows = virtualTable?.rows?.(body) || Array.from(body.rows);
    const sortable = rows.filter((row) => row.cells.length > index && !row.querySelector("td[colspan]") && row.dataset.sortDisabled !== "true");
    const sortableSet = new Set(sortable), fixed = rows.filter((row) => !sortableSet.has(row));
    sortable.forEach((row, order) => { row.__tableSortOrder = order; });
    sortable.sort((left, right) => {
      const a = left.cells[index]?.dataset?.sortValue ?? left.cells[index]?.textContent ?? "";
      const b = right.cells[index]?.dataset?.sortValue ?? right.cells[index]?.textContent ?? "";
      const emptyA = !String(a ?? "").trim(), emptyB = !String(b ?? "").trim();
      if (emptyA !== emptyB) return emptyA ? 1 : -1;
      const compared = compareValues(a, b);
      return (direction === "desc" ? -compared : compared) || left.__tableSortOrder - right.__tableSortOrder;
    });
    if (virtualTable?.sort?.(body, (left, right) => sortable.indexOf(left) - sortable.indexOf(right))) {
      sortable.forEach((row) => { delete row.__tableSortOrder; });
      return true;
    }
    const fragment = document.createDocumentFragment();
    [...sortable, ...fixed].forEach((row) => { delete row.__tableSortOrder; fragment.appendChild(row); });
    body.appendChild(fragment);
    return true;
  }
  function headerFromEvent(event) {
    const header = event.target?.closest?.("th");
    if (!header || !header.closest("table") || event.target.closest(".column-resize-handle")) return null;
    return header;
  }
  function decorate(scope) {
    scope.querySelectorAll?.("table:not(#enhancedMovementTable):not([data-sort-disabled='true']) thead th").forEach((header) => {
      if (header.querySelector("input, select, button") || header.dataset.sortDisabled === "true") return;
      header.classList.add("sortable-column"); header.tabIndex = 0; header.setAttribute("role", "button");
      if (!header.hasAttribute("aria-sort")) header.setAttribute("aria-sort", "none");
      if (!header.querySelector(".sort-indicator")) { const indicator = document.createElement("span"); indicator.className = "sort-indicator"; indicator.setAttribute("aria-hidden", "true"); indicator.textContent = "↕"; header.appendChild(indicator); }
    });
  }
  function install(scope = document) {
    if (!scope?.addEventListener || scope.documentElement?.dataset?.tableSorter === "ready") return;
    scope.documentElement.dataset.tableSorter = "ready";
    decorate(scope);
    scope.addEventListener("click", (event) => { const header = headerFromEvent(event); if (header) sortTable(header.closest("table"), header); });
    scope.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const header = headerFromEvent(event); if (!header) return;
      event.preventDefault(); sortTable(header.closest("table"), header);
    });
    if (typeof MutationObserver !== "undefined") new MutationObserver((mutations) => { if (mutations.some((item) => item.addedNodes.length)) decorate(scope); }).observe(scope.body || scope.documentElement, { childList: true, subtree: true });
  }
  const api = { compareValues, decorate, install, sortTable };
  if (typeof window !== "undefined") window.MacAnalyzerTableSorter = Object.freeze(api); else globalThis.MacAnalyzerTableSorter = Object.freeze(api);
  if (typeof document !== "undefined") install(document);
})();

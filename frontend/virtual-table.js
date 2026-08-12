(() => {
  "use strict";

  const states = new WeakMap();
  const threshold = 100;
  const visibleRows = 20;

  function wrapperFor(tbody) {
    return tbody.closest(".table-wrap") || tbody.parentElement;
  }

  function makeSpacer(height, columns) {
    const row = document.createElement("tr");
    row.dataset.virtualSpacer = "true";
    row.setAttribute("aria-hidden", "true");
    const cell = document.createElement("td");
    cell.colSpan = Math.max(1, columns);
    cell.style.height = `${Math.max(0, height)}px`;
    cell.style.padding = "0";
    cell.style.border = "0";
    row.append(cell);
    return row;
  }

  function render(tbody) {
    const state = states.get(tbody);
    if (!state) return;
    const total = state.dataMode ? state.data.length : state.rows.length;
    const start = Math.max(0, Math.min(total - visibleRows, Math.floor(state.wrapper.scrollTop / state.rowHeight)));
    if (start === state.start && tbody.childElementCount) return;
    state.start = start;
    state.internal = true;
    const fragment = document.createDocumentFragment();
    fragment.append(makeSpacer(start * state.rowHeight, state.columns));
    for (let index = start; index < Math.min(total, start + visibleRows); index += 1) {
      if (!state.dataMode) fragment.append(state.rows[index]);
      else {
        const template = document.createElement("template");
        template.innerHTML = state.renderRow(state.data[index], index).trim();
        if (template.content.firstElementChild) fragment.append(template.content.firstElementChild);
      }
    }
    fragment.append(makeSpacer(Math.max(0, total - start - visibleRows) * state.rowHeight, state.columns));
    tbody.replaceChildren(fragment);
    state.internal = false;
  }

  function detach(tbody) {
    const state = states.get(tbody);
    if (!state) return;
    state.wrapper.removeEventListener("scroll", state.onScroll);
    states.delete(tbody);
  }

  function setData(tbody, data, renderRow) {
    if (!tbody || typeof renderRow !== "function") return false;
    detach(tbody);
    const rows = Array.from(data || []);
    if (rows.length <= threshold) {
      tbody.innerHTML = rows.map(renderRow).join("");
      return false;
    }
    const wrapper = wrapperFor(tbody);
    let frame = 0;
    const state = { dataMode: true, data: rows, renderRow, rows: [], wrapper, rowHeight: 38, columns: tbody.closest("table")?.tHead?.rows?.[0]?.cells?.length || 1, start: -1, internal: false, onScroll: null };
    state.onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => { frame = 0; render(tbody); });
    };
    states.set(tbody, state);
    wrapper.classList.add("virtual-table-wrap");
    wrapper.scrollTop = 0;
    wrapper.addEventListener("scroll", state.onScroll, { passive: true });
    render(tbody);
    return true;
  }

  function refresh(tbody) {
    if (!tbody) return false;
    const existing = states.get(tbody);
    if (existing?.internal) return true;
    const rows = Array.from(tbody.children).filter((row) => !row.dataset.virtualSpacer);
    if (rows.length <= threshold) {
      if (existing) {
        existing.internal = true;
        tbody.replaceChildren(...existing.rows);
        detach(tbody);
      }
      return false;
    }
    const sample = rows.find((row) => row.getBoundingClientRect().height > 0);
    const rowHeight = Math.max(28, Math.round(sample?.getBoundingClientRect().height || existing?.rowHeight || 38));
    if (existing) {
      existing.rows = rows;
      existing.rowHeight = rowHeight;
      existing.start = -1;
      render(tbody);
      return true;
    }
    const wrapper = wrapperFor(tbody);
    let frame = 0;
    const state = { rows, wrapper, rowHeight, columns: tbody.closest("table")?.tHead?.rows?.[0]?.cells?.length || 1, start: -1, internal: false, onScroll: null };
    state.onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => { frame = 0; render(tbody); });
    };
    states.set(tbody, state);
    wrapper.classList.add("virtual-table-wrap");
    wrapper.addEventListener("scroll", state.onScroll, { passive: true });
    render(tbody);
    return true;
  }

  function sort(tbody, compare) {
    const state = states.get(tbody);
    if (!state) return false;
    if (state.dataMode) state.data.sort(compare); else state.rows.sort(compare);
    state.wrapper.scrollTop = 0;
    state.start = -1;
    render(tbody);
    return true;
  }

  function rows(tbody) {
    return states.get(tbody)?.rows || Array.from(tbody?.children || []).filter((row) => !row.dataset.virtualSpacer);
  }

  function initialize(root = document) {
    root.querySelectorAll("table[data-virtual-scroll] tbody").forEach(refresh);
    if (typeof MutationObserver !== "undefined") {
      let frame = 0;
      new MutationObserver((mutations) => {
        const externalChange = mutations.some((item) => {
          if (!item.addedNodes.length && !item.removedNodes.length) return false;
          const tbody = item.target?.closest?.("tbody"), state = states.get(tbody);
          if (!state) return true;
          return !Array.from(item.addedNodes).some((node) => node?.dataset?.virtualSpacer === "true");
        });
        if (!externalChange) return;
        if (frame) return;
        frame = requestAnimationFrame(() => { frame = 0; root.querySelectorAll("table[data-virtual-scroll] tbody").forEach(refresh); });
      }).observe(root.body || root.documentElement, { childList: true, subtree: true });
    }
  }

  window.MacAnalyzerVirtualTable = Object.freeze({ initialize, refresh, setData, sort, rows, threshold, visibleRows });
})();

(() => {
  "use strict";

  const charts = new Map();

  function colors() {
    const style = getComputedStyle(document.documentElement);
    return {
      text: style.getPropertyValue("--text").trim() || "#172126",
      grid: style.getPropertyValue("--border").trim() || "#d8e0dc",
      green: style.getPropertyValue("--accent").trim() || "#157a5b",
      yellow: "#d99a18",
      red: "#c74444",
      blue: "#3a78c2",
    };
  }

  const valueLabels = {
    id: "smartroomValueLabels",
    afterDatasetsDraw(chart) {
      const context = chart.ctx;
      context.save();
      context.font = "600 11px system-ui, sans-serif";
      context.textAlign = "center";
      context.textBaseline = "bottom";
      context.fillStyle = colors().text;
      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        if (meta.hidden) return;
        meta.data.forEach((element, index) => {
          const value = Number(dataset.data[index]);
          if (!Number.isFinite(value)) return;
          const position = element.tooltipPosition();
          context.fillText(value.toLocaleString("ru-RU"), position.x, position.y - 5);
        });
      });
      context.restore();
    },
  };

  function chartState(id, message = "", error = false) {
    const canvas = document.getElementById(id);
    const state = document.querySelector(`[data-chart-state="${id}"]`);
    if (canvas) canvas.hidden = Boolean(message);
    if (!state) return;
    state.hidden = !message;
    state.classList.toggle("error", error);
    state.textContent = message;
  }

  function destroy(id) {
    const canvas = document.getElementById(id);
    charts.get(id)?.destroy();
    charts.delete(id);
    if (canvas && typeof Chart !== "undefined") Chart.getChart?.(canvas)?.destroy();
  }

  function upsert(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas) return false;
    if (typeof Chart === "undefined") {
      chartState(id, "Ошибка: библиотека Chart.js не загружена.", true);
      return false;
    }
    try {
      destroy(id);
      chartState(id);
      const context = canvas.getContext?.("2d");
      if (!context) throw new Error("браузер не предоставил Canvas 2D context");
      config.plugins = [...(config.plugins || []), valueLabels];
      charts.set(id, new Chart(context, config));
      return true;
    } catch (error) {
      destroy(id);
      chartState(id, `Не удалось построить график: ${error.message || error}`, true);
      return false;
    }
  }

  function options(c) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { labels: { color: c.text } } },
      scales: {
        x: { ticks: { color: c.text }, grid: { color: c.grid } },
        y: { beginAtZero: true, ticks: { color: c.text, precision: 0 }, grid: { color: c.grid } },
      },
    };
  }

  function normalizeRows(report) {
    if (!Array.isArray(report?.charts)) return [];
    return report.charts
      .filter((row) => row && typeof row === "object")
      .map((row) => ({
        date: String(row.date || "Без даты"),
        changes: Math.max(0, Number(row.changes) || 0),
        added: Math.max(0, Number(row.added) || 0),
        removed: Math.max(0, Number(row.removed) || 0),
        total: Math.max(0, Number(row.total) || 0),
      }));
  }

  function monthKey(value) {
    const direct = String(value || "").match(/^(\d{4})-(\d{2})/);
    if (direct) return `${direct[1]}-${direct[2]}`;
    const timestamp = Date.parse(String(value || ""));
    if (!Number.isFinite(timestamp)) return "";
    const date = new Date(timestamp);
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
  }

  function monthLabel(key) {
    const match = String(key).match(/^(\d{4})-(\d{2})$/);
    if (!match) return "Без даты";
    const formatted = new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric", timeZone: "UTC" }).format(
      new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, 1)),
    );
    return formatted.charAt(0).toUpperCase() + formatted.slice(1);
  }

  function monthlyRows(report) {
    const source = Array.isArray(report?.charts) ? report.charts : [];
    const buckets = new Map();
    for (const row of source) {
      if (!row || typeof row !== "object") continue;
      const key = monthKey(row.date);
      if (!key) continue;
      const bucket = buckets.get(key) || {
        date: key,
        label: monthLabel(key),
        changes: 0,
        added: 0,
        removed: 0,
        total: 0,
        changedRooms: new Set(),
        changedMacs: new Set(),
      };
      bucket.changes += Math.max(0, Number(row.changes) || 0);
      bucket.added += Math.max(0, Number(row.added) || 0);
      bucket.removed += Math.max(0, Number(row.removed) || 0);
      bucket.total = Math.max(0, Number(row.total) || 0);
      for (const value of row.changedRooms || [])
        if (String(value || "").trim()) bucket.changedRooms.add(String(value).trim());
      for (const value of row.changedMacs || [])
        if (String(value || "").trim()) bucket.changedMacs.add(String(value).trim());
      buckets.set(key, bucket);
    }
    const keys = Array.from(buckets.keys()).sort();
    if (!keys.length) return [];
    const cursor = new Date(`${keys[0]}-01T00:00:00Z`);
    const last = keys.at(-1);
    const result = [];
    while (`${cursor.getUTCFullYear()}-${String(cursor.getUTCMonth() + 1).padStart(2, "0")}` <= last) {
      const key = `${cursor.getUTCFullYear()}-${String(cursor.getUTCMonth() + 1).padStart(2, "0")}`;
      const bucket = buckets.get(key) || {
        date: key,
        label: monthLabel(key),
        changes: 0,
        added: 0,
        removed: 0,
        total: result.at(-1)?.total || 0,
        changedRooms: new Set(),
        changedMacs: new Set(),
      };
      result.push({
        ...bucket,
        changedRooms: Array.from(bucket.changedRooms),
        changedMacs: Array.from(bucket.changedMacs),
      });
      cursor.setUTCMonth(cursor.getUTCMonth() + 1);
    }
    return result;
  }

  function nextFrame() {
    return new Promise((resolve) => (window.requestAnimationFrame || setTimeout)(resolve));
  }

  async function render(report = {}) {
    const rows = monthlyRows(report);
    const ids = ["smartroomChangesChart", "smartroomAddedRemovedChart", "smartroomTotalChart"];
    if (!rows.length) {
      ids.forEach((id) => {
        destroy(id);
        chartState(id, "Нет данных для построения графика.");
      });
      return false;
    }

    await nextFrame();
    const c = colors();
    const rendered = [];
    const changesOptions = options(c);
    changesOptions.plugins.tooltip = {
      callbacks: {
        afterLabel(context) {
          const row = rows[context.dataIndex] || {};
          return `Переговорных: ${(row.changedRooms || []).length.toLocaleString("ru-RU")} · MAC-адресов: ${(row.changedMacs || []).length.toLocaleString("ru-RU")}`;
        },
      },
    };
    rendered.push(
      upsert("smartroomChangesChart", {
        type: "bar",
        data: {
          labels: rows.map((row) => row.label),
          datasets: [{ label: "Изменений", data: rows.map((row) => row.changes), backgroundColor: c.yellow }],
        },
        options: changesOptions,
      }),
    );
    rendered.push(
      upsert("smartroomAddedRemovedChart", {
        type: "line",
        data: {
          labels: rows.map((row) => row.label),
          datasets: [
            { label: "Добавлено", data: rows.map((row) => row.added), borderColor: c.green, backgroundColor: c.green },
            { label: "Пропало", data: rows.map((row) => row.removed), borderColor: c.red, backgroundColor: c.red },
          ],
        },
        options: options(c),
      }),
    );

    const previous = Number(rows.at(-2)?.total || 0);
    const current = Number(rows.at(-1)?.total || 0);
    const percent = previous ? ((current - previous) / previous) * 100 : current ? 100 : 0;
    const totalOptions = options(c);
    totalOptions.plugins.title = {
      display: true,
      color: c.text,
      text: `Было ${previous.toLocaleString("ru-RU")}, стало ${current.toLocaleString("ru-RU")} (${percent >= 0 ? "+" : ""}${percent.toFixed(1)}%)`,
    };
    rendered.push(
      upsert("smartroomTotalChart", {
        type: "bar",
        data: {
          labels: ["Было", "Стало"],
          datasets: [
            {
              label: "Устройств",
              data: [previous, current],
              backgroundColor: [c.blue, current < previous ? c.red : c.green],
            },
          ],
        },
        options: totalOptions,
      }),
    );
    return rendered.every(Boolean);
  }

  window.MacAnalyzerSmartroomCharts = Object.freeze({ destroy, normalizeRows, monthlyRows, render });
})();

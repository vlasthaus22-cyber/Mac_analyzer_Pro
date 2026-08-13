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
      config.plugins = [...(config.plugins || []), valueLabels];
      charts.set(id, new Chart(canvas.getContext("2d"), config));
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
      parsing: false,
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

  function nextFrame() {
    return new Promise((resolve) => (window.requestAnimationFrame || setTimeout)(resolve));
  }

  async function render(report = {}) {
    const rows = normalizeRows(report);
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
    upsert("smartroomChangesChart", {
      type: "bar",
      data: {
        labels: rows.map((row) => row.date),
        datasets: [{ label: "Изменений", data: rows.map((row) => row.changes), backgroundColor: c.yellow }],
      },
      options: options(c),
    });
    upsert("smartroomAddedRemovedChart", {
      type: "line",
      data: {
        labels: rows.map((row) => row.date),
        datasets: [
          { label: "Добавлено", data: rows.map((row) => row.added), borderColor: c.green, backgroundColor: c.green },
          { label: "Пропало", data: rows.map((row) => row.removed), borderColor: c.red, backgroundColor: c.red },
        ],
      },
      options: options(c),
    });

    const previous = Number(rows.at(-2)?.total || 0);
    const current = Number(rows.at(-1)?.total || 0);
    const percent = previous ? ((current - previous) / previous) * 100 : current ? 100 : 0;
    const totalOptions = options(c);
    totalOptions.plugins.title = {
      display: true,
      color: c.text,
      text: `Было ${previous.toLocaleString("ru-RU")}, стало ${current.toLocaleString("ru-RU")} (${percent >= 0 ? "+" : ""}${percent.toFixed(1)}%)`,
    };
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
    });
    return true;
  }

  window.MacAnalyzerSmartroomCharts = Object.freeze({ destroy, normalizeRows, render });
})();

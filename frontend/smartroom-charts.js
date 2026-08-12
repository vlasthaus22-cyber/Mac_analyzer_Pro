(() => {
  "use strict";

  const charts = new Map();
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
  function colors() {
    const style = getComputedStyle(document.documentElement);
    return { text: style.getPropertyValue("--text").trim() || "#172126", grid: style.getPropertyValue("--border").trim() || "#d8e0dc", green: style.getPropertyValue("--accent").trim() || "#157a5b", yellow: "#d99a18", red: "#c74444", blue: "#3a78c2" };
  }
  function upsert(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas || typeof Chart === "undefined") return;
    charts.get(id)?.destroy();
    config.plugins = [...(config.plugins || []), valueLabels];
    charts.set(id, new Chart(canvas, config));
  }
  function render(report = {}) {
    const rows = report.charts || [], c = colors(), common = { responsive: true, maintainAspectRatio: false, animation: false, parsing: false, plugins: { legend: { labels: { color: c.text } } }, scales: { x: { ticks: { color: c.text }, grid: { color: c.grid } }, y: { beginAtZero: true, ticks: { color: c.text, precision: 0 }, grid: { color: c.grid } } } };
    upsert("smartroomChangesChart", { type: "bar", data: { labels: rows.map((row) => row.date), datasets: [{ label: "Изменений", data: rows.map((row) => row.changes), backgroundColor: c.yellow }] }, options: common });
    upsert("smartroomAddedRemovedChart", { type: "line", data: { labels: rows.map((row) => row.date), datasets: [{ label: "Добавлено", data: rows.map((row) => row.added), borderColor: c.green, backgroundColor: c.green }, { label: "Пропало", data: rows.map((row) => row.removed), borderColor: c.red, backgroundColor: c.red }] }, options: common });
    const previous = Number(rows.at(-2)?.total || 0), current = Number(rows.at(-1)?.total || 0);
    const percent = previous ? ((current - previous) / previous) * 100 : (current ? 100 : 0);
    const totalOptions = { ...common, plugins: { ...common.plugins, title: { display: true, color: c.text, text: `Было ${previous.toLocaleString("ru-RU")}, стало ${current.toLocaleString("ru-RU")} (${percent >= 0 ? "+" : ""}${percent.toFixed(1)}%)` } } };
    upsert("smartroomTotalChart", { type: "bar", data: { labels: ["Было", "Стало"], datasets: [{ label: "Устройств", data: [previous, current], backgroundColor: [c.blue, current < previous ? c.red : c.green] }] }, options: totalOptions });
  }
  window.MacAnalyzerSmartroomCharts = Object.freeze({ render });
})();

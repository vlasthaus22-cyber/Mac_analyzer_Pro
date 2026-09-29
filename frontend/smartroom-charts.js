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

  function snapshotRows(report) {
    const source = Array.isArray(report?.snapshotChanges)
      ? report.snapshotChanges
      : Array.isArray(report?.snapshots)
        ? report.snapshots
        : [];
    return source
      .filter((row) => row && typeof row === "object")
      .map((row, index) => ({
        date: String(row.date || "Без даты"),
        label: String(row.name || row.date || `Final ${index + 1}`),
        changes: Math.max(0, Number(row.changes) || 0),
        added: index === 0 ? 0 : Math.max(0, Number(row.added) || 0),
        removed: index === 0 ? 0 : Math.max(0, Number(row.removed) || 0),
        total: Math.max(0, Number(row.total) || 0),
      }));
  }

  function weekKey(value) {
    const direct = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    const date = direct
      ? new Date(Date.UTC(Number(direct[1]), Number(direct[2]) - 1, Number(direct[3])))
      : new Date(Date.parse(String(value || "")));
    if (!Number.isFinite(date.getTime())) return "";
    const dayFromMonday = (date.getUTCDay() + 6) % 7;
    date.setUTCDate(date.getUTCDate() - dayFromMonday);
    return date.toISOString().slice(0, 10);
  }

  function weekLabel(key) {
    const start = new Date(`${key}T00:00:00Z`);
    if (!Number.isFinite(start.getTime())) return "Без даты";
    const end = new Date(start);
    end.setUTCDate(end.getUTCDate() + 6);
    const format = (date) =>
      `${String(date.getUTCDate()).padStart(2, "0")}.${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
    const year =
      start.getUTCFullYear() === end.getUTCFullYear()
        ? String(start.getUTCFullYear())
        : `${start.getUTCFullYear()}/${end.getUTCFullYear()}`;
    return `${format(start)}–${format(end)}.${year}`;
  }

  function weeklyRows(report) {
    const source = (Array.isArray(report?.charts) ? report.charts : [])
      .filter((row) => row && typeof row === "object" && weekKey(row.date))
      .sort((left, right) => String(left.date || "").localeCompare(String(right.date || "")));
    const buckets = new Map();
    for (const row of source) {
      const key = weekKey(row.date);
      const bucket = buckets.get(key) || {
        date: key,
        label: weekLabel(key),
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
    const cursor = new Date(`${keys[0]}T00:00:00Z`);
    const last = keys.at(-1);
    const result = [];
    while (cursor.toISOString().slice(0, 10) <= last) {
      const key = cursor.toISOString().slice(0, 10);
      const bucket = buckets.get(key) || {
        date: key,
        label: weekLabel(key),
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
      cursor.setUTCDate(cursor.getUTCDate() + 7);
    }
    return result;
  }

  function nextFrame() {
    return new Promise((resolve) => (window.requestAnimationFrame || setTimeout)(resolve));
  }

  async function render(report = {}) {
    const rows = normalizeRows(report);
    const weeks = weeklyRows(report);
    const finals = snapshotRows(report);
    const ids = ["smartroomChangesChart", "smartroomAddedRemovedChart", "smartroomTotalChart"];
    if (!rows.length && !finals.length) {
      ids.forEach((id) => {
        destroy(id);
        chartState(id, "Нет данных для построения графика.");
      });
      return false;
    }

    await nextFrame();
    const c = colors();
    const rendered = [];
    if (weeks.length) {
      const changesOptions = options(c);
      changesOptions.plugins.tooltip = {
        callbacks: {
          afterLabel(context) {
            const row = weeks[context.dataIndex] || {};
            return `Переговорных: ${(row.changedRooms || []).length.toLocaleString("ru-RU")} · MAC-адресов: ${(row.changedMacs || []).length.toLocaleString("ru-RU")}`;
          },
        },
      };
      rendered.push(
        upsert("smartroomChangesChart", {
          type: "bar",
          data: {
            labels: weeks.map((row) => row.label),
            datasets: [{ label: "Изменений", data: weeks.map((row) => row.changes), backgroundColor: c.yellow }],
          },
          options: changesOptions,
        }),
      );
    } else {
      destroy("smartroomChangesChart");
      chartState("smartroomChangesChart", "Нет данных для недельной динамики изменений.");
      rendered.push(true);
    }
    const changesByFinal = finals.slice(1);
    if (changesByFinal.length)
      rendered.push(
        upsert("smartroomAddedRemovedChart", {
          type: "line",
          data: {
            labels: changesByFinal.map((row) => row.label),
            datasets: [
              {
                label: "Добавлено",
                data: changesByFinal.map((row) => row.added),
                borderColor: c.green,
                backgroundColor: c.green,
              },
              {
                label: "Отсутствовало",
                data: changesByFinal.map((row) => -row.removed),
                borderColor: c.red,
                backgroundColor: c.red,
              },
            ],
          },
          options: options(c),
        }),
      );
    else {
      destroy("smartroomAddedRemovedChart");
      chartState("smartroomAddedRemovedChart", "Для сравнения нужны минимум два финальных обогащения.");
      rendered.push(true);
    }

    const totalRows = finals.length ? finals : rows;
    const previous = Number(totalRows.at(-2)?.total || 0);
    const current = Number(totalRows.at(-1)?.total || 0);
    const percent = previous ? ((current - previous) / previous) * 100 : current ? 100 : 0;
    const totalOptions = options(c);
    totalOptions.plugins.title = {
      display: true,
      color: c.text,
      text: `Было ${previous.toLocaleString("ru-RU")}, стало ${current.toLocaleString("ru-RU")} (${percent >= 0 ? "+" : ""}${percent.toFixed(1)}%)`,
    };
    rendered.push(
      upsert("smartroomTotalChart", {
        type: "line",
        data: {
          labels: totalRows.map((row, index) => row.label || `Final ${index + 1}`),
          datasets: [
            {
              label: "Устройств",
              data: totalRows.map((row) => row.total),
              borderColor: c.blue,
              backgroundColor: c.blue,
            },
          ],
        },
        options: totalOptions,
      }),
    );
    return rendered.every(Boolean);
  }

  window.MacAnalyzerSmartroomCharts = Object.freeze({
    destroy,
    normalizeRows,
    snapshotRows,
    weeklyRows,
    render,
  });
})();

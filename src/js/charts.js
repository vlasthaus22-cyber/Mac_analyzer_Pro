/** Lazy Chart.js dashboard facade. Existing instances are destroyed by the renderer. */
export function charts() {
  const value = window.MacAnalyzerSmartroomCharts;
  if (!value) throw new Error("Модуль графиков ещё не загружен");
  return value;
}

export const renderCharts = (report) => charts().render(report);
export const destroyCharts = () => charts().destroy?.();

/** Lazy tabs and bounded virtual-table facade. */
export function ui() {
  const value = window.MacAnalyzerSmartroomUI;
  if (!value) throw new Error("Модуль интерфейса ещё не загружен");
  return value;
}

export const renderActiveView = (name, force = false) => ui().render(name, force);
export const refreshSmartroomReport = (force = false) => ui().build(force);

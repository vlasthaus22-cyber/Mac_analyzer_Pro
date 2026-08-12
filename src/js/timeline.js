/** Complete MAC chronology facade. Events are returned oldest-to-newest. */
export function timeline() {
  const value = window.MacAnalyzerMacChronology;
  if (!value) throw new Error("Модуль хронологии MAC ещё не загружен");
  return value;
}

export const getMacTimeline = (options) => timeline().getMacHistory(options);
export const renderMacTimeline = (events, options) => timeline().renderTimeline(events, options);

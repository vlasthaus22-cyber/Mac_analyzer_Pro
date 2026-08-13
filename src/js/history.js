/** DDIO switch-IP history facade. */
export function history() {
  const value = window.MacAnalyzerDdioOverlay;
  if (!value) throw new Error("Модуль истории DDIO ещё не загружен");
  return value;
}

export const getPossibleIPs = (rows, mapping) => history().buildPossibleIpIndex(rows, mapping);
export const buildIpOverlay = (changes, candidates, currentIpByMac) => history().buildOverlay(changes, candidates, currentIpByMac);

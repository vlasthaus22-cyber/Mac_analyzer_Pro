/** IndexedDB facade for the Smartroom v2 source layout. */
export function database() {
  const value = window.MacAnalyzerSmartroomStore;
  if (!value) throw new Error("Модуль IndexedDB ещё не загружен");
  return value;
}

export const syncEquipment = (...args) => database().syncEquipment(...args);
export const appendHistory = (...args) => database().appendHistory(...args);
export const saveDdioSnapshot = (...args) => database().saveDdioSnapshot(...args);
export const latestDdioSnapshot = (...args) => database().latestDdioSnapshot(...args);
export const saveKnownModel = (...args) => database().saveKnownModel(...args);

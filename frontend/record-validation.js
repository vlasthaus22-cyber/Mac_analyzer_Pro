(() => {
  "use strict";

  const text = (value) => String(value ?? "").trim();

  function isEmptyRow(row) {
    return !Array.isArray(row) || !row.some((value) => text(value));
  }

  function invalidIdentity({
    row = [],
    rowNumber = 0,
    source = "",
    sourceRole = "",
    rawMac = "",
    macColumn = null,
  } = {}) {
    const rawMacText = text(rawMac);
    const compactMac = rawMacText.toUpperCase().replace(/[^0-9A-F]/g, "");
    const hasMacValue = Boolean(rawMacText);
    const explanation = hasMacValue
      ? `Значение MAC «${rawMacText}» после удаления разделителей содержит ${compactMac.length} из 12 шестнадцатеричных символов; серийный номер и Device ID отсутствуют.`
      : "В сопоставленных колонках не заполнены MAC, серийный номер и Device ID.";
    return {
      invalid: true,
      valid: false,
      errorCode: hasMacValue ? "INVALID_MAC" : "MISSING_IDENTITY",
      row: rowNumber,
      source: text(source),
      sourceRole: text(sourceRole),
      raw: row
        .map(text)
        .join(" | ")
        .replace(/^\s*\|+|\|+\s*$/g, "")
        .slice(0, 500),
      rawMac: rawMacText,
      macHexLength: compactMac.length,
      expectedMacHexLength: 12,
      macColumn,
      error: hasMacValue ? "Некорректный MAC" : "Отсутствует идентификатор устройства",
      explanation,
      suggestion: hasMacValue
        ? "Исправьте MAC либо укажите серийный номер или Device ID в сопоставленных колонках."
        : "Проверьте сопоставление колонок и заполненность исходной строки.",
    };
  }

  const api = Object.freeze({ invalidIdentity, isEmptyRow });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.MacAnalyzerRecordValidation = api;
})();

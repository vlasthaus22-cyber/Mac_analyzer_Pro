(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.MacAnalyzerColumnPresets = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const emptyMapping = () => ({
    mac: "", secondaryMac: "", vendor: "", model: "", ip: "", address: "",
    room: "", smartroomId: "", switchIp: "", switchPort: "",
    authenticationTime: "", hostname: "", serialNumber: "", deviceId: "", deviceName: ""
  });

  const normalizeHeader = (value) => String(value ?? "")
    .trim()
    .toLocaleLowerCase("ru-RU")
    .replace(/ё/g, "е")
    .replace(/[\s_\-.,:;()\[\]{}\\/]+/g, "")
    .replace(/[^a-zа-я0-9]/g, "");

  const aliases = {
    primary: {
      mac: ["CallingStarionID", "CallingStationID", "Calling Station ID", "MAC", "MAC-адрес"],
      switchIp: ["NasIP", "NAS IP", "IP коммутатора"],
      switchPort: ["NasPortID", "NAS Port ID", "Порт коммутатора"],
      authenticationTime: ["B_ReceiptTime", "ReceiptTime", "Время аутентификации устройства"]
    },
    smartroom: {
      mac: ["MAC", "MAC-адрес"],
      secondaryMac: ["MAC 2", "MAC-адрес 2", "MAC дополнительного интерфейса", "MAC второго интерфейса"],
      ip: ["IP", "IP адрес", "IP-адрес"],
      vendor: ["Производитель"],
      model: ["Модель"],
      address: ["Адрес локации", "Адрес комнаты"],
      room: ["Название комнаты", "Наименование локации"],
      smartroomId: ["Smartroom ID локации", "ID комнаты", "Smartroom ID"]
    },
    ddio: {
      reservationMac: ["Column3"],
      reservationIp: ["Column2"],
      leaseMac: ["Column10"],
      leaseIp: ["Column9"]
    }
  };

  function headerNames(headers = []) {
    return headers.map((header, index) => String(header && typeof header === "object" ? header.name ?? header.title ?? index : header));
  }

  function exactIndex(headers, candidates, used = new Set()) {
    const names = headerNames(headers);
    const wanted = new Set((candidates || []).map(normalizeHeader));
    const index = names.findIndex((name, column) => !used.has(column) && wanted.has(normalizeHeader(name)));
    return index >= 0 ? index : "";
  }

  function mappingForRole(headers = [], role = "primary", fallback = {}) {
    const result = role === "ddio" ? {} : { ...emptyMapping(), ...(fallback || {}) };
    const roleAliases = aliases[role] || aliases.primary;
    const used = new Set();
    for (const [field, candidates] of Object.entries(roleAliases)) {
      const index = exactIndex(headers, candidates, used);
      if (index === "") continue;
      result[field] = index;
      used.add(index);
    }
    return result;
  }

  function describe(headers = [], mapping = {}, role = "primary") {
    const names = headerNames(headers);
    const labels = role === "ddio"
      ? { reservationMac: "MAC резервации", reservationIp: "IP резервации", leaseMac: "MAC аренды", leaseIp: "IP аренды" }
      : { mac: "MAC", secondaryMac: "Дополнительный MAC", ip: "IP устройства", switchIp: "IP коммутатора", switchPort: "Порт", authenticationTime: "Время аутентификации", vendor: "Производитель", model: "Модель", address: "Адрес", room: "Помещение", smartroomId: "Smartroom ID" };
    return Object.entries(labels).map(([field, label]) => ({ field, label, index: mapping[field], header: mapping[field] === "" || mapping[field] == null ? "Не определено" : names[Number(mapping[field])] || `Колонка ${Number(mapping[field]) + 1}` }));
  }

  return { aliases, normalizeHeader, headerNames, exactIndex, mappingForRole, describe, emptyMapping };
});

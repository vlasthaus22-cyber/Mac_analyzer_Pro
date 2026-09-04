(() => {
  "use strict";

  const text = (value) => String(value ?? "").trim();
  const fields = Object.freeze(["tb", "city", "site", "floor", "room"]);

  function parse(room = {}) {
    const result = {
      tb: text(room.tb || room.TB || room.territorialBank || room.territorial_bank || room["ТБ"]),
      city: text(room.city || room.city_name || room.location_city || room.City || room["Город"]),
      site: text(room.site || room.siteName || room.site_name || room["Площадка"]),
      floor: text(room.floor || room.floorName || room.floor_name || room["Этаж"]),
      room: text(room.room || room.room_name || room.Room || room["Помещение"]),
    };
    const candidates = [
      room.locationPath,
      room.location_path,
      room.location_hierarchy,
      room.hierarchy,
      room.address,
      room.physicalAddress,
      result.room,
    ]
      .map(text)
      .filter(Boolean);
    const path = candidates.find((candidate) => candidate.split(",").length >= 5) || "";
    // Empty segments still occupy their level (e.g. an unknown floor).
    const parts = path.split(",").map(text);
    if (parts.length >= 5) {
      result.tb = result.tb || parts[0];
      result.city = result.city || parts[1];
      result.site = result.site || parts[2];
      result.floor = result.floor || parts[3];
      if (!result.room || result.room === path) result.room = parts.slice(4).join(", ");
    } else if (!result.city && parts.length) result.city = text(parts[0].replace(/^г\.?\s*/i, ""));
    return { ...result, path: path || text(room.locationPath || room.address || room.physicalAddress) };
  }

  function matches(room, filters = {}, query = "") {
    const location = parse(room);
    if (fields.some((field) => text(filters[field]) && location[field] !== text(filters[field]))) return false;
    const needle = text(query).toLocaleLowerCase("ru-RU");
    if (!needle) return true;
    const haystack = [
      room.smartroomId,
      room.smartroom_id,
      ...fields.map((field) => location[field]),
      location.path,
      room.address,
      ...(room.devices || []).flatMap((device) => [
        device.mac,
        device.macFormatted,
        device.ip,
        device.switchIp,
        device.switch_ip,
        device.hostname,
        device.deviceId,
        device.serialNumber,
        device.vendor,
        device.model,
      ]),
    ]
      .join(" ")
      .toLocaleLowerCase("ru-RU");
    if (haystack.includes(needle)) return true;
    const compactNeedle = needle.replace(/[^0-9a-f]/gi, "").toUpperCase();
    if (compactNeedle.length !== 12) return false;
    return (room.devices || []).some(
      (device) =>
        text(device.mac || device.macFormatted)
          .replace(/[^0-9a-f]/gi, "")
          .toUpperCase() === compactNeedle,
    );
  }

  function cascade(rooms = [], filters = {}) {
    const normalized = Object.fromEntries(fields.map((field) => [field, text(filters[field])]));
    const result = {};
    fields.forEach((field, fieldIndex) => {
      const upstream = fields.slice(0, fieldIndex);
      const values = (rooms || [])
        .filter((room) => {
          const location = parse(room);
          return upstream.every((key) => !normalized[key] || location[key] === normalized[key]);
        })
        .map((room) => parse(room)[field])
        .filter(Boolean);
      result[field] = Array.from(new Set(values)).sort((left, right) =>
        left.localeCompare(right, "ru", { numeric: true, sensitivity: "base" }),
      );
      if (normalized[field] && !result[field].includes(normalized[field])) normalized[field] = "";
    });
    return { filters: normalized, options: result };
  }

  const api = Object.freeze({ fields, parse, matches, cascade });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.MacAnalyzerRoomLocation = api;
})();

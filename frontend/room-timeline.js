(() => {
  "use strict";

  const text = (value) => String(value ?? "").trim();
  const normalizeMac = (value) => {
    const normalized = text(value)
      .toUpperCase()
      .replace(/[^0-9A-F]/g, "");
    return normalized.length === 12 ? normalized : "";
  };
  const Time =
    (typeof window !== "undefined" && window.MacAnalyzerTime) ||
    (typeof require === "function" ? require("./time-utils.js") : null);

  const value = (device, ...keys) => {
    for (const key of keys) {
      const candidate = text(device?.[key]);
      if (candidate) return candidate;
    }
    return "";
  };

  function deviceIdentity(device, index = 0) {
    const mac = normalizeMac(device?.mac || device?.macFormatted || device?.mac_formatted);
    if (mac) return `mac:${mac}`;
    const deviceId = value(device, "deviceId", "device_id").toLowerCase();
    if (deviceId) return `device:${deviceId}`;
    const serial = value(device, "serialNumber", "serial_number", "serial").toUpperCase();
    if (serial) return `serial:${serial}`;
    const hostname = value(device, "hostname", "host_name").toLowerCase();
    if (hostname) return `host:${hostname}`;
    return `unidentified:${index}`;
  }

  function deviceMap(devices) {
    const result = new Map();
    (devices || []).forEach((device, index) => {
      const baseKey = deviceIdentity(device, index);
      const existing = result.get(baseKey);
      if (!existing) {
        result.set(baseKey, device);
        return;
      }
      const merged = { ...existing };
      for (const [field, fieldValue] of Object.entries(device || {})) {
        if (text(fieldValue)) merged[field] = fieldValue;
      }
      result.set(baseKey, merged);
    });
    return result;
  }

  function deviceAliases(device) {
    const mac = normalizeMac(device?.mac || device?.macFormatted || device?.mac_formatted);
    const deviceId = value(device, "deviceId", "device_id").toLowerCase();
    const serial = value(device, "serialNumber", "serial_number", "serial").toUpperCase();
    const hostname = value(device, "hostname", "host_name").toLowerCase();
    const internalId = value(device, "internalDeviceId", "internal_device_id").toLowerCase();
    return [
      internalId && `internal:${internalId}`,
      mac && `mac:${mac}`,
      serial && `serial:${serial}`,
      deviceId && `device:${deviceId}`,
      hostname && serial && `host-serial:${hostname}|${serial}`,
    ].filter(Boolean);
  }

  function pairDevices(previousDevices, currentDevices) {
    const previous = Array.from(deviceMap(previousDevices).values());
    const current = Array.from(deviceMap(currentDevices).values());
    const aliases = new Map();
    const ambiguous = new Set();
    for (const device of previous) {
      for (const alias of deviceAliases(device)) {
        if (ambiguous.has(alias)) continue;
        if (aliases.has(alias) && aliases.get(alias) !== device) {
          aliases.delete(alias);
          ambiguous.add(alias);
        } else aliases.set(alias, device);
      }
    }
    const used = new Set();
    const pairs = [];
    const added = [];
    for (const device of current) {
      let match = null;
      for (const alias of deviceAliases(device)) {
        if (ambiguous.has(alias)) continue;
        const candidate = aliases.get(alias);
        if (candidate && !used.has(candidate)) { match = candidate; break; }
      }
      if (!match || used.has(match)) added.push(device);
      else {
        used.add(match);
        pairs.push([match, device]);
      }
    }
    return { pairs, added, removed: previous.filter((device) => !used.has(device)) };
  }

  function mergeKnownDevice(previous, current) {
    const merged = { ...(previous || {}) };
    for (const [field, fieldValue] of Object.entries(current || {})) {
      if (Array.isArray(fieldValue)) merged[field] = Array.from(new Set([...(merged[field] || []), ...fieldValue]));
      else if (text(fieldValue) || !Object.prototype.hasOwnProperty.call(merged, field)) merged[field] = fieldValue;
    }
    return merged;
  }

  function hydrateKnownHistory(history) {
    const hydrated = [];
    let known = [];
    for (const observation of history || []) {
      const current = Array.from(deviceMap(observation?.devices || []).values());
      const paired = pairDevices(known, current);
      const devices = paired.pairs.map(([previous, device]) => mergeKnownDevice(previous, device));
      devices.push(...paired.added);
      // Keep the last trustworthy values even while a device/room is absent in a
      // snapshot. The active observation remains empty, but a later reappearance
      // can still inherit non-empty fields from the previous Final.
      const retained = known.filter((device) => !paired.pairs.some(([previous]) => previous === device));
      known = retained.concat(devices);
      hydrated.push({ ...observation, devices });
    }
    return hydrated;
  }

  const trackedFields = Object.freeze([
    ["mac", ["mac", "macFormatted", "mac_formatted"], "MAC / физический адрес"],
    ["switchIp", ["switchIp", "switch_ip", "ip_switch"], "IP коммутатора"],
    ["switchPort", ["switchPort", "switch_port", "port"], "Порт"],
    ["ip", ["ip", "deviceIp", "device_ip"], "IP устройства"],
    ["model", ["model"], "Модель"],
    ["vendor", ["vendor", "manufacturer"], "Производитель"],
    ["tb", ["tb", "territorialBank", "territorial_bank"], "ТБ"],
    ["city", ["city", "city_name"], "Город"],
    ["site", ["site", "siteName", "site_name"], "Площадка"],
    ["floor", ["floor", "floorName", "floor_name"], "Этаж"],
    ["room", ["room", "room_name"], "Помещение"],
    ["address", ["address", "physicalAddress"], "Адрес"],
  ]);

  const unknownValues = new Set([
    "",
    "unknown",
    "not found",
    "n/a",
    "none",
    "null",
    "не определено",
    "неизвестно",
    "не указано",
  ]);

  function trackedValue(field, device, keys) {
    const result = field === "mac" ? normalizeMac(value(device, ...keys)) : value(device, ...keys);
    return ["model", "vendor"].includes(field) && unknownValues.has(text(result).toLowerCase()) ? "" : result;
  }

  function changedValues(before, after) {
    const changes = [];
    for (const [field, keys, label] of trackedFields) {
      const oldValue = trackedValue(field, before, keys);
      const newValue = trackedValue(field, after, keys);
      // A newly filled or temporarily absent attribute is enrichment quality,
      // not a confirmed physical change in the room. Added/removed devices are
      // handled separately by pairDevices().
      if (!oldValue || !newValue || oldValue === newValue) continue;
      changes.push({ field, label, before: oldValue, after: newValue });
    }
    return changes;
  }

  function compareLatest(room) {
    const history = hydrateKnownHistory(
      Array.from(room?.history || []).filter((item) => item && typeof item === "object"),
    );
    const previousObservation = history.at(-2) || null;
    const currentObservation = history.at(-1) || null;
    const entries = [];
    const paired = pairDevices(previousObservation?.devices || [], currentObservation?.devices || []);
    for (const [beforeDevice, device] of paired.pairs) {
      const changes = changedValues(beforeDevice, device);
      const moved = changes.some((change) => change.field === "switchIp" || change.field === "switchPort");
      let status = "Без изменений";
      if (moved) status = "Перемещен";
      else if (changes.length) status = "Изменен";
      entries.push({
        identity: deviceIdentity(device),
        mac: normalizeMac(device?.mac || beforeDevice?.mac),
        model: text(device?.model || beforeDevice?.model) || "Unknown",
        status,
        changes,
        beforeDevice,
        device,
      });
    }
    for (const device of paired.added)
      entries.push({
        identity: deviceIdentity(device),
        mac: normalizeMac(device.mac),
        model: text(device.model) || "Unknown",
        status: "Добавлен",
        changes: [],
        beforeDevice: null,
        device,
      });
    for (const beforeDevice of paired.removed)
      entries.push({
        identity: deviceIdentity(beforeDevice),
        mac: normalizeMac(beforeDevice.mac),
        model: text(beforeDevice.model) || "Unknown",
        status: "Удален",
        changes: [],
        beforeDevice,
        device: beforeDevice,
      });
    const changed = entries.filter((item) => item.status !== "Без изменений");
    return {
      previousDate: Time.toUtcIso(previousObservation?.date),
      currentDate: Time.toUtcIso(currentObservation?.date),
      total: entries.length,
      changed: changed.length,
      unchanged: entries.length - changed.length,
      allChanged: entries.length > 0 && changed.length === entries.length,
      entries,
    };
  }

  function roomDescriptor(device = {}) {
    const smartroomId = value(device, "smartroomId", "smartroom_id");
    const room = value(device, "room", "room_name");
    const key = smartroomId ? `smartroom:${smartroomId.toLowerCase()}` : room ? `room:${room.toLowerCase()}` : "";
    return {
      key,
      smartroomId,
      room,
      tb: value(device, "tb", "territorialBank", "territorial_bank"),
      city: value(device, "city", "city_name"),
      site: value(device, "site", "siteName", "site_name"),
      floor: value(device, "floor", "floorName", "floor_name"),
    };
  }

  function compareFleetRooms(previousDevices = [], currentDevices = []) {
    const paired = pairDevices(previousDevices, currentDevices);
    const rooms = new Map();
    let anonymous = 0;
    const mark = (device, identity, changed, type) => {
      const room = roomDescriptor(device);
      if (!room.key) return;
      let row = rooms.get(room.key);
      if (!row) {
        row = { ...room, members: new Map(), added: 0, removed: 0, modified: 0 };
        rooms.set(room.key, row);
      }
      const memberKey = identity || deviceAliases(device)[0] || `anonymous:${anonymous++}`;
      const existed = row.members.has(memberKey);
      const previous = row.members.get(memberKey);
      row.members.set(memberKey, Boolean(previous || changed));
      if (!existed && type && Object.prototype.hasOwnProperty.call(row, type)) row[type] += 1;
    };
    for (const [before, after] of paired.pairs) {
      const identity = deviceAliases(after)[0] || deviceAliases(before)[0] || "";
      const beforeRoom = roomDescriptor(before);
      const afterRoom = roomDescriptor(after);
      if (beforeRoom.key !== afterRoom.key) {
        mark(before, identity, true, "removed");
        mark(after, identity, true, "added");
      } else {
        const changed = changedValues(before, after).length > 0;
        mark(after, identity, changed, changed ? "modified" : "");
      }
    }
    paired.added.forEach((device) => mark(device, deviceAliases(device)[0], true, "added"));
    paired.removed.forEach((device) => mark(device, deviceAliases(device)[0], true, "removed"));
    const result = Array.from(rooms.values()).map((row) => {
      const total = row.members.size;
      const changed = Array.from(row.members.values()).filter(Boolean).length;
      const { members, ...metadata } = row;
      return { ...metadata, total, changed, unchanged: total - changed, allChanged: total > 0 && changed === total };
    }).sort((left, right) => Number(right.allChanged) - Number(left.allChanged) || String(left.room || left.smartroomId).localeCompare(String(right.room || right.smartroomId), "ru"));
    return { totalRooms: result.length, changedRooms: result.filter((row) => row.changed > 0).length, allChangedRoomCount: result.filter((row) => row.allChanged).length, rooms: result };
  }

  function events(room) {
    const result = [];
    let previous = [];
    for (const observation of hydrateKnownHistory(room?.history || [])) {
      const current = Array.from(deviceMap(observation.devices || []).values());
      const paired = pairDevices(previous, current);
      for (const device of paired.removed)
        result.push({
          date: observation.date,
          mac: normalizeMac(device.mac),
          model: text(device.model) || "Unknown",
          vendor: text(device.vendor) || "Unknown",
          status: "Удален",
          device,
        });
      for (const device of paired.added)
        result.push({
          date: observation.date,
          mac: normalizeMac(device.mac),
          model: text(device.model) || "Unknown",
          vendor: text(device.vendor) || "Unknown",
          status: "Добавлен",
          device,
        });
      for (const [beforeDevice, device] of paired.pairs) {
        const changes = changedValues(beforeDevice, device);
        if (!changes.length) continue;
        const moved = changes.some((change) => change.field === "switchIp" || change.field === "switchPort");
        result.push({
          date: observation.date,
          mac: normalizeMac(device.mac || beforeDevice.mac),
          model: text(device.model || beforeDevice.model) || "Unknown",
          vendor: text(device.vendor || beforeDevice.vendor) || "Unknown",
          status: moved ? "Перемещен" : "Изменен",
          changes,
          beforeDevice,
          device,
        });
      }
      previous = current;
    }
    result.sort(
      (left, right) =>
        (Time.timestamp(left.date) ?? Number.MAX_SAFE_INTEGER) -
        (Time.timestamp(right.date) ?? Number.MAX_SAFE_INTEGER),
    );
    return result.map((item, index) => ({
      ...item,
      date: Time.toUtcIso(item.date),
      elapsedMs: index ? Time.difference(result[index - 1].date, item.date) : null,
    }));
  }

  function statusTone(status) {
    if (status === "Добавлен") return "added";
    if (status === "Удален") return "removed";
    if (status === "Перемещен") return "moved";
    return "changed";
  }

  function changesHtml(item, escapeHtml) {
    if (!item.changes?.length) return "";
    return `<div class="room-timeline-changes">${item.changes
      .map(
        (change) =>
          `<span><b>${escapeHtml(change.label)}:</b> ${escapeHtml(change.before || "Не заполнено")} → ${escapeHtml(change.after)}</span>`,
      )
      .join("")}</div>`;
  }

  function render(room, helpers = {}) {
    const escapeHtml = helpers.escapeHtml || ((value) => text(value));
    const formatDate = helpers.formatDate || Time.formatUtc;
    const formatMac = helpers.formatMac || text;
    const rows = events(room);
    if (!rows.length)
      return {
        rows,
        tableHtml: '<tr><td colspan="4" class="empty-state">Изменений оборудования не найдено.</td></tr>',
        timelineHtml: '<p class="empty-state">История помещения отсутствует.</p>',
      };
    const rowHtml = rows
      .slice()
      .reverse()
      .map((item) => {
        const model = escapeHtml(item.model || "Unknown");
        const manual = /^unknown$/i.test(item.model)
          ? ` <button type="button" class="link-button" data-add-known-model="${escapeHtml(item.mac)}" data-known-vendor="${escapeHtml(item.vendor)}">Указать модель</button>`
          : "";
        const interval = item.elapsedMs === null ? "Первое событие" : `Через ${Time.formatDuration(item.elapsedMs)}`;
        return `<tr><td>${escapeHtml(formatDate(item.date))}<small class="timeline-duration">${escapeHtml(interval)}</small></td><td>${escapeHtml(formatMac(item.mac) || "—")}</td><td>${model}${changesHtml(item, escapeHtml)}${manual}</td><td><span class="room-status room-status-${statusTone(item.status)}">${escapeHtml(item.status)}</span></td></tr>`;
      })
      .join("");
    const timelineHtml = rows
      .map(
        (item, index) =>
          `<article class="room-timeline-event room-timeline-${statusTone(item.status)}">${index ? '<span class="room-timeline-arrow" aria-hidden="true">→</span>' : ""}<time>${escapeHtml(formatDate(item.date))}</time><small class="timeline-duration">${escapeHtml(item.elapsedMs === null ? "Первое событие" : `Через ${Time.formatDuration(item.elapsedMs)}`)}</small><strong>${escapeHtml(item.status)}</strong><span>${escapeHtml(formatMac(item.mac) || "—")}</span><small>${escapeHtml(item.model || "Unknown")}</small>${changesHtml(item, escapeHtml)}</article>`,
      )
      .join("");
    return { rows, tableHtml: rowHtml, timelineHtml };
  }

  window.MacAnalyzerRoomTimeline = Object.freeze({ events, compareLatest, compareFleetRooms, hydrateKnownHistory, pairDevices, render });
})();

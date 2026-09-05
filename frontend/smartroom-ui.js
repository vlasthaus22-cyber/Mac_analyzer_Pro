(() => {
  "use strict";

  const WorkerApi = window.MacAnalyzerSmartroomWorker;
  const Store = window.MacAnalyzerSmartroomStore;
  const Charts = window.MacAnalyzerSmartroomCharts;
  const RoomTimeline = window.MacAnalyzerRoomTimeline;
  const RoomLocation = window.MacAnalyzerRoomLocation;
  const VirtualTable = window.MacAnalyzerVirtualTable;
  const LazyTabs = window.MacAnalyzerLazyTabs;
  const Feedback = window.MacAnalyzerUiFeedback;
  const Time = window.MacAnalyzerTime;
  const cache = new Map();
  const inflight = new Map();
  const selectedRoomKey = "mac-analyzer-selected-smartroom-id";
  let options = null;
  let report = null;
  let generation = 0;
  let autoLoadRevision = 0;
  let initialized = false;

  const $ = (selector) => document.querySelector(selector) || LazyTabs?.querySelector(selector) || null;
  const text = (value) => String(value ?? "").trim();
  const normalizeMac = (value) =>
    text(value)
      .toUpperCase()
      .replace(/[^0-9A-F]/g, "")
      .slice(0, 12);
  const formatMac = (value) =>
    normalizeMac(value)
      .match(/.{1,2}/g)
      ?.join(":") || text(value);
  const formatDate = (value) => Time?.formatUtc?.(value) || "Дата не указана";
  const escapeHtml = (value) =>
    String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  const debounce = (callback, delay = 120) => {
    let timer = 0;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => callback(...args), delay);
    };
  };

  function snapshots() {
    const rows = Array.from(options?.getSnapshots?.() || []);
    if (!rows.length) {
      const devices = options?.getCurrentDevices?.() || [];
      if (devices.length)
        rows.push({
          id: "current",
          name: "Текущий результат",
          createdAt: options?.getLastAnalysis?.() || new Date().toISOString(),
          deviceCount: devices.length,
          devices,
        });
    }
    return rows;
  }

  function cacheKey(snapshotRows = snapshots()) {
    return JSON.stringify({
      snapshots: snapshotRows.map((item) => [item.id, item.createdAt, item.deviceCount]),
      ddio: Object.keys(options?.getDdioOverlay?.() || {}).length,
    });
  }

  async function build(force = false) {
    let snapshotRows = null;
    if (typeof options?.refreshSnapshots === "function") {
      try {
        const refreshed = await options.refreshSnapshots(force);
        if (Array.isArray(refreshed)) snapshotRows = refreshed;
      } catch (error) {
        if (!snapshots().length) throw error;
      }
    }
    snapshotRows = snapshotRows || snapshots();
    const key = cacheKey(snapshotRows);
    if (!force && cache.has(key)) return cache.get(key);
    if (!force && inflight.has(key)) return inflight.get(key);
    if (!WorkerApi) throw new Error("Модуль вычислений Smartroom не загружен");
    if (force) {
      cache.clear();
      inflight.clear();
    }
    const currentGeneration = ++generation;
    const promise = WorkerApi.build(snapshotRows, {
      ddioOverlay: options?.getDdioOverlay?.() || {},
      streamSnapshot: options?.streamSnapshot,
      loadSnapshot: options?.loadSnapshot,
    })
      .then(async (value) => {
        if (currentGeneration !== generation) return report || value;
        cache.clear();
        cache.set(key, value);
        report = value;
        const current = value.rooms.flatMap((room) => room.devices || []);
        const persistence = await Promise.allSettled([
          Store?.syncEquipment(current, options?.getLastAnalysis?.() || new Date().toISOString()),
          Store?.appendHistory(
            (value.criticalSwitchChanges || []).map((item) => ({
              entity_type: "ip_switch",
              smartroomId: item.smartroomId,
              mac: item.mac,
              field: "ip_switch",
              old_value: item.previousIp,
              new_value: item.currentIp,
              timestamp: item.date,
            })),
          ),
        ]);
        for (const result of persistence) if (result.status === "rejected") Feedback?.showError(result.reason);
        return value;
      })
      .finally(() => {
        if (inflight.get(key) === promise) inflight.delete(key);
      });
    inflight.set(key, promise);
    return promise;
  }

  function invalidate() {
    generation += 1;
    cache.clear();
    inflight.clear();
    report = null;
  }

  function roomLocation(room) {
    if (RoomLocation?.parse) return RoomLocation.parse(room);
    const result = {
      tb: text(room?.tb),
      city: text(room?.city),
      site: text(room?.site),
      floor: text(room?.floor),
      room: text(room?.room),
    };
    const parts = text(room?.locationPath || room?.address)
      .split(",")
      .map(text)
      .filter(Boolean);
    if (parts.length >= 5) {
      if (!result.tb) result.tb = parts[0];
      if (!result.city) result.city = parts[1];
      if (!result.site) result.site = parts[2];
      if (!result.floor) result.floor = parts[3];
      if (!result.room) result.room = parts.slice(4).join(", ");
    } else if (!result.city && parts.length) result.city = text(parts[0].replace(/^г\.?\s*/i, ""));
    return result;
  }

  function roomCity(room) {
    return roomLocation(room).city;
  }

  function fillSelect(id, label, values) {
    const select = $("#" + id);
    if (!select) return;
    const selected = text(select.value);
    select.innerHTML =
      `<option value="">${escapeHtml(label)}</option>` +
      values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
    if (values.includes(selected)) select.value = selected;
  }

  const chronologyFilterIds = Object.freeze({
    tb: "roomChronologyTbFilter",
    city: "roomChronologyCityFilter",
    site: "roomChronologySiteFilter",
    floor: "roomChronologyFloorFilter",
    room: "roomChronologyRoomFilter",
  });

  function readChronologyFilters() {
    return Object.fromEntries(
      Object.entries(chronologyFilterIds).map(([field, id]) => [field, text($("#" + id)?.value)]),
    );
  }

  function fillLocationFilters(value) {
    const rooms = value.rooms || [];
    const cascade = RoomLocation?.cascade?.(rooms, readChronologyFilters());
    const locations = rooms.map(roomLocation);
    const unique = (field) =>
      Array.from(new Set(locations.map((location) => location[field]).filter(Boolean))).sort((a, b) =>
        a.localeCompare(b, "ru", { numeric: true }),
      );
    const options =
      cascade?.options || Object.fromEntries(Object.keys(chronologyFilterIds).map((field) => [field, unique(field)]));
    const normalized = cascade?.filters || readChronologyFilters();
    const labels = {
      tb: "Все ТБ",
      city: "Все города",
      site: "Все площадки",
      floor: "Все этажи",
      room: "Все помещения",
    };
    for (const [field, id] of Object.entries(chronologyFilterIds)) {
      const select = $("#" + id);
      if (!select) continue;
      select.value = normalized[field] || "";
      fillSelect(id, labels[field], options[field] || []);
      select.value = normalized[field] || "";
    }
    const cities = unique("city");
    fillSelect("roomsCityFilter", "Все города", cities);
    return normalized;
  }

  function chronologyRooms(value) {
    const filters = readChronologyFilters();
    const query = text($("#roomChronologySearchInput")?.value).toLowerCase();
    return (value.rooms || []).filter((room) => {
      if (RoomLocation?.matches) return RoomLocation.matches(room, filters, query);
      const location = roomLocation(room);
      if (Object.entries(filters).some(([field, expected]) => expected && location[field] !== expected)) return false;
      if (!query) return true;
      return [
        room.smartroomId,
        location.tb,
        location.city,
        location.site,
        location.floor,
        location.room,
        room.address,
        ...(room.devices || []).flatMap((device) => [
          device.mac,
          device.ip,
          device.switchIp,
          device.hostname,
          device.vendor,
          device.model,
        ]),
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }

  function clearDownstreamFilters(changedField) {
    const order = Object.keys(chronologyFilterIds);
    const index = order.indexOf(changedField);
    for (const field of order.slice(index + 1)) {
      const select = $("#" + chronologyFilterIds[field]);
      if (select) select.value = "";
    }
    const roomSelect = $("#roomChronologySelect");
    if (roomSelect) roomSelect.value = "";
    sessionStorage.removeItem(selectedRoomKey);
  }

  function fillRoomSelect(value) {
    const select = $("#roomChronologySelect");
    if (!select) return;
    const saved = text(select.value || sessionStorage.getItem(selectedRoomKey));
    const rooms = chronologyRooms(value);
    select.innerHTML =
      '<option value="">Выберите Smartroom ID</option>' +
      rooms
        .map(
          (room) =>
            `<option value="${escapeHtml(room.smartroomId)}">${escapeHtml(room.smartroomId)}${room.room ? ` · ${escapeHtml(room.room)}` : ""}</option>`,
        )
        .join("");
    if (rooms.some((room) => room.smartroomId === saved)) select.value = saved;
    else if (rooms.length === 1) select.value = rooms[0].smartroomId;
  }

  function roomRow(room) {
    const switches = Array.from(new Set(room.devices.map((item) => item.switchIp).filter(Boolean))),
      missing = room.missing || [];
    return `<tr data-room-key="${escapeHtml(room.smartroomId)}" class="${missing.length ? "missing-smartroom" : ""}" tabindex="0"><td>${escapeHtml(room.smartroomId || "—")}</td><td>${escapeHtml(roomCity(room) || "—")}</td><td>${escapeHtml(room.room || "—")}</td><td>${escapeHtml(room.address || "—")}</td><td>${room.devices.length}</td><td title="${escapeHtml(missing.map((item) => formatMac(item.mac)).join(", "))}">${missing.length}</td><td>${escapeHtml(switches.join(", ") || "—")}</td><td>${escapeHtml(formatDate(room.history.at(-1)?.date || ""))}</td></tr>`;
  }

  async function renderRooms(force = false) {
    const body = $("#roomsBody"),
      summary = $("#roomsSummary");
    if (!body || !summary) return;
    summary.textContent = "Формирование истории в отдельном потоке…";
    try {
      const value = await build(force),
        query = text($("#roomsSearchInput")?.value).toLowerCase(),
        city = text($("#roomsCityFilter")?.value);
      fillLocationFilters(value);
      const rooms = (value.rooms || []).filter(
        (room) =>
          (!city || roomCity(room) === city) &&
          (!query ||
            [
              room.smartroomId,
              roomCity(room),
              room.room,
              room.address,
              ...(room.devices || []).flatMap((item) => [item.mac, item.switchIp, item.vendor, item.model]),
            ]
              .join(" ")
              .toLowerCase()
              .includes(query)),
      );
      if (rooms.length) VirtualTable?.setData(body, rooms, roomRow);
      else body.innerHTML = '<tr><td colspan="8" class="empty-state">Помещения не найдены.</td></tr>';
      summary.textContent = `Помещений: ${rooms.length.toLocaleString("ru-RU")} · пропущено строк без Smartroom ID и корректного MAC: ${Number(value.skipped || 0).toLocaleString("ru-RU")} · некорректных значений MAC: ${Number(value.invalidMacRows || 0).toLocaleString("ru-RU")} · красным отмечены исчезнувшие устройства.`;
      fillRoomSelect(value);
    } catch (error) {
      body.innerHTML = '<tr><td colspan="8" class="empty-state">Не удалось построить историю.</td></tr>';
      summary.textContent = error.message;
      Feedback?.showError(error);
    }
  }

  function renderTimelineInto(room, timelineTarget, tableTarget) {
    const rendered = RoomTimeline?.render(room, { escapeHtml, formatDate, formatMac }) || {
      timelineHtml: "",
      tableHtml: "",
    };
    if (timelineTarget) timelineTarget.innerHTML = rendered.timelineHtml;
    if (tableTarget) tableTarget.innerHTML = rendered.tableHtml;
    return rendered;
  }

  function renderRoomCoverage(room) {
    const button = $("#roomChronologyAllChangedButton"),
      target = $("#roomChronologyCoverageDetails");
    if (!button || !target) return null;
    const comparison = RoomTimeline?.compareLatest?.(room) || {
      total: 0,
      changed: 0,
      unchanged: 0,
      allChanged: false,
      entries: [],
    };
    const available = Boolean(room && room.history?.length >= 2);
    button.disabled = !available;
    button.classList.toggle("critical-change", comparison.allChanged);
    button.textContent = available
      ? `Проверить изменения всех устройств (${comparison.changed}/${comparison.total})`
      : "Проверить изменения всех устройств";
    button.title = available
      ? "Показать сравнение всех устройств выбранной комнаты между двумя последними Final"
      : "Для сравнения нужны минимум две финальные выгрузки";
    if (!available) button.setAttribute("aria-expanded", "false");
    const expanded = available && button.getAttribute("aria-expanded") === "true";
    target.hidden = !expanded;
    if (!available) {
      target.innerHTML = "";
      return comparison;
    }
    const verdict = comparison.allChanged
      ? "Во всех устройствах этой переговорной есть подтверждённые изменения."
      : `Изменено ${comparison.changed} из ${comparison.total}; без изменений: ${comparison.unchanged}.`;
    target.innerHTML =
      `<p class="${comparison.allChanged ? "critical-change" : "muted"}">${escapeHtml(verdict)} Сравнение: ${escapeHtml(formatDate(comparison.previousDate))} → ${escapeHtml(formatDate(comparison.currentDate))}.</p>` +
      '<div class="table-wrap"><table><thead><tr><th>MAC / идентификатор</th><th>Модель</th><th>Результат</th><th>Было → стало</th></tr></thead><tbody>' +
      comparison.entries
        .map((entry) => {
          const details = entry.changes?.length
            ? entry.changes
                .map((change) => `${change.label}: ${change.before || "Не заполнено"} → ${change.after}`)
                .join("; ")
            : entry.status === "Добавлен"
              ? "Нет в предыдущем Final → есть в новом Final"
              : entry.status === "Удален"
                ? "Есть в предыдущем Final → нет в новом Final"
                : "Значения совпадают";
          return `<tr><td>${escapeHtml(formatMac(entry.mac) || entry.identity)}</td><td>${escapeHtml(entry.model)}</td><td><span class="room-status room-status-${entry.status === "Без изменений" ? "unchanged" : "changed"}">${escapeHtml(entry.status)}</span></td><td>${escapeHtml(details)}</td></tr>`;
        })
        .join("") +
      "</tbody></table></div>";
    return comparison;
  }

  async function renderRoomChronology(force = false) {
    try {
      const value = await build(force);
      fillLocationFilters(value);
      fillRoomSelect(value);
      const id = text($("#roomChronologySelect")?.value),
        room = value.rooms.find((item) => item.smartroomId === id),
        summary = $("#roomChronologySummary");
      if (id) sessionStorage.setItem(selectedRoomKey, id);
      else sessionStorage.removeItem(selectedRoomKey);
      const rendered = renderTimelineInto(room, $("#roomChronologyTimeline"), $("#roomChronologyTableBody"));
      const comparison = renderRoomCoverage(room);
      if (summary)
        summary.textContent = room
          ? `${[room.smartroomId, roomLocation(room).tb, roomLocation(room).city, roomLocation(room).site, roomLocation(room).floor, roomLocation(room).room].filter(Boolean).join(" · ")} · событий: ${rendered.rows.length} · изменено устройств: ${comparison?.changed || 0}/${comparison?.total || 0}`
          : value.rooms.length
            ? "Выберите помещение, чтобы увидеть всю цепочку замен оборудования."
            : `Помещения со Smartroom ID не найдены. Обработано финальных выгрузок: ${value.snapshots?.length || 0}.`;
    } catch (error) {
      Feedback?.showError(error);
      throw error;
    }
  }

  function showRoom(id) {
    const room = report?.rooms?.find((item) => item.smartroomId === id);
    if (!room) return;
    sessionStorage.setItem(selectedRoomKey, id);
    $("#roomChronologyDialogTitle").textContent = `Хронология ${room.smartroomId}`;
    const location = roomLocation(room),
      comparison = RoomTimeline?.compareLatest?.(room);
    $("#roomChronologyDialogSubtitle").textContent = [
      location.tb,
      location.city,
      location.site,
      location.floor,
      location.room,
      room.address,
      comparison ? `Изменено ${comparison.changed}/${comparison.total}` : "",
    ]
      .filter(Boolean)
      .join(" · ");
    renderTimelineInto(room, $("#roomChronologyDialogTimeline"), $("#roomChronologyDialogTableBody"));
    $("#roomChronologyDialog").showModal();
  }

  async function addKnownModel(button) {
    const mac = normalizeMac(button?.dataset.addKnownModel),
      model = text(window.prompt(`Введите модель для ${formatMac(mac)}`));
    if (!model) return;
    await Store?.saveKnownModel(mac, model, button?.dataset.knownVendor || "");
    for (const room of report?.rooms || [])
      for (const observation of room.history || [])
        for (const device of observation.devices || []) if (normalizeMac(device.mac) === mac) device.model = model;
    await renderRoomChronology(false);
    options?.notify?.("Модель сохранена и будет применяться при следующих обогащениях.");
  }

  async function renderCharts(force = false) {
    if (!Charts) throw new Error("Модуль графиков не загружен");
    const value = await build(force);
    const rendered = await Charts.render(value);
    if (!rendered && value?.charts?.length)
      throw new Error("Графики не построены. Проверьте доступность Chart.js и Canvas в браузере.");
    return rendered;
  }

  async function autoLoad() {
    const revision = ++autoLoadRevision;
    if (!Store || options?.hasDdioFile?.()) return;
    const url = Store.apiUrl(),
      input = $("#ddioApiUrlInput");
    if (input) input.value = url;
    let rows = null,
      name = "ddio-auto.json";
    if (url)
      try {
        rows = await Store.fetchDdio(url);
        if (revision !== autoLoadRevision) return;
        name = (new URL(url, location.href).pathname.split("/").pop() || name).replace(/[^\p{L}\p{N}_.-]+/gu, "-");
        await Store.saveDdioSnapshot(rows);
      } catch (error) {
        Feedback?.showError(new Error(`Автозагрузка DDIO не выполнена: ${error.message || error}`));
      }
    if (!rows) rows = (await Store.latestDdioSnapshot().catch(() => null))?.devices || null;
    if (revision !== autoLoadRevision || options?.hasDdioFile?.()) return;
    if (rows?.length)
      await options?.loadDdioFile?.([
        new File([JSON.stringify(rows, null, 2)], name, { type: "application/json", lastModified: Date.now() }),
      ]);
  }

  function initialize(configuration) {
    options = configuration;
    if (initialized) return;
    initialized = true;
    const input = $("#ddioApiUrlInput");
    if (input) input.value = Store?.apiUrl?.() || "";
    $("#saveDdioApiUrlButton")?.addEventListener("click", () => {
      Store?.saveApiUrl(input?.value || "");
      options?.notify?.("Ссылка DDIO сохранена. Автозагрузка выполнится при следующем открытии.");
    });
    $("#refreshRoomsButton")?.addEventListener("click", () => renderRooms(true));
    $("#roomsSearchInput")?.addEventListener(
      "input",
      debounce(() => renderRooms(false)),
    );
    $("#roomsCityFilter")?.addEventListener("change", () => renderRooms(false));
    $("#roomChronologySelect")?.addEventListener("change", () => renderRoomChronology(false));
    Object.entries(chronologyFilterIds).forEach(([field, id]) =>
      $("#" + id)?.addEventListener("change", () => {
        clearDownstreamFilters(field);
        fillLocationFilters(report || { rooms: [] });
        fillRoomSelect(report || { rooms: [] });
        renderRoomChronology(false);
      }),
    );
    $("#roomChronologySearchInput")?.addEventListener(
      "input",
      debounce(() => {
        fillRoomSelect(report || { rooms: [] });
        renderRoomChronology(false);
      }),
    );
    $("#roomChronologyAllChangedButton")?.addEventListener("click", (event) => {
      const button = event.currentTarget;
      button.setAttribute("aria-expanded", button.getAttribute("aria-expanded") === "true" ? "false" : "true");
      const room = report?.rooms?.find((item) => item.smartroomId === text($("#roomChronologySelect")?.value));
      renderRoomCoverage(room);
    });
    $("#refreshRoomChronologyButton")?.addEventListener("click", () => renderRoomChronology(true));
    $("#roomsBody")?.addEventListener("click", (event) => {
      const row = event.target.closest("[data-room-key]");
      if (row) showRoom(row.dataset.roomKey);
    });
    $("#roomsBody")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        const row = event.target.closest("[data-room-key]");
        if (row) showRoom(row.dataset.roomKey);
      }
    });
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-add-known-model]");
      if (button) addKnownModel(button).catch((error) => Feedback?.showError(error));
    });
    $("#closeRoomChronologyDialog")?.addEventListener("click", () => $("#roomChronologyDialog")?.close());
  }

  async function render(name, force = false) {
    if (name === "rooms") return renderRooms(force);
    if (name === "roomhistory") return renderRoomChronology(force);
    if (name === "analytics") return renderCharts(force);
  }

  window.MacAnalyzerSmartroomUI = Object.freeze({ initialize, render, autoLoad, build, invalidate });
})();

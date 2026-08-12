(() => {
  "use strict";

  const WorkerApi = window.MacAnalyzerSmartroomWorker;
  const Store = window.MacAnalyzerSmartroomStore;
  const Charts = window.MacAnalyzerSmartroomCharts;
  const RoomTimeline = window.MacAnalyzerRoomTimeline;
  const VirtualTable = window.MacAnalyzerVirtualTable;
  const LazyTabs = window.MacAnalyzerLazyTabs;
  const Feedback = window.MacAnalyzerUiFeedback;
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
  const normalizeMac = (value) => text(value).toUpperCase().replace(/[^0-9A-F]/g, "").slice(0, 12);
  const formatMac = (value) => normalizeMac(value).match(/.{1,2}/g)?.join(":") || text(value);
  const formatDate = (value) => { const date = new Date(value); return Number.isNaN(date.getTime()) ? text(value) : date.toLocaleString("ru-RU"); };
  const escapeHtml = (value) => String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  const debounce = (callback, delay = 120) => { let timer = 0; return (...args) => { clearTimeout(timer); timer = setTimeout(() => callback(...args), delay); }; };

  function snapshots() {
    const rows = Array.from(options?.getSnapshots?.() || []);
    if (!rows.length) {
      const devices = options?.getCurrentDevices?.() || [];
      if (devices.length) rows.push({ id: "current", name: "Текущий результат", createdAt: options?.getLastAnalysis?.() || new Date().toISOString(), deviceCount: devices.length, devices });
    }
    return rows;
  }

  function cacheKey() {
    return JSON.stringify({ snapshots: snapshots().map((item) => [item.id, item.createdAt, item.deviceCount]), ddio: Object.keys(options?.getDdioOverlay?.() || {}).length });
  }

  async function build(force = false) {
    const key = cacheKey();
    if (!force && cache.has(key)) return cache.get(key);
    if (!force && inflight.has(key)) return inflight.get(key);
    if (!WorkerApi) throw new Error("Модуль вычислений Smartroom не загружен");
    if (force) { cache.clear(); inflight.clear(); }
    const currentGeneration = ++generation;
    const promise = WorkerApi.build(snapshots(), {
      ddioOverlay: options?.getDdioOverlay?.() || {},
      streamSnapshot: options?.streamSnapshot,
      loadSnapshot: options?.loadSnapshot,
    }).then(async (value) => {
      if (currentGeneration !== generation) return report || value;
      cache.clear(); cache.set(key, value); report = value;
      const current = value.rooms.flatMap((room) => room.devices || []);
      const persistence = await Promise.allSettled([
        Store?.syncEquipment(current, options?.getLastAnalysis?.() || new Date().toISOString()),
        Store?.appendHistory((value.ipHistory || []).map((item) => ({ entity_type: "ip_switch", smartroomId: item.smartroomId, mac: item.mac, field: "ip_switch", old_value: item.previousIp, new_value: item.currentIp, timestamp: item.date }))),
      ]);
      for (const result of persistence) if (result.status === "rejected") console.warn("Smartroom IndexedDB:", result.reason);
      return value;
    }).finally(() => { if (inflight.get(key) === promise) inflight.delete(key); });
    inflight.set(key, promise);
    return promise;
  }

  function fillRoomSelect(value) {
    const select = $("#roomChronologySelect"); if (!select) return;
    const saved = text(select.value || sessionStorage.getItem(selectedRoomKey));
    select.innerHTML = '<option value="">Выберите Smartroom ID</option>' + (value.rooms || []).map((room) => `<option value="${escapeHtml(room.smartroomId)}">${escapeHtml(room.smartroomId)}${room.room ? ` · ${escapeHtml(room.room)}` : ""}</option>`).join("");
    if (value.rooms.some((room) => room.smartroomId === saved)) select.value = saved;
  }

  function roomRow(room) {
    const switches = Array.from(new Set(room.devices.map((item) => item.switchIp).filter(Boolean))), missing = room.missing || [];
    return `<tr data-room-key="${escapeHtml(room.smartroomId)}" class="${missing.length ? "missing-smartroom" : ""}" tabindex="0"><td>${escapeHtml(room.smartroomId || "—")}</td><td>${escapeHtml(room.room || "—")}</td><td>${escapeHtml(room.address || "—")}</td><td>${room.devices.length}</td><td title="${escapeHtml(missing.map((item) => formatMac(item.mac)).join(", "))}">${missing.length}</td><td>${escapeHtml(switches.join(", ") || "—")}</td><td>${escapeHtml(formatDate(room.history.at(-1)?.date || ""))}</td></tr>`;
  }

  async function renderRooms(force = false) {
    const body = $("#roomsBody"), summary = $("#roomsSummary"); if (!body || !summary) return;
    summary.textContent = "Формирование истории в отдельном потоке…";
    try {
      const value = await build(force), query = text($("#roomsSearchInput")?.value).toLowerCase();
      const rooms = (value.rooms || []).filter((room) => !query || [room.smartroomId, room.room, room.address, ...(room.devices || []).flatMap((item) => [item.mac, item.switchIp, item.vendor, item.model])].join(" ").toLowerCase().includes(query));
      if (rooms.length) VirtualTable?.setData(body, rooms, roomRow); else body.innerHTML = '<tr><td colspan="7" class="empty-state">Помещения не найдены.</td></tr>';
      summary.textContent = `Помещений: ${rooms.length.toLocaleString("ru-RU")} · пропущено строк без Smartroom ID: ${Number(value.skipped || 0).toLocaleString("ru-RU")} · красным отмечены исчезнувшие устройства.`;
      fillRoomSelect(value);
    } catch (error) { body.innerHTML = '<tr><td colspan="7" class="empty-state">Не удалось построить историю.</td></tr>'; summary.textContent = error.message; Feedback?.showError(error); }
  }

  function ipRow(item) {
    const possible = (item.possibleIps || []).join(", "), tip = possible ? `Возможные IP из DDIO: ${possible}` : "В DDIO нет дополнительных IP";
    return `<tr class="ip-changed-row"><td>${escapeHtml(formatDate(item.date))}</td><td>${escapeHtml(item.smartroomId || "—")}</td><td>${escapeHtml(item.room || "—")}</td><td>${escapeHtml(formatMac(item.mac) || "—")}</td><td>${escapeHtml(item.previousIp || "—")}</td><td>${escapeHtml(item.currentIp || "—")}<span class="ip-change-warning" title="${escapeHtml(tip)}">❗</span></td><td title="${escapeHtml(possible)}">${escapeHtml(possible || "—")}</td></tr>`;
  }

  async function renderIpHistory(force = false) {
    const body = $("#ipHistoryBody"), summary = $("#ipHistorySummary"); if (!body || !summary) return;
    summary.textContent = "Сравнение сохраненных IP в отдельном потоке…";
    try {
      const value = await build(force), query = text($("#ipHistorySearchInput")?.value).toLowerCase();
      const rows = (value.ipHistory || []).filter((item) => !query || [item.smartroomId, item.room, item.mac, item.previousIp, item.currentIp, ...(item.possibleIps || [])].join(" ").toLowerCase().includes(query)).slice().reverse();
      if (rows.length) VirtualTable?.setData(body, rows, ipRow); else body.innerHTML = '<tr><td colspan="7" class="empty-state">Смен IP коммутатора не найдено.</td></tr>';
      summary.textContent = `Смен IP относительно предыдущего сохраненного снимка: ${rows.length.toLocaleString("ru-RU")} · ❗ показывает Possible_IPs из DDIO.`;
    } catch (error) { summary.textContent = error.message; Feedback?.showError(error); }
  }

  function renderTimelineInto(room, timelineTarget, tableTarget) {
    const rendered = RoomTimeline?.render(room, { escapeHtml, formatDate, formatMac }) || { timelineHtml: "", tableHtml: "" };
    if (timelineTarget) timelineTarget.innerHTML = rendered.timelineHtml;
    if (tableTarget) tableTarget.innerHTML = rendered.tableHtml;
    return rendered;
  }

  async function renderRoomChronology(force = false) {
    try {
      const value = await build(force); fillRoomSelect(value);
      const id = text($("#roomChronologySelect")?.value), room = value.rooms.find((item) => item.smartroomId === id), summary = $("#roomChronologySummary");
      if (id) sessionStorage.setItem(selectedRoomKey, id); else sessionStorage.removeItem(selectedRoomKey);
      const rendered = renderTimelineInto(room, $("#roomChronologyTimeline"), $("#roomChronologyTableBody"));
      if (summary) summary.textContent = room ? `${room.smartroomId}${room.room ? ` · ${room.room}` : ""} · событий: ${rendered.rows.length}` : "Выберите помещение, чтобы увидеть всю цепочку замен оборудования.";
    } catch (error) { Feedback?.showError(error); throw error; }
  }

  function showRoom(id) {
    const room = report?.rooms?.find((item) => item.smartroomId === id); if (!room) return;
    sessionStorage.setItem(selectedRoomKey, id);
    $("#roomChronologyDialogTitle").textContent = `Хронология ${room.smartroomId}`;
    $("#roomChronologyDialogSubtitle").textContent = [room.room, room.address].filter(Boolean).join(" · ");
    renderTimelineInto(room, $("#roomChronologyDialogTimeline"), $("#roomChronologyDialogTableBody"));
    $("#roomChronologyDialog").showModal();
  }

  async function addKnownModel(button) {
    const mac = normalizeMac(button?.dataset.addKnownModel), model = text(window.prompt(`Введите модель для ${formatMac(mac)}`));
    if (!model) return;
    Store?.saveKnownModel(mac, model, button?.dataset.knownVendor || "");
    for (const room of report?.rooms || []) for (const observation of room.history || []) for (const device of observation.devices || []) if (normalizeMac(device.mac) === mac) device.model = model;
    await renderRoomChronology(false);
    options?.notify?.("Модель сохранена и будет применяться при следующих обогащениях.");
  }

  async function renderCharts(force = false) { Charts?.render(await build(force)); }

  async function autoLoad() {
    const revision = ++autoLoadRevision;
    if (!Store || options?.hasDdioFile?.()) return;
    const url = Store.apiUrl(), input = $("#ddioApiUrlInput"); if (input) input.value = url;
    let rows = null, name = "ddio-auto.json";
    if (url) try { rows = await Store.fetchDdio(url); if (revision !== autoLoadRevision) return; name = (new URL(url, location.href).pathname.split("/").pop() || name).replace(/[^\p{L}\p{N}_.-]+/gu, "-"); await Store.saveDdioSnapshot(rows); } catch (error) { console.warn("Автозагрузка DDIO:", error); }
    if (!rows) rows = (await Store.latestDdioSnapshot().catch(() => null))?.devices || null;
    if (revision !== autoLoadRevision || options?.hasDdioFile?.()) return;
    if (rows?.length) await options?.loadDdioFile?.([new File([JSON.stringify(rows, null, 2)], name, { type: "application/json", lastModified: Date.now() })]);
  }

  function initialize(configuration) {
    options = configuration;
    if (initialized) return;
    initialized = true;
    const input = $("#ddioApiUrlInput"); if (input) input.value = Store?.apiUrl?.() || "";
    $("#saveDdioApiUrlButton")?.addEventListener("click", () => { Store?.saveApiUrl(input?.value || ""); options?.notify?.("Ссылка DDIO сохранена. Автозагрузка выполнится при следующем открытии."); });
    $("#refreshRoomsButton")?.addEventListener("click", () => renderRooms(true));
    $("#roomsSearchInput")?.addEventListener("input", debounce(() => renderRooms(false)));
    $("#refreshIpHistoryButton")?.addEventListener("click", () => renderIpHistory(true));
    $("#ipHistorySearchInput")?.addEventListener("input", debounce(() => renderIpHistory(false)));
    $("#roomChronologySelect")?.addEventListener("change", () => renderRoomChronology(false));
    $("#refreshRoomChronologyButton")?.addEventListener("click", () => renderRoomChronology(true));
    $("#roomsBody")?.addEventListener("click", (event) => { const row = event.target.closest("[data-room-key]"); if (row) showRoom(row.dataset.roomKey); });
    $("#roomsBody")?.addEventListener("keydown", (event) => { if (event.key === "Enter") { const row = event.target.closest("[data-room-key]"); if (row) showRoom(row.dataset.roomKey); } });
    document.addEventListener("click", (event) => { const button = event.target.closest("[data-add-known-model]"); if (button) addKnownModel(button).catch((error) => Feedback?.showError(error)); });
    $("#closeRoomChronologyDialog")?.addEventListener("click", () => $("#roomChronologyDialog")?.close());
  }

  async function render(name, force = false) {
    if (name === "rooms") return renderRooms(force);
    if (name === "iphistory") return renderIpHistory(force);
    if (name === "roomhistory") return renderRoomChronology(force);
    if (name === "analytics") return renderCharts(force);
  }

  window.MacAnalyzerSmartroomUI = Object.freeze({ initialize, render, autoLoad, build });
})();

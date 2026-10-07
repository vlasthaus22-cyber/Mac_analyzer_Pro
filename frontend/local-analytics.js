(() => {
  "use strict";

  const unknownVendors = new Set(["", "unknown", "не определено", "неизвестный вендор", "unknown vendor"]);
  const fieldLabels = {
    vendor: "Производитель",
    model: "Модель",
    room: "Помещение",
    smartroomId: "Smartroom ID",
    switchIp: "IP коммутатора",
    switchPort: "Порт",
    address: "Адрес",
  };

  function text(value, fallback = "") {
    const result = value === null || value === undefined ? "" : String(value).trim();
    return result || fallback;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeXml(value) {
    return escapeHtml(value);
  }

  function normalizeMac(value) {
    return String(value || "").toUpperCase().replace(/[^0-9A-F]/g, "").slice(0, 12);
  }

  function deviceValue(device, field) {
    if (field === "switchIp") return text(device?.switchIp || device?.switch_ip, "Без коммутатора");
    if (field === "switchPort") return text(device?.switchPort || device?.switch_port, "Без порта");
    if (field === "smartroomId") return text(device?.smartroomId || device?.smartroom_id, "Без Smartroom ID");
    return text(device?.[field], {
      vendor: "Unknown",
      model: "Не определено",
      room: "Без помещения",
      address: "Без адреса",
    }[field] || "Не указано");
  }

  function tally(map, value, limit = 20_000) {
    const key = text(value, "Unknown");
    if (map.has(key)) {
      map.set(key, map.get(key) + 1);
    } else if (map.size < limit) {
      map.set(key, 1);
    }
  }

  function ranked(map, limit = 50) {
    return Array.from(map.entries())
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "ru"))
      .slice(0, Math.max(1, Number(limit) || 50))
      .map(([label, value]) => ({ label, value }));
  }

  function roomDescriptor(device = {}) {
    const smartroomId = text(device.smartroomId || device.smartroom_id);
    const room = text(device.room || device.room_name);
    const address = text(device.address || device.physicalAddress);
    const parsed = typeof window !== "undefined" && window.MacAnalyzerRoomLocation?.parse
      ? window.MacAnalyzerRoomLocation.parse(device)
      : { tb: text(device.tb), city: text(device.city), site: text(device.site), floor: text(device.floor), room };
    const resolvedRoom = text(parsed.room || room);
    const hierarchy = [parsed.tb, parsed.city, parsed.site, parsed.floor]
      .map((value) => text(value).replace(/\s+/g, " ").toLocaleLowerCase("ru-RU"));
    const normalizedRoom = resolvedRoom.replace(/\s+/g, " ").toLocaleLowerCase("ru-RU");
    const normalizedAddress = address.replace(/\s+/g, " ").toLocaleLowerCase("ru-RU");
    // A room name is mandatory for a fallback identity. Address alone often
    // names a whole site and must never merge all rooms of that site.
    const locationContext = hierarchy.some(Boolean) ? hierarchy : [normalizedAddress];
    const locationKey = normalizedRoom
      ? `location:${[...locationContext, normalizedRoom].join("\u0000")}`
      : "";
    const smartroomKey = smartroomId ? `smartroom:${smartroomId.toLocaleLowerCase("ru-RU")}` : "";
    return {
      key: smartroomKey || locationKey,
      smartroomKey,
      locationKey,
      smartroomId,
      room: resolvedRoom,
      address,
      tb: text(parsed.tb),
      city: text(parsed.city),
      site: text(parsed.site),
      floor: text(parsed.floor),
    };
  }

  function compactRoomSwitchDevice(device = {}, switchIp = "") {
    return {
      mac: normalizeMac(device.mac || device.macFormatted || device.mac_formatted),
      vendor: text(device.vendor),
      model: text(device.model),
      deviceType: text(device.deviceType || device.device_type || device.modelType || device.model_type || device.type),
      ip: text(device.ip),
      switchIp,
      switchPort: text(device.switchPort || device.switch_port),
      authenticationTime: text(device.authenticationTime || device.authentication_time),
      hostname: text(device.hostname || device.host_name),
      serialNumber: text(device.serialNumber || device.serial_number || device.serial),
      deviceId: text(device.deviceId || device.device_id),
      deviceName: text(device.deviceName || device.device_name || device.name),
      source: text(device.source || (Array.isArray(device.sourceFiles) ? device.sourceFiles.join(" + ") : "")),
    };
  }

  function mergeRoomSwitchRow(target, source) {
    if (!target) return source;
    target.totalDevices += source.totalDevices;
    target.missingSwitchDevices += source.missingSwitchDevices;
    target.missingDevices.push(...source.missingDevices);
    for (const field of ["smartroomId", "room", "address", "tb", "city", "site", "floor", "locationKey", "smartroomKey"])
      if (!target[field] && source[field]) target[field] = source[field];
    for (const [switchIp, sourceSwitch] of source.switches.entries()) {
      const targetSwitch = target.switches.get(switchIp) || { count: 0, devices: [] };
      targetSwitch.count += sourceSwitch.count;
      targetSwitch.devices.push(...sourceSwitch.devices);
      target.switches.set(switchIp, targetSwitch);
    }
    return target;
  }

  function reconcileRoomSwitchRows(roomSwitchRows, locationSmartroomKeys) {
    const reconciled = new Map();
    for (const row of roomSwitchRows.values()) {
      let targetKey = row.key;
      if (!row.smartroomId && row.locationKey) {
        const smartroomKeys = locationSmartroomKeys.get(row.locationKey) || new Set();
        // Missing IDs are attached only when the physical room location maps
        // to exactly one observed Smartroom ID. Ambiguous rows remain isolated.
        if (smartroomKeys.size === 1) targetKey = smartroomKeys.values().next().value;
        else if (smartroomKeys.size > 1) row.ambiguousSmartroomIds = Array.from(smartroomKeys);
      }
      const existing = reconciled.get(targetKey);
      const merged = mergeRoomSwitchRow(existing, row);
      merged.key = targetKey;
      reconciled.set(targetKey, merged);
    }
    return reconciled;
  }

  function finishRoomSwitchAnomalies(roomSwitchRows) {
    const rooms = [];
    let analyzedRooms = 0;
    for (const row of roomSwitchRows.values()) {
      const switches = Array.from(row.switches.entries())
        .map(([switchIp, value]) => ({ switchIp, count: value.count, devices: value.devices }))
        .sort((left, right) => right.count - left.count || left.switchIp.localeCompare(right.switchIp, "ru"));
      const knownSwitchDevices = switches.reduce((total, item) => total + item.count, 0);
      // Several Smartroom IDs at the same fallback location make anonymous
      // devices impossible to assign safely. Do not manufacture an anomaly.
      if ((row.ambiguousSmartroomIds || []).length) continue;
      if (knownSwitchDevices >= 3) analyzedRooms += 1;
      const dominant = switches[0];
      const runnerUp = switches[1];
      // A deviation requires a unique strict majority. A 1:1 split is a
      // conflict without enough evidence to call either switch the expected one.
      if (!dominant || !runnerUp || knownSwitchDevices < 3 || dominant.count < 2
          || dominant.count <= runnerUp.count || dominant.count <= knownSwitchDevices / 2) continue;
      const deviations = switches.slice(1).flatMap((item) => item.devices);
      const devices = switches.flatMap((item) => item.devices.map((device) => ({
        ...device,
        isDeviation: item.switchIp !== dominant.switchIp,
      }))).concat(row.missingDevices.map((device) => ({ ...device, isDeviation: false, missingSwitchIp: true })));
      rooms.push({
        key: row.key,
        smartroomId: row.smartroomId,
        room: row.room,
        address: row.address,
        tb: row.tb,
        city: row.city,
        site: row.site,
        floor: row.floor,
        totalDevices: row.totalDevices,
        knownSwitchDevices,
        missingSwitchDevices: row.missingSwitchDevices,
        expectedSwitchIp: dominant.switchIp,
        expectedCount: dominant.count,
        deviationCount: knownSwitchDevices - dominant.count,
        switchIps: switches.map(({ switchIp, count }) => ({ switchIp, count })),
        devices,
        deviations,
        devicesTruncated: devices.length < row.totalDevices,
        identitySource: row.smartroomId ? "smartroom-id" : "location",
        ambiguousSmartroomIds: row.ambiguousSmartroomIds || [],
      });
    }
    rooms.sort((left, right) => right.deviationCount - left.deviationCount
      || (left.room || left.smartroomId).localeCompare(right.room || right.smartroomId, "ru"));
    return { totalRooms: roomSwitchRows.size, analyzedRooms, anomalyRoomCount: rooms.length, rooms };
  }

  function createRoomSwitchIpAnomalyCollector(options = {}) {
    const rows = new Map();
    const locationSmartroomKeys = new Map();
    const roomDeviceSampleLimit = Math.max(20, Math.min(2_000, Number(options.roomDeviceSampleLimit || 500)));
    const totalDeviceSampleLimit = Math.max(500, Math.min(100_000, Number(options.roomDeviceTotalSampleLimit || 50_000)));
    let sampledDevices = 0;
    function acceptOne(device) {
      if (!device || typeof device !== "object") return;
      const descriptor = roomDescriptor(device);
      if (!descriptor.key) return;
      if (descriptor.smartroomKey && descriptor.locationKey) {
        const keys = locationSmartroomKeys.get(descriptor.locationKey) || new Set();
        keys.add(descriptor.smartroomKey);
        locationSmartroomKeys.set(descriptor.locationKey, keys);
      }
      let roomSwitch = rows.get(descriptor.key);
      if (!roomSwitch) {
        roomSwitch = { ...descriptor, totalDevices: 0, missingSwitchDevices: 0, missingDevices: [], switches: new Map() };
        rows.set(descriptor.key, roomSwitch);
      }
      roomSwitch.totalDevices += 1;
      const switchIp = text(device.switchIp || device.switch_ip);
      if (!switchIp) {
        roomSwitch.missingSwitchDevices += 1;
        if (roomSwitch.missingDevices.length < roomDeviceSampleLimit && sampledDevices < totalDeviceSampleLimit) {
          roomSwitch.missingDevices.push(compactRoomSwitchDevice(device, ""));
          sampledDevices += 1;
        }
        return;
      }
      let switchRow = roomSwitch.switches.get(switchIp);
      if (!switchRow) {
        switchRow = { count: 0, devices: [] };
        roomSwitch.switches.set(switchIp, switchRow);
      }
      switchRow.count += 1;
      if (switchRow.devices.length < roomDeviceSampleLimit && sampledDevices < totalDeviceSampleLimit) {
        switchRow.devices.push(compactRoomSwitchDevice(device, switchIp));
        sampledDevices += 1;
      }
    }
    function accept(devices = []) {
      for (const device of Array.isArray(devices) ? devices : []) acceptOne(device);
    }
    return Object.freeze({
      accept,
      acceptOne,
      finish: () => finishRoomSwitchAnomalies(reconcileRoomSwitchRows(rows, locationSmartroomKeys)),
    });
  }

  function analyzeRoomSwitchIpAnomalies(devices = [], options = {}) {
    const collector = createRoomSwitchIpAnomalyCollector(options);
    collector.accept(devices);
    return collector.finish();
  }

  function createCollector(options = {}) {
    const vendors = new Map();
    const models = new Map();
    const rooms = new Map();
    const roomIdentities = new Set();
    const smartrooms = new Map();
    const switchCounts = new Map();
    const clusterMap = new Map();
    const topologyMap = new Map();
    const roomSwitchCollector = createRoomSwitchIpAnomalyCollector(options);
    const clusterFields = Array.isArray(options.clusterFields) && options.clusterFields.length
      ? options.clusterFields
      : ["vendor", "room", "switchIp"];
    const clusterLimit = Math.max(100, Math.min(50_000, Number(options.clusterLimit || 20_000)));
    const switchLimit = Math.max(100, Math.min(50_000, Number(options.switchLimit || 20_000)));
    const portLimit = Math.max(32, Math.min(4_096, Number(options.portLimit || 2_048)));
    const vendorFilter = text(options.vendor);
    const roomFilter = text(options.room);
    const showUnknown = options.showUnknown !== false;
    let devices = 0;
    let knownVendors = 0;
    let withIp = 0;
    let withRoom = 0;
    let withAddress = 0;
    let withSwitch = 0;
    let withModel = 0;
    let clusterOverflow = 0;
    let topologyOverflow = 0;

    function accept(rows) {
      for (const device of Array.isArray(rows) ? rows : []) {
        if (!device || typeof device !== "object") continue;
        const vendor = deviceValue(device, "vendor");
        const model = text(device.model);
        const room = text(device.room);
        if (vendorFilter && vendor !== vendorFilter) continue;
        if (roomFilter && room !== roomFilter) continue;
        if (!showUnknown && unknownVendors.has(vendor.toLowerCase())) continue;
        const smartroomId = text(device.smartroomId || device.smartroom_id);
        const switchIp = text(device.switchIp || device.switch_ip);
        const switchPort = text(device.switchPort || device.switch_port, "Не указан");
        const mac = normalizeMac(device.mac || device.macFormatted || device.mac_formatted);
        devices += 1;
        tally(vendors, vendor);
        if (model) tally(models, model);
        if (room) tally(rooms, room);
        if (smartroomId) tally(smartrooms, smartroomId);
        if (smartroomId || room) roomIdentities.add(smartroomId || room);
        if (switchIp) tally(switchCounts, switchIp);
        if (!unknownVendors.has(vendor.toLowerCase())) knownVendors += 1;
        if (text(device.ip)) withIp += 1;
        if (room) withRoom += 1;
        if (text(device.address)) withAddress += 1;
        if (switchIp) withSwitch += 1;
        if (model) withModel += 1;

        roomSwitchCollector.acceptOne(device);

        const clusterValues = Object.fromEntries(clusterFields.map((field) => [field, deviceValue(device, field)]));
        const clusterKey = clusterFields.map((field) => clusterValues[field]).join("\u0000");
        let cluster = clusterMap.get(clusterKey);
        if (!cluster && clusterMap.size < clusterLimit) {
          cluster = { id: clusterKey, label: clusterFields.map((field) => clusterValues[field]).join(" · "), fields: clusterValues, count: 0 };
          clusterMap.set(clusterKey, cluster);
        }
        if (cluster) cluster.count += 1;
        else clusterOverflow += 1;

        if (!switchIp) continue;
        let switchNode = topologyMap.get(switchIp);
        if (!switchNode && topologyMap.size < switchLimit) {
          switchNode = { switchIp, deviceCount: 0, rooms: new Set(), ports: new Map(), sampleMacs: [] };
          topologyMap.set(switchIp, switchNode);
        }
        if (!switchNode) {
          topologyOverflow += 1;
          continue;
        }
        switchNode.deviceCount += 1;
        if (room) switchNode.rooms.add(room);
        if (mac && switchNode.sampleMacs.length < 12) switchNode.sampleMacs.push(mac);
        let port = switchNode.ports.get(switchPort);
        if (!port && switchNode.ports.size < portLimit) {
          port = { port: switchPort, deviceCount: 0, sampleMacs: [] };
          switchNode.ports.set(switchPort, port);
        }
        if (port) {
          port.deviceCount += 1;
          if (mac && port.sampleMacs.length < 8) port.sampleMacs.push(mac);
        }
      }
      return devices;
    }

    function finish() {
      const clusters = Array.from(clusterMap.values())
        .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label, "ru"));
      const nodes = Array.from(topologyMap.values())
        .map((node) => ({
          switchIp: node.switchIp,
          deviceCount: node.deviceCount,
          rooms: Array.from(node.rooms).sort((left, right) => left.localeCompare(right, "ru")),
          ports: Array.from(node.ports.values()).sort((left, right) => left.port.localeCompare(right.port, "ru")),
          portCount: node.ports.size,
          sampleMacs: node.sampleMacs,
        }))
        .sort((left, right) => right.deviceCount - left.deviceCount || left.switchIp.localeCompare(right.switchIp));
      const invalid = Math.max(0, Number(options.invalidCount || 0));
      return {
        summary: {
          devices,
          knownVendors,
          unknownVendors: Math.max(0, devices - knownVendors),
          uniqueVendors: Array.from(vendors.keys()).filter((value) => !unknownVendors.has(value.toLowerCase())).length,
          uniqueModels: models.size,
          uniqueRooms: roomIdentities.size,
          uniqueSmartrooms: smartrooms.size,
          uniqueSwitches: topologyMap.size,
          withIp,
          withRoom,
          withAddress,
          withSwitch,
          withModel,
          invalid,
        },
        charts: {
          vendors: ranked(vendors),
          models: ranked(models),
          rooms: ranked(rooms),
          smartrooms: ranked(smartrooms),
          switches: ranked(switchCounts),
        },
        clusters: {
          fields: clusterFields,
          items: clusters,
          overflowRows: clusterOverflow,
          summary: {
            clusters: clusters.length,
            devices: clusters.reduce((total, item) => total + item.count, 0) + clusterOverflow,
            largestCluster: clusters[0]?.count || 0,
          },
        },
        topology: {
          nodes,
          overflowRows: topologyOverflow,
          summary: {
            switches: nodes.length,
            ports: nodes.reduce((total, node) => total + node.portCount, 0),
            linkedDevices: withSwitch,
            unassignedDevices: Math.max(0, devices - withSwitch),
          },
        },
        switchIpAnomalies: roomSwitchCollector.finish(),
      };
    }

    return Object.freeze({ accept, finish });
  }

  function build(devices, options = {}) {
    const collector = createCollector(options);
    collector.accept(devices);
    return collector.finish();
  }

  function barHtml(items, emptyText = "Недостаточно данных.") {
    const rows = Array.isArray(items) ? items : [];
    const max = Math.max(1, ...rows.map((item) => Number(item?.value ?? item?.[1] ?? 0)));
    if (!rows.length) return `<p class="muted">${escapeHtml(emptyText)}</p>`;
    return rows.map((item) => {
      const label = item?.label ?? item?.[0] ?? "";
      const value = Number(item?.value ?? item?.[1] ?? 0);
      return `<div class="bar-item"><div class="bar-label"><span>${escapeHtml(label)}</span><strong>${value.toLocaleString("ru-RU")}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${Math.round(value / max * 100)}%"></div></div></div>`;
    }).join("");
  }

  function renderOverview(payload) {
    const summary = payload?.summary || {};
    return barHtml([
      { label: "Устройств", value: summary.devices || 0 },
      { label: "Производителей", value: summary.uniqueVendors || 0 },
      { label: "Моделей", value: summary.uniqueModels || 0 },
      { label: "Помещений", value: summary.uniqueRooms || 0 },
      { label: "Smartroom ID", value: summary.uniqueSmartrooms || 0 },
      { label: "Коммутаторов", value: summary.uniqueSwitches || 0 },
    ]);
  }

  function renderClusters(payload, limit = 30) {
    const clusters = payload?.clusters?.items || [];
    if (!clusters.length) return '<p class="muted">Нет данных для кластеризации.</p>';
    const rows = clusters.slice(0, Math.max(1, Number(limit) || 30)).map((cluster) => (
      `<div class="summary-line local-cluster-row"><strong>${escapeHtml(cluster.label)}</strong><span>${Number(cluster.count || 0).toLocaleString("ru-RU")} устройств</span></div>`
    )).join("");
    const overflow = Number(payload?.clusters?.overflowRows || 0);
    return `${rows}${overflow ? `<p class="muted">Ещё ${overflow.toLocaleString("ru-RU")} строк учтено в ограниченном агрегате.</p>` : ""}`;
  }

  function renderTopology(payload, limit = 30) {
    const nodes = payload?.topology?.nodes || [];
    if (!nodes.length) return '<p class="muted">Нет устройств, привязанных к коммутаторам.</p>';
    return nodes.slice(0, Math.max(1, Number(limit) || 30)).map((node) => {
      const ports = node.ports.slice(0, 30).map((port) => (
        `<div class="summary-line"><strong>${escapeHtml(port.port)}</strong><span>${Number(port.deviceCount || 0).toLocaleString("ru-RU")} устройств${port.sampleMacs.length ? ` · ${escapeHtml(port.sampleMacs.slice(0, 3).join(", "))}` : ""}</span></div>`
      )).join("");
      return `<details class="local-topology-node"><summary><strong>${escapeHtml(node.switchIp)}</strong><span>${Number(node.deviceCount || 0).toLocaleString("ru-RU")} устройств · ${node.portCount} портов</span></summary><div class="local-topology-details"><p class="muted">Помещения: ${escapeHtml(node.rooms.join(", ") || "не указаны")}</p>${ports}</div></details>`;
    }).join("");
  }

  function snapshotRows(snapshots) {
    return (Array.isArray(snapshots) ? snapshots : [])
      .map((snapshot, index) => ({
        id: text(snapshot?.id, `snapshot-${index + 1}`),
        name: text(snapshot?.name || snapshot?.source, `Выгрузка ${index + 1}`),
        date: text(snapshot?.fileCreatedAt || snapshot?.createdAt || snapshot?.savedAt || snapshot?.date),
        count: Math.max(0, Number(snapshot?.deviceCount ?? snapshot?.devices?.length ?? 0)),
      }))
      .sort((left, right) => left.date.localeCompare(right.date));
  }

  function renderStatistics(snapshots, currentDevices = 0, changes = 0) {
    const rows = snapshotRows(snapshots);
    const counts = rows.map((item) => item.count);
    const average = counts.length ? Math.round(counts.reduce((total, value) => total + value, 0) / counts.length) : 0;
    return barHtml([
      { label: "Финальных выгрузок", value: rows.length },
      { label: "Устройств в последней", value: rows.at(-1)?.count || Number(currentDevices || 0) },
      { label: "Максимум устройств", value: counts.length ? Math.max(...counts) : Number(currentDevices || 0) },
      { label: "Среднее по выгрузкам", value: average },
      { label: "Изменений", value: Number(changes || 0) },
    ]);
  }

  function renderTemporal(snapshots, limit = 24) {
    const rows = snapshotRows(snapshots).slice(-Math.max(1, Number(limit) || 24));
    return barHtml(rows.map((item) => ({ label: `${item.date.slice(0, 10) || "Без даты"} · ${item.name}`, value: item.count })), "Сохранённых выгрузок пока нет.");
  }

  function csvCell(value) {
    const source = String(value ?? "");
    return /[",\r\n;]/.test(source) ? `"${source.replaceAll('"', '""')}"` : source;
  }

  function clustersCsv(payload) {
    const fields = payload?.clusters?.fields || [];
    const lines = [[...fields.map((field) => fieldLabels[field] || field), "Устройств"]];
    for (const cluster of payload?.clusters?.items || []) {
      lines.push([...fields.map((field) => cluster.fields?.[field] || ""), cluster.count || 0]);
    }
    return "\uFEFF" + lines.map((row) => row.map(csvCell).join(";")).join("\r\n");
  }

  function topologyDocument(payload) {
    const summary = payload?.topology?.summary || {};
    const sections = (payload?.topology?.nodes || []).map((node) => {
      const rows = node.ports.map((port) => `<tr><td>${escapeHtml(port.port)}</td><td>${Number(port.deviceCount || 0)}</td><td>${escapeHtml(port.sampleMacs.join(", "))}</td></tr>`).join("");
      return `<section><h2>${escapeHtml(node.switchIp)}</h2><p>Устройств: ${Number(node.deviceCount || 0)} · Помещения: ${escapeHtml(node.rooms.join(", ") || "-")}</p><table><thead><tr><th>Порт</th><th>Устройств</th><th>Примеры MAC</th></tr></thead><tbody>${rows}</tbody></table></section>`;
    }).join("");
    return `<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>MAC Analyzer: топология</title><style>body{font:14px Arial;margin:32px;color:#172033}table{border-collapse:collapse;width:100%;margin:12px 0 28px}th,td{border:1px solid #cbd5e1;padding:8px;text-align:left}th{background:#eef2f7}h1,h2{color:#0f766e}</style></head><body><h1>Топология MAC Analyzer</h1><p>Коммутаторов: ${Number(summary.switches || 0)} · портов: ${Number(summary.ports || 0)} · связанных устройств: ${Number(summary.linkedDevices || 0)} · без коммутатора: ${Number(summary.unassignedDevices || 0)}</p>${sections || "<p>Нет данных топологии.</p>"}</body></html>`;
  }

  function chartsSvg(payload) {
    const charts = [
      ["Производители", payload?.charts?.vendors || []],
      ["Модели", payload?.charts?.models || []],
      ["Помещения", payload?.charts?.rooms || []],
      ["Коммутаторы", payload?.charts?.switches || []],
    ];
    const width = 1_200;
    const sectionHeight = 280;
    const height = 90 + charts.length * sectionHeight;
    const parts = [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
      '<rect width="100%" height="100%" fill="#ffffff"/>',
      '<text x="32" y="44" font-family="Arial" font-size="26" font-weight="700" fill="#172033">MAC Analyzer: аналитика</text>',
    ];
    let y = 90;
    for (const [title, items] of charts) {
      const rows = items.slice(0, 8);
      const max = Math.max(1, ...rows.map((item) => Number(item.value || 0)));
      parts.push(`<text x="32" y="${y}" font-family="Arial" font-size="19" font-weight="700" fill="#0f766e">${escapeXml(title)}</text>`);
      let rowY = y + 18;
      for (const item of rows) {
        const value = Number(item.value || 0);
        const barWidth = Math.round(720 * value / max);
        parts.push(`<text x="32" y="${rowY + 17}" font-family="Arial" font-size="13" fill="#334155">${escapeXml(item.label)}</text>`);
        parts.push(`<rect x="330" y="${rowY}" width="${barWidth}" height="20" rx="3" fill="#0f766e"/>`);
        parts.push(`<text x="${340 + barWidth}" y="${rowY + 16}" font-family="Arial" font-size="13" fill="#172033">${value}</text>`);
        rowY += 27;
      }
      y += sectionHeight;
    }
    parts.push("</svg>");
    return parts.join("");
  }

  window.MacAnalyzerLocalAnalytics = Object.freeze({
    createCollector,
    createRoomSwitchIpAnomalyCollector,
    build,
    analyzeRoomSwitchIpAnomalies,
    barHtml,
    renderOverview,
    renderClusters,
    renderTopology,
    renderStatistics,
    renderTemporal,
    clustersCsv,
    topologyDocument,
    chartsSvg,
    snapshotRows,
  });
  document.documentElement.dataset.localAnalytics = "ready";
})();

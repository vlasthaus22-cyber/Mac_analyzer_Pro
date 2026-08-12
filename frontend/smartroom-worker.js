(() => {
  "use strict";

  const source = `
    const sessions = new Map();
    const text = value => String(value ?? '').trim();
    const mac = value => text(value).toUpperCase().replace(/[^0-9A-F]/g, '').slice(0, 12);
    const ipVersion = value => { const candidate = text(value).replace(/^\\[|\\]$/g, '').split('%')[0]; if (/^\\d{1,3}(?:\\.\\d{1,3}){3}$/.test(candidate) && candidate.split('.').every(part => Number(part) >= 0 && Number(part) <= 255)) return 4; if (!candidate.includes(':') || !/^[0-9a-f:]+$/i.test(candidate) || (candidate.match(/::/g) || []).length > 1) return 0; const sides = candidate.split('::'), groups = sides.flatMap(side => side ? side.split(':') : []).filter(Boolean); if (!groups.every(group => /^[0-9a-f]{1,4}$/i.test(group))) return 0; return sides.length === 2 ? (groups.length < 8 ? 6 : 0) : (groups.length === 8 ? 6 : 0); };
    const ips = value => Array.from(new Set((Array.isArray(value) ? value : text(value).split(/[;,|\\s]+/)).map(text).filter(ipVersion)));
    const utc = value => { const milliseconds = Date.parse(text(value)); return Number.isFinite(milliseconds) ? new Date(milliseconds).toISOString() : ''; };
    const city = row => { const explicit = text(row.city || row.city_name || row.location_city || row.City); if (explicit) return explicit; const address = text(row.address || row.physicalAddress), match = address.match(/^(?:г\\.?\\s*)?([^,]+),/i); return text(match?.[1]); };
    const compact = row => ({
      mac: mac(row.mac || row.macFormatted || row.physical_address),
      smartroomId: text(row.smartroomId || row.smartroom_id || row.Smartroom_ID),
      room: text(row.room || row.room_name || row.Room), city: city(row), address: text(row.address || row.physicalAddress),
      switchIp: text(row.switchIp || row.switch_ip || row.ip_switch), switchPort: text(row.switchPort || row.switch_port || row.port),
      ip: text(row.ip || row.deviceIp || row.device_ip), deviceId: text(row.deviceId || row.device_id), vendor: text(row.vendor || row.manufacturer), model: text(row.model),
      possibleIps: ips(row.Possible_IPs || row.possible_ips || row.possibleIps)
    });
    const key = row => row.smartroomId || ('MAC:' + row.mac);
    function begin(id, options) { sessions.set(id, { options: options || {}, snapshots: [], current: new Map(), previous: new Map(), rooms: new Map(), macs: new Map(), ipHistory: [], daily: new Map(), pending: null, skipped: 0 }); }
    function beginSnapshot(id, meta) { const s = sessions.get(id); if (!s) throw new Error('Worker session not found'); s.pending = { meta: meta || {}, next: new Map(), byRoom: new Map() }; }
    function ingest(id, rows) {
      const s = sessions.get(id); if (!s) throw new Error('Worker session not found');
      if (!s.pending) throw new Error('Worker snapshot not started');
      for (const raw of rows || []) {
        const row = compact(raw);
        if (!row.smartroomId) {
          s.skipped += 1;
          continue;
        }
        const identity = row.smartroomId + '|' + row.mac;
        s.pending.next.set(identity, row);
        const roomKey = key(row); if (!s.pending.byRoom.has(roomKey)) s.pending.byRoom.set(roomKey, []); s.pending.byRoom.get(roomKey).push(row);
      }
    }
    function endSnapshot(id) {
      const s = sessions.get(id); if (!s?.pending) throw new Error('Worker snapshot not started');
      const meta = s.pending.meta, next = s.pending.next, date = utc(meta.createdAt || meta.date);
      for (const roomKey of s.rooms.keys()) if (!s.pending.byRoom.has(roomKey)) s.pending.byRoom.set(roomKey, []);
      for (const [roomKey, devices] of s.pending.byRoom) { if (!s.rooms.has(roomKey)) s.rooms.set(roomKey, []); s.rooms.get(roomKey).push({ date, name: meta.name || '', devices }); }
      for (const row of next.values()) if (row.mac) { if (!s.macs.has(row.mac)) s.macs.set(row.mac, []); s.macs.get(row.mac).push({ date, ...row }); }
      let added = 0, removed = 0, changed = 0;
      for (const [identity, row] of next) {
        const before = s.current.get(identity); if (!before) { added += 1; continue; }
        if (before.switchIp && row.switchIp && before.switchIp !== row.switchIp) {
          changed += 1;
          const overlay = s.options.ddioOverlay?.[row.mac] || s.options.ddioOverlay?.['device-id:' + row.deviceId.toLowerCase()] || {};
          s.ipHistory.push({ date, smartroomId: row.smartroomId, room: row.room, mac: row.mac, previousIp: before.switchIp, currentIp: row.switchIp, possibleIps: Array.from(new Set([...row.possibleIps, ...ips(overlay.possibleIps), text(overlay.ip)].filter(Boolean))) });
        }
      }
      for (const identity of s.current.keys()) if (!next.has(identity)) removed += 1;
      const day = date.slice(0, 10) || 'Без даты'; const bucket = s.daily.get(day) || { date: day, changes: 0, added: 0, removed: 0, total: 0 };
      bucket.changes += changed; bucket.added += added; bucket.removed += removed; bucket.total = next.size; s.daily.set(day, bucket);
      s.previous = s.current; s.current = next; s.snapshots.push({ date, name: meta.name || '', total: next.size });
      s.pending = null;
    }
    function finish(id) {
      const s = sessions.get(id); if (!s) throw new Error('Worker session not found');
      const rooms = [];
      for (const [roomKey, events] of s.rooms) {
        const latest = events.at(-1) || { devices: [] }; const prior = events.at(-2) || { devices: [] };
        const latestMacs = new Set(latest.devices.map(item => item.mac).filter(Boolean));
        const missing = prior.devices.filter(item => item.mac && !latestMacs.has(item.mac));
        rooms.push({ smartroomId: latest.devices[0]?.smartroomId || prior.devices[0]?.smartroomId || roomKey.replace(/^MAC:/, ''), room: latest.devices[0]?.room || prior.devices[0]?.room || '', city: latest.devices[0]?.city || prior.devices[0]?.city || '', address: latest.devices[0]?.address || prior.devices[0]?.address || '', devices: latest.devices, missing, history: events });
      }
      rooms.sort((a,b) => a.smartroomId.localeCompare(b.smartroomId, 'ru', { numeric: true }));
      const result = { rooms, ipHistory: s.ipHistory, macTimelines: Object.fromEntries(s.macs), charts: Array.from(s.daily.values()).sort((a,b) => a.date.localeCompare(b.date)), snapshots: s.snapshots, skipped: s.skipped };
      sessions.delete(id); return result;
    }
    self.onmessage = event => { const { requestId, action, sessionId, meta, rows, options } = event.data || {}; try { let value = true; if (action === 'begin') begin(sessionId, options); else if (action === 'beginSnapshot') beginSnapshot(sessionId, meta || {}); else if (action === 'ingest') ingest(sessionId, rows || []); else if (action === 'endSnapshot') endSnapshot(sessionId); else if (action === 'finish') value = finish(sessionId); self.postMessage({ requestId, value }); } catch (error) { self.postMessage({ requestId, error: error.message || String(error) }); } };
  `;

  let worker = null;
  let sequence = 0;
  const pending = new Map();

  function getWorker() {
    if (worker) return worker;
    worker = new Worker(URL.createObjectURL(new Blob([source], { type: "text/javascript" })));
    worker.onmessage = ({ data }) => {
      const waiter = pending.get(data.requestId);
      if (!waiter) return;
      pending.delete(data.requestId);
      if (data.error) waiter.reject(new Error(data.error)); else waiter.resolve(data.value);
    };
    return worker;
  }

  function request(action, payload = {}) {
    const requestId = ++sequence;
    return new Promise((resolve, reject) => {
      pending.set(requestId, { resolve, reject });
      getWorker().postMessage({ requestId, action, ...payload });
    });
  }

  async function build(snapshots, options = {}) {
    const sessionId = crypto.randomUUID();
    await request("begin", { sessionId, options: { ddioOverlay: options.ddioOverlay || {} } });
    const ordered = Array.from(snapshots || []).sort((a, b) => {
      const left = Date.parse(a.createdAt || a.date || ""), right = Date.parse(b.createdAt || b.date || "");
      return (Number.isFinite(left) ? left : Number.MAX_SAFE_INTEGER) - (Number.isFinite(right) ? right : Number.MAX_SAFE_INTEGER);
    });
    for (const snapshot of ordered) {
      await request("beginSnapshot", { sessionId, meta: snapshot });
      let streamed = false;
      if (snapshot.browserStored && typeof options.streamSnapshot === "function") {
        await options.streamSnapshot(snapshot, async (kind, rows) => {
          if (kind !== "device" || !rows?.length) return;
          streamed = true;
          await request("ingest", { sessionId, rows });
        });
      }
      if (!streamed) {
        let loaded = snapshot;
        if ((!snapshot.devices?.length) && typeof options.loadSnapshot === "function") loaded = await options.loadSnapshot(snapshot) || snapshot;
        const rows = Array.isArray(loaded.devices) ? loaded.devices : [];
        for (let offset = 0; offset < rows.length; offset += 1000) {
          await request("ingest", { sessionId, rows: rows.slice(offset, offset + 1000) });
        }
      }
      await request("endSnapshot", { sessionId });
    }
    return request("finish", { sessionId });
  }

  window.MacAnalyzerSmartroomWorker = Object.freeze({ build });
})();

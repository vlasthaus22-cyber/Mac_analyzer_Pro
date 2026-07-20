import html
from datetime import datetime
from typing import Any


def _text(value: Any, fallback: str = "") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def build_topology(devices: list[dict[str, Any]]) -> dict[str, Any]:
    switches: dict[str, dict[str, Any]] = {}
    unassigned: list[dict[str, Any]] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        switch_ip = _text(device.get("switchIp") or device.get("switch_ip"))
        port = _text(device.get("switchPort") or device.get("switch_port"))
        node = {
            "mac": _text(device.get("mac") or device.get("macFormatted")),
            "macFormatted": _text(device.get("macFormatted") or device.get("mac")),
            "vendor": _text(device.get("vendor"), "Unknown"),
            "model": _text(device.get("model")),
            "ip": _text(device.get("ip")),
            "room": _text(device.get("room")),
            "address": _text(device.get("address")),
            "port": port,
        }
        if not switch_ip:
            unassigned.append(node)
            continue
        switch = switches.setdefault(switch_ip, {
            "id": switch_ip,
            "switchIp": switch_ip,
            "deviceCount": 0,
            "rooms": set(),
            "ports": {},
            "devices": [],
        })
        switch["deviceCount"] += 1
        if node["room"]:
            switch["rooms"].add(node["room"])
        port_key = port or "unknown"
        port_entry = switch["ports"].setdefault(port_key, {"port": port or "Не указан", "deviceCount": 0, "devices": []})
        port_entry["deviceCount"] += 1
        port_entry["devices"].append(node)
        switch["devices"].append(node)

    nodes = []
    links = []
    for switch in sorted(switches.values(), key=lambda item: (-item["deviceCount"], item["switchIp"])):
        ports = sorted(switch["ports"].values(), key=lambda item: (item["port"] == "Не указан", item["port"]))
        switch_node = {
            **switch,
            "rooms": sorted(switch["rooms"]),
            "ports": ports,
            "portCount": len(ports),
        }
        nodes.append(switch_node)
        for port in ports:
            for device in port["devices"]:
                links.append({
                    "switchIp": switch["switchIp"],
                    "port": port["port"],
                    "mac": device["mac"],
                    "ip": device["ip"],
                    "room": device["room"],
                })

    return {
        "summary": {
            "switches": len(nodes),
            "ports": sum(node["portCount"] for node in nodes),
            "linkedDevices": sum(node["deviceCount"] for node in nodes),
            "unassignedDevices": len(unassigned),
        },
        "nodes": nodes,
        "links": links,
        "unassigned": unassigned,
    }


def export_topology_html(topology: dict[str, Any]) -> dict[str, str]:
    node_sections = []
    for node in topology.get("nodes", []):
        port_rows = []
        for port in node.get("ports", []):
            devices = ", ".join(
                filter(None, [device.get("macFormatted") or device.get("mac") for device in port.get("devices", [])])
            )
            port_rows.append(
                "<tr>"
                f"<td>{html.escape(str(port.get('port', '')))}</td>"
                f"<td>{html.escape(str(port.get('deviceCount', 0)))}</td>"
                f"<td>{html.escape(devices)}</td>"
                "</tr>"
            )
        node_sections.append(
            f"<h2>{html.escape(str(node.get('switchIp', 'Switch')))}</h2>"
            f"<p>Devices: {html.escape(str(node.get('deviceCount', 0)))} · Rooms: {html.escape(', '.join(node.get('rooms', [])) or '-')}</p>"
            "<table><thead><tr><th>Port</th><th>Devices</th><th>MAC</th></tr></thead>"
            f"<tbody>{''.join(port_rows)}</tbody></table>"
        )
    summary = topology.get("summary", {})
    content = (
        '<!doctype html><html><head><meta charset="utf-8"><title>MAC Analyzer Topology</title>'
        "<style>body{font:14px Arial;margin:32px}table{border-collapse:collapse;margin:12px 0 24px;width:100%}"
        "td,th{border:1px solid #bbb;padding:7px;text-align:left}th{background:#eee}</style></head><body>"
        f"<h1>MAC Analyzer Topology</h1><p>Created: {html.escape(datetime.utcnow().isoformat(timespec='seconds'))}Z</p>"
        f"<p>Switches: {summary.get('switches', 0)} · Ports: {summary.get('ports', 0)} · Linked devices: {summary.get('linkedDevices', 0)} · Unassigned: {summary.get('unassignedDevices', 0)}</p>"
        f"{''.join(node_sections)}</body></html>"
    )
    return {"filename": "mac-topology.html", "mimeType": "text/html", "content": content}

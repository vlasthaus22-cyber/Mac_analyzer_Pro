import csv
import io
from typing import Any


DEFAULT_FIELDS = ["vendor", "room", "switchIp"]
FIELD_TITLES = {
    "vendor": "Производитель",
    "model": "Модель",
    "room": "Помещение",
    "switchIp": "Коммутатор",
    "switchPort": "Порт",
    "address": "Адрес",
}


def _text(value: Any, fallback: str = "") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def _field_value(device: dict[str, Any], field: str) -> str:
    if field == "switchIp":
        return _text(device.get("switchIp") or device.get("switch_ip"), "Без коммутатора")
    if field == "switchPort":
        return _text(device.get("switchPort") or device.get("switch_port"), "Без порта")
    return _text(device.get(field), {
        "vendor": "Unknown",
        "model": "Не определено",
        "room": "Без помещения",
        "address": "Без адреса",
    }.get(field, "Не указано"))


def build_clusters(devices: list[dict[str, Any]], fields: list[str] | None = None, min_size: int = 1) -> dict[str, Any]:
    selected_fields = [field for field in (fields or DEFAULT_FIELDS) if field]
    if not selected_fields:
        selected_fields = DEFAULT_FIELDS
    threshold = max(1, int(min_size or 1))
    buckets: dict[str, dict[str, Any]] = {}
    for device in devices:
        if not isinstance(device, dict):
            continue
        values = {field: _field_value(device, field) for field in selected_fields}
        key = " · ".join(values[field] for field in selected_fields)
        cluster = buckets.setdefault(key, {
            "id": key,
            "label": key,
            "fields": values,
            "count": 0,
            "uniqueMacs": set(),
            "vendors": set(),
            "rooms": set(),
            "switches": set(),
            "devices": [],
        })
        mac = _text(device.get("mac") or device.get("macFormatted"))
        cluster["count"] += 1
        if mac:
            cluster["uniqueMacs"].add(mac)
        cluster["vendors"].add(_field_value(device, "vendor"))
        cluster["rooms"].add(_field_value(device, "room"))
        cluster["switches"].add(_field_value(device, "switchIp"))
        cluster["devices"].append({
            "mac": mac,
            "macFormatted": _text(device.get("macFormatted") or mac),
            "vendor": _text(device.get("vendor"), "Unknown"),
            "model": _text(device.get("model")),
            "ip": _text(device.get("ip")),
            "room": _text(device.get("room")),
            "switchIp": _text(device.get("switchIp") or device.get("switch_ip")),
            "switchPort": _text(device.get("switchPort") or device.get("switch_port")),
        })

    clusters = []
    for cluster in buckets.values():
        if cluster["count"] < threshold:
            continue
        clusters.append({
            "id": cluster["id"],
            "label": cluster["label"],
            "fields": cluster["fields"],
            "count": cluster["count"],
            "uniqueMacs": len(cluster["uniqueMacs"]),
            "vendors": sorted(cluster["vendors"]),
            "rooms": sorted(cluster["rooms"]),
            "switches": sorted(cluster["switches"]),
            "devices": cluster["devices"],
        })
    clusters.sort(key=lambda item: (-item["count"], item["label"]))
    return {
        "fields": selected_fields,
        "summary": {
            "clusters": len(clusters),
            "devices": sum(item["count"] for item in clusters),
            "largestCluster": clusters[0]["count"] if clusters else 0,
        },
        "clusters": clusters,
    }


def export_clusters_csv(payload: dict[str, Any]) -> dict[str, str]:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Cluster", "Devices", "Unique MAC", "Vendors", "Rooms", "Switches"])
    for cluster in payload.get("clusters", []):
        writer.writerow([
            cluster.get("label", ""),
            cluster.get("count", 0),
            cluster.get("uniqueMacs", 0),
            ", ".join(cluster.get("vendors", [])),
            ", ".join(cluster.get("rooms", [])),
            ", ".join(cluster.get("switches", [])),
        ])
    return {"filename": "mac-clusters.csv", "mimeType": "text/csv", "content": output.getvalue()}

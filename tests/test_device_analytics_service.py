from device_analytics_service import build_device_analytics, build_model_analytics, export_device_analytics_html


DEVICES = [
    {"mac": "AABBCC000001", "macFormatted": "AA:BB:CC:00:00:01", "vendor": "Cisco", "vendorSource": "OUI 3 bytes", "model": "Catalyst", "model_source": "MAC5 history", "matchDetails": "Matched by longest prefix", "ip": "10.0.0.1", "address": "Main", "room": "101", "switchIp": "10.1.1.1", "switchPort": "Gi1/0/1"},
    {"mac": "AABBCC000002", "macFormatted": "AA:BB:CC:00:00:02", "vendor": "Apple", "model": "MacBook", "room": "202", "switchIp": "10.1.1.2"},
]

SNAPSHOTS = [
    {"id": "s1", "name": "First", "source": "first.csv", "createdAt": "2026-01-01T10:00:00Z", "devices": [DEVICES[0]]},
    {"id": "s2", "name": "Second", "source": "second.csv", "createdAt": "2026-01-02T10:00:00Z", "devices": DEVICES},
]

HISTORY = [{"mac": "AABBCC000001", "vendor": "Cisco", "model": "Catalyst", "ip": "10.0.0.1", "address": "Main", "room": "101", "source": r"C:\imports\scan.xlsx", "recorded_at": "2026-01-03T10:00:00Z"}]
MOVEMENTS = [{"mac": "AABBCC000001", "field_name": "room", "from_value": "100", "to_value": "101", "source": r"C:\imports\scan.xlsx", "changed_at": "2026-01-02T09:00:00Z"}]
MODELS = {"AABBCC00": "Catalyst", "AABBCC0000": "Catalyst", "AABBCC01": "Other"}
MODEL_SOURCES = {"AABBCC00": "builtin", "AABBCC0000": "learned", "AABBCC01": "custom"}


def test_device_and_model_analytics():
    payload = build_device_analytics("AA:BB:CC:00:00:01", DEVICES, SNAPSHOTS, HISTORY, MOVEMENTS, MODELS)

    assert payload["current"]["vendor"] == "Cisco"
    assert payload["current"]["model"] == "Catalyst"
    assert payload["macFormatted"] == "AA:BB:CC:00:00:01"
    assert payload["metrics"]["appearances"] == 2
    assert payload["metrics"]["sources"] == 2
    assert payload["metrics"]["historyRecords"] == 1
    assert payload["metrics"]["movements"] == 1
    assert payload["metrics"]["modelPrefixes"] == 2
    assert "<span>Снимков</span><strong>2</strong>" in payload["metricsHtml"]
    assert "<span>Производитель</span><strong>Cisco</strong>" in payload["fieldsHtml"]
    assert "<span>Префиксы модели</span>" in payload["fieldsHtml"]
    assert payload["modelPrefixes"][0]["matchesDevice"] is True
    assert "=== ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ОБ УСТРОЙСТВЕ ===" in payload["detailedReportText"]
    assert "MAC-адрес: AA:BB:CC:00:00:01" in payload["detailedReportText"]
    assert "Коммутатор: 10.1.1.1" in payload["detailedReportText"]
    assert "Порт: Gi1/0/1" in payload["detailedReportText"]
    assert "Производитель: OUI 3 bytes" in payload["detailedReportText"]
    assert "Модель: MAC5 history" in payload["detailedReportText"]
    assert "Примечания: Matched by longest prefix" in payload["detailedReportText"]
    assert [row["field"] for row in payload["timelineRows"]] == ["history", "snapshot", "room", "snapshot"]
    assert payload["timelineRows"][1]["source"] == "Second"
    assert payload["timelineRows"][2]["before"] == "100"
    assert payload["timelineRows"][2]["after"] == "101"
    assert "03.01.2026, 10:00:00" in payload["historyRowsHtml"]
    assert "<td>snapshot</td>" in payload["historyRowsHtml"]
    assert payload["emptyHistoryRowsHtml"].startswith("<tr>")
    assert payload["historyStats"] == {
        "totalAppearances": 1,
        "firstSeen": "2026-01-03T10:00:00Z",
        "lastSeen": "2026-01-03T10:00:00Z",
        "uniqueFiles": 1,
        "totalMovements": 1,
    }
    assert "Всего появлений" in payload["macHistoryStatsHtml"]
    assert "03.01.2026, 10:00:00" in payload["historyRecordsRowsHtml"]
    assert "scan.xlsx" in payload["historyRecordsRowsHtml"]
    assert "<td>Cisco</td><td>Catalyst</td><td>10.0.0.1</td><td>Main</td><td>101</td>" in payload["historyRecordsRowsHtml"]
    assert "<td>room</td><td>100</td><td>101</td><td>scan.xlsx</td>" in payload["movementRowsHtml"]
    assert 'colspan="7"' in payload["emptyHistoryRecordsRowsHtml"]
    assert 'colspan="5"' in payload["emptyMovementRowsHtml"]

    model = build_model_analytics("catalyst", MODELS, DEVICES, MODEL_SOURCES)
    assert model["metrics"]["prefixes"] == 2
    assert model["metrics"]["matchedDevices"] == 2
    assert '<strong>AABBCC00</strong>' in model["prefixRowsHtml"]
    assert '<span>AA:BB:CC:00:00:00</span>' in model["prefixRowsHtml"]
    assert model["prefixes"][0]["formattedPrefix"] == "AA:BB:CC:00"
    assert model["prefixes"][0]["sourceLabel"] == "Встроенная база"
    assert "Обучение по истории" in model["tableRowsHtml"]
    assert "<td>AA:BB:CC:00:00</td><td>Catalyst</td>" in model["tableRowsHtml"]
    assert "2 найдено в текущем наборе" in model["summaryRowHtml"]
    assert model["dialogRowsHtml"].endswith(model["summaryRowHtml"])

    family = build_model_analytics("cisco", {"00112233": "Cisco Catalyst 2960", "00112244": "Cisco Catalyst 3560"}, [], {"00112233": "builtin", "00112244": "builtin"})
    assert family["metrics"]["prefixes"] == 2
    assert "00:11:22:33" in family["tableRowsHtml"]
    assert "Встроенная база" in family["tableRowsHtml"]

    empty_model = build_model_analytics("missing", MODELS)
    assert empty_model["tableRowsHtml"] == '<tr><td>Нет данных</td><td></td><td></td></tr>'

    exported = export_device_analytics_html(payload)
    assert exported["mimeType"] == "text/html"
    assert "MAC Device Analytics" in exported["content"]
    assert "AA:BB:CC:00:00:01" in exported["content"]
    assert "Detailed device report" in exported["content"]
    assert "Matched by longest prefix" in exported["content"]


if __name__ == "__main__":
    test_device_and_model_analytics()
    print("device analytics service test passed")

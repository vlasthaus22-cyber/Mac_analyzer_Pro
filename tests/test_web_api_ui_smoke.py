import base64
import json
import threading
import urllib.error
import urllib.request
from io import BytesIO
from http.server import ThreadingHTTPServer
from pathlib import Path

from openpyxl import Workbook
from server import AppHandler, WORKSPACE_FILE_CACHE, db_connection, init_database


SNAPSHOT_ID = "ui-api-smoke-snapshot"
VENDOR_MAPPING_KEY = "A1B2C3"
VENDOR_MAPPING_KEY_4BYTE = "A1B2C300"
VENDOR_MAPPING_KEY_5BYTE = "A1B2C30000"
MODEL_MAPPING_KEY = "A1B2C300"
LEARN_SOURCE = "ui-api-smoke-learn"
LEARN_VENDOR_PREFIX_3BYTE = "C0FFEE"
LEARN_VENDOR_PREFIX_4BYTE = "C0FFEE11"
LEARN_VENDOR_PREFIX_5BYTE = "C0FFEE1122"
COLUMN_VIEW = "ui-api-smoke-columns"
AUTOSAVE_SLOT = "ui-api-smoke"
CACHE_TOKENS = set()
EXTERNAL_SNAPSHOT_IDS = set()


def cleanup():
    while CACHE_TOKENS:
        WORKSPACE_FILE_CACHE.discard(CACHE_TOKENS.pop())
    with db_connection() as conn:
        while EXTERNAL_SNAPSHOT_IDS:
            conn.execute("DELETE FROM snapshots WHERE id = ?", (EXTERNAL_SNAPSHOT_IDS.pop(),))
        conn.execute("DELETE FROM snapshots WHERE id = ?", (SNAPSHOT_ID,))
        conn.execute("DELETE FROM mac_history WHERE source IN (?, ?)", ("ui-api-smoke.csv", "ui-api-smoke"))
        conn.execute("DELETE FROM mac_history WHERE source = ?", (LEARN_SOURCE,))
        conn.execute("DELETE FROM mac_movements WHERE source IN (?, ?)", ("ui-api-smoke.csv", "ui-api-smoke"))
        conn.execute("DELETE FROM mac_movements WHERE source = ?", (LEARN_SOURCE,))
        conn.execute("DELETE FROM vendor_model_history WHERE source IN (?, ?)", ("ui-api-smoke.csv", "ui-api-smoke"))
        conn.execute("DELETE FROM vendor_model_history WHERE source = ?", (LEARN_SOURCE,))
        conn.execute("DELETE FROM snapshots WHERE source IN (?, ?)", ("ui-api-smoke.csv", "ui-api-smoke"))
        conn.execute("DELETE FROM performance_metrics WHERE details LIKE 'source=ui-api-smoke%'")
        conn.execute("DELETE FROM data_quality_reports WHERE source = ?", ("ui-api-smoke-quality",))
        conn.execute("DELETE FROM engineering_sessions")
        conn.execute("DELETE FROM ip_address_mappings WHERE switch_ip = ?", ("203.0.113.77",))
        conn.execute("DELETE FROM app_autosaves WHERE slot = ?", (AUTOSAVE_SLOT,))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", (VENDOR_MAPPING_KEY,))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", (VENDOR_MAPPING_KEY_4BYTE,))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", (VENDOR_MAPPING_KEY_5BYTE,))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", (LEARN_VENDOR_PREFIX_3BYTE,))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", (LEARN_VENDOR_PREFIX_4BYTE,))
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", (LEARN_VENDOR_PREFIX_5BYTE,))
        conn.execute("DELETE FROM model_mappings WHERE prefix = ?", (MODEL_MAPPING_KEY,))
        conn.execute("DELETE FROM model_mappings WHERE prefix = ?", (LEARN_VENDOR_PREFIX_3BYTE,))
        conn.execute("DELETE FROM model_mappings WHERE prefix = ?", (LEARN_VENDOR_PREFIX_4BYTE,))
        conn.execute("DELETE FROM model_mappings WHERE prefix = ?", (LEARN_VENDOR_PREFIX_5BYTE,))
        conn.execute("DELETE FROM column_preferences WHERE view_name = ?", (COLUMN_VIEW,))
        conn.execute("DELETE FROM notification_settings WHERE channel = ?", ("telegram",))
        conn.execute("DELETE FROM app_settings WHERE key IN ('theme', 'oui_format', 'external_api', 'dashboard', 'vendor_detector', 'history_enrichment', 'enhanced_history_columns')")


class SmokeServer:
    def __enter__(self):
        init_database()
        cleanup()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        cleanup()


def request_json(base_url, method, path, payload=None, token=""):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body) if body else {}
            if path in {"/api/files/import", "/api/files/import-binary"} and result.get("fileToken"):
                CACHE_TOKENS.add(result["fileToken"])
            return response.status, result
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        return error.code, json.loads(body) if body else {}


def csv_payload():
    content = "MAC Address,Vendor,Model,IP Address,Room\nAA:BB:CC:00:00:09,SmokeVendor,SmokeModel,10.9.0.1,909\n"
    return base64.b64encode(content.encode("utf-8")).decode("ascii")


def xlsx_payload():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Devices"
    sheet.append(["MAC Address", "Vendor", "Model"])
    sheet.append(["AA:BB:CC:00:00:13", "XlsxVendor", "XlsxModel"])
    buffer = BytesIO()
    workbook.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_rest_api_and_ui_controls_smoke():
    html = Path("index.html").read_text(encoding="utf-8")
    for selector in (
        'data-view="single"',
        'id="singleFileAnalyzeButton"',
        'id="legacyImportButton"',
        'id="databaseMaintenanceButton"',
        'id="qualityAnalysisButton"',
        'id="analyticsReportPreview"',
        'id="dashboardStatusFilter"',
        'id="dashboardTotalMetric"',
        'id="dashboardChangedMetric"',
        'id="dashboardMissingMetric"',
        'id="dashboardUnchangedMetric"',
        'id="dashboardDynamicsChart"',
        'id="dashboardFieldChangesChart"',
        'id="dashboardMissingChart"',
        'id="dashboardSettingsDialog"',
        'id="dashboardAutoRefresh"',
        'id="dashboardRefreshInterval"',
        'id="applyDashboardSettingsButton"',
        'id="dashboardChangeMode"',
        'id="dashboardChangeDateFrom"',
        'id="dashboardChangeDateTo"',
        'id="dashboardBaselineSnapshot"',
        'id="dashboardComparisonSnapshot"',
        'id="dashboardChangesDialog"',
        'id="dashboardCriticalCount"',
        'id="dashboardChangesBody"',
        'id="refreshAnalyticsReportButton"',
        'id="exportAnalyticsReportButton"',
        'id="compareButton"',
        'id="exportCsvButton"',
        'id="parityStatusSummary"',
        'id="refreshParityStatusButton"',
        'id="exportParityReportButton"',
        'id="parityDetailsList"',
        'id="deleteAutosaveButton"',
        'id="timeStatsSummary"',
        'id="timeStatsBody"',
    ):
        assert selector in html

    with SmokeServer() as app:
        status, health = request_json(app.base_url, "GET", "/api/health")
        assert status == 200
        assert health["status"] == "ok"
        assert Path(health["databasePath"]).parent.name == "databases"
        assert Path(health["dataDirectory"]).is_dir()
        assert Path(health["databasePath"]).is_relative_to(Path(health["dataDirectory"]))

        status, storage = request_json(app.base_url, "GET", "/api/storage/structure")
        assert status == 200
        assert Path(storage["layout"]["database"]).parent.name == "databases"
        assert Path(storage["layout"]["legacy"]).name == "legacy"
        assert Path(storage["layout"]["backups"]).name == "backups"

        status, bootstrap = request_json(app.base_url, "GET", "/api/bootstrap")
        assert status == 200
        assert "snapshots" in bootstrap
        assert "columns" in bootstrap
        assert "customColumnMappings" in bootstrap

        status, theme = request_json(app.base_url, "POST", "/api/theme", {"theme": "dark"})
        assert status == 200
        assert theme["theme"] == "dark"
        assert theme["active"]["name"] == "Темная"
        assert [item["key"] for item in theme["themes"]] == ["dark", "light"]

        status, loaded_theme = request_json(app.base_url, "GET", "/api/theme")
        assert status == 200
        assert loaded_theme["theme"] == "dark"
        assert loaded_theme["active"]["background"] == "#1e1e1e"

        status, oui = request_json(app.base_url, "POST", "/api/oui/settings", {"settings": {"length": 5, "style": "dash"}})
        assert status == 200
        assert oui["settings"]["length"] == 5
        assert oui["settings"]["style"] == "dash"

        status, loaded_oui = request_json(app.base_url, "GET", "/api/oui/settings")
        assert status == 200
        assert loaded_oui["settings"]["length"] == 5

        status, detector_settings = request_json(
            app.base_url,
            "POST",
            "/api/vendor-detector/settings",
            {"settings": {"enabled": True, "useOui3": False, "useMac5": True, "useText": True, "useInference": False, "confidenceThreshold": 0.7}},
        )
        assert status == 200
        assert detector_settings["settings"]["useOui3"] is False
        assert detector_settings["settings"]["useMac5"] is True
        assert detector_settings["settings"]["useInference"] is False
        assert detector_settings["settings"]["confidenceThreshold"] == 0.7

        status, loaded_detector_settings = request_json(app.base_url, "GET", "/api/vendor-detector/settings")
        assert status == 200
        assert loaded_detector_settings["settings"]["useOui3"] is False
        status, reset_detector_settings = request_json(app.base_url, "POST", "/api/vendor-detector/settings", {"settings": {}})
        assert status == 200
        assert reset_detector_settings["settings"]["useOui3"] is True

        status, history_enrichment = request_json(
            app.base_url,
            "POST",
            "/api/history-enrichment/settings",
            {"settings": {"enabled": True, "priorityHistory": False, "useOuiMatch": False, "useMac5Match": True}},
        )
        assert status == 200
        assert history_enrichment["settings"]["priorityHistory"] is False
        assert history_enrichment["settings"]["useOuiMatch"] is False
        assert history_enrichment["settings"]["useMac5Match"] is True

        status, loaded_history_enrichment = request_json(app.base_url, "GET", "/api/history-enrichment/settings")
        assert status == 200
        assert loaded_history_enrichment["settings"]["priorityHistory"] is False
        status, reset_history_enrichment = request_json(app.base_url, "POST", "/api/history-enrichment/settings", {"settings": {}})
        assert status == 200
        assert reset_history_enrichment["settings"]["priorityHistory"] is True

        status, imported = request_json(
            app.base_url,
            "POST",
            "/api/files/import",
            {"filename": "ui-api-smoke.csv", "content": csv_payload()},
        )
        assert status == 200
        assert imported["headers"][0] == "MAC Address"
        assert len(imported["rows"]) == 1

        status, imported_xlsx = request_json(app.base_url, "POST", "/api/files/import", {"filename": "ui-api-smoke.xlsx", "content": xlsx_payload()})
        assert status == 200
        assert imported_xlsx["sheet"] == "Devices"
        assert imported_xlsx["headers"] == ["MAC Address", "Vendor", "Model"]
        assert imported_xlsx["rows"] == [["AA:BB:CC:00:00:13", "XlsxVendor", "XlsxModel"]]

        status, xlsx_enrichment = request_json(
            app.base_url,
            "POST",
            "/api/enrichment/run",
            {
                "files": [{
                    "id": "xlsx-file-1",
                    "name": "ui-api-smoke.xlsx",
                    "sheet": imported_xlsx["sheet"],
                    "headers": [{"name": name, "index": index} for index, name in enumerate(imported_xlsx["headers"])],
                    "rows": [imported_xlsx["headers"], *imported_xlsx["rows"]],
                    "mapping": {"mac": 0, "vendor": 1, "model": 2},
                }],
                "fields": {"vendor": True, "model": True, "history": False},
                "source": "ui-api-smoke.xlsx",
                "saveHistory": False,
                "notify": False,
            },
        )
        assert status == 200
        assert xlsx_enrichment["progress"]["valid"] == 1
        assert xlsx_enrichment["devices"][0]["vendor"] == "XlsxVendor"
        assert xlsx_enrichment["devices"][0]["model"] == "XlsxModel"
        assert "progressHtml" in xlsx_enrichment

        json_content = base64.b64encode(json.dumps({"devices": [{"mac": "AABBCC000011", "vendor": "JsonVendor"}]}).encode("utf-8")).decode("ascii")
        status, imported_json = request_json(app.base_url, "POST", "/api/files/import", {"filename": "ui-api-smoke.json", "content": json_content})
        assert status == 200
        assert imported_json["headers"] == ["mac", "vendor"]
        assert imported_json["rows"] == [["AABBCC000011", "JsonVendor"]]

        tsv_content = base64.b64encode("MAC\tVendor\nAA:BB:CC:00:00:12\tTsvVendor\n".encode("utf-8")).decode("ascii")
        status, imported_tsv = request_json(app.base_url, "POST", "/api/files/import", {"filename": "ui-api-smoke.tsv", "content": tsv_content})
        assert status == 200
        assert imported_tsv["headers"] == ["MAC", "Vendor"]
        assert imported_tsv["rows"] == [["AA:BB:CC:00:00:12", "TsvVendor"]]

        cp1251_content = base64.b64encode("MAC;Производитель\nAA:BB:CC:00:00:14;РусскийВендор\n".encode("cp1251")).decode("ascii")
        status, imported_cp1251 = request_json(app.base_url, "POST", "/api/files/import", {"filename": "ui-api-smoke-cp1251.csv", "content": cp1251_content})
        assert status == 200
        assert imported_cp1251["headers"] == ["MAC", "Производитель"]
        assert imported_cp1251["rows"] == [["AA:BB:CC:00:00:14", "РусскийВендор"]]

        empty_content = base64.b64encode(b"").decode("ascii")
        status, empty_import = request_json(app.base_url, "POST", "/api/files/import", {"filename": "empty.csv", "content": empty_content})
        assert status == 400
        assert "Не удалось прочитать файл" in empty_import["error"]

        status, workspace_files = request_json(
            app.base_url,
            "POST",
            "/api/workspace/files",
            {"files": [{"id": "file-1", "name": "ui-api-smoke.csv", "rows": [imported["headers"], *imported["rows"]]}]},
        )
        assert status == 200
        assert 'data-remove-file="file-1"' in workspace_files["fileRowsHtml"]
        assert 'data-file-id="file-1"' in workspace_files["fileRowsHtml"]
        assert "ui-api-smoke.csv" in workspace_files["fileRowsHtml"]
        assert "Файлы пока не добавлены" in workspace_files["emptyFilesHtml"]

        status, mapping_grid = request_json(
            app.base_url,
            "POST",
            "/api/workspace/mapping-grid",
            {
                "file": {
                    "headers": [{"name": name, "index": index} for index, name in enumerate(imported["headers"])],
                    "mapping": {"mac": 0, "vendor": 1},
                }
            },
        )
        assert status == 200
        assert 'data-map="mac"' in mapping_grid["mappingGridHtml"]
        assert '<option value="0" selected>MAC Address</option>' in mapping_grid["mappingGridHtml"]
        assert '<option value="1">Vendor</option>' in mapping_grid["customColumnOptionsHtml"]

        status, single_mapping_grid = request_json(
            app.base_url,
            "POST",
            "/api/workspace/single-mapping-grid",
            {"headers": imported["headers"]},
        )
        assert status == 200
        assert single_mapping_grid["headers"][0]["name"] == "MAC Address"
        assert 'data-single-map="mac"' in single_mapping_grid["singleMappingGridHtml"]
        assert '<option value="0">MAC Address</option>' in single_mapping_grid["singleMappingGridHtml"]

        status, empty_single_mapping_grid = request_json(app.base_url, "POST", "/api/workspace/single-mapping-grid", {"headers": []})
        assert status == 200
        assert "Колонки появятся после выбора файла" in empty_single_mapping_grid["singleMappingGridHtml"]

        status, single_preview = request_json(
            app.base_url,
            "POST",
            "/api/single-file/preview",
            {"headers": imported["headers"], "rows": imported["rows"], "invalid": []},
        )
        assert status == 200
        assert "<th>MAC Address</th>" in single_preview["previewHeadHtml"]
        assert "SmokeVendor" in single_preview["previewBodyHtml"]
        assert "ошибок 0" in single_preview["previewCountText"]

        status, empty_single_preview = request_json(app.base_url, "POST", "/api/single-file/preview", {"headers": [], "rows": [], "invalid": []})
        assert status == 200
        assert "Нет данных" in empty_single_preview["previewBodyHtml"]

        status, detected_columns = request_json(
            app.base_url,
            "POST",
            "/api/columns/detect",
            {
                "headers": imported["headers"],
                "rows": imported["rows"],
                "ai": False,
                "mode": "auto",
            },
        )
        assert status == 200
        assert detected_columns["mapping"]["mac"] == 0
        assert detected_columns["mapping"]["vendor"] == 1
        assert detected_columns["mapping"]["model"] == 2
        assert "detectorHtml" in detected_columns
        assert "Column detector" in detected_columns["detectorHtml"]
        assert len(detected_columns["review"]["fields"]) == 9
        assert detected_columns["review"]["autoMapping"]["mac"] == 0
        assert 'data-conflict-field="mac"' in detected_columns["review"]["rowsHtml"]
        assert 'data-conflict-column="mac"' in detected_columns["review"]["rowsHtml"]
        assert "AA:BB:CC:00:00:09" in detected_columns["review"]["rowsHtml"]

        status, ai_detected_columns = request_json(
            app.base_url,
            "POST",
            "/api/columns/detect",
            {
                "headers": ["Device ID", "Host IP", "Switch IP", "Location", "Device Type"],
                "rows": [["AA:BB:CC:00:00:09", "192.0.2.9", "10.0.0.1", "Rack A", "Catalyst 9200"]],
                "ai": True,
                "mode": "ai",
            },
        )
        assert status == 200
        assert ai_detected_columns["mode"] == "auto+ai"
        assert ai_detected_columns["review"]["autoMapping"]["switchIp"] == 2
        assert ai_detected_columns["review"]["autoMapping"]["model"] == 4
        assert "Catalyst 9200" in ai_detected_columns["review"]["rowsHtml"]

        status, mapping = request_json(
            app.base_url,
            "POST",
            "/api/mapping/summary",
            {
                "headers": imported["headers"],
                "mapping": detected_columns["mapping"],
                "fields": {"vendor": True, "model": True, "ip": True, "history": True},
            },
        )
        assert status == 200
        assert mapping["requiredMissing"] == []
        assert len(mapping["mapped"]) >= 3
        assert "ip" in mapping["enrichment"]["enabled"]
        assert "summaryHtml" in mapping
        assert "Mapping summary" in mapping["summaryHtml"]

        status, single = request_json(
            app.base_url,
            "POST",
            "/api/single-file/analyze",
            {
                "filename": "ui-api-smoke.csv",
                "fileToken": imported["fileToken"],
                "createdAt": "2024-03-04T05:06:07Z",
                "saveHistory": False,
                "saveSnapshot": True,
                "notify": False,
                "compactResult": True,
                "resultPageSize": 25,
            },
        )
        assert status == 200
        assert single["compactResult"] is True
        assert single["resultReference"]["deviceCount"] == 1
        assert single["resultReference"]["snapshotId"] == single["snapshot"]["id"]
        assert single["summary"]["valid"] == 1
        assert single["summary"]["invalid"] == 0
        assert "single-metrics" in single["summaryHtml"]
        assert "detectedColumnsHtml" in single
        assert "previewHeadHtml" in single
        assert "SmokeVendor" in single["previewBodyHtml"]
        assert single["snapshot"]["createdAt"] == "2024-03-04T05:06:07Z"

        devices = single["devices"]
        status, start_progress = request_json(app.base_url, "POST", "/api/enrichment/progress", {"status": "starting"})
        assert status == 200
        assert "bar-fill" in start_progress["progressHtml"]
        assert "15%" in start_progress["progressHtml"]

        status, enrichment = request_json(
            app.base_url,
            "POST",
            "/api/enrichment/run",
            {
                "files": [{
                    "id": "file-1",
                    "name": "ui-api-smoke.csv",
                    "headers": [{"name": name, "index": index} for index, name in enumerate(imported["headers"])],
                    "rows": [imported["headers"], *imported["rows"]],
                    "mapping": {"mac": 0, "vendor": 1, "model": 2},
                }],
                "fields": {"vendor": True, "model": True, "history": False},
                "source": "ui-api-smoke",
                "createdAt": "2024-05-06T07:08:09Z",
                "saveHistory": True,
                "notify": False,
            },
        )
        assert status == 200
        assert enrichment["progress"]["valid"] == 1
        assert "progressHtml" in enrichment
        assert "bar-fill" in enrichment["progressHtml"]
        assert "OK: 1" in enrichment["progressHtml"]
        assert enrichment["snapshot"]["deviceCount"] == 1
        assert enrichment["snapshot"]["createdAt"] == "2024-05-06T07:08:09Z"
        with db_connection() as conn:
            row = conn.execute(
                "SELECT recorded_at FROM mac_history WHERE source = ? ORDER BY id DESC LIMIT 1",
                ("ui-api-smoke",),
            ).fetchone()
        assert row["recorded_at"] == "2024-05-06T07:08:09Z"

        status, analysis = request_json(
            app.base_url,
            "POST",
            "/api/analyze",
            {"devices": devices, "source": "ui-api-smoke", "saveHistory": False, "notify": False},
        )
        assert status == 200
        assert len(analysis["devices"]) == 1

        status, result_header = request_json(
            app.base_url,
            "POST",
            "/api/results/header",
            {"columns": ["macFormatted", "oui", "vendor"], "labels": {"macFormatted": "MAC", "oui": "OUI", "vendor": "Vendor"}},
        )
        assert status == 200
        assert 'data-sort-field="macFormatted"' in result_header["headerHtml"]
        assert "Vendor" in result_header["headerHtml"]
        assert result_header["columnCount"] == 3
        assert 'colspan="3"' in result_header["emptyTableRowsHtml"]

        status, filtered_results = request_json(
            app.base_url,
            "POST",
            "/api/results/filter",
            {
                "devices": devices,
                "invalid": [{"row": 2, "source": "ui-api-smoke.csv", "raw": "not-a-mac"}],
                "filters": {"query": "SmokeModel", "vendor": "SmokeVendor", "validity": "valid", "ouiLength": 4, "ouiStyle": "dash"},
                "columns": ["macFormatted", "oui", "vendor", "model"],
                "labels": {"macFormatted": "MAC", "oui": "OUI", "vendor": "Производитель", "model": "Модель"},
            },
        )
        assert status == 200
        assert filtered_results["summary"]["total"] == 1
        assert filtered_results["summaryText"] == "1 записей"
        assert filtered_results["items"][0]["vendor"] == "SmokeVendor"
        assert filtered_results["items"][0]["oui"] == "AA-BB-CC-00"
        assert filtered_results["items"][0]["valid"] is True
        assert filtered_results["vendors"] == ["SmokeVendor"]
        assert 'data-sort-field="vendor"' in filtered_results["headerHtml"]
        assert "Производитель" in filtered_results["headerHtml"]
        assert 'data-mac="AABBCC000009"' in filtered_results["tableRowsHtml"]
        assert "<td>AA-BB-CC-00</td>" in filtered_results["tableRowsHtml"]
        assert '<option value="SmokeVendor" selected>SmokeVendor</option>' in filtered_results["vendorOptionsHtml"]

        status, invalid_results = request_json(
            app.base_url,
            "POST",
            "/api/results/filter",
            {"devices": devices, "invalid": [{"row": 2, "source": "ui-api-smoke.csv", "raw": "not-a-mac"}], "filters": {"validity": "invalid"}},
        )
        assert status == 200
        assert invalid_results["summary"]["invalid"] == 1
        assert "not-a-mac" in invalid_results["tableRowsHtml"]

        status, history_analysis = request_json(
            app.base_url,
            "POST",
            "/api/analyze",
            {"devices": devices, "source": "ui-api-smoke", "saveHistory": True, "notify": False},
        )
        assert status == 200
        assert len(history_analysis["devices"]) == 1

        status, history_stats = request_json(app.base_url, "GET", "/api/history/statistics?query=SmokeVendor")
        assert status == 200
        assert history_stats["totals"]["records"] >= 1
        assert history_stats["vendors"][0]["name"] == "SmokeVendor"
        assert history_stats["vendors"][0]["unique_macs"] == 1

        status, history_panel = request_json(app.base_url, "GET", "/api/history/panel?query=SmokeVendor")
        assert status == 200
        assert history_panel["historyStats"]["totals"]["records"] >= 1
        assert history_panel["historySearch"]["statistics"]["records"] >= 1
        assert history_panel["summaryTables"]["vendors"][0]["name"] == "SmokeVendor"
        assert "<td>SmokeVendor</td>" in history_panel["summaryTables"]["vendorRowsHtml"]
        assert "<td>SmokeModel</td>" in history_panel["summaryTables"]["modelRowsHtml"]
        assert "Backend history is empty" in history_panel["summaryTables"]["emptyRowsHtml"]
        assert "Records" in history_panel["historySearch"]["summaryHtml"]
        assert "SmokeVendor" in history_panel["historySearch"]["summaryHtml"]
        assert "Uploads" in history_panel["vendorModelHistory"]["summaryHtml"]
        assert "SmokeModel" in history_panel["vendorModelHistory"]["summaryHtml"]
        assert 'data-mac="' in history_panel["historySearch"]["tableRowsHtml"]
        assert "SmokeVendor" in history_panel["historySearch"]["tableRowsHtml"]
        assert "SmokeVendor" in history_panel["vendorModelHistory"]["tableRowsHtml"]
        assert "SmokeModel" in history_panel["vendorModelHistory"]["tableRowsHtml"]

        changed_device = {**devices[0], "model": "SmokeModel Updated"}
        status, changed_history = request_json(
            app.base_url,
            "POST",
            "/api/analyze",
            {"devices": [changed_device], "source": "ui-api-smoke", "saveHistory": True, "notify": False},
        )
        assert status == 200
        assert changed_history["devices"][0]["model"] == "SmokeModel Updated"

        status, movement_history = request_json(
            app.base_url,
            "GET",
            "/api/history/movements?query=SmokeVendor&type=modified&field=model&limit=50",
        )
        assert status == 200
        assert movement_history["count"] == 1
        assert movement_history["groups"] == 1
        assert movement_history["records"][0]["to_value"] == "SmokeModel Updated"
        assert 'data-toggle-movement-group=' in movement_history["rowsHtml"]
        assert 'movement-modified' in movement_history["rowsHtml"]
        assert "Всего изменений" in movement_history["summaryHtml"]

        status, movement_export = request_json(
            app.base_url,
            "GET",
            "/api/history/movements/export?query=SmokeVendor&type=modified&field=model&format=xlsx",
        )
        assert status == 200
        assert movement_export["filename"] == "filtered-history.xlsx"
        assert base64.b64decode(movement_export["content"]).startswith(b"PK")

        status, movement_columns = request_json(
            app.base_url,
            "POST",
            "/api/history/movements/columns",
            {"settings": {"visible": ["mac", "dates", "field", "after"], "widths": {"mac": 205, "after": 315}}},
        )
        assert status == 200
        assert movement_columns["settings"]["visible"] == ["mac", "dates", "field", "after"]
        assert movement_columns["settings"]["widths"]["after"] == 315

        status, loaded_movement_columns = request_json(app.base_url, "GET", "/api/history/movements/columns")
        assert status == 200
        assert loaded_movement_columns["settings"]["widths"]["mac"] == 205
        assert 'data-movement-column-toggle="mac" checked' in loaded_movement_columns["settings"]["controlsHtml"]

        status, vendor_model_stats = request_json(app.base_url, "GET", "/api/vendor-model-history/statistics?query=SmokeVendor")
        assert status == 200
        assert vendor_model_stats["totals"]["records"] >= 1
        assert vendor_model_stats["vendors"][0]["name"] == "SmokeVendor"
        assert vendor_model_stats["models"][0]["name"] == "SmokeModel"

        status, saved_dashboard = request_json(
            app.base_url,
            "POST",
            "/api/dashboard",
            {
                "devices": devices,
                "snapshots": [],
                "settings": {
                    "vendor": "SmokeVendor", "room": "909", "chartLimit": 5, "showUnknown": False,
                    "visibleCards": {"missing": False}, "visibleCharts": {"fields": False},
                    "autoRefresh": False, "refreshInterval": 45,
                },
                "saveSettings": True,
            },
        )
        assert status == 200
        assert saved_dashboard["settings"]["vendor"] == "SmokeVendor"
        assert saved_dashboard["settings"]["room"] == "909"
        assert saved_dashboard["settings"]["chartLimit"] == 5
        assert saved_dashboard["settings"]["showUnknown"] is False
        assert saved_dashboard["settings"]["visibleCards"]["missing"] is False
        assert saved_dashboard["settings"]["visibleCharts"]["fields"] is False
        assert saved_dashboard["settings"]["autoRefresh"] is False
        assert saved_dashboard["settings"]["refreshInterval"] == 45
        assert saved_dashboard["metrics"]["devices"] == 1
        assert saved_dashboard["metrics"]["uniqueMacs"] == 1
        assert saved_dashboard["metrics"]["vendors"] == 1
        assert saved_dashboard["devices"][0]["vendor"] == "SmokeVendor"
        assert saved_dashboard["filters"]["vendors"] == ["SmokeVendor"]
        assert saved_dashboard["filters"]["rooms"] == ["909"]
        assert '<option value="SmokeVendor" selected>SmokeVendor</option>' in saved_dashboard["filterOptionsHtml"]["vendors"]
        assert '<option value="909" selected>909</option>' in saved_dashboard["filterOptionsHtml"]["rooms"]

        status, dashboard_metrics = request_json(
            app.base_url,
            "POST",
            "/api/dashboard/metrics",
            {
                "devices": devices + [{"mac": "AABBCC000099", "vendor": "Unknown"}],
                "invalid": [{"row": 99, "raw": "bad-mac"}],
                "snapshots": [],
                "settings": {"vendor": "", "room": "", "chartLimit": 5, "showUnknown": True},
            },
        )
        assert status == 200
        assert dashboard_metrics["metrics"]["devices"] == 2
        assert dashboard_metrics["metrics"]["vendors"] == 1
        assert dashboard_metrics["metrics"]["knownDevices"] == 1
        assert dashboard_metrics["metrics"]["unknownVendor"] == 1
        assert dashboard_metrics["metrics"]["knownPercent"] == 50
        assert dashboard_metrics["metrics"]["invalid"] == 1
        assert dashboard_metrics["metrics"]["rooms"] == 1
        assert dashboard_metrics["metrics"]["switches"] == 0
        assert dashboard_metrics["metrics"]["uniqueOui3"] == 1
        assert dashboard_metrics["distributions"]["vendors"][0] == {"label": "SmokeVendor", "value": 1}
        assert dashboard_metrics["distributions"]["rooms"][0] == {"label": "909", "value": 1}
        assert dashboard_metrics["distributions"]["oui3"][0] == {"label": "AABBCC", "value": 2}

        status, loaded_dashboard = request_json(app.base_url, "GET", "/api/dashboard/settings")
        assert status == 200
        assert loaded_dashboard["settings"]["vendor"] == "SmokeVendor"
        assert loaded_dashboard["settings"]["room"] == "909"
        assert loaded_dashboard["settings"]["visibleCards"]["missing"] is False
        assert loaded_dashboard["settings"]["visibleCharts"]["fields"] is False
        assert loaded_dashboard["settings"]["autoRefresh"] is False
        assert loaded_dashboard["settings"]["refreshInterval"] == 45

        status, status_dashboard = request_json(
            app.base_url,
            "POST",
            "/api/dashboard",
            {
                "devices": [
                    {"mac": "AABBCC000001", "vendor": "Cisco", "room": "101"},
                    {"mac": "AABBCC000002", "vendor": "Cisco", "room": "102"},
                ],
                "snapshots": [{"kind": "analysis", "name": "Анализ: previous", "devices": [
                    {"mac": "AABBCC000001", "vendor": "Cisco", "room": "101"},
                    {"mac": "AABBCC000002", "vendor": "Cisco", "room": "102"},
                    {"mac": "AABBCC000003", "vendor": "Juniper", "room": "103"},
                ]}],
                "movements": [{
                    "mac": "AABBCC000001", "field": "model", "before": "A", "after": "B",
                    "changedAt": "2026-07-13T09:00:00Z",
                }],
                "settings": {"status": "missing", "chartLimit": 5},
            },
        )
        assert status == 200
        assert status_dashboard["metrics"]["total"] == 2
        assert status_dashboard["metrics"]["changed"] == 1
        assert status_dashboard["metrics"]["missing"] == 1
        assert status_dashboard["metrics"]["unchanged"] == 1
        assert status_dashboard["devices"][0]["mac"] == "AABBCC000003"
        assert status_dashboard["statusCharts"]["fields"] == [{"label": "Модель", "value": 1}]

        assert status_dashboard["changeAnalysis"]["summary"]["modified"] == 1

        status, snapshot_changes = request_json(
            app.base_url,
            "POST",
            "/api/dashboard",
            {
                "devices": [],
                "snapshots": [
                    {"id": "before", "kind": "analysis", "createdAt": "2026-07-01T08:00:00Z", "devices": [{"mac": "AABBCC000001", "switchPort": "Gi1"}, {"mac": "AABBCC000099"}]},
                    {"id": "after", "kind": "analysis", "createdAt": "2026-07-12T08:00:00Z", "devices": [{"mac": "AABBCC000001", "switchPort": "Gi2"}]},
                ],
                "settings": {"changeMode": "snapshots", "baselineSnapshotId": "before", "comparisonSnapshotId": "after"},
            },
        )
        assert status == 200
        assert snapshot_changes["changeAnalysis"]["summary"]["total"] == 2
        assert snapshot_changes["changeAnalysis"]["summary"]["critical"] == 0
        assert snapshot_changes["changeAnalysis"]["baselineSnapshotId"] == "before"
        assert snapshot_changes["changeAnalysis"]["comparisonSnapshotId"] == "after"

        status, png_dashboard = request_json(
            app.base_url,
            "POST",
            "/api/dashboard",
            {
                "devices": devices,
                "snapshots": [],
                "movements": [],
                "settings": {"status": "all"},
                "exportFormat": "png",
            },
        )
        assert status == 200
        assert png_dashboard["export"]["binary"] is True
        assert png_dashboard["export"]["mimeType"] == "image/png"
        assert png_dashboard["export"]["width"] == 2000
        assert png_dashboard["export"]["height"] == 1200
        assert base64.b64decode(png_dashboard["export"]["content"]).startswith(b"\x89PNG\r\n\x1a\n")

        snapshot_devices = [{**devices[0], "switchIp": "203.0.113.77"}]
        status, snapshot = request_json(
            app.base_url,
            "POST",
            "/api/snapshots",
            {"id": SNAPSHOT_ID, "name": "Анализ: UI/API smoke", "source": "ui-api-smoke", "devices": snapshot_devices},
        )
        assert status == 201
        assert snapshot["id"] == SNAPSHOT_ID

        status, snapshots = request_json(app.base_url, "GET", "/api/snapshots")
        assert status == 200
        assert any(item["id"] == SNAPSHOT_ID for item in snapshots["snapshots"])
        stored_metadata = next(item for item in snapshots["snapshots"] if item["id"] == SNAPSHOT_ID)
        assert stored_metadata["devices"] == []
        assert stored_metadata["deviceCount"] == 1
        assert stored_metadata["backendStored"] is True

        status, snapshot_options = request_json(app.base_url, "POST", "/api/snapshots/options", {"snapshots": [
            *snapshots["snapshots"],
            {"id": "legacy-ip-mapping", "kind": "analysis", "name": "Обогащение: IP-маппинг", "source": "local-ip-mapping"},
            {"id": "legacy-model-mapping", "kind": "analysis", "name": "Автоопределение производителей и моделей", "source": "local-vendor-model-rules"},
        ]})
        assert status == 200
        assert SNAPSHOT_ID in snapshot_options["optionsHtml"]
        assert "legacy-ip-mapping" not in snapshot_options["optionsHtml"]
        assert "legacy-model-mapping" not in snapshot_options["optionsHtml"]
        assert snapshot_options["count"] >= 1

        status, opened_snapshot = request_json(app.base_url, "POST", "/api/snapshots/open", {"id": SNAPSHOT_ID, "snapshots": []})
        assert status == 200
        assert opened_snapshot["snapshot"]["id"] == SNAPSHOT_ID
        assert opened_snapshot["snapshot"]["deviceCount"] == 1
        assert opened_snapshot["devices"][0]["vendor"] == "SmokeVendor"
        assert opened_snapshot["invalid"] == []

        status, compact_snapshot = request_json(
            app.base_url,
            "POST",
            "/api/snapshots/open",
            {"id": SNAPSHOT_ID, "snapshots": [], "compactResult": True, "resultPageSize": 25},
        )
        assert status == 200
        assert compact_snapshot["compactResult"] is True
        assert compact_snapshot["resultReference"]["snapshotId"] == SNAPSHOT_ID
        assert compact_snapshot["resultReference"]["deviceCount"] == 1
        assert compact_snapshot["resultPage"]["pagination"]["total"] == 1
        assert len(compact_snapshot["devices"]) == 1

        status, snapshot_history = request_json(app.base_url, "GET", "/api/statistics/snapshots?query=SmokeVendor")
        assert status == 200
        assert any(item["id"] == SNAPSHOT_ID for item in snapshot_history["snapshots"])
        assert snapshot_history["summary"]["uniqueMacs"] >= 1
        assert f'data-load-snapshot="{SNAPSHOT_ID}"' in snapshot_history["tableRowsHtml"]

        status, statistics_panel = request_json(app.base_url, "GET", "/api/statistics/panel")
        assert status == 200
        assert "trendRows" in statistics_panel
        assert "temporalRows" in statistics_panel
        assert "recent snapshots" in statistics_panel["statisticsApiDetail"]
        assert "SQLite snapshots" in statistics_panel["statisticsHtml"]
        assert "StatisticsDatabase API" in statistics_panel["statisticsHtml"]
        assert "MAC" in statistics_panel["temporalHtml"] or "Нет SQLite-снимков" in statistics_panel["temporalHtml"]

        status, database = request_json(app.base_url, "GET", "/api/database/summary")
        assert status == 200
        assert "summary" in database and "database" in database

        status, services_panel = request_json(app.base_url, "GET", "/api/services/panel")
        assert status == 200
        assert "ip" in services_panel
        assert "tasks" in services_panel
        assert "notifications" in services_panel
        assert "database" in services_panel
        assert "legacy" in services_panel
        assert "html" in services_panel
        assert "Coverage" in services_panel["html"]["ipRowsHtml"]
        assert "Задачи пока не созданы" in services_panel["html"]["taskRowsHtml"] or "data-remove-task=" in services_panel["html"]["taskRowsHtml"]
        assert "AppLogger" in services_panel["html"]["logRowsHtml"]
        assert "timeStatsSummaryHtml" in services_panel["html"]
        assert "timeStatsRowsHtml" in services_panel["html"]
        assert "Operations" in services_panel["html"]["timeStatsSummaryHtml"]
        assert "SQLite file" in services_panel["html"]["databaseSummaryHtml"]
        assert "Legacy rows" in services_panel["html"]["legacySummaryHtml"]
        assert "Autosave" in services_panel["html"]["autosaveStatusText"]

        status, search = request_json(app.base_url, "GET", "/api/database/search?query=SmokeVendor")
        assert status == 200
        assert "results" in search
        assert "resultsHtml" in search
        assert 'data-db-type="device"' in search["resultsHtml"]
        assert 'data-db-mac="' in search["resultsHtml"]
        assert "SmokeVendor" in search["resultsHtml"]
        assert "Ничего не найдено" in search["emptyResultsHtml"]

        status, managed_history = request_json(
            app.base_url,
            "GET",
            "/api/database/history/records?vendor=SmokeVendor&source=ui-api-smoke&limit=50",
        )
        assert status == 200
        assert managed_history["total"] >= 1
        assert managed_history["records"][0]["vendor"] == "SmokeVendor"
        assert 'data-db-history-select' in managed_history["rowsHtml"]
        assert 'data-delete-db-history-id=' in managed_history["rowsHtml"]
        assert "Уникальных MAC" in managed_history["summaryHtml"]

        status, fallback_device = request_json(app.base_url, "GET", "/api/database/device?mac=AA:BB:CC:00:00:99")
        assert status == 200
        assert fallback_device["found"] is False
        assert fallback_device["device"]["mac"] == "AABBCC000099"
        assert fallback_device["device"]["database"]["found"] is False

        status, comparison = request_json(
            app.base_url,
            "POST",
            "/api/compare",
            {"baselineDevices": [], "currentDevices": devices, "fields": ["vendor", "model"]},
        )
        assert status == 200
        assert comparison["summary"]["added"] == 1
        assert comparison["changesRowsHtml"]
        assert "Результат сравнения" in comparison["summaryHtml"]

        status, snapshot_comparison = request_json(
            app.base_url,
            "POST",
            "/api/compare/snapshots",
            {
                "snapshots": [
                    {"id": "baseline-smoke", "name": "Baseline smoke", "source": "baseline-smoke.csv", "devices": []},
                    {"id": "current-smoke", "name": "Current smoke", "source": "current-smoke.csv", "devices": devices},
                ],
                "baselineId": "baseline-smoke",
                "currentId": "current-smoke",
                "fields": ["vendor", "model"],
            },
        )
        assert status == 200
        assert snapshot_comparison["summary"]["added"] == 1
        assert snapshot_comparison["baseline"]["name"] == "Baseline smoke"
        assert snapshot_comparison["current"]["deviceCount"] == 1
        assert snapshot_comparison["changesRowsHtml"]

        status, snapshot_many_comparison = request_json(
            app.base_url,
            "POST",
            "/api/compare/snapshots/many",
            {
                "snapshots": [
                    {"id": "baseline-smoke", "name": "Baseline smoke", "source": "baseline-smoke.csv", "devices": []},
                    {"id": "current-smoke", "name": "Current smoke", "source": "current-smoke.csv", "mapping": {"mac": 0}, "devices": devices},
                ],
                "baselineId": "baseline-smoke",
                "comparisonIds": ["baseline-smoke", "current-smoke"],
                "fields": ["vendor", "model"],
            },
        )
        assert status == 200
        assert snapshot_many_comparison["summary"]["added"] == 1
        assert snapshot_many_comparison["sets"][0]["mapping"] == {"mac": 0}
        assert "Массовое сравнение" in snapshot_many_comparison["summaryHtml"]

        status, analytics_report = request_json(
            app.base_url,
            "POST",
            "/api/analytics/report",
            {"devices": devices, "exportFormat": "txt"},
        )
        assert status == 200
        assert analytics_report["total"] == 1
        assert analytics_report["vendors"][0]["label"] == "SmokeVendor"
        assert "=== АНАЛИТИКА ПО УСТРОЙСТВАМ ===" in analytics_report["reportText"]
        assert analytics_report["export"]["mimeType"] == "text/plain"
        assert analytics_report["export"]["content"] == analytics_report["reportText"]

        status, quality = request_json(
            app.base_url,
            "POST",
            "/api/quality/analyze",
            {"devices": devices, "invalid": [], "source": "ui-api-smoke-quality", "save": True},
        )
        assert status == 200
        assert quality["report"]["source"] == "ui-api-smoke-quality"
        assert "id" in quality["report"]

        status, quality_panel = request_json(
            app.base_url,
            "POST",
            "/api/quality/panel",
            {"devices": devices, "invalid": [], "source": "ui-api-smoke-quality-panel", "save": False},
        )
        assert status == 200
        assert quality_panel["headline"].startswith("Quality score")
        assert "summaryText" in quality_panel
        assert "issueRows" in quality_panel
        assert "insightsHtml" in quality_panel
        assert "Quality score" in quality_panel["insightsHtml"]
        assert "reportsHtml" in quality_panel

        status, quality_reports = request_json(app.base_url, "GET", "/api/quality/reports?limit=5")
        assert status == 200
        assert any(item["id"] == quality["report"]["id"] for item in quality_reports["reports"])
        assert "reportsHtml" in quality_reports
        assert "Saved quality reports" in quality_reports["reportsHtml"]
        assert "Saved quality reports are empty" in quality_reports["emptyReportsHtml"]

        status, charts = request_json(
            app.base_url,
            "POST",
            "/api/charts",
            {"devices": devices, "snapshots": [{"id": SNAPSHOT_ID, "name": "Анализ: UI/API smoke", "source": "ui-api-smoke", "devices": devices}]},
        )
        assert status == 200
        chart_map = {item["id"]: item for item in charts["charts"]}
        assert chart_map["vendors"]["items"][0]["label"] == "SmokeVendor"
        assert chart_map["quality"]["items"][0]["value"] == 1
        assert chart_map["timeline"]["items"][0]["value"] == 1

        status, analytics_panel = request_json(
            app.base_url,
            "POST",
            "/api/analytics/panel",
            {"devices": devices, "snapshots": [{"id": SNAPSHOT_ID, "name": "UI/API smoke", "source": "ui-api-smoke", "devices": devices}]},
        )
        assert status == 200
        assert analytics_panel["primaryCharts"]["vendors"][0]["label"] == "SmokeVendor"
        assert "primaryChartsHtml" in analytics_panel
        assert "SmokeVendor" in analytics_panel["primaryChartsHtml"]["vendors"]
        assert "bar-item" in analytics_panel["primaryChartsHtml"]["quality"]
        assert analytics_panel["backendCharts"]
        assert "backendChartsHtml" in analytics_panel
        assert "Vendor" in analytics_panel["backendChartsHtml"] or "Backend не вернул диаграммы" in analytics_panel["backendChartsHtml"]
        assert analytics_panel["clusterRows"]
        assert "clusterRowsHtml" in analytics_panel
        assert "MAC" in analytics_panel["clusterRowsHtml"] or "Backend не нашёл кластеров" in analytics_panel["clusterRowsHtml"]

        status, export_csv = request_json(
            app.base_url,
            "POST",
            "/api/export",
            {
                "format": "csv",
                "devices": devices,
                "columns": [{"key": "macFormatted", "title": "MAC"}, {"key": "oui", "title": "OUI"}, {"key": "vendor", "title": "Vendor"}],
                "ouiSettings": {"length": 4, "style": "dash"},
            },
        )
        assert status == 200
        assert export_csv["format"] == "csv"
        assert "AA-BB-CC-00" in export_csv["content"]

        for path, payload in (
            ("/api/dashboard", {"devices": devices}),
            ("/api/quality/analyze", {"devices": devices, "invalid": [], "save": False}),
        ):
            status, data = request_json(app.base_url, "POST", path, payload)
            assert status == 200
            assert data

        status, clusters = request_json(
            app.base_url,
            "POST",
            "/api/clusters",
            {"devices": devices, "fields": ["vendor", "room", "switchIp"], "minSize": 1},
        )
        assert status == 200
        assert clusters["summary"]["clusters"] >= 1
        assert clusters["clusters"][0]["count"] == 1

        status, topology = request_json(app.base_url, "POST", "/api/topology", {"devices": devices})
        assert status == 200
        assert topology["summary"]["linkedDevices"] == 0
        assert topology["summary"]["unassignedDevices"] == 1
        assert "topologyHtml" in topology
        assert "Backend не нашёл связей топологии" in topology["topologyHtml"]

        status, device_analytics = request_json(
            app.base_url,
            "POST",
            "/api/device/analytics",
            {"mac": devices[0]["mac"], "devices": devices, "snapshots": [{"id": SNAPSHOT_ID, "name": "UI/API smoke", "source": "ui-api-smoke", "devices": devices}]},
        )
        assert status == 200
        assert device_analytics["mac"] == devices[0]["mac"]
        assert device_analytics["current"]["vendor"] == "SmokeVendor"
        assert device_analytics["macFormatted"] == devices[0]["macFormatted"]
        assert device_analytics["metrics"]["appearances"] == 1
        assert device_analytics["metrics"]["sources"] == 1
        assert "metricsHtml" in device_analytics
        assert "fieldsHtml" in device_analytics
        assert "Снимков" in device_analytics["metricsHtml"]
        assert "SmokeVendor" in device_analytics["fieldsHtml"]
        assert "=== ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ОБ УСТРОЙСТВЕ ===" in device_analytics["detailedReportText"]
        assert "Производитель: SmokeVendor" in device_analytics["detailedReportText"]
        assert "MAC-адрес: AA:BB:CC:00:00:09" in device_analytics["detailedReportText"]
        assert any(row["field"] == "snapshot" and row["source"] == "UI/API smoke" for row in device_analytics["timelineRows"])
        assert any(row["event"] == "Появление в снимке" for row in device_analytics["chronology"])
        assert device_analytics["metrics"]["chronologyEvents"] >= 1
        assert "chronologyRowsHtml" in device_analytics
        assert "chronologySummaryHtml" in device_analytics
        assert "Появление в снимке" in device_analytics["chronologyRowsHtml"]
        assert "Chronology events" in device_analytics["chronologySummaryHtml"]
        assert "<td>snapshot</td>" in device_analytics["historyRowsHtml"]
        assert device_analytics["historyStats"]["totalAppearances"] >= 1
        assert device_analytics["historyStats"]["uniqueFiles"] >= 1
        assert "Всего появлений" in device_analytics["macHistoryStatsHtml"]
        assert "SmokeVendor" in device_analytics["historyRecordsRowsHtml"]
        assert "ui-api-smoke" in device_analytics["historyRecordsRowsHtml"]
        assert 'colspan="7"' in device_analytics["emptyHistoryRecordsRowsHtml"]
        assert 'colspan="5"' in device_analytics["emptyMovementRowsHtml"]

        status, legacy = request_json(app.base_url, "GET", "/api/legacy/import/status")
        assert status == 200
        assert "summary" in legacy

        status, parity = request_json(app.base_url, "GET", "/api/parity/status")
        assert status == 200
        assert parity["status"] == "complete"
        assert "Status" in parity["summaryHtml"]
        assert "PyQt blocks" in parity["summaryHtml"]

        status, diagnostics = request_json(app.base_url, "GET", "/api/system/diagnostics")
        assert status == 200
        assert diagnostics["status"] == "healthy"
        assert diagnostics["summary"]["readinessPercent"] == 100
        assert diagnostics["summary"]["parityPercent"] == 100
        assert diagnostics["summary"]["failed"] == 0
        assert any("Out of Memory" in item["name"] for item in diagnostics["checks"])
        assert "Database management" in parity["detailsHtml"]

        status, parity_report = request_json(app.base_url, "GET", "/api/parity/report")
        assert status == 200
        assert parity_report["mimeType"] == "application/json"

        status, history_export = request_json(app.base_url, "GET", "/api/statistics/snapshots/export?format=html&query=SmokeVendor")
        assert status == 200
        assert history_export["filename"] == "mac-history.html"
        assert history_export["mimeType"] == "text/html"

        status, denied = request_json(app.base_url, "POST", "/api/legacy/import", {"dryRun": True})
        assert status == 403
        assert denied["error"]

        status, denied_history_delete = request_json(
            app.base_url,
            "POST",
            "/api/database/history/delete",
            {"ids": [managed_history["records"][0]["id"]], "filters": {}},
        )
        assert status == 403
        assert denied_history_delete["error"]

        status, denied_movement_delete = request_json(
            app.base_url,
            "POST",
            "/api/history/movements/delete",
            {"ids": [movement_history["ids"][0]]},
        )
        assert status == 403
        assert denied_movement_delete["error"]

        status, session = request_json(app.base_url, "POST", "/api/engineering/login", {"password": "admin123", "ttlMinutes": 5})
        assert status == 200
        assert "write:migration" in session["permissions"]
        assert "write:settings" in session["permissions"]

        status, selected_history_delete = request_json(
            app.base_url,
            "POST",
            "/api/database/history/delete",
            {"ids": [managed_history["records"][0]["id"]], "filters": {}},
            token=session["token"],
        )
        assert status == 200
        assert selected_history_delete == {"ok": True, "deleted": 1}

        status, deleted_movement = request_json(
            app.base_url,
            "POST",
            "/api/history/movements/delete",
            {"ids": [movement_history["ids"][0]]},
            token=session["token"],
        )
        assert status == 200
        assert deleted_movement == {"ok": True, "deleted": 1}

        status, deleted_device_history = request_json(
            app.base_url,
            "DELETE",
            f"/api/history?mac={devices[0]['macFormatted']}",
            token=session["token"],
        )
        assert status == 200
        assert deleted_device_history["ok"] is True
        assert "historyRowsHtml" in deleted_device_history
        assert 'colspan="5"' in deleted_device_history["historyRowsHtml"]

        notification_config = {"botToken": "smoke-token", "chatId": "smoke-chat"}
        status, saved_notification = request_json(
            app.base_url,
            "POST",
            "/api/notifications",
            {"channel": "telegram", "configText": json.dumps(notification_config), "enabled": False},
            token=session["token"],
        )
        assert status == 200
        assert saved_notification["channel"] == "telegram"
        assert saved_notification["config"] == notification_config
        assert saved_notification["enabled"] is False

        status, notifications = request_json(app.base_url, "GET", "/api/notifications")
        assert status == 200
        telegram = next(item for item in notifications["channels"] if item["channel"] == "telegram")
        assert telegram["config"] == notification_config
        assert telegram["enabled"] is False

        status, invalid_notification = request_json(
            app.base_url,
            "POST",
            "/api/notifications",
            {"channel": "telegram", "configText": "{bad-json", "enabled": False},
            token=session["token"],
        )
        assert status == 400
        assert "Invalid notification config JSON" in invalid_notification["error"]

        ip_mapping_content = base64.b64encode("switch_ip,physical_address\n203.0.113.77,Smoke rack\n".encode("utf-8")).decode("ascii")
        status, imported_ip_mapping = request_json(
            app.base_url,
            "POST",
            "/api/ip-mappings/import",
            {"filename": "ui-api-smoke-ip.csv", "contentBase64": ip_mapping_content},
            token=session["token"],
        )
        assert status == 200
        assert imported_ip_mapping["imported"] == 1

        status, applied_ip_mapping = request_json(
            app.base_url,
            "POST",
            "/api/ip-mappings/apply",
            {"snapshotId": SNAPSHOT_ID, "devices": [], "compactResult": True, "resultPageSize": 25},
        )
        assert status == 200
        assert applied_ip_mapping["compactResult"] is True
        assert applied_ip_mapping["summary"]["matched"] == 1
        assert applied_ip_mapping["devices"][0]["address"] == "Smoke rack"
        assert applied_ip_mapping["resultReference"]["deviceCount"] == 1
        assert applied_ip_mapping["resultReference"]["snapshotId"] == SNAPSHOT_ID
        EXTERNAL_SNAPSHOT_IDS.add(applied_ip_mapping["resultReference"]["snapshotId"])

        status, autodetected_ip_mapping = request_json(
            app.base_url,
            "POST",
            "/api/ip-mappings/autodetect",
            {"snapshotId": applied_ip_mapping["resultReference"]["snapshotId"], "devices": []},
        )
        assert status == 200
        assert autodetected_ip_mapping["imported"] >= 1

        status, saved_autosave = request_json(
            app.base_url,
            "POST",
            "/api/autosave",
            {"slot": AUTOSAVE_SLOT, "reason": "ui-api-smoke", "state": {"devices": devices, "dashboardSettings": {"vendor": "SmokeVendor"}}},
        )
        assert status == 200
        assert saved_autosave["slot"] == AUTOSAVE_SLOT
        assert saved_autosave["bytes"] > 0
        assert saved_autosave["statusText"].startswith("Autosaved:")

        status, autosave = request_json(app.base_url, "GET", f"/api/autosave?slot={AUTOSAVE_SLOT}")
        assert status == 200
        assert autosave["autosave"]["state"]["devices"][0]["vendor"] == "SmokeVendor"
        assert autosave["autosave"]["statusText"].startswith("Autosave restored:")

        status, autosaves = request_json(app.base_url, "GET", "/api/autosaves")
        assert status == 200
        assert AUTOSAVE_SLOT in autosaves["summary"]["slots"]

        status, previous_main_autosave = request_json(app.base_url, "GET", "/api/autosave?slot=main")
        assert status == 200
        previous_main_state = previous_main_autosave.get("autosave")
        try:
            status, saved_main_autosave = request_json(
                app.base_url,
                "POST",
                "/api/autosave",
                {"slot": "main", "reason": "ui-api-smoke-bootstrap", "state": {"devices": devices, "movementHistory": [{"mac": "AA:BB:CC:00:00:09", "field": "vendor", "before": "Old", "after": "SmokeVendor"}]}},
            )
            assert status == 200
            assert saved_main_autosave["slot"] == "main"

            status, bootstrap_with_autosave = request_json(app.base_url, "GET", "/api/bootstrap")
            assert status == 200
            assert bootstrap_with_autosave["autosave"]["slot"] == "main"
            assert bootstrap_with_autosave["autosave"]["state"]["devices"] == []
            assert bootstrap_with_autosave["autosave"]["state"]["movementHistory"][0]["before"] == "Old"
        finally:
            if previous_main_state:
                request_json(
                    app.base_url,
                    "POST",
                    "/api/autosave",
                    {"slot": "main", "reason": previous_main_state.get("reason", "restore-before-smoke"), "state": previous_main_state.get("state", {})},
                )
            else:
                request_json(app.base_url, "DELETE", "/api/autosave?slot=main", token=session["token"])

        backup_state = {"devices": devices, "dashboardSettings": {"vendor": "SmokeVendor"}}
        status, exported_backup = request_json(app.base_url, "POST", "/api/backup/export", {"state": backup_state})
        assert status == 200
        assert exported_backup["filename"] == "mac-analyzer-backup.json"
        assert exported_backup["mimeType"] == "application/json"
        assert exported_backup["bytes"] == len(exported_backup["content"].encode("utf-8"))
        assert '"version": 1' in exported_backup["content"]
        assert Path(exported_backup["storedPath"]).parent.name == "backups"

        backup_content = base64.b64encode(exported_backup["content"].encode("utf-8")).decode("ascii")
        status, restored_backup = request_json(app.base_url, "POST", "/api/backup/restore", {"contentBase64": backup_content})
        assert status == 200
        assert restored_backup["version"] == 1
        assert restored_backup["state"] == backup_state
        assert Path(restored_backup["storedPath"]).parent.name == "backups"

        status, deleted_autosave = request_json(app.base_url, "DELETE", f"/api/autosaves/{AUTOSAVE_SLOT}", token=session["token"])
        assert status == 200
        assert deleted_autosave["deleted"] is True
        assert deleted_autosave["statusText"] == "Autosave deleted from SQLite."

        status, empty_autosave = request_json(app.base_url, "GET", f"/api/autosave?slot={AUTOSAVE_SLOT}")
        assert status == 200
        assert empty_autosave["autosave"] is None

        status, saved_external_api = request_json(
            app.base_url,
            "POST",
            "/api/external-enrichment/settings",
            {"settings": {"enabled": False, "provider": "macvendors", "rateLimit": 7, "cacheTtlDays": 3}},
        )
        assert status == 200
        assert saved_external_api["settings"]["enabled"] is False
        assert saved_external_api["settings"]["provider"] == "macvendors"
        assert saved_external_api["settings"]["rateLimit"] == 7
        assert saved_external_api["settings"]["cacheTtlDays"] == 3

        status, loaded_external_api = request_json(app.base_url, "GET", "/api/external-enrichment/settings")
        assert status == 200
        assert loaded_external_api["settings"]["provider"] == "macvendors"
        assert loaded_external_api["settings"]["rateLimit"] == 7
        assert [item["key"] for item in loaded_external_api["providers"][:3]] == ["macvendors", "maclookup", "mac2vendor"]
        assert loaded_external_api["providers"][2]["description"] == "mac2vendor.com"
        assert loaded_external_api["settings"]["cacheTtlDays"] == 3

        status, external_run = request_json(
            app.base_url,
            "POST",
            "/api/external-enrichment/run",
            {"devices": [{**devices[0], "vendor": "Unknown"}, {**devices[0], "mac": "AABBCC000010", "vendor": "Known"}], "saveHistory": False},
        )
        assert status == 200
        assert external_run["summary"]["candidates"] == 1
        assert external_run["summary"]["enabled"] is False

        status, compact_external_run = request_json(
            app.base_url,
            "POST",
            "/api/external-enrichment/run",
            {
                "devices": [{**devices[0], "vendor": "Unknown"}, {**devices[0], "mac": "AABBCC000010", "vendor": "Known"}],
                "saveHistory": False,
                "compactResult": True,
                "resultPageSize": 25,
            },
        )
        assert status == 200
        assert compact_external_run["compactResult"] is True
        assert compact_external_run["resultReference"]["deviceCount"] == 2
        assert compact_external_run["resultReference"]["snapshotId"] == compact_external_run["snapshot"]["id"]
        EXTERNAL_SNAPSHOT_IDS.add(compact_external_run["snapshot"]["id"])

        status, vendor_mapping = request_json(
            app.base_url,
            "POST",
            "/api/mappings/vendors",
            {"key": VENDOR_MAPPING_KEY, "value": "Smoke Vendor Mapping"},
        )
        assert status == 200
        assert vendor_mapping["ok"] is True

        for key, value in (
            (VENDOR_MAPPING_KEY_4BYTE, "Smoke Vendor Mapping 4-byte"),
            (VENDOR_MAPPING_KEY_5BYTE, "Smoke Vendor Mapping 5-byte"),
        ):
            status, vendor_mapping_extended = request_json(
                app.base_url,
                "POST",
                "/api/mappings/vendors",
                {"key": key, "value": value},
            )
            assert status == 200
            assert vendor_mapping_extended["ok"] is True

        status, model_mapping = request_json(
            app.base_url,
            "POST",
            "/api/mappings/models",
            {"key": MODEL_MAPPING_KEY, "value": "Smoke Model Mapping"},
        )
        assert status == 200
        assert model_mapping["ok"] is True

        status, reapplied_detection = request_json(
            app.base_url,
            "POST",
            "/api/detection/apply",
            {"snapshotId": SNAPSHOT_ID, "devices": [], "compactResult": True, "resultPageSize": 25},
        )
        assert status == 200
        assert reapplied_detection["resultReference"]["snapshotId"] == SNAPSHOT_ID
        assert reapplied_detection["resultReference"]["deviceCount"] == 1

        status, vendors = request_json(app.base_url, "GET", "/api/mappings/vendors")
        assert status == 200
        assert vendors["vendors"][VENDOR_MAPPING_KEY] == "Smoke Vendor Mapping"
        assert any(item["oui"] == VENDOR_MAPPING_KEY and item["vendor"] == "Smoke Vendor Mapping" for item in vendors["rules"])

        status, mappings_panel = request_json(app.base_url, "GET", "/api/mappings/panel")
        assert status == 200
        assert mappings_panel["vendors"][VENDOR_MAPPING_KEY] == "Smoke Vendor Mapping"
        assert any(item["oui"] == VENDOR_MAPPING_KEY for item in mappings_panel["vendorRules"])
        assert mappings_panel["summary"]["vendorRules"] >= 1
        assert f'data-remove-vendor="{VENDOR_MAPPING_KEY}"' in mappings_panel["vendorRowsHtml"]
        assert "Smoke Vendor Mapping" in mappings_panel["vendorRowsHtml"]

        status, models = request_json(app.base_url, "GET", "/api/mappings/models")
        assert status == 200
        assert models["models"][MODEL_MAPPING_KEY] == "Smoke Model Mapping"
        assert any(item["prefix"] == MODEL_MAPPING_KEY and item["model"] == "Smoke Model Mapping" for item in models["rules"])
        assert f'data-remove-model="{MODEL_MAPPING_KEY}"' in mappings_panel["modelRowsHtml"]
        assert 'data-model-prefixes="Smoke Model Mapping"' in mappings_panel["modelRowsHtml"]

        status, prefix_analysis = request_json(
            app.base_url,
            "POST",
            "/api/analyze",
            {
                "devices": [{"mac": "A1:B2:C3:00:00:99", "source": "prefix-smoke"}],
                "strategy": "primary",
                "saveHistory": False,
                "notify": False,
            },
        )
        assert status == 200
        assert prefix_analysis["devices"][0]["vendor"] == "Smoke Vendor Mapping 5-byte"
        assert prefix_analysis["devices"][0]["vendorMatchedPrefix"] == VENDOR_MAPPING_KEY_5BYTE
        assert prefix_analysis["devices"][0]["model"] == "Smoke Model Mapping"
        assert prefix_analysis["devices"][0]["modelMatchedPrefix"] == MODEL_MAPPING_KEY

        status, learned_history = request_json(
            app.base_url,
            "POST",
            "/api/analyze",
            {
                "devices": [{"mac": "C0:FF:EE:11:22:33", "vendor": "Learned Smoke Vendor", "model": "Learned Smoke Model"}],
                "source": LEARN_SOURCE,
                "saveHistory": True,
                "notify": False,
            },
        )
        assert status == 200
        assert learned_history["devices"][0]["vendor"] == "Learned Smoke Vendor"
        assert learned_history["devices"][0]["model"] == "Learned Smoke Model"

        status, learned_rules = request_json(
            app.base_url,
            "POST",
            "/api/vendor-model-history/learn",
            {"minCount": 1, "source": LEARN_SOURCE},
        )
        assert status == 200
        assert learned_rules["learned"]["vendors"] == 3
        assert learned_rules["learned"]["models"] == 0

        status, learned_vendors = request_json(app.base_url, "GET", "/api/mappings/vendors")
        assert status == 200
        for key in (LEARN_VENDOR_PREFIX_3BYTE, LEARN_VENDOR_PREFIX_4BYTE, LEARN_VENDOR_PREFIX_5BYTE):
            assert learned_vendors["vendors"][key] == "Learned Smoke Vendor"

        status, learned_models = request_json(app.base_url, "GET", "/api/mappings/models")
        assert status == 200
        assert learned_models["models"][LEARN_VENDOR_PREFIX_5BYTE] == "Learned Smoke Model"
        assert LEARN_VENDOR_PREFIX_3BYTE not in learned_models["models"]
        assert LEARN_VENDOR_PREFIX_4BYTE not in learned_models["models"]

        status, model_analytics = request_json(
            app.base_url,
            "POST",
            "/api/model/analytics",
            {"model": "Smoke Model Mapping", "devices": devices},
        )
        assert status == 200
        assert model_analytics["metrics"]["prefixes"] == 1
        assert model_analytics["prefixes"][0]["prefix"] == MODEL_MAPPING_KEY
        assert MODEL_MAPPING_KEY in model_analytics["prefixRowsHtml"]
        assert model_analytics["prefixes"][0]["source"] == "custom"
        assert model_analytics["prefixes"][0]["sourceLabel"] == "Пользовательское правило"
        assert "<th>" not in model_analytics["tableRowsHtml"]
        assert "Пользовательское правило" in model_analytics["tableRowsHtml"]
        assert "Устройств" in model_analytics["dialogRowsHtml"]

        status, deleted_vendor = request_json(app.base_url, "DELETE", f"/api/mappings/vendors/{VENDOR_MAPPING_KEY}", token=session["token"])
        assert status == 200
        assert deleted_vendor["ok"] is True

        status, deleted_model = request_json(app.base_url, "DELETE", f"/api/mappings/models/{MODEL_MAPPING_KEY}", token=session["token"])
        assert status == 200
        assert deleted_model["ok"] is True

        status, vendors_after_delete = request_json(app.base_url, "GET", "/api/mappings/vendors")
        assert status == 200
        assert VENDOR_MAPPING_KEY not in vendors_after_delete["vendors"]
        assert all(item["oui"] != VENDOR_MAPPING_KEY for item in vendors_after_delete["rules"])

        status, models_after_delete = request_json(app.base_url, "GET", "/api/mappings/models")
        assert status == 200
        assert MODEL_MAPPING_KEY not in models_after_delete["models"]
        assert all(item["prefix"] != MODEL_MAPPING_KEY for item in models_after_delete["rules"])

        status, saved_columns = request_json(
            app.base_url,
            "POST",
            f"/api/columns/preferences/{COLUMN_VIEW}",
            {
                "order": ["vendor", "macFormatted", "ip"],
                "visible": ["macFormatted", "vendor"],
                "custom": [{"key": "custom_smoke", "title": "Smoke", "sourceIndex": 2}],
                "widths": {"macFormatted": 188, "vendor": 222, "custom_smoke": 333},
            },
            token=session["token"],
        )
        assert status == 200
        assert saved_columns["preferences"]["visible"] == ["macFormatted", "vendor"]
        assert saved_columns["preferences"]["custom"][0]["key"] == "custom_smoke"
        assert saved_columns["preferences"]["widths"]["vendor"] == 222
        assert saved_columns["preferences"]["widths"]["custom_smoke"] == 333

        status, rendered_columns = request_json(
            app.base_url,
            "POST",
            "/api/columns/preferences/results/render",
            {"preferences": saved_columns["preferences"], "labels": {"custom_smoke": "Smoke"}},
        )
        assert status == 200
        assert 'data-column-field="vendor"' in rendered_columns["listHtml"]
        assert 'data-move-column="vendor"' in rendered_columns["listHtml"]
        assert 'data-remove-custom-column="custom_smoke"' in rendered_columns["listHtml"]
        assert 'data-column-width="vendor"' in rendered_columns["listHtml"]
        assert 'value="222"' in rendered_columns["listHtml"]

        status, loaded_columns = request_json(app.base_url, "GET", f"/api/columns/preferences/{COLUMN_VIEW}")
        assert status == 200
        assert loaded_columns["preferences"]["order"][:3] == ["vendor", "macFormatted", "ip"]
        assert loaded_columns["preferences"]["widths"]["vendor"] == 222
        assert 'data-column-field="custom_smoke"' in loaded_columns["listHtml"]

        status, reset_columns = request_json(app.base_url, "DELETE", f"/api/columns/preferences/{COLUMN_VIEW}", token=session["token"])
        assert status == 200
        assert reset_columns["ok"] is True
        assert reset_columns["preferences"]["updatedAt"] is None

        status, legacy_post = request_json(app.base_url, "POST", "/api/legacy/import", {"dryRun": True}, token=session["token"])
        assert status == 200
        assert "summary" in legacy_post


if __name__ == "__main__":
    test_rest_api_and_ui_controls_smoke()
    print("web api/ui smoke test passed")

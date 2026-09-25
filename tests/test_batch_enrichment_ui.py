from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_batch_enrichment_ui_and_module_are_wired():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    module = (ROOT / "frontend" / "batch-enrichment.js").read_text(encoding="utf-8")

    for element_id in (
        "batchPrimaryFolderInput", "batchSmartroomFolderInput", "batchDdioFolderInput",
        "batchPairingMode", "batchToleranceHours", "batchBuildPlanButton", "batchRunButton",
        "batchPrimaryPath", "batchSmartroomPath", "batchDdioPath", "batchScanPathsButton",
    ):
        assert f'id="{element_id}"' in html
    assert "frontend/batch-enrichment.js" in html
    assert 'BatchEnrichment.describeFiles' in app
    assert 'BatchEnrichment.buildPlan' in app
    assert 'await stageBatchSourceFiles(descriptors' in app
    assert 'await BrowserSnapshots.saveSourceFile(storageId,item.file)' in app
    assert 'await BrowserSnapshots.loadSourceFile(item.sourceStorageId)' in app
    assert 'ids.push(...batchStagedSourceIds)' in app
    assert 'const analysisResult=await analyze()' in app
    assert 'if(!analysisResult?.ok)' in app
    assert 'return{ok:true,deviceCount:currentDeviceCount()' in app
    assert 'DDIO «${ddio.name}»: не определены четыре колонки' in app
    assert 'SUPPORTED_EXTENSIONS' in module
    assert '"csv"' in module


def test_python_folder_scan_and_import_routes_are_present():
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    assert 'parsed.path == "/api/batch/folders/scan"' in server
    assert 'parsed.path == "/api/batch/folders/import"' in server
    assert 'scan_batch_folders(paths, BATCH_FOLDER_REGISTRY)' in server

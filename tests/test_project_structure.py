from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_structure_and_maintenance_commands_exist():
    required = (
        ".agents/README.md",
        "AGENTS.md",
        "PROJECT_STRUCTURE.md",
        "START_MAC_ANALYZER.cmd",
        "STOP_MAC_ANALYZER.cmd",
        "scripts/start_server.ps1",
        "scripts/stop_server.ps1",
        "scripts/portable_start.ps1",
        "scripts/portable_stop.ps1",
        "scripts/build_portable.ps1",
        "scripts/build_html_portable.ps1",
        "scripts/build_complete_release.ps1",
        "scripts/build_source_portable.ps1",
        "scripts/run_tests.ps1",
        "tests/README.md",
        "tools/README.md",
        "tools/_bootstrap.py",
        "tools/generate_parity_status.py",
        "tools/migrate_legacy.py",
        "tools/verify_portable_backend.py",
        "backend/services/detection/column_detector_service.py",
        "backend/services/detection/detection_index_service.py",
        "backend/services/detection/oui_service.py",
        "backend/services/detection/reference_data_service.py",
        "backend/services/detection/vendor_detector_service.py",
        "backend/services/workspace/enrichment_service.py",
        "backend/services/workspace/file_import_service.py",
        "backend/services/workspace/single_file_service.py",
        "backend/services/workspace/workspace_cache_service.py",
        "backend/services/workspace/xlsx_service.py",
        "backend/services/analytics/__init__.py",
        "backend/services/analytics/analytics_report_service.py",
        "backend/services/analytics/chart_service.py",
        "backend/services/analytics/cluster_service.py",
        "backend/services/analytics/dashboard_service.py",
        "backend/services/analytics/data_quality_service.py",
        "backend/services/analytics/device_analytics_service.py",
        "backend/services/analytics/topology_service.py",
        "backend/services/integrations/__init__.py",
        "backend/services/integrations/external_api_service.py",
        "backend/services/integrations/notification_service.py",
        "backend/services/integrations/scheduler_service.py",
        "backend/services/comparison/__init__.py",
        "backend/services/comparison/comparison_service.py",
        "backend/services/exporting/__init__.py",
        "backend/services/exporting/export_manager_service.py",
        "backend/services/exporting/export_service.py",
        "backend/services/exporting/pdf_service.py",
        "backend/services/system/__init__.py",
        "backend/services/system/legacy_migration_service.py",
        "backend/services/system/parity_service.py",
        "backend/services/system/storage_paths.py",
        "frontend/README.md",
        "frontend/memory-guard.js",
        "frontend/file-readers.js",
        "frontend/state-persistence.js",
        "frontend/browser-snapshot-store.js",
        "frontend/mac-chronology.js",
        "frontend/xlsx-exporter.js",
        "frontend/full-xlsx-report.js",
        "frontend/portable-database.js",
        "frontend/workspace-file-lifecycle.js",
        "frontend/guide.js",
        "backend/services/system/diagnostics_service.py",
        "tests/frontend_memory_guard.test.js",
        "tests/frontend_file_readers.test.js",
        "tests/browser_xlsx_memory_harness.html",
        "tests/frontend_state_persistence.test.js",
        "tests/frontend_repeated_persistence_memory.test.js",
        "tests/frontend_snapshot_chunking_memory.test.js",
        "tests/frontend_mac_chronology.test.js",
        "tests/local_folder_store.test.js",
        "tests/workspace_file_lifecycle.test.js",
        "tests/portable_database.test.js",
        "tests/test_html_portable_build.py",
        "tests/test_complete_release_build.py",
        "tests/test_repeated_enrichment_memory.py",
        "data/README.md",
        "data/reference/.gitkeep",
    )
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, f"Missing project structure files: {missing}"

    start_script = (ROOT / "scripts/start_server.ps1").read_text(encoding="utf-8-sig")
    test_script = (ROOT / "scripts/run_tests.ps1").read_text(encoding="utf-8-sig")
    assert 'Join-Path $root "data\\runtime"' in start_script
    assert 'Join-Path $runtimeDirectory "server.pid"' in start_script
    assert "-WindowStyle Hidden" in start_script
    assert "function Test-BackendPort" in start_script
    assert "function Get-ListeningProcessId" in start_script
    assert "Set-Content -LiteralPath $pidFile -Value $listenerPid" in start_script
    assert 'Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health"' in start_script
    assert "Backend exited before startup" in start_script
    assert "Set-Content -LiteralPath $pidFile" in start_script
    assert 'Filter = "test_*.py"' in test_script
    assert 'Join-Path $root "tests"' in test_script
    assert 'Join-Path $root "frontend"' in test_script
    assert 'foreach ($javascriptFile in $javascriptFiles)' in test_script
    assert 'Filter "*.test.js"' in test_script
    assert "--check" in test_script
    assert not list(ROOT.glob("test_*.py"))
    assert not list(ROOT.glob("migrate_legacy*.py"))
    for old_detection_module in (
        "column_detector_service.py",
        "detection_index_service.py",
        "oui_service.py",
        "vendor_detector_service.py",
    ):
        assert not (ROOT / old_detection_module).exists()
    for old_workspace_module in (
        "enrichment_service.py",
        "file_import_service.py",
        "single_file_service.py",
        "workspace_cache_service.py",
        "xlsx_service.py",
    ):
        assert not (ROOT / old_workspace_module).exists()
    for analytics_adapter in (
        "analytics_report_service.py",
        "chart_service.py",
        "cluster_service.py",
        "dashboard_service.py",
        "data_quality_service.py",
        "device_analytics_service.py",
        "topology_service.py",
    ):
        adapter = (ROOT / analytics_adapter).read_text(encoding="utf-8-sig")
        assert len(adapter.splitlines()) <= 4
        assert "backend.services.analytics" in adapter
    for integration_adapter in (
        "external_api_service.py",
        "notification_service.py",
        "scheduler_service.py",
    ):
        adapter = (ROOT / integration_adapter).read_text(encoding="utf-8-sig")
        assert len(adapter.splitlines()) <= 4
        assert "backend.services.integrations" in adapter
    for comparison_adapter in ("comparison_service.py",):
        adapter = (ROOT / comparison_adapter).read_text(encoding="utf-8-sig")
        assert len(adapter.splitlines()) <= 4
        assert "backend.services.comparison" in adapter
    for export_adapter in (
        "export_manager_service.py",
        "export_service.py",
        "pdf_service.py",
    ):
        adapter = (ROOT / export_adapter).read_text(encoding="utf-8-sig")
        assert len(adapter.splitlines()) <= 4
        assert "backend.services.exporting" in adapter
    for system_adapter in (
        "legacy_migration_service.py",
        "parity_service.py",
        "storage_paths.py",
    ):
        adapter = (ROOT / system_adapter).read_text(encoding="utf-8-sig")
        assert len(adapter.splitlines()) <= 4
        assert "backend.services.system" in adapter


if __name__ == "__main__":
    test_project_structure_and_maintenance_commands_exist()
    print("project structure test passed")

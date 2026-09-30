from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_analytics_lifecycle_module_loads_before_main_controller():
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    lifecycle = html.index('src="frontend/analytics-lifecycle.js')
    controller = html.index('src="app.js')

    assert lifecycle < controller


def test_partial_result_page_cannot_replace_full_analytics():
    app = (ROOT / "app.js").read_text(encoding="utf-8")

    assert "function incompleteAnalyticsPreview()" in app
    assert "AnalyticsLifecycle.fallbackMode(state,backendDashboardCache,key)" in app
    assert 'mode==="preserve"' in app
    assert "AnalyticsLifecycle.previewCount(state).toLocaleString(\"ru-RU\")" in app
    assert "Экспорт неполных 50 строк отменён." in app
    assert 'if(revision!==analyticsRenderRevision||!$("#analyticsView")?.classList.contains("active"))return;' in app
    assert "async function recoverActiveFinalReference" in app
    assert "applyBrowserFinalReference" in app
    assert "expectedDeviceCount:expected,partialPreview:partial" in app
    assert 'browserComparisonCache.key===comparisonKey?browserComparisonCache.data:null' in app


def test_autosave_keeps_storage_type_and_does_not_guess_legacy_browser_id():
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    lifecycle = (ROOT / "frontend" / "analytics-lifecycle.js").read_text(encoding="utf-8")

    assert 'const activeSnapshotStorage=state.resultSnapshotId?"backend":state.resultBrowserSnapshotId?"browser":"";' in app
    assert "const references=AnalyticsLifecycle.restoredReferences(merged);" in app
    assert 'if (storage === "browser"' in lifecycle
    assert 'return { backend: "", browser: "" };' in lifecycle


def test_backend_rejects_partial_preview_instead_of_reporting_fifty_as_full_final():
    server = (ROOT / "server.py").read_text(encoding="utf-8")

    assert server.count('payload.get("partialPreview") is True') >= 2
    assert "аналитика по усечённой странице предпросмотра запрещена" in server
    assert "dashboard по усечённой странице предпросмотра запрещён" in server


def test_returning_to_analytics_forces_full_refresh_and_invalidates_old_requests():
    app = (ROOT / "app.js").read_text(encoding="utf-8")

    assert 'if(same&&name==="analytics"){void renderAnalytics({force:true});return;}' in app
    assert 'if(activeViewName()==="analytics"&&name!=="analytics")analyticsRenderRevision++;' in app

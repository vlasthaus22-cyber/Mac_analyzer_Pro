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


def test_returning_to_analytics_forces_full_refresh_and_invalidates_old_requests():
    app = (ROOT / "app.js").read_text(encoding="utf-8")

    assert 'if(same&&name==="analytics"){void renderAnalytics({force:true});return;}' in app
    assert 'if(activeViewName()==="analytics"&&name!=="analytics")analyticsRenderRevision++;' in app

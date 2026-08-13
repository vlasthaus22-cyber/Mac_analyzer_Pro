from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ip_change_is_integrated_into_critical_analytics_only():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    assert 'data-view="iphistory"' not in html
    assert 'id="iphistoryView"' not in html
    assert "История IP коммутаторов" not in html
    assert "Аналитике критических изменений" in html
    assert "ddioHistoryBadge(item)" in app
    assert 'if(name==="iphistory")return"analytics"' in app


def test_user_mode_starts_with_search_and_table():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'data-view="workspace" role="tab"' in html
    assert 'id="searchInput"' in html
    assert 'id="resultsTable"' in html
    assert 'id="workspaceView"' in html


def test_local_comparison_uses_unified_strong_identity_service():
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    assert "DeviceIdentity.pairSets(baseline.devices||[],current.devices||[])" in app
    assert "oldValue===newValue||oldValue&&!newValue" in app


if __name__ == "__main__":
    test_ip_change_is_integrated_into_critical_analytics_only()
    test_user_mode_starts_with_search_and_table()
    test_local_comparison_uses_unified_strong_identity_service()
    print("critical IP UI tests passed")

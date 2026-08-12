from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_smartroom_tabs_and_chart_canvases_are_present():
    html = read("index.html")
    for view in ("rooms", "iphistory", "roomhistory"):
        assert f'data-view="{view}"' in html
        assert f'id="{view}View"' in html
    for canvas in ("smartroomChangesChart", "smartroomAddedRemovedChart", "smartroomTotalChart"):
        assert f'id="{canvas}"' in html
    assert 'frontend/vendor/chart.umd.min.js?v=4.5.1' in html


def test_worker_uses_chunked_ingestion_and_full_timeline_fields():
    source = read("frontend/smartroom-worker.js")
    assert 'action === \'ingest\'' in source
    assert 'offset += 1000' in source
    assert "ipHistory" in source
    assert "macTimelines" in source
    assert "Possible_IPs" in source
    assert "switchPort" in source


def test_virtual_scroll_keeps_twenty_visible_rows():
    source = read("frontend/virtual-table.js")
    assert "const threshold = 100;" in source
    assert "const visibleRows = 20;" in source
    assert 'data-virtual-scroll="true"' in read("index.html")


def test_indexeddb_contract_has_requested_stores():
    source = read("frontend/smartroom-store.js")
    assert 'const equipmentStore = "Equipment";' in source
    assert 'const historyStore = "History";' in source
    assert 'const ddioStore = "DDIO_Snapshot";' in source
    assert "async function enrichData" in source
    assert "async function fetchDdio" in source
    assert "function resolvePhysicalAddress" in source
    assert '"MAC не найден"' in source


def test_lazy_tabs_keep_detached_content_in_document_fragments():
    source = read("frontend/lazy-tabs.js")
    assert "document.createDocumentFragment()" in source
    assert "function activate(name)" in source
    assert "entry.fragment.querySelector" in source


def test_portable_build_embeds_new_runtime_modules():
    script = read("scripts/build_html_portable.ps1")
    for module in (
        "frontend/vendor/chart.umd.min.js",
        "frontend/lazy-tabs.js",
        "frontend/virtual-table.js",
        "frontend/smartroom-worker.js",
        "frontend/smartroom-store.js",
        "frontend/room-timeline.js",
        "frontend/ui-feedback.js",
        "frontend/smartroom-ui.js",
    ):
        assert f'"{module}"' in script


if __name__ == "__main__":
    test_smartroom_tabs_and_chart_canvases_are_present()
    test_worker_uses_chunked_ingestion_and_full_timeline_fields()
    test_virtual_scroll_keeps_twenty_visible_rows()
    test_indexeddb_contract_has_requested_stores()
    test_lazy_tabs_keep_detached_content_in_document_fragments()
    test_portable_build_embeds_new_runtime_modules()
    print("smartroom performance UI tests passed")

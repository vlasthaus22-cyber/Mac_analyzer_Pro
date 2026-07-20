from tempfile import TemporaryDirectory

from backend.services.workspace.workspace_cache_service import WorkspaceCacheMiss, WorkspaceFileCache, resolve_workspace_files


def test_cached_table_is_resolved_without_rows_in_browser_payload():
    cache = WorkspaceFileCache(ttl_seconds=3600, max_entries=4, max_rows=100)
    token = cache.put(
        "devices.xlsx",
        {"headers": ["MAC", "Vendor"], "rows": [["001122334455", "Cisco"]], "sheet": "Devices"},
    )

    resolved = resolve_workspace_files(
        [{"id": "main", "name": "devices.xlsx", "fileToken": token, "mapping": {"mac": 0, "vendor": 1}}],
        cache,
    )

    assert resolved[0]["rows"] == [["MAC", "Vendor"], ["001122334455", "Cisco"]]
    assert resolved[0]["mapping"] == {"mac": 0, "vendor": 1}
    assert cache.stats()["rows"] == 1


def test_full_rows_are_valid_fallback_for_an_expired_token():
    cache = WorkspaceFileCache(ttl_seconds=3600, max_entries=1, max_rows=100)
    stale_token = cache.put("first.xlsx", {"headers": ["MAC"], "rows": [["001122334455"]]})
    cache.put("second.xlsx", {"headers": ["MAC"], "rows": [["AABBCCDDEEFF"]]})

    try:
        resolve_workspace_files([{"fileToken": stale_token, "mapping": {"mac": 0}}], cache)
    except WorkspaceCacheMiss:
        pass
    else:
        raise AssertionError("stale token must cause a cache miss")

    fallback = resolve_workspace_files(
        [{"fileToken": stale_token, "rows": [["MAC"], ["001122334455"]], "mapping": {"mac": 0}}],
        cache,
    )
    assert fallback[0]["rows"][1][0] == "001122334455"


def test_persisted_table_is_restored_by_new_cache_instance():
    with TemporaryDirectory() as directory:
        first_cache = WorkspaceFileCache(
            ttl_seconds=3600,
            max_entries=4,
            max_rows=100,
            storage_directory=directory,
        )
        token = first_cache.put(
            "restart.xlsx",
            {"headers": ["MAC", "IP"], "rows": [["001122334455", "10.0.0.1"]], "sheet": "Data"},
        )

        restarted_cache = WorkspaceFileCache(
            ttl_seconds=3600,
            max_entries=4,
            max_rows=100,
            storage_directory=directory,
        )
        restored = restarted_cache.get(token)

        assert restored["filename"] == "restart.xlsx"
        assert restored["headers"] == ["MAC", "IP"]
        assert restored["rows"] == [["001122334455", "10.0.0.1"]]
        assert restored["rowCount"] == 1
        assert restarted_cache.stats()["persistentEntries"] == 1


if __name__ == "__main__":
    test_cached_table_is_resolved_without_rows_in_browser_payload()
    test_full_rows_are_valid_fallback_for_an_expired_token()
    test_persisted_table_is_restored_by_new_cache_instance()
    print("workspace cache service test passed")

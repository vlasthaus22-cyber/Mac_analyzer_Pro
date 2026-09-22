from backend.services.system.snapshot_cache_service import SnapshotDeviceCache


def test_snapshot_cache_is_versioned_and_bounded():
    cache = SnapshotDeviceCache(max_entries=2, max_devices=3, max_bytes=100)
    first = [{"mac": "A"}]
    second = [{"mac": "B"}]
    third = [{"mac": "C"}, {"mac": "D"}]
    cache.put("one", (1,), first, 10)
    assert cache.get("one", (1,)) is first
    assert cache.get("one", (2,)) is None
    cache.put("one", (2,), first, 10)
    cache.put("two", (1,), second, 10)
    cache.put("three", (1,), third, 20)
    assert cache.summary() == {"entries": 2, "devices": 3, "bytes": 30}
    assert cache.get("one", (2,)) is None
    assert cache.get("three", (1,)) is third
    cache.invalidate()
    assert cache.summary() == {"entries": 0, "devices": 0, "bytes": 0}

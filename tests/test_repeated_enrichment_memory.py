import gc
import tracemalloc
from tempfile import TemporaryDirectory

from backend.services.workspace.enrichment_service import enrich_files, enrich_workspace_files
from backend.services.workspace.workspace_cache_service import WorkspaceFileCache


def test_repeated_two_file_enrichment_releases_intermediate_allocations():
    count = 12_000
    primary = [["mac", "vendor", "room"]] + [
        [f"A9B8C7{index:06X}", "Stress Vendor", str(100 + index % 80)]
        for index in range(count)
    ]
    enrichment = [["mac", "ip", "switch"]] + [
        [f"A9B8C7{index:06X}", f"10.20.{index // 256}.{index % 256}", f"172.20.{index // 256}.{index % 256}"]
        for index in range(count)
    ]
    files = [
        {"name": "primary.csv", "rows": primary, "mapping": {"mac": 0, "vendor": 1, "room": 2}},
        {"name": "enrichment.csv", "rows": enrichment, "mapping": {"mac": 0, "ip": 1, "switchIp": 2}},
    ]

    tracemalloc.start()
    live_allocations = []
    try:
        for _ in range(4):
            result = enrich_files(files, "primary")
            assert len(result["devices"]) == count
            assert result["devices"][-1]["ip"]
            assert result["devices"][-1]["switchIp"]
            del result
            gc.collect()
            live_allocations.append(tracemalloc.get_traced_memory()[0])
    finally:
        tracemalloc.stop()

    assert max(live_allocations) - min(live_allocations) < 2 * 1024 * 1024


def test_repeated_large_enrichment_streams_inputs_from_sqlite():
    count = 100_000
    with TemporaryDirectory() as directory:
        cache = WorkspaceFileCache(ttl_seconds=3600, max_entries=4, max_rows=count * 3, storage_directory=directory)
        primary_rows = [
            [f"A9B8C7{index:06X}", "Stress Vendor", str(100 + index % 80)]
            for index in range(count)
        ]
        enrichment_rows = [
            [f"A9B8C7{index:06X}", f"10.20.{index // 256}.{index % 256}", f"172.20.{index // 256}.{index % 256}"]
            for index in range(count)
        ]
        primary_token = cache.put("primary-large.csv", {"headers": ["mac", "vendor", "room"], "rows": primary_rows})
        enrichment_token = cache.put("enrichment-large.csv", {"headers": ["mac", "ip", "switch"], "rows": enrichment_rows})
        del primary_rows, enrichment_rows
        gc.collect()

        files = [
            {"name": "primary-large.csv", "fileToken": primary_token, "rowCount": count, "mapping": {"mac": 0, "vendor": 1, "room": 2}},
            {"name": "enrichment-large.csv", "fileToken": enrichment_token, "rowCount": count, "mapping": {"mac": 0, "ip": 1, "switchIp": 2}},
        ]
        stats = cache.stats()
        assert stats["rows"] == count * 2
        assert stats["memoryRows"] == 0

        tracemalloc.start()
        live_allocations = []
        try:
            for _ in range(3):
                result = enrich_workspace_files(files, cache, "primary")
                assert len(result["devices"]) == count
                assert result["devices"][-1]["ip"]
                del result
                gc.collect()
                live_allocations.append(tracemalloc.get_traced_memory()[0])
        finally:
            tracemalloc.stop()

        retained_growth = max(live_allocations) - min(live_allocations)
        assert retained_growth < 4 * 1024 * 1024
        print(
            "sqlite enrichment stress passed; "
            f"rows={count * 2}, runs=3, memoryRows={stats['memoryRows']}, retainedGrowthMiB={retained_growth / 1024 / 1024:.2f}"
        )


if __name__ == "__main__":
    test_repeated_two_file_enrichment_releases_intermediate_allocations()
    test_repeated_large_enrichment_streams_inputs_from_sqlite()
    print("repeated enrichment memory test passed")

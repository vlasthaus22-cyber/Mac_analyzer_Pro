import gc
import tracemalloc

from backend.services.workspace.enrichment_service import enrich_files


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


if __name__ == "__main__":
    test_repeated_two_file_enrichment_releases_intermediate_allocations()
    print("repeated enrichment memory test passed")

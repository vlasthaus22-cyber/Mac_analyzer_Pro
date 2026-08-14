from backend.services.workspace.enrichment_service import enrich_files
from server import (
    ENRICHMENT_JOBS,
    cancel_enrichment_job,
    enrichment_job_status,
    start_enrichment_job,
    update_enrichment_job,
)


FILES = [
    {
        "name": "primary.csv",
        "mapping": {"mac": 0, "vendor": 1, "ip": 2},
        "rows": [
            ["mac", "vendor", "ip"],
            ["AA:BB:CC:00:00:01", "Vendor A", "10.0.0.1"],
            ["AA:BB:CC:00:00:02", "Vendor B", "10.0.0.2"],
        ],
    },
    {
        "name": "extra.csv",
        "mapping": {"mac": 0, "address": 1},
        "rows": [
            ["mac", "address"],
            ["AA:BB:CC:00:00:01", "Rack 1"],
            ["AA:BB:CC:00:00:03", "Rack 3"],
        ],
    },
]


def test_enrichment_progress_callback_and_cancel():
    updates = []
    result = enrich_files(FILES, "merge", progress_callback=updates.append)

    assert result["progress"]["status"] == "completed"
    assert result["progress"]["percent"] == 100
    assert result["progress"]["totalRows"] == 4
    assert updates[0]["status"] == "running"
    assert updates[-1]["percent"] == 100

    calls = {"count": 0}

    def cancelled():
        calls["count"] += 1
        return calls["count"] > 1

    cancelled_result = enrich_files(FILES, "merge", progress_callback=lambda _: None, is_cancelled=cancelled)
    assert cancelled_result["progress"]["status"] == "cancelled"
    assert cancelled_result["progress"]["rows"] == 1


def test_enrichment_job_registry_status_and_cancel():
    ENRICHMENT_JOBS.pop("job-test", None)
    job = start_enrichment_job("job-test", "source.csv", "merge")
    assert job["id"] == "job-test"
    assert enrichment_job_status("job-test")["status"] == "running"

    update_enrichment_job("job-test", {"stage": "smartroom-matching", "rows": 4, "percent": 50, "status": "running"})
    assert enrichment_job_status("job-test")["progress"]["percent"] == 50
    assert [item["stage"] for item in enrichment_job_status("job-test")["stageHistory"]] == [
        "validation", "smartroom-matching",
    ]

    cancelled = cancel_enrichment_job("job-test")
    assert cancelled["cancelRequested"] is True
    assert enrichment_job_status("job-test")["status"] == "cancelled"
    ENRICHMENT_JOBS.pop("job-test", None)


if __name__ == "__main__":
    test_enrichment_progress_callback_and_cancel()
    test_enrichment_job_registry_status_and_cancel()
    print("enrichment jobs test passed")

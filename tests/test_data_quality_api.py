from data_quality_service import analyze_data_quality
from server import db_connection, init_database, quality_reports, save_quality_report


SOURCE = "quality-test-source"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM data_quality_reports WHERE source = ?", (SOURCE,))


def test_quality_report_is_saved_and_listed_from_sqlite():
    init_database()
    cleanup()
    report = analyze_data_quality(
        [{"mac": "AA:BB:CC:00:00:01", "vendor": "Unknown", "ip": "", "room": "", "switchIp": "", "switchPort": ""}],
        invalid=[],
    )

    saved = save_quality_report(report, SOURCE)
    reports = quality_reports(10)
    found = next(item for item in reports if item["id"] == saved["id"])

    assert saved["source"] == SOURCE
    assert found["source"] == SOURCE
    assert found["score"] == saved["score"]
    assert found["summary"]["devices"] == 1
    assert any(issue["id"] == "unknown_vendors" for issue in found["issues"])
    cleanup()


if __name__ == "__main__":
    test_quality_report_is_saved_and_listed_from_sqlite()
    print("data quality api test passed")

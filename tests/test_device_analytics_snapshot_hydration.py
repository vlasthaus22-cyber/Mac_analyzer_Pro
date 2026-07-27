from server import (
    build_device_analytics,
    hydrate_snapshot_devices,
    init_database,
    save_statistics_snapshot,
)


MAC = "0A0B0C0D0E0F"
SNAPSHOT_ID = "device-chronology-hydration"


def test_device_analytics_hydrates_snapshot_metadata_before_building_chronology():
    init_database()
    device = {
        "mac": MAC,
        "macFormatted": "0A:0B:0C:0D:0E:0F",
        "vendor": "Hydrated Vendor",
        "model": "Hydrated Model",
        "address": "Main building",
        "room": "401",
    }
    save_statistics_snapshot(
        [device],
        "Hydrated snapshot",
        "hydrated.xlsx",
        SNAPSHOT_ID,
        "2026-07-27T09:15:00Z",
    )

    snapshots = hydrate_snapshot_devices([{
        "id": SNAPSHOT_ID,
        "name": "Hydrated snapshot",
        "source": "hydrated.xlsx",
        "devices": [],
        "backendStored": True,
    }])
    payload = build_device_analytics(MAC, [device], snapshots)

    assert len(payload["appearances"]) == 1
    assert payload["appearances"][0]["device"]["room"] == "401"
    assert "Появление в снимке" in payload["chronologyRowsHtml"]
    assert "Hydrated snapshot" in payload["chronologyRowsHtml"]


if __name__ == "__main__":
    test_device_analytics_hydrates_snapshot_metadata_before_building_chronology()
    print("device analytics snapshot hydration test passed")

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


def test_sparse_snapshot_appearance_recovers_values_from_matching_history_row():
    sparse = {"mac": MAC, "model": "", "address": "", "source": "old-final.xlsx"}
    history = [{
        "mac": MAC,
        "model": "Model retained from old final",
        "address": "Building retained from old final",
        "source": "old-final.xlsx",
        "recorded_at": "2026-07-01T08:00:00Z",
    }]
    payload = build_device_analytics(MAC, [sparse], [{
        "id": "old-final",
        "name": "Analysis: old-final.xlsx",
        "source": "old-final.xlsx",
        "createdAt": "2026-07-01T08:00:00Z",
        "devices": [sparse],
    }], history)

    appearance = payload["appearances"][0]["device"]
    assert appearance["model"] == "Model retained from old final"
    assert appearance["address"] == "Building retained from old final"


if __name__ == "__main__":
    test_device_analytics_hydrates_snapshot_metadata_before_building_chronology()
    test_sparse_snapshot_appearance_recovers_values_from_matching_history_row()
    print("device analytics snapshot hydration test passed")

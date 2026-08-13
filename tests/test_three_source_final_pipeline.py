import json
import tempfile
from contextlib import contextmanager
from pathlib import Path

import server
from backend.services.analytics.dashboard_service import analyze_dashboard_changes
from backend.services.identity.device_identity_service import build_identity_index
from backend.services.workspace.ddio_overlay_service import (
    apply_ddio_ip_fallback,
    build_ddio_device_index,
    build_ddio_overlay_from_index,
)
from backend.services.workspace.enrichment_service import enrich_files


@contextmanager
def isolated_server_database():
    previous = server.DATABASE_PATH
    with tempfile.TemporaryDirectory() as directory:
        server.DATABASE_PATH = Path(directory) / "mac_analyzer.sqlite3"
        server.init_database()
        try:
            yield server.DATABASE_PATH
        finally:
            server.DATABASE_PATH = previous


def source_files():
    return [
        {
            "name": "file-1-primary.csv",
            "role": "primary",
            "mapping": {"mac": 0, "serialNumber": 1, "model": 2, "switchIp": 3},
            "rows": [
                ["MAC", "Serial", "Model", "Switch IP"],
                ["00:11:22:33:44:55", "SERIAL-A", "Primary model", "10.0.0.1"],
            ],
        },
        {
            "name": "file-2-smartroom.csv",
            "role": "smartroom",
            "mapping": {"mac": 0, "serialNumber": 1, "deviceId": 2, "model": 3, "smartroomId": 4, "room": 5, "switchIp": 6},
            "rows": [
                ["MAC", "Serial", "Device ID", "Model", "Smartroom ID", "Room", "Switch IP"],
                ["00-11-22-33-44-55", "serial-a", "DEV-A", "Conflicting secondary model", "SR-1", "Room 1", "10.0.0.1"],
                ["", "SERIAL-B", "DEV-B", "SmartRoom-only model", "SR-2", "Room 2", "10.0.0.2"],
            ],
        },
    ]


def test_primary_smartroom_union_and_ddio_overlay_have_correct_boundaries():
    result = enrich_files(source_files())
    assert len(result["devices"]) == 2
    primary = next(item for item in result["devices"] if item.get("mac") == "001122334455")
    smartroom_only = next(item for item in result["devices"] if item.get("deviceId") == "DEV-B")
    assert primary["model"] == "Primary model"
    assert primary["smartroomId"] == "SR-1"
    assert primary["hasConflict"] is True
    assert smartroom_only["mac"] == ""
    assert smartroom_only["sourceRoles"] == ["smartroom"]

    ddio_index = build_ddio_device_index(
        [
            ["DEV-B", "192.0.2.20", "192.0.2.21", "192.0.2.20;192.0.2.22"],
            ["DDIO-ONLY", "192.0.2.99", "", "192.0.2.99"],
        ],
        {"deviceId": 0, "reservationIp": 1, "leaseIp": 2, "possibleIps": 3},
    )
    assert apply_ddio_ip_fallback(result["devices"], ddio_index) == 1
    assert smartroom_only["ip"] == "192.0.2.21"
    assert smartroom_only["ipSource"] == "ddio"
    assert len(result["devices"]) == 2, "DDIO-only records must never become final devices"
    assert all(item.get("deviceId") != "DDIO-ONLY" for item in result["devices"])


def test_possible_ddio_ips_are_diagnostic_and_device_id_overlay_is_supported():
    index = build_ddio_device_index(
        [["DEV-B", "", "192.0.2.20;192.0.2.21"]],
        {"deviceId": 0, "ip": 1, "possibleIps": 2},
    )
    device = {"deviceId": "DEV-B", "ip": ""}
    assert apply_ddio_ip_fallback([device], index) == 0
    assert device["ip"] == ""
    overlay = build_ddio_overlay_from_index(index, [{
        "mac": "", "deviceId": "DEV-B", "before": "10.0.0.1", "after": "10.0.0.2",
    }])
    assert overlay["device-id:dev-b"]["possibleIps"] == ["192.0.2.20", "192.0.2.21"]
    assert overlay["device-id:dev-b"]["previousSwitchIp"] == "10.0.0.1"


def test_previous_final_state_is_persistent_idempotent_and_does_not_lose_values():
    with isolated_server_database():
        previous = {
            "deviceId": "DEV-B", "serialNumber": "SERIAL-B", "model": "Known model",
            "address": "Building A", "switchIp": "10.0.0.1", "source": "first.csv",
        }
        first = server.save_final_state_atomic([previous], "Анализ: first.csv", "first.csv", "2026-08-01T10:00:00Z")
        repeated = server.save_final_state_atomic([previous], "Анализ: first.csv", "first.csv", "2026-08-01T10:00:00Z")
        assert repeated["id"] == first["id"]
        assert repeated["deduplicated"] is True
        with server.db_connection() as connection:
            assert connection.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM resolved_device_inventory").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM resolved_device_history").fetchone()[0] == 1

        current = {"deviceId": " dev-b ", "serialNumber": "serial-b", "model": "", "address": "", "switchIp": "10.0.0.2"}
        context = server.build_enrichment_context([current])
        enriched = server.enrich_device(current, context)
        assert enriched["model"] == "Known model"
        assert enriched["address"] == "Building A"
        assert enriched["switchIp"] == "10.0.0.2"
        assert enriched["previousFinalMatched"] is True
        assert enriched["internalDeviceId"]

        changes = server.merge_switch_ip_changes_with_history([enriched], context)
        assert changes[0]["before"] == "10.0.0.1"
        assert changes[0]["after"] == "10.0.0.2"
        server.save_final_state_atomic([enriched], "Анализ: second.csv", "second.csv", "2026-08-02T10:00:00Z")
        restored = server.all_devices_page(0, 100)
        assert restored["total"] == 1
        assert restored["items"][0]["address"] == "Building A"
        assert restored["items"][0]["switchIp"] == "10.0.0.2"


def test_final_state_transaction_rolls_back_inventory_when_snapshot_fails():
    with isolated_server_database():
        original = server._save_statistics_snapshot_row

        def fail_snapshot(*_args, **_kwargs):
            raise RuntimeError("simulated snapshot failure")

        server._save_statistics_snapshot_row = fail_snapshot
        try:
            try:
                server.save_final_state_atomic([{"deviceId": "DEV-ROLLBACK"}], "failure", "test", "2026-08-03T10:00:00Z")
            except RuntimeError:
                pass
            else:
                raise AssertionError("simulated transaction failure was ignored")
        finally:
            server._save_statistics_snapshot_row = original
        with server.db_connection() as connection:
            assert connection.execute("SELECT COUNT(*) FROM resolved_device_inventory").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM resolved_device_history").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0


def test_critical_analytics_includes_switch_change_for_device_without_mac():
    before = {"internalDeviceId": "dev-room-b", "deviceId": "DEV-B", "model": "Codec", "switchIp": "10.0.0.1", "ip": "192.0.2.20"}
    after = {**before, "switchIp": "10.0.0.2", "possibleIps": ["192.0.2.20", "192.0.2.21"], "ipSource": "DDIO"}
    result = analyze_dashboard_changes(
        [
            {"id": "before", "createdAt": "2026-08-01T10:00:00Z", "devices": [before]},
            {"id": "after", "createdAt": "2026-08-02T10:00:00Z", "devices": [after]},
        ],
        [],
        {"changeMode": "snapshots", "baselineSnapshotId": "before", "comparisonSnapshotId": "after"},
    )
    switch_change = next(item for item in result["changes"] if item["field"] == "switchIp")
    assert switch_change["severity"] == "critical"
    assert switch_change["before"] == "10.0.0.1"
    assert switch_change["after"] == "10.0.0.2"
    assert switch_change["possibleDdioIps"] == ["192.0.2.20", "192.0.2.21"]
    assert result["summary"]["modified"] == 1


def test_user_search_covers_non_mac_identifiers_and_ip_page_is_absent():
    payload = server.filter_result_devices(
        [{"internalDeviceId": "dev-b", "deviceId": "DEV-B", "hostname": "room-codec", "serialNumber": "SERIAL-B", "ip": "192.0.2.20", "valid": True}],
        [],
        {"query": "serial-b", "limit": 25},
    )
    assert payload["pagination"]["total"] == 1
    html = (Path(__file__).parents[1] / "index.html").read_text(encoding="utf-8")
    assert 'data-view="ip-changes"' not in html
    assert '>Изменения IP<' not in html
    assert "критических изменений" in html


if __name__ == "__main__":
    test_primary_smartroom_union_and_ddio_overlay_have_correct_boundaries()
    test_possible_ddio_ips_are_diagnostic_and_device_id_overlay_is_supported()
    test_previous_final_state_is_persistent_idempotent_and_does_not_lose_values()
    test_final_state_transaction_rolls_back_inventory_when_snapshot_fails()
    test_critical_analytics_includes_switch_change_for_device_without_mac()
    test_user_search_covers_non_mac_identifiers_and_ip_page_is_absent()
    print("three-source final pipeline tests passed")

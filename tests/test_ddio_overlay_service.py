from copy import deepcopy

from backend.services.workspace.ddio_overlay_service import build_ddio_overlay
from backend.services.workspace.enrichment_service import enrich_files
from server import merge_switch_ip_changes_with_history


def test_ddio_uses_reservation_and_lease_mac_without_mutating_devices():
    files = [
        {
            "name": "primary.xlsx",
            "mapping": {"mac": 0, "ip": 1, "switchIp": 2},
            "rows": [
                ["MAC", "IP", "Switch IP"],
                ["00:11:22:33:44:55", "192.168.1.10", "10.0.0.1"],
                ["00:11:22:33:44:66", "192.168.1.11", "10.0.0.8"],
            ],
        },
        {
            "name": "enrichment.xlsx",
            "mapping": {"mac": 0, "switchIp": 1},
            "rows": [
                ["MAC", "Switch IP"],
                ["00:11:22:33:44:55", "10.0.0.2"],
                ["00:11:22:33:44:66", "10.0.0.8"],
            ],
        },
    ]
    enriched = enrich_files(files)
    assert enriched["switchIpChanges"] == []
    devices_before = deepcopy(enriched["devices"])
    rows = [
        ["192.168.1.20", "00:11:22:33:44:55", ""],
        ["192.168.1.30", "", "00:11:22:33:44:55"],
        ["192.168.1.40", "00:11:22:33:44:66", ""],
    ]
    overlay = build_ddio_overlay(
        rows,
        {"ip": 0, "reservationMac": 1, "leaseMac": 2},
        [{"mac": "001122334455", "before": "10.0.0.1", "after": "10.0.0.2"}],
        {"001122334455": "192.168.1.10"},
    )
    assert overlay == {
        "001122334455": {
            "ip": "192.168.1.30",
            "possibleIps": ["192.168.1.20", "192.168.1.30"],
            "match": "lease",
            "source": "DDIO",
            "previousSwitchIp": "10.0.0.1",
            "currentSwitchIp": "10.0.0.2",
        }
    }
    assert enriched["devices"] == devices_before


def test_ddio_requires_ip_and_at_least_one_mac_column():
    changes = [{"mac": "001122334455", "before": "10.0.0.1", "after": "10.0.0.2"}]
    try:
        build_ddio_overlay([], {"reservationMac": 0}, changes)
    except ValueError as error:
        assert "IP" in str(error)
    else:
        raise AssertionError("DDIO mapping without IP must fail")
    try:
        build_ddio_overlay([], {"ip": 0}, changes)
    except ValueError as error:
        assert "MAC" in str(error)
    else:
        raise AssertionError("DDIO mapping without MAC must fail")


def test_ddio_uses_independent_reservation_and_lease_ip_columns_after_h():
    changes = [{"mac": "001122334455", "before": "10.0.0.1", "after": "10.0.0.2"}]
    row = [""] * 14
    row[9] = "00:11:22:33:44:55"
    row[10] = "192.168.1.40"
    row[12] = "00:11:22:33:44:55"
    row[13] = "192.168.1.50"
    overlay = build_ddio_overlay(
        [row],
        {"reservationMac": 9, "reservationIp": 10, "leaseMac": 12, "leaseIp": 13},
        changes,
        {"001122334455": "192.168.1.10"},
    )
    assert overlay == {
        "001122334455": {
            "ip": "192.168.1.50",
            "possibleIps": ["192.168.1.40", "192.168.1.50"],
            "match": "lease",
            "source": "DDIO",
            "previousSwitchIp": "10.0.0.1",
            "currentSwitchIp": "10.0.0.2",
        }
    }


def test_ddio_switch_change_is_derived_from_saved_exact_mac_history():
    changes = merge_switch_ip_changes_with_history(
        [{"mac": "00:11:22:33:44:55", "switchIp": "10.0.0.9", "ip": "192.168.1.10"}],
        {"latestHistory": {"001122334455": {"switch_ip": "10.0.0.1"}}},
        [],
    )
    assert changes == [{"mac": "001122334455", "before": "10.0.0.1", "after": "10.0.0.9"}]
    overlay = build_ddio_overlay(
        [["00:11:22:33:44:55", "192.168.1.50"]],
        {"leaseMac": 0, "leaseIp": 1},
        changes,
        {"001122334455": "192.168.1.10"},
    )
    assert overlay["001122334455"]["ip"] == "192.168.1.50"


def test_enrichment_fills_blanks_without_overwriting_primary_values():
    enriched = enrich_files(
        [
            {
                "name": "current.csv",
                "mapping": {"mac": 0, "model": 1, "address": 2, "switchPort": 3},
                "rows": [["MAC", "Model", "Address", "Port"], ["00:1A:11:22:33:44", "Apple TV 4K", "", "Gi1/0/10"]],
            },
            {
                "name": "previous.csv",
                "mapping": {"mac": 0, "model": 1, "address": 2, "switchPort": 3},
                "rows": [["MAC", "Model", "Address", "Port"], ["00:1A:11:22:33:44", "Apple TV", "Building A", "Gi1/0/8"]],
            },
        ]
    )
    assert enriched["devices"][0]["model"] == "Apple TV 4K"
    assert enriched["devices"][0]["address"] == "Building A"
    assert enriched["devices"][0]["switchPort"] == "Gi1/0/10"
    assert enriched["devices"][0]["source"] == "current.csv + previous.csv"
    assert enriched["devices"][0]["hasConflict"] is True


if __name__ == "__main__":
    test_ddio_uses_reservation_and_lease_mac_without_mutating_devices()
    test_ddio_requires_ip_and_at_least_one_mac_column()
    test_ddio_uses_independent_reservation_and_lease_ip_columns_after_h()
    test_ddio_switch_change_is_derived_from_saved_exact_mac_history()
    test_enrichment_fills_blanks_without_overwriting_primary_values()
    print("DDIO overlay service test passed")

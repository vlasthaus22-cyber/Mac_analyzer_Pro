from backend.services.identity.device_identity_service import (
    build_identity_index,
    find_identity_match,
    merge_device_records,
    preserve_known_values,
)
from backend.services.workspace.ddio_overlay_service import (
    apply_ddio_ip_fallback,
    build_ddio_device_index,
    build_ddio_overlay_from_index,
)
from backend.services.workspace.enrichment_service import enrich_files


def test_secondary_only_device_is_preserved_with_provenance():
    result = enrich_files([
        {"name": "sr.csv", "role": "primary", "mapping": {"mac": 0, "smartroomId": 1}, "rows": [["mac", "sr"], ["00:11:22:33:44:55", "SR-1"]]},
        {"name": "enrichment.csv", "role": "enrichment", "mapping": {"mac": 0, "ip": 1, "model": 2}, "rows": [["mac", "ip", "model"], ["00:11:22:33:44:66", "192.0.2.66", "Codec X"]]},
    ], "primary")
    assert len(result["devices"]) == 2
    secondary = next(item for item in result["devices"] if item["mac"] == "001122334466")
    assert secondary["ip"] == "192.0.2.66"
    assert secondary["sourceFiles"] == ["enrichment.csv"]
    assert secondary["sourceRoles"] == ["enrichment"]


def test_ddio_fills_missing_ip_and_retains_source():
    index = build_ddio_device_index(
        [["00:11:22:33:44:55", "192.0.2.10"]],
        {"leaseMac": 0, "leaseIp": 1},
    )
    devices = [{"mac": "001122334455", "ip": "", "switchIp": "10.0.0.2"}]
    assert apply_ddio_ip_fallback(devices, index) == 1
    assert devices[0]["ip"] == "192.0.2.10"
    assert devices[0]["ipSource"] == "ddio"
    assert devices[0]["fieldSources"]["ip"] == "DDIO"
    overlay = build_ddio_overlay_from_index(index, [{"mac": devices[0]["mac"], "before": "10.0.0.1", "after": "10.0.0.2"}])
    assert overlay[devices[0]["mac"]]["previousSwitchIp"] == "10.0.0.1"
    assert overlay[devices[0]["mac"]]["source"] == "DDIO"


def test_previous_final_preserves_non_empty_values_by_strong_identity():
    previous = {"mac": "00:11:22:33:44:55", "model": "Codec X", "address": "Floor 5", "switchIp": "10.0.0.1"}
    current = {"mac": "001122334455", "model": "", "address": "", "switchIp": "10.0.0.2"}
    index = build_identity_index([previous])
    matched = find_identity_match(current, index)
    result = preserve_known_values(current, matched)
    assert result["model"] == "Codec X"
    assert result["address"] == "Floor 5"
    assert result["switchIp"] == "10.0.0.2"
    assert result["previousFinalMatched"] is True


def test_previous_physical_address_is_reused_only_by_strong_serial_identity():
    previous = {
        "mac": "00:11:22:33:44:55",
        "serialNumber": "SERIAL-100",
        "hostname": "room-codec-1",
    }
    current = {
        "mac": "",
        "serialNumber": " serial-100 ",
        "hostname": "ROOM-CODEC-1",
    }
    match = find_identity_match(current, build_identity_index([previous]))
    result = preserve_known_values(current, match)
    assert result["mac"] == "00:11:22:33:44:55"
    assert result["fieldSources"]["mac"] == "previous-final"


def test_repeated_identical_enrichment_is_idempotent():
    files = [
        {
            "name": "sr.csv",
            "role": "primary",
            "mapping": {"mac": 0, "smartroomId": 1},
            "rows": [["mac", "sr"], ["00:11:22:33:44:55", "SR-1"]],
        },
        {
            "name": "enrichment.csv",
            "role": "enrichment",
            "mapping": {"mac": 0, "ip": 1},
            "rows": [["mac", "ip"], ["00:11:22:33:44:55", "192.0.2.55"]],
        },
    ]
    first = enrich_files(files, "primary")["devices"]
    second = enrich_files(files, "primary")["devices"]
    assert second == first
    assert len(second) == 1


def test_conflicting_sources_are_explicit_and_deterministic():
    first = merge_device_records({}, {"mac": "001122334455", "ip": "192.0.2.1"}, source="sr.csv", role="primary")
    merged = merge_device_records(first, {"mac": "001122334455", "ip": "192.0.2.2"}, source="extra.csv", role="enrichment", prefer_existing=True)
    assert merged["ip"] == "192.0.2.1"
    assert merged["hasConflict"] is True
    assert merged["conflicts"][0]["alternative"] == "192.0.2.2"


if __name__ == "__main__":
    test_secondary_only_device_is_preserved_with_provenance()
    test_ddio_fills_missing_ip_and_retains_source()
    test_previous_final_preserves_non_empty_values_by_strong_identity()
    test_previous_physical_address_is_reused_only_by_strong_serial_identity()
    test_repeated_identical_enrichment_is_idempotent()
    test_conflicting_sources_are_explicit_and_deterministic()
    print("device identity enrichment tests passed")

from server import db_connection, init_database, mappings_panel_payload


VENDOR_KEY = "ABCDEF"
MODEL_KEY = "ABCDEF01"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM vendor_mappings WHERE oui = ?", (VENDOR_KEY,))
        conn.execute("DELETE FROM model_mappings WHERE prefix = ?", (MODEL_KEY,))


def test_mappings_panel_payload_combines_vendor_and_model_rules():
    init_database()
    cleanup()
    with db_connection() as conn:
        conn.execute("INSERT INTO vendor_mappings (oui, vendor, source, updated_at) VALUES (?, ?, ?, ?)", (VENDOR_KEY, "Panel Vendor", "test", "2026-01-01T00:00:00Z"))
        conn.execute("INSERT INTO model_mappings (prefix, model, source, updated_at) VALUES (?, ?, ?, ?)", (MODEL_KEY, "Panel Model", "test", "2026-01-01T00:00:00Z"))

    panel = mappings_panel_payload()

    assert "vendors" in panel
    assert "models" in panel
    assert "vendorRules" in panel
    assert "modelRules" in panel
    assert "vendorRowsHtml" in panel
    assert "modelRowsHtml" in panel
    assert panel["summary"]["vendorRules"] == len(panel["vendorRules"])
    assert panel["summary"]["modelRules"] == len(panel["modelRules"])
    assert len(panel["vendorRules"]) <= 250
    assert panel["summary"]["totalVendorRules"] >= len(panel["vendorRules"])
    assert panel["summary"]["totalModelRules"] >= len(panel["modelRules"])
    assert f'data-remove-vendor="{VENDOR_KEY}"' in panel["vendorRowsHtml"]
    assert "Panel Vendor" in panel["vendorRowsHtml"]
    assert f'data-remove-model="{MODEL_KEY}"' in panel["modelRowsHtml"]
    assert 'data-model-prefixes="Panel Model"' in panel["modelRowsHtml"]
    cleanup()


if __name__ == "__main__":
    test_mappings_panel_payload_combines_vendor_and_model_rules()
    print("mappings panel test passed")

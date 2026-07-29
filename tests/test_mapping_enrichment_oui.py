from server import (
    db_connection,
    enrichment_field_summary,
    init_database,
    mapping_summary,
    normalize_enrichment_fields,
    oui_settings,
    save_oui_settings,
)


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM app_settings WHERE key = 'oui_format'")


def test_mapping_summary_enrichment_fields_and_oui_settings():
    init_database()
    cleanup()

    summary = mapping_summary(
        ["MAC Address", "Vendor", "IP", "Room"],
        {"mac": 0, "vendor": 1, "ip": 2},
        {"vendor": True, "model": False, "ip": True, "history": False},
    )
    assert summary["headers"] == 4
    assert {"field": "mac", "index": 0, "header": "MAC Address"} in summary["mapped"]
    assert "model" in summary["missing"]
    assert summary["requiredMissing"] == []
    assert summary["enrichment"]["enabledCount"] >= 2
    assert "model" in summary["enrichment"]["disabled"]
    assert "history" in summary["enrichment"]["disabled"]

    fields = normalize_enrichment_fields({"vendor": False, "room": True})
    assert fields["vendor"] is False
    assert fields["room"] is True
    assert fields["history"] is True
    field_stats = enrichment_field_summary(fields)
    assert field_stats["total"] == 9
    assert "vendor" in field_stats["disabled"]

    saved = save_oui_settings({"length": 5, "style": "dash"})
    assert saved["length"] == 5
    assert saved["style"] == "dash"
    loaded = oui_settings()
    assert loaded["length"] == 5
    assert loaded["style"] == "dash"

    fallback = save_oui_settings({"length": 99, "style": "bad"})
    assert fallback["length"] == 6
    assert fallback["style"] == "plain"

    cleanup()


if __name__ == "__main__":
    test_mapping_summary_enrichment_fields_and_oui_settings()
    print("mapping enrichment oui test passed")

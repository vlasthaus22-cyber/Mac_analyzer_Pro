from server import enrich_device, quality_panel_payload


def test_quality_panel_payload_prepares_issue_rows():
    devices = [
        enrich_device({"mac": "AABBCC000201", "vendor": "Unknown", "model": "", "ip": "bad-ip"}),
        enrich_device({"mac": "AABBCC000201", "vendor": "Unknown", "model": "", "ip": ""}),
    ]
    panel = quality_panel_payload(devices, invalid=[{"row": 3}], source="quality-panel-test", save=False)

    assert panel["headline"].startswith("Quality score")
    assert "devices" in panel["summaryText"]
    assert panel["issueRows"]
    assert all("percent" in item for item in panel["issueRows"])
    assert panel["recommendationRows"]


if __name__ == "__main__":
    test_quality_panel_payload_prepares_issue_rows()
    print("quality panel test passed")

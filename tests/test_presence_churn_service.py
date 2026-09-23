from backend.services.analytics.presence_churn_service import build_presence_churn


def test_presence_churn_requires_disappearance_and_return():
    mac = "00:11:22:33:44:55"
    snapshots = [
        {"id": "1", "devices": [{"mac": mac}]},
        {"id": "2", "devices": []},
        {"id": "3", "devices": [{"mac": mac, "model": "Cisco"}]},
        {"id": "4", "devices": []},
        {"id": "5", "devices": [{"mac": mac, "model": "Cisco"}]},
    ]
    payload = build_presence_churn(snapshots)
    assert payload["total"] == 1
    assert payload["items"][0]["disappearances"] == 2
    assert payload["items"][0]["reappearances"] == 2
    assert payload["items"][0]["model"] == "Cisco"

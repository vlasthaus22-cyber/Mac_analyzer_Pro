import base64
import json
from pathlib import Path

from server import export_app_backup, restore_app_backup


def test_backup_export_restore_roundtrip_and_legacy_state():
    state = {"devices": [{"mac": "AABBCC000001", "vendor": "Cisco"}], "theme": "dark"}
    exported = export_app_backup(state)

    assert exported["filename"] == "mac-analyzer-backup.json"
    assert exported["mimeType"] == "application/json"
    assert exported["bytes"] == len(exported["content"].encode("utf-8"))
    assert Path(exported["storedPath"]).is_file()
    assert Path(exported["storedPath"]).parent.name == "backups"

    restored = restore_app_backup(base64.b64encode(exported["content"].encode("utf-8")).decode("ascii"))
    assert restored["version"] == 1
    assert restored["state"] == state
    assert Path(restored["storedPath"]).is_file()

    legacy = base64.b64encode(json.dumps(state).encode("utf-8")).decode("ascii")
    restored_legacy = restore_app_backup(legacy)
    assert restored_legacy["version"] == 0
    assert restored_legacy["state"] == state


if __name__ == "__main__":
    test_backup_export_restore_roundtrip_and_legacy_state()
    print("backup service test passed")

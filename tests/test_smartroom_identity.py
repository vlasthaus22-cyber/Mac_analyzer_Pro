from backend.services.detection.smartroom_service import (
    normalized_room_name,
    smartroom_identity,
    synchronize_smartroom_device,
)


def test_smartroom_id_and_room_name_remain_independent():
    first = synchronize_smartroom_device({"room": "  Переговорная   1 ", "smartroomId": "legacy-1"})
    second = synchronize_smartroom_device({"room": "Переговорная 2", "smartroomId": "legacy-2"})

    assert first["room"] == "Переговорная 1"
    assert first["smartroomId"] == "legacy-1"
    assert second["room"] == "Переговорная 2"
    assert second["smartroomId"] == "legacy-2"
    assert first["smartroomId"] != second["smartroomId"]


def test_legacy_id_resolves_to_exact_room_name():
    assert normalized_room_name("  Зал   12  ") == "Зал 12"
    room, smartroom_id = smartroom_identity("", "SR-12", {"SR-12": "Зал 12"})
    assert room == "Зал 12"
    assert smartroom_id == "SR-12"


def test_room_name_never_backfills_missing_smartroom_id():
    device = synchronize_smartroom_device({"room": "Переговорная 3", "smartroomId": ""})
    assert device == {"room": "Переговорная 3", "smartroomId": ""}


if __name__ == "__main__":
    test_smartroom_id_and_room_name_remain_independent()
    test_legacy_id_resolves_to_exact_room_name()
    test_room_name_never_backfills_missing_smartroom_id()
    print("smartroom identity test passed")

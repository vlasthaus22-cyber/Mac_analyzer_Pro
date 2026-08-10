from backend.services.detection.smartroom_service import (
    normalized_room_name,
    smartroom_identity,
    synchronize_smartroom_device,
)


def test_numbered_rooms_remain_distinct_and_ids_equal_full_names():
    first = synchronize_smartroom_device({"room": "  Переговорная   1 ", "smartroomId": "legacy-1"})
    second = synchronize_smartroom_device({"room": "Переговорная 2", "smartroomId": "legacy-2"})

    assert first["room"] == first["smartroomId"] == "Переговорная 1"
    assert second["room"] == second["smartroomId"] == "Переговорная 2"
    assert first["smartroomId"] != second["smartroomId"]


def test_legacy_id_resolves_to_exact_room_name():
    assert normalized_room_name("  Зал   12  ") == "Зал 12"
    room, smartroom_id = smartroom_identity("", "SR-12", {"SR-12": "Зал 12"})
    assert room == smartroom_id == "Зал 12"


if __name__ == "__main__":
    test_numbered_rooms_remain_distinct_and_ids_equal_full_names()
    test_legacy_id_resolves_to_exact_room_name()
    print("smartroom identity test passed")

from backend.services.detection.oui_service import format_oui, format_oui_for_devices


def test_oui_formats_and_lengths():
    assert format_oui("00:11:22:33:44:55", 3, "plain") == "001122"
    assert format_oui("00:11:22:33:44:55", 3, "colon") == "00:11:22"
    assert format_oui("00:11:22:33:44:55", 4, "dash") == "00-11-22-33"
    assert format_oui("001122334455", 5, "dot") == "0011.2233.44"
    assert format_oui("001122334455", 9, "plain") == "001122334455"
    assert format_oui("0011", 3, "plain") == ""

    formatted = format_oui_for_devices(
        [{"mac": "AA:BB:CC:DD:EE:FF"}, {"macFormatted": "00-11-22-33-44-55"}],
        4,
        "colon",
    )
    assert formatted == [
        {"mac": "AABBCCDDEEFF", "oui": "AA:BB:CC:DD"},
        {"mac": "001122334455", "oui": "00:11:22:33"},
    ]


if __name__ == "__main__":
    test_oui_formats_and_lengths()
    print("oui service test passed")

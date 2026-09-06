from backend.services.detection.vendor_detector_service import detect_model, detect_vendor, infer_similar_vendor


def test_vendor_detector_prefers_file_then_mac5_then_oui():
    rules = [
        {"oui": "AABBCC", "vendor": "OUI Vendor", "source": "builtin"},
        {"oui": "AABBCC0000", "vendor": "MAC5 Vendor", "source": "custom"},
    ]

    file_vendor = detect_vendor("AA:BB:CC:00:00:01", "File Vendor", "", rules)
    mac5_vendor = detect_vendor("AA:BB:CC:00:00:01", "", "", rules)
    oui_vendor = detect_vendor("AA:BB:CC:12:34:56", "", "", rules)

    assert file_vendor["value"] == "File Vendor"
    assert file_vendor["source"] == "file"
    assert file_vendor["confidence"] == 1.0
    assert mac5_vendor["value"] == "MAC5 Vendor"
    assert mac5_vendor["source"] == "mac5"
    assert mac5_vendor["matchedPrefix"] == "AABBCC0000"
    assert mac5_vendor["confidence"] > oui_vendor["confidence"]
    assert oui_vendor["value"] == "OUI Vendor"
    assert oui_vendor["source"] == "oui"


def test_vendor_detector_infers_from_similar_history():
    inferred = infer_similar_vendor(
        "AA:BB:CC:11:22:33",
        [
            {"mac": "AABBCC112244", "vendor": "Similar Vendor"},
            {"mac": "AABBCC112255", "vendor": "Similar Vendor"},
            {"mac": "AABBCC998877", "vendor": "Other Vendor"},
        ],
    )

    assert inferred["value"] == "Similar Vendor"
    assert inferred["source"] == "similar"
    assert inferred["matchedPrefix"] == "AABBCC1122"
    assert inferred["matches"] == 2


def test_model_detector_uses_longest_prefix():
    model = detect_model(
        "AA:BB:CC:00:00:01",
        "",
        "",
        [
            {"prefix": "AABBCC", "model": "Generic Model", "source": "builtin"},
            {"prefix": "AABBCC0000", "model": "Specific Model", "source": "custom"},
        ],
    )

    assert model["value"] == "Specific Model"
    assert model["source"] == "prefix"
    assert model["matchedPrefix"] == "AABBCC0000"


def test_vendor_detector_matches_python_text_keywords():
    vendor = detect_vendor(
        "12:34:56:78:90:AB",
        "",
        "",
        [],
        text_values=["Cisco Catalyst 9300 access switch"],
    )

    assert vendor["value"] == "Cisco"
    assert vendor["source"] == "text"
    assert vendor["confidence"] >= 0.6


def test_model_detector_uses_python_compatible_mac5_prefix():
    model = detect_model(
        "AA:BB:CC:12:34:01",
        "",
        "",
        [{"prefix": "AABBCC9900", "model": "Wrong 4-byte Model", "source": "custom"},
         {"prefix": "AABBCC1200", "model": "Compatible MAC5 Model", "source": "custom"}],
    )

    assert model["value"] == "Compatible MAC5 Model"
    assert model["source"] == "prefix_compatible"
    assert model["matchedPrefix"] == "AABBCC1200"


def test_unknown_model_placeholder_does_not_block_automatic_detection():
    from_history = detect_model("AA:BB:CC:00:00:01", "Unknown", "Known Room Kit", [])
    from_prefix = detect_model(
        "AA:BB:CC:12:34:01",
        "Не определено",
        "",
        [{"prefix": "AABBCC1234", "model": "Codec Pro", "source": "learned"}],
    )

    assert from_history["value"] == "Known Room Kit"
    assert from_history["source"] == "history"
    assert from_prefix["value"] == "Codec Pro"
    assert from_prefix["source"] == "prefix"


def test_detector_settings_control_automatic_sources():
    disabled_vendor = detect_vendor(
        "AA:BB:CC:00:00:01",
        "",
        "",
        [{"oui": "AABBCC", "vendor": "OUI Vendor", "source": "builtin"}],
        text_values=["Cisco Catalyst"],
        settings={"enabled": False},
    )
    no_text_vendor = detect_vendor(
        "12:34:56:78:90:AB",
        "",
        "",
        [],
        text_values=["Cisco Catalyst"],
        settings={"useText": False},
    )
    no_mac5_model = detect_model(
        "AA:BB:CC:12:34:01",
        "",
        "",
        [{"prefix": "AABBCC1200", "model": "Compatible MAC5 Model", "source": "custom"}],
        settings={"useMac5": False},
    )

    assert disabled_vendor["source"] == "disabled"
    assert no_text_vendor["source"] == "unknown"
    assert no_mac5_model["source"] == "unknown"


if __name__ == "__main__":
    test_vendor_detector_prefers_file_then_mac5_then_oui()
    test_vendor_detector_infers_from_similar_history()
    test_model_detector_uses_longest_prefix()
    test_vendor_detector_matches_python_text_keywords()
    test_model_detector_uses_python_compatible_mac5_prefix()
    test_unknown_model_placeholder_does_not_block_automatic_detection()
    test_detector_settings_control_automatic_sources()
    print("vendor detector service test passed")

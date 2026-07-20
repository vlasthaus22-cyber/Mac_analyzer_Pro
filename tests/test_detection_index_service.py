from backend.services.detection.detection_index_service import (
    build_similarity_index,
    build_vendor_model_history_index,
    compile_rule_index,
    indexed_history_suggestion,
    indexed_prefix_rule,
    similarity_detection,
)
from backend.services.detection.vendor_detector_service import detect_model, detect_vendor


def test_compiled_rules_prefer_oui_five_then_four_then_three_bytes():
    rules = [
        {"oui": "AABBCC", "vendor": "Vendor 3", "source": "builtin"},
        {"oui": "AABBCC11", "vendor": "Vendor 4", "source": "custom"},
        {"oui": "AABBCC1122", "vendor": "Vendor 5", "source": "custom"},
    ]
    index = compile_rule_index(rules, "oui", "vendor")

    assert indexed_prefix_rule("AA:BB:CC:11:22:99", index)["vendor"] == "Vendor 5"
    assert indexed_prefix_rule("AA:BB:CC:11:99:00", index)["vendor"] == "Vendor 4"
    assert indexed_prefix_rule("AA:BB:CC:99:00:00", index)["vendor"] == "Vendor 3"

    detected = detect_vendor("AA:BB:CC:11:22:99", "", "", rules, rule_index=index)
    assert detected["value"] == "Vendor 5"
    assert detected["matchedPrefix"] == "AABBCC1122"


def test_similarity_index_infers_python_vendor_and_model_logic():
    observations = [
        {"mac": "AABBCC112201", "vendor": "Similar Vendor", "model": "Model X"},
        {"mac": "AABBCC112202", "vendor": "Similar Vendor", "model": "Model X"},
        {"mac": "AABBCC119999", "vendor": "Other Vendor", "model": "Model Y"},
    ]
    result = similarity_detection("AABBCC1122FF", build_similarity_index(observations))

    assert result["vendor"] == "Similar Vendor"
    assert result["model"] == "Model X"
    assert result["matchedPrefix"] == "AABBCC1122"

    model = detect_model("AABBCC1122FF", "", "", [], similar_result=result)
    assert model["value"] == "Model X"
    assert model["source"] == "similar"


def test_similarity_index_does_not_allocate_empty_prefix_buckets():
    index = build_similarity_index([
        {"mac": f"AABBCC{number:06X}", "vendor": "Unknown", "model": ""}
        for number in range(1000)
    ])

    assert index == {10: {}, 8: {}, 6: {}}


def test_indexed_vendor_model_history_uses_exact_then_mac5_oui4_oui3():
    rows = [
        {"mac": "DDEEFF112233", "vendor": "Exact Vendor", "model": "Exact Model"},
        {"mac": "DDEEFF112244", "vendor": "Prefix Vendor", "model": "Prefix Model"},
        {"mac": "DDEEFF112255", "vendor": "Prefix Vendor", "model": "Prefix Model"},
    ]
    index = build_vendor_model_history_index(rows)
    settings = {"enabled": True, "useMac5Match": True, "useOuiMatch": True}

    exact = indexed_history_suggestion("DDEEFF112233", index, settings)
    prefix = indexed_history_suggestion("DDEEFF1122AA", index, settings)

    assert exact["source"] == "vendor_model_history_exact"
    assert exact["model"] == "Exact Model"
    assert prefix["source"] == "vendor_model_history_prefix"
    assert prefix["vendor"] == "Prefix Vendor"
    assert prefix["matchedPrefix"] == "DDEEFF1122"


if __name__ == "__main__":
    test_compiled_rules_prefer_oui_five_then_four_then_three_bytes()
    test_similarity_index_infers_python_vendor_and_model_logic()
    test_similarity_index_does_not_allocate_empty_prefix_buckets()
    test_indexed_vendor_model_history_uses_exact_then_mac5_oui4_oui3()
    print("detection index service test passed")

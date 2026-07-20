"""Measure JSON overhead removed by workspace file tokens."""

import json
import time


def main(row_count: int = 100_000) -> None:
    rows = [
        [
            f"001122{index:06X}",
            f"Vendor {index % 100}",
            f"Model {index % 250}",
            f"10.0.{index // 256 % 256}.{index % 256}",
            f"Address {index % 500}",
            f"Room {index % 50}",
        ]
        for index in range(row_count)
    ]
    file_info = {
        "id": "main",
        "name": "devices.xlsx",
        "role": "primary",
        "rows": [["MAC", "Vendor", "Model", "IP", "Address", "Room"], *rows],
        "mapping": {"mac": 0, "vendor": 1, "model": 2, "ip": 3, "address": 4, "room": 5},
        "fileToken": "workspace-token",
        "rowCount": row_count,
    }
    started = time.perf_counter()
    full = json.dumps({"files": [file_info]}, ensure_ascii=False, separators=(",", ":"))
    full_ms = (time.perf_counter() - started) * 1000
    compact_file = {key: value for key, value in file_info.items() if key != "rows"}
    started = time.perf_counter()
    compact = json.dumps({"files": [compact_file]}, ensure_ascii=False, separators=(",", ":"))
    compact_ms = (time.perf_counter() - started) * 1000
    print(json.dumps({
        "rows": row_count,
        "fullBytes": len(full.encode("utf-8")),
        "compactBytes": len(compact.encode("utf-8")),
        "payloadReduction": round(len(full) / max(1, len(compact))),
        "fullSerializationMs": round(full_ms, 2),
        "compactSerializationMs": round(compact_ms, 4),
    }))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path

from openpyxl import Workbook


def create_fixture(output: Path, rows: int = 100_000) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet("Devices")
    worksheet.append(("Smartroom ID", "MAC", "IP switch", "Model"))
    for index in range(rows):
        worksheet.append(
            (
                f"ROOM-{index % 2_500:04d}",
                f"02:00:{(index >> 16) & 0xFF:02X}:{(index >> 8) & 0xFF:02X}:{index & 0xFF:02X}:01",
                f"10.{(index >> 16) & 0xFF}.{(index >> 8) & 0xFF}.{index & 0xFF}",
                f"Model-{index % 25}",
            )
        )
    workbook.save(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the repeatable XLSX memory-test fixture.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--rows", type=int, default=100_000)
    arguments = parser.parse_args()
    create_fixture(arguments.output.resolve(), arguments.rows)


if __name__ == "__main__":
    main()

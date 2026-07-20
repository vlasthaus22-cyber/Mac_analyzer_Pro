"""Run an end-to-end smoke test against a built portable backend."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import Workbook


def request_json(base_url: str, method: str, path: str, payload: Any = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def import_xlsx(base_url: str, filename: str, rows: list[list[str]]) -> dict[str, Any]:
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Devices")
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    request = urllib.request.Request(
        base_url + "/api/files/import-binary",
        data=output.getvalue(),
        headers={
            "Content-Type": "application/octet-stream",
            "X-File-Name": urllib.parse.quote(filename),
            "X-Sheet-Name": "Devices",
            "X-Preview-Rows": "25",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_until_healthy(base_url: str, process: subprocess.Popen[bytes]) -> dict[str, Any]:
    deadline = time.monotonic() + 20
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Portable backend exited with code {process.returncode}")
        try:
            return request_json(base_url, "GET", "/api/health")
        except (OSError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(0.1)
    raise RuntimeError(f"Portable backend did not become healthy: {last_error}")


def verify(package: Path, port: int) -> dict[str, Any]:
    package = package.resolve()
    executable = package / "MACAnalyzerBackend.exe"
    if not executable.is_file():
        raise FileNotFoundError(executable)

    data_root = package / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    verification_storage = tempfile.TemporaryDirectory(prefix="portable-smoke-", dir=data_root)
    environment = os.environ.copy()
    environment["MAC_ANALYZER_PORT"] = str(port)
    environment["MAC_ANALYZER_DATA_DIR"] = verification_storage.name
    process = subprocess.Popen(
        [str(executable)],
        cwd=package,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        health = wait_until_healthy(base_url, process)
        diagnostics = request_json(base_url, "GET", "/api/system/diagnostics")
        storage = request_json(base_url, "GET", "/api/storage/structure")
        if diagnostics["status"] != "healthy":
            failed = [item for item in diagnostics["checks"] if item["status"] != "passed"]
            raise AssertionError(f"Portable diagnostics are not healthy: {failed}")

        primary = import_xlsx(
            base_url,
            "portable-primary.xlsx",
            [
                ["MAC Address", "IP Address", "Room"],
                ["A1:B2:C3:00:00:01", "10.10.0.1", "101"],
                ["A1:B2:C3:00:00:02", "10.10.0.2", "102"],
            ],
        )
        enrichment = import_xlsx(
            base_url,
            "portable-enrichment.xlsx",
            [
                ["MAC Address", "Vendor", "Model"],
                ["A1:B2:C3:00:00:01", "Portable Vendor", "Portable Model A"],
                ["A1:B2:C3:00:00:02", "Portable Vendor", "Portable Model B"],
            ],
        )
        assert primary.get("fileToken") and enrichment.get("fileToken")

        files = [
            {
                "id": "portable-primary",
                "name": "portable-primary.xlsx",
                "role": "primary",
                "fileToken": primary["fileToken"],
                "mapping": {"mac": 0, "ip": 1, "room": 2},
            },
            {
                "id": "portable-enrichment",
                "name": "portable-enrichment.xlsx",
                "role": "enrichment",
                "fileToken": enrichment["fileToken"],
                "mapping": {"mac": 0, "vendor": 1, "model": 2},
            },
        ]
        rounds = []
        for index in range(3):
            result = request_json(
                base_url,
                "POST",
                "/api/enrichment/run",
                {
                    "jobId": f"portable-smoke-{index}",
                    "files": files,
                    "strategy": "primary",
                    "fields": {"vendor": True, "model": True, "ip": True, "room": True, "history": True},
                    "source": f"portable-smoke-{index}.xlsx",
                    "saveHistory": True,
                    "saveSnapshot": True,
                    "notify": False,
                    "compactResult": True,
                    "resultPageSize": 25,
                },
            )
            assert result["status"] == "completed"
            assert result["compactResult"] is True
            assert result["resultReference"]["deviceCount"] == 2
            assert len(result["devices"]) <= 25
            assert {item["vendor"] for item in result["devices"]} == {"Portable Vendor"}
            assert result["snapshot"]["id"]
            rounds.append(round(float(result["performance"]["durationMs"]), 2))

        database_path = Path(health["databasePath"])
        assert database_path.is_file()
        assert package in database_path.parents
        return {
            "status": "passed",
            "health": health["status"],
            "diagnostics": diagnostics["status"],
            "diagnosticChecks": f'{diagnostics["summary"]["passed"]}/{diagnostics["summary"]["total"]}',
            "database": str(database_path),
            "storageRoot": storage["layout"]["root"],
            "xlsxImports": 2,
            "enrichmentRounds": 3,
            "devicesPerRound": 2,
            "durationMs": rounds,
        }
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        verification_storage.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--port", type=int, default=8091)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.package, arguments.port), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

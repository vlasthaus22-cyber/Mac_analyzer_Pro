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
import pefile


def embedded_manifest(executable: Path) -> bytes:
    image = pefile.PE(str(executable), fast_load=True)
    image.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
    )
    resources = getattr(image, "DIRECTORY_ENTRY_RESOURCE", None)
    if resources is None:
        return b""
    manifests: list[bytes] = []
    for resource_type in resources.entries:
        if resource_type.id != pefile.RESOURCE_TYPE["RT_MANIFEST"]:
            continue
        for resource_name in resource_type.directory.entries:
            for language in resource_name.directory.entries:
                data = language.data.struct
                manifests.append(image.get_data(data.OffsetToData, data.Size))
    return b"".join(manifests).replace(b"\x00", b"")


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


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def verify(package: Path, port: int, use_package_database: bool = False) -> dict[str, Any]:
    package = package.resolve()
    executable = package / "MACAnalyzerBackend.exe"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    if (package / "mac_analyzer_standalone.html").exists():
        raise AssertionError("Universal package must expose only the primary index.html interface")
    package_info = json.loads((package / "PACKAGE_INFO.json").read_text(encoding="utf-8-sig"))
    manifest = embedded_manifest(executable)
    if package_info.get("administratorRightsRequired") is not False:
        raise AssertionError("Portable package unexpectedly requires administrator rights")
    if b"requestedExecutionLevel" not in manifest or b"asInvoker" not in manifest:
        raise AssertionError("Portable backend does not contain the asInvoker manifest")

    data_root = package / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    verification_storage = None
    environment = os.environ.copy()
    environment["MAC_ANALYZER_PORT"] = str(port)
    if use_package_database:
        included_database = data_root / "databases" / "mac_analyzer_web.db"
        if not included_database.is_file():
            raise FileNotFoundError(included_database)
        environment.pop("MAC_ANALYZER_DATA_DIR", None)
        environment.pop("MAC_ANALYZER_DATABASE_PATH", None)
    else:
        verification_storage = tempfile.TemporaryDirectory(prefix="portable-smoke-", dir=data_root)
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
        restart_persistence = False
        if use_package_database:
            stop_process(process)
            process = subprocess.Popen(
                [str(executable)],
                cwd=package,
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            wait_until_healthy(base_url, process)
            persisted = request_json(
                base_url,
                "GET",
                "/api/database/search?query=" + urllib.parse.quote("Portable Vendor"),
            )
            if int(persisted.get("count", 0)) < 2:
                raise AssertionError("Database records did not persist after backend restart")
            restart_persistence = True
        return {
            "status": "passed",
            "package": package_info["package"],
            "administratorRightsRequired": package_info["administratorRightsRequired"],
            "embeddedManifest": "asInvoker",
            "standaloneHtmlIncluded": False,
            "health": health["status"],
            "diagnostics": diagnostics["status"],
            "diagnosticChecks": f'{diagnostics["summary"]["passed"]}/{diagnostics["summary"]["total"]}',
            "database": str(database_path),
            "storageRoot": storage["layout"]["root"],
            "xlsxImports": 2,
            "enrichmentRounds": 3,
            "devicesPerRound": 2,
            "durationMs": rounds,
            "includedDatabaseUsed": use_package_database,
            "restartPersistence": restart_persistence,
        }
    finally:
        stop_process(process)
        if verification_storage is not None:
            verification_storage.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--use-package-database", action="store_true")
    arguments = parser.parse_args()
    print(
        json.dumps(
            verify(arguments.package, arguments.port, arguments.use_package_database),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

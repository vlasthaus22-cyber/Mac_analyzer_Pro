import json
import sqlite3
import tempfile
import threading
import urllib.request
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path

import server
from backend.services.detection.reference_data_service import import_oui_reference, parse_oui_reference


def test_ieee_text_and_csv_reference_formats_are_imported_without_overwriting_custom_rules():
    text = b"F0-E1-D2   (hex)\tReference Vendor\n"
    csv_content = b"Registry,Assignment,Organization Name\nMA-L,A1B2C3,CSV Vendor\n"

    assert parse_oui_reference(text, "oui.txt")["mappings"] == {"F0E1D2": "Reference Vendor"}
    assert parse_oui_reference(csv_content, "oui.csv")["mappings"] == {"A1B2C3": "CSV Vendor"}

    with server.db_connection() as connection:
        connection.execute("DELETE FROM vendor_mappings WHERE oui IN ('F0E1D2', 'A1B2C3')")
        connection.execute(
            "INSERT INTO vendor_mappings (oui, vendor, source, updated_at) VALUES ('F0E1D2', 'Custom Vendor', 'custom', ?)",
            (server.utc_now(),),
        )
        result = import_oui_reference(connection, text, "oui.txt")
        row = connection.execute("SELECT vendor, source FROM vendor_mappings WHERE oui = 'F0E1D2'").fetchone()
        connection.execute("DELETE FROM vendor_mappings WHERE oui IN ('F0E1D2', 'A1B2C3')")

    assert result["count"] == 1
    assert result["preserved"] == 1
    assert dict(row) == {"vendor": "Custom Vendor", "source": "custom"}


def test_saved_enrichment_learns_five_byte_model_and_detects_next_device():
    source = "autodetect-mac5-regression"
    prefix = "F0E1D2C3B4"
    server.init_database()
    with server.db_connection() as connection:
        connection.execute("DELETE FROM mac_history WHERE source = ?", (source,))
        connection.execute("DELETE FROM vendor_model_history WHERE source = ?", (source,))
        connection.execute("DELETE FROM vendor_mappings WHERE source = 'learned' AND oui LIKE 'F0E1D2%'")
        connection.execute("DELETE FROM model_mappings WHERE source = 'learned' AND prefix = ?", (prefix,))

    devices = [
        {"mac": prefix + "01", "vendor": "Learned Vendor", "model": "Learned Model"},
        {"mac": prefix + "02", "vendor": "Learned Vendor", "model": "Learned Model"},
    ]
    server.save_history(devices, source, "2026-07-17T10:00:00Z")
    detected = server.enrich_device({"mac": prefix + "99"})

    with server.db_connection() as connection:
        stored_prefixes = {
            row["prefix"] for row in connection.execute(
                "SELECT DISTINCT prefix FROM vendor_model_history WHERE source = ?", (source,)
            ).fetchall()
        }
        model_rule = connection.execute("SELECT model, source FROM model_mappings WHERE prefix = ?", (prefix,)).fetchone()
        connection.execute("DELETE FROM mac_history WHERE source = ?", (source,))
        connection.execute("DELETE FROM vendor_model_history WHERE source = ?", (source,))
        connection.execute("DELETE FROM vendor_mappings WHERE source = 'learned' AND oui LIKE 'F0E1D2%'")
        connection.execute("DELETE FROM model_mappings WHERE source = 'learned' AND prefix = ?", (prefix,))

    assert stored_prefixes == {prefix}
    assert dict(model_rule) == {"model": "Learned Model", "source": "learned"}
    assert detected["vendor"] == "Learned Vendor"
    assert detected["model"] == "Learned Model"
    assert detected["modelMatchedPrefix"] == prefix


def test_enrichment_context_aggregates_repeated_history_instead_of_loading_every_row():
    original_database = server.DATABASE_PATH
    try:
        with tempfile.TemporaryDirectory() as directory:
            server.DATABASE_PATH = Path(directory) / "bounded-context.db"
            server.init_database()
            mac = "F1E2D3C4B5A6"
            repeated = [
                (mac, mac[:6], mac[:10], "Bounded Vendor", "Bounded Model", "memory-regression", f"2026-07-17T10:{index // 60:02d}:{index % 60:02d}Z")
                for index in range(5_000)
            ]
            with server.db_connection() as connection:
                connection.executemany(
                    "INSERT INTO vendor_model_history (mac, oui, prefix, vendor, model, source, observed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    repeated,
                )
            context = server.build_enrichment_context([{"mac": mac}])
            suggestion = server.enrich_device({"mac": mac}, context)
    finally:
        server.DATABASE_PATH = original_database

    assert context["statistics"]["historyRows"] <= 1
    assert context["statistics"]["vendorModelAggregates"] <= 2
    assert suggestion["vendor"] == "Bounded Vendor"
    assert suggestion["model"] == "Bounded Model"


def test_binary_reference_api_persists_file_in_structured_reference_directory():
    original_database = server.DATABASE_PATH
    original_storage = server.STORAGE
    httpd = None
    thread = None
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference"
            reference.mkdir()
            server.DATABASE_PATH = root / "reference-api.db"
            server.STORAGE = replace(original_storage, reference=reference)
            server.init_database()
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.AppHandler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            host, port = httpd.server_address
            content = b"D4-E5-F6   (hex)\tAPI Reference Vendor\n"
            request = urllib.request.Request(
                f"http://{host}:{port}/api/reference/oui/import",
                data=content,
                method="POST",
                headers={"Content-Type": "application/octet-stream", "X-File-Name": "oui.txt"},
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                imported = json.loads(response.read().decode("utf-8"))
            with urllib.request.urlopen(f"http://{host}:{port}/api/reference/oui/status", timeout=10) as response:
                status = json.loads(response.read().decode("utf-8"))

            assert imported["imported"]["count"] == 1
            assert status["referenceMappings"] == 1
            assert (reference / "oui.txt").read_bytes() == content
    finally:
        if httpd:
            httpd.shutdown()
            httpd.server_close()
        if thread:
            thread.join(timeout=5)
        server.DATABASE_PATH = original_database
        server.STORAGE = original_storage


def test_managed_sqlite_context_releases_the_connection_handle():
    connection = server.db_connection()
    with connection as active:
        assert active.execute("SELECT 1").fetchone()[0] == 1
    try:
        connection.execute("SELECT 1")
    except sqlite3.ProgrammingError as error:
        assert "closed" in str(error).lower()
    else:
        raise AssertionError("db_connection() must close its handle after the with block")


if __name__ == "__main__":
    server.init_database()
    test_ieee_text_and_csv_reference_formats_are_imported_without_overwriting_custom_rules()
    test_saved_enrichment_learns_five_byte_model_and_detects_next_device()
    test_enrichment_context_aggregates_repeated_history_instead_of_loading_every_row()
    test_binary_reference_api_persists_file_in_structured_reference_directory()
    test_managed_sqlite_context_releases_the_connection_handle()
    print("OUI reference and autodetection tests passed")

import base64
import csv
import io
from typing import Any, Callable


Analyzer = Callable[[str, bytes], dict[str, Any]]


def decode_queue_content(content_base64: str) -> bytes:
    return base64.b64decode(str(content_base64 or "").encode("ascii"), validate=True)


def encode_rows_for_queue(rows: list[Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        if isinstance(row, list):
            writer.writerow(row)
        else:
            writer.writerow([row])
    return base64.b64encode(output.getvalue().encode("utf-8")).decode("ascii")


def prepare_queue_files(files: list[dict[str, Any]]) -> list[dict[str, str]]:
    prepared = []
    for file_item in files:
        if not isinstance(file_item, dict):
            continue
        filename = str(file_item.get("filename") or file_item.get("name") or "queued.csv").strip()
        content = str(file_item.get("content") or file_item.get("contentBase64") or "").strip()
        rows = file_item.get("rows", [])
        if not content and isinstance(rows, list) and rows:
            content = encode_rows_for_queue(rows)
        if filename and content:
            prepared.append({"filename": filename, "content": content})
    return prepared


def run_file_queue(queue_items: list[dict[str, Any]], analyzer: Analyzer) -> dict[str, Any]:
    results = []
    for item in queue_items:
        item_id = str(item.get("id") or "")
        filename = str(item.get("filename") or "queued-file.csv")
        try:
            content = decode_queue_content(str(item.get("content_base64") or item.get("content") or ""))
            analysis = analyzer(filename, content)
            results.append({
                "id": item_id,
                "filename": filename,
                "status": "done",
                "devices": len(analysis.get("devices", [])),
                "invalid": len(analysis.get("invalid", [])),
                "result": analysis,
            })
        except Exception as error:  # noqa: BLE001
            results.append({
                "id": item_id,
                "filename": filename,
                "status": "error",
                "error": str(error),
            })
    return {
        "processed": len(results),
        "done": sum(1 for item in results if item["status"] == "done"),
        "errors": sum(1 for item in results if item["status"] == "error"),
        "results": results,
    }


def queue_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"pending": 0, "running": 0, "done": 0, "error": 0, "total": len(items)}
    for item in items:
        status = str(item.get("status") or "pending")
        if status not in summary:
            summary[status] = 0
        summary[status] += 1
    return summary

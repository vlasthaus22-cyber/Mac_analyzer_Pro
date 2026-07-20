"""Central storage layout and safe migration for MAC Analyzer data files."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StorageLayout:
    root: Path
    data: Path
    databases: Path
    legacy: Path
    backups: Path
    exports: Path
    imports: Path
    reference: Path
    runtime: Path
    logs: Path
    config: Path
    database: Path

    def directories(self) -> tuple[Path, ...]:
        return (
            self.data,
            self.databases,
            self.legacy,
            self.backups,
            self.exports,
            self.imports,
            self.reference,
            self.runtime,
            self.logs,
            self.config,
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "root": str(self.root),
            "data": str(self.data),
            "databases": str(self.databases),
            "legacy": str(self.legacy),
            "backups": str(self.backups),
            "exports": str(self.exports),
            "imports": str(self.imports),
            "reference": str(self.reference),
            "runtime": str(self.runtime),
            "logs": str(self.logs),
            "config": str(self.config),
            "database": str(self.database),
        }


def _configured_path(root: Path, environment_name: str, default: Path) -> Path:
    configured = os.environ.get(environment_name, "").strip()
    if not configured:
        return default.resolve()
    path = Path(configured).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def build_storage_layout(root: Path | str) -> StorageLayout:
    app_root = Path(root).resolve()
    data = _configured_path(app_root, "MAC_ANALYZER_DATA_DIR", app_root / "data")
    database = _configured_path(
        app_root,
        "MAC_ANALYZER_DATABASE_PATH",
        data / "databases" / "mac_analyzer_web.db",
    )
    return StorageLayout(
        root=app_root,
        data=data,
        databases=database.parent,
        legacy=data / "legacy",
        backups=data / "backups",
        exports=data / "exports",
        imports=data / "imports",
        reference=data / "reference",
        runtime=data / "runtime",
        logs=app_root / "logs",
        config=app_root / "config",
        database=database,
    )


def ensure_storage_layout(layout: StorageLayout) -> None:
    for directory in layout.directories():
        directory.mkdir(parents=True, exist_ok=True)


def known_file_targets(layout: StorageLayout) -> tuple[tuple[Path, Path], ...]:
    database_name = "mac_analyzer_web.db"
    targets: list[tuple[Path, Path]] = [
        (layout.root / database_name, layout.database),
        (layout.root / f"{database_name}-wal", layout.database.with_name(layout.database.name + "-wal")),
        (layout.root / f"{database_name}-shm", layout.database.with_name(layout.database.name + "-shm")),
        (layout.root / "mac_history.db", layout.legacy / "mac_history.db"),
        (layout.root / "vendor_model_history.db", layout.legacy / "vendor_model_history.db"),
        (layout.root / "mac_analyzer_stats.db", layout.legacy / "mac_analyzer_stats.db"),
        (layout.root / "mac_analyzer.log", layout.logs / "mac_analyzer.log"),
        (layout.root / "mac_analyzer_settings.json", layout.config / "mac_analyzer_settings.json"),
        (layout.root / "oui.txt", layout.reference / "oui.txt"),
        (layout.root / "oui.csv", layout.reference / "oui.csv"),
    ]
    for name in ("server.stdout.log", "server.stderr.log", "server-start.out.log", "server-start.err.log"):
        targets.append((layout.root / name, layout.logs / name))
    return tuple(targets)


def migrate_known_root_files(layout: StorageLayout) -> dict[str, Any]:
    """Move only known application files and never overwrite a destination."""
    ensure_storage_layout(layout)
    moved: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for source, destination in known_file_targets(layout):
        if source.resolve() == destination.resolve() or not source.exists():
            continue
        if destination.exists():
            skipped.append({"source": str(source), "destination": str(destination), "reason": "destination exists"})
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        moved.append({"source": str(source), "destination": str(destination)})
    return {"moved": moved, "skipped": skipped, "layout": layout.as_dict()}


def initialize_storage(root: Path | str) -> tuple[StorageLayout, dict[str, Any]]:
    layout = build_storage_layout(root)
    report = migrate_known_root_files(layout)
    return layout, report


def resolve_legacy_database(layout: StorageLayout, filename: str) -> Path:
    preferred = layout.legacy / Path(filename).name
    if preferred.exists():
        return preferred
    return layout.root / Path(filename).name

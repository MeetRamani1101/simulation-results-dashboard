"""Walks the data root and discovers (project, component, revision) CSV files.

Two folder layouts are supported, auto-detected per file so new data just
needs to be dropped in -- nothing is hard-coded about project, component, or
revision names:

  <root>/<revision>/<component>.csv            -> single implicit project
  <root>/<project>/<revision>/<component>.csv   -> explicit project folder

A CSV's parent directory is always treated as the revision; if the parent's
parent is the scan root itself, the file belongs to the single default
project (``config.DEFAULT_PROJECT_NAME``), otherwise the parent's parent
name is the project name.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..config import DEFAULT_PROJECT_NAME


@dataclass(frozen=True)
class DiscoveredFile:
    project_name: str
    revision_label: str
    component_name: str
    path: Path


_NATURAL_CHUNK = re.compile(r"(\d+)")


def natural_sort_key(label: str) -> tuple:
    """Splits 'rev10' into ('rev', 10) style chunks so rev2 < rev10."""
    parts = _NATURAL_CHUNK.split(label)
    return tuple(int(p) if p.isdigit() else p.lower() for p in parts)


def discover_csv_files(root: Path) -> list[DiscoveredFile]:
    if not root.exists():
        return []

    found: list[DiscoveredFile] = []
    for path in sorted(root.rglob("*.csv")):
        revision_dir = path.parent
        if revision_dir == root:
            # A CSV directly under root has no revision folder; skip it rather
            # than guessing, and let the caller surface it as an error.
            continue
        project_dir = revision_dir.parent
        project_name = DEFAULT_PROJECT_NAME if project_dir == root else project_dir.name
        found.append(
            DiscoveredFile(
                project_name=project_name,
                revision_label=revision_dir.name,
                component_name=path.stem,
                path=path,
            )
        )
    return found


def orphan_csv_files(root: Path) -> list[Path]:
    """CSV files sitting directly under root with no revision folder - these
    cannot be assigned a revision and are reported as import errors."""
    if not root.exists():
        return []
    return sorted(p for p in root.glob("*.csv") if p.is_file())


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def find_component_image(project_dir: Path, component_name: str) -> Path | None:
    """Looks for an optional reference photo for a component, e.g.
    ``<project_dir>/Bracket.png``, sitting alongside the revision folders.
    Not required - components without a matching image simply have none."""
    if not project_dir or not project_dir.exists():
        return None
    for ext in IMAGE_EXTENSIONS:
        candidate = project_dir / f"{component_name}{ext}"
        if candidate.is_file():
            return candidate
    return None

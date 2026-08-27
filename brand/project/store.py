"""
brand/project/store.py

Where projects live. One JSON file per project — the same posture
``brand.store.brand_repo.FileBrandRepository`` already takes for Brands:
human-readable, diffable, no database required for the CLI, the tests or
a designer on a laptop. A Project is mutable (unlike a published Brand
version), so ``save`` simply overwrites; the immutability guarantee in
this system lives in ``ProjectVersion``, not in the file on disk.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from brand.project.model import Project


class ProjectNotFound(KeyError):
    def __init__(self, project_id: str) -> None:
        super().__init__(f"no project {project_id!r} in this store")


def _atomic_write_text(path: Path, data: str) -> None:
    """Write-then-rename, never write-in-place (ADOS-M3.6 production
    hardening). ``Path.write_text`` truncates and writes in place — two
    concurrent writers to the same path (e.g. two overlapping
    closed-loop iterations on the same document) can interleave their
    writes, leaving a torn, unparseable JSON file that fails every
    future read of this project until someone repairs the file by hand.
    ``os.replace`` is an atomic rename on the same filesystem (POSIX and
    Windows both guarantee this): a reader always sees either the
    complete old file or the complete new one, never a mix."""
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


class FileProjectRepository:
    """One JSON file per project, under ``root/<project_id>.json``.

    Default root is ``storage/ados-projects``, deliberately not
    ``storage/projects`` — that path already belongs to REVELATION's own,
    unrelated 3D-render ``Project`` aggregate (``api/routers/v2_projects.py``,
    ``storage/projects/<uuid>/state.json``). Sharing a directory with a
    different domain's files by coincidence of naming is exactly the kind
    of silent collision ADOS's independence from REVELATION exists to
    avoid.
    """

    def __init__(self, root: str | Path = "storage/ados-projects") -> None:
        self.root = Path(root)

    def save(self, project: Project) -> Project:
        path = self._path(project.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(path, project.model_dump_json(indent=2))
        return project

    def get(self, project_id: str) -> Project:
        path = self._path(project_id)
        if not path.exists():
            raise ProjectNotFound(project_id)
        return Project.model_validate_json(path.read_text())

    def delete(self, project_id: str) -> None:
        path = self._path(project_id)
        if not path.exists():
            raise ProjectNotFound(project_id)
        path.unlink()

    def list_projects(self) -> list[Project]:
        if not self.root.is_dir():
            return []
        out = []
        for file in sorted(self.root.glob("*.json")):
            out.append(Project.model_validate_json(file.read_text()))
        return out

    def asset_storage_dir(self, project_id: str) -> Path:
        """Where this project's uploaded files actually live — kept beside
        its JSON record rather than inside it, the same separation
        ``brand.store``'s own asset paths already assume (a JSON record
        names a path; it does not carry the bytes)."""
        return self.root / project_id / "assets"

    def export_storage_dir(self, project_id: str) -> Path:
        """Where this project's exported PDFs live — the same separation
        as :meth:`asset_storage_dir`, for the same reason."""
        return self.root / project_id / "exports"

    def _path(self, project_id: str) -> Path:
        return self.root / f"{project_id}.json"

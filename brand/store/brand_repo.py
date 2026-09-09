"""
brand/store/brand_repo.py

Where brands live.

A file-backed store behind a protocol, so the CLI, the tests and a designer
on a laptop can work without a database. (The original design paired this
with a SQL-backed implementation for production, following the pattern in
``services/design_state_repo.py``; ADOS's own deployments only ever used the
file-backed store, so that alternate implementation stayed behind in the
source monorepo rather than migrating here.)

The invariant it enforces is the one from ``brand/versioning``: a published
version is immutable. ``save`` on an already-published version with different
content raises rather than overwriting, because the failure it prevents —
a reprint that silently differs from the issue — is invisible when it happens
and expensive when it is found.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Optional, Protocol, runtime_checkable

from brand.models.brand import Brand, BrandStatus
from brand.versioning.brand_version import (
    BrandVersionHistory,
    VersionError,
    parse_version,
)


def _atomic_write_text(path: Path, data: str) -> None:
    """Write-then-rename, never write-in-place (ADOS-M3.6 production
    hardening) — see ``brand.project.store``'s identical helper for the
    torn-file race this prevents. Duplicated rather than imported: the
    two stores are otherwise independent siblings under ``brand/``, and
    this is a 15-line filesystem primitive, not shared domain logic."""
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


@runtime_checkable
class BrandRepository(Protocol):
    """The store contract every consumer depends on."""

    def save(self, brand: Brand) -> Brand: ...

    def get(self, brand_id: str, version: Optional[str] = None) -> Brand: ...

    def history(self, brand_id: str) -> BrandVersionHistory: ...

    def list_brands(self) -> list[tuple[str, str, str]]:
        """``(brand_id, name, latest_version)`` for each known brand."""
        ...


class BrandNotFound(KeyError):
    def __init__(self, brand_id: str, version: Optional[str] = None) -> None:
        target = f"{brand_id}@{version}" if version else brand_id
        super().__init__(f"no brand {target} in this store")


# ---------------------------------------------------------------------------
# File-backed
# ---------------------------------------------------------------------------


class FileBrandRepository:
    """One JSON file per version, under ``root/<brand_id>/<version>.json``.

    Human-readable and diffable on purpose: a brand change is a change to the
    practice's identity, and it should show up in a code review as a legible
    diff rather than as an opaque row update.
    """

    def __init__(self, root: str | Path = "storage/brands") -> None:
        self.root = Path(root)

    # -- write ----------------------------------------------------------
    def save(self, brand: Brand) -> Brand:
        brand = brand if brand.content_hash else brand.with_content_hash()
        path = self._path(str(brand.brand_id), brand.version)

        if path.exists():
            existing = Brand.from_json(path.read_text())
            if (
                existing.status is BrandStatus.PUBLISHED
                and not existing.is_equivalent_to(brand)
            ):
                raise VersionError(
                    f"{brand.identity.name} {brand.version} is published and "
                    f"its content differs. Published versions are immutable — "
                    f"call brand.bump() and save the new version."
                )

        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(path, brand.to_json())
        self._write_index(brand)
        return brand

    def _write_index(self, brand: Brand) -> None:
        """A small index so ``list_brands`` does not parse every version."""
        index_path = self.root / "index.json"
        index: dict[str, dict] = {}
        if index_path.exists():
            index = json.loads(index_path.read_text())
        entry = index.setdefault(str(brand.brand_id), {})
        entry["name"] = brand.identity.name
        versions = set(entry.get("versions", []))
        versions.add(brand.version)
        entry["versions"] = sorted(versions, key=parse_version)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(index_path, json.dumps(index, indent=2, sort_keys=True))

    # -- read -----------------------------------------------------------
    def get(self, brand_id: str, version: Optional[str] = None) -> Brand:
        if version is None:
            return self.history(brand_id).resolve(None)
        path = self._path(brand_id, version)
        if not path.exists():
            raise BrandNotFound(brand_id, version)
        return Brand.from_json(path.read_text())

    def history(self, brand_id: str) -> BrandVersionHistory:
        folder = self.root / brand_id
        if not folder.is_dir():
            raise BrandNotFound(brand_id)
        h = BrandVersionHistory(brand_id=brand_id)
        for file in sorted(folder.glob("*.json")):
            h.add(Brand.from_json(file.read_text()))
        return h

    def list_brands(self) -> list[tuple[str, str, str]]:
        index_path = self.root / "index.json"
        if not index_path.exists():
            return []
        index = json.loads(index_path.read_text())
        out = []
        for brand_id, entry in sorted(index.items()):
            versions = entry.get("versions") or []
            out.append((brand_id, entry.get("name", ""), versions[-1] if versions else ""))
        return out

    def _path(self, brand_id: str, version: str) -> Path:
        return self.root / brand_id / f"{version}.json"

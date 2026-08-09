"""
brand/versioning/brand_version.py

Brand versions, and why they are immutable once published.

A drawing issued in 2024 was drawn against the brand as it stood in 2024. If
the practice changes its typeface in 2026 and the 2024 sheet is reprinted
against the current brand, the reprint is not the document that was issued:
the line breaks move, the title block reflows, and the revision history now
describes a sheet that no longer exists. ADOS treats a superseded revision as
a permanent record (``ADOS-2.6.030``); a brand version is the same kind of
object.

So: a published version is frozen, a document stores the exact version it was
built against, and a change is always a new version rather than an edit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from brand.models.brand import Brand, BrandStatus

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

#: What each level means for downstream artefacts.
LEVEL_MEANING = {
    "major": "a downstream document changes shape — reflow, repaginate, re-issue",
    "minor": "a value changes but layouts hold — colours, wording, render defaults",
    "patch": "metadata only — no resolved token changes",
}


class VersionError(ValueError):
    """An invalid version string, or an illegal transition between versions."""


def parse_version(version: str) -> tuple[int, int, int]:
    m = _SEMVER.match(version or "")
    if not m:
        raise VersionError(
            f"{version!r} is not a semantic version like '1.2.0'"
        )
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump_version(version: str, level: str = "minor") -> str:
    major, minor, patch = parse_version(version)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise VersionError(
        f"unknown bump level {level!r}; expected one of {', '.join(LEVEL_MEANING)}"
    )


def compare_versions(a: str, b: str) -> int:
    """-1, 0 or 1 — the sign of ``a - b``."""
    pa, pb = parse_version(a), parse_version(b)
    return (pa > pb) - (pa < pb)


def is_compatible(document_version: str, brand_version: str) -> bool:
    """Whether a document pinned to ``document_version`` may use ``brand_version``.

    Same major, and the brand not older than the pin. A major bump is by
    definition a change that reflows documents, so it is never automatic.
    """
    dm, _, _ = parse_version(document_version)
    bm, _, _ = parse_version(brand_version)
    return dm == bm and compare_versions(brand_version, document_version) >= 0


@dataclass
class BrandVersionHistory:
    """The published lineage of one brand.

    Keyed by version string. Publishing the same version twice with different
    content is refused: that is the failure this whole module exists to
    prevent, and it is much cheaper to catch at the write than at the reprint.
    """

    brand_id: str
    _versions: dict[str, Brand] = field(default_factory=dict)

    def add(self, brand: Brand) -> "BrandVersionHistory":
        if str(brand.brand_id) != self.brand_id:
            raise VersionError(
                f"brand {brand.brand_id} does not belong to history {self.brand_id}"
            )
        existing = self._versions.get(brand.version)
        if existing is not None:
            if existing.status is BrandStatus.PUBLISHED and not existing.is_equivalent_to(brand):
                raise VersionError(
                    f"version {brand.version} is already published with different "
                    f"content. Published versions are immutable — bump instead "
                    f"({LEVEL_MEANING['minor']})."
                )
        self._versions[brand.version] = brand
        return self

    def get(self, version: str) -> Brand:
        try:
            return self._versions[version]
        except KeyError:
            raise VersionError(
                f"brand {self.brand_id} has no version {version}. "
                f"Known: {', '.join(self.versions()) or '(none)'}"
            ) from None

    def versions(self) -> list[str]:
        """Every known version, oldest first."""
        return sorted(self._versions, key=parse_version)

    def latest(self, *, usable_only: bool = True) -> Optional[Brand]:
        """The highest version, by default restricted to approved/published."""
        candidates: Iterable[Brand] = self._versions.values()
        if usable_only:
            candidates = [b for b in candidates if b.is_usable]
        ordered = sorted(candidates, key=lambda b: parse_version(b.version))
        return ordered[-1] if ordered else None

    def resolve(self, pin: Optional[str]) -> Brand:
        """The version a document pinned to ``pin`` should use.

        ``None`` means 'track the latest usable version' — appropriate for a
        live template, never for an issued document.
        """
        if pin is None:
            latest = self.latest()
            if latest is None:
                raise VersionError(
                    f"brand {self.brand_id} has no approved version to track"
                )
            return latest
        return self.get(pin)

    def __len__(self) -> int:                              # pragma: no cover
        return len(self._versions)

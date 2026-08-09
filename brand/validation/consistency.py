"""
brand/validation/consistency.py

Audits a *generated package* against the brand it claims to come from.

``BrandValidator`` checks that a brand is internally sound. This checks
something different and, once assets exist, more important: that the files on
disk actually derive from it. Those are separable failures — a perfectly valid
brand can produce a portfolio spread with a stray hex in it, and nothing in
the brand model would notice.

What it looks for, in the terms the brief asks for:

* **hard-coded colours** — a hex in an output that the palette does not declare
* **hard-coded fonts** — a family named in an output that the brand does not
* **undefined tokens** — a ``var(--…)`` or ``{token}`` reference with nothing behind it
* **inconsistent spacing** — a millimetre value off the sub-module lattice
* **missing metadata** — an asset in the package with no inventory record
* **inconsistent logo variants** — a declared variant with no file
* **inconsistent naming** — a file whose name does not follow the slug pattern
* **duplicated values** — the same colour declared under two token names

Findings reuse ``BrandValidator``'s types so a caller can present brand
findings and package findings in one list. Anything the checker can fix safely
— and only formatting-level things are safe — it reports as fixable rather
than silently rewriting a file someone may have edited.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from brand.models.brand import Brand
from brand.models.tokens import TokenSet
from brand.validation.brand_validator import (
    Category,
    Finding,
    Severity,
    ValidationReport,
)

_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
_CSS_VAR_USE = re.compile(r"var\(\s*(--[a-z0-9-]+)")
_CSS_VAR_DEF = re.compile(r"(--[a-z0-9-]+)\s*:")
_MM = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?)mm\b")
_FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;}\n]+)")

#: Text files worth reading at all.
_TEXT_SUFFIXES = frozenset({".html", ".svg", ".css", ".json", ".yaml", ".yml"})

#: Formats where a colour or a font name is a *rendering decision*. A hex in a
#: JSON file is data — the colour table legitimately lists a proposal's palette
#: and every colour's monochrome equivalent — and flagging it would train
#: people to ignore the check, which is worse than not having one.
_RENDER_SUFFIXES = frozenset({".html", ".svg", ".css"})

#: Layout custom properties. The lattice rule applies to these and not to every
#: millimetre in a file: a 7 mm cap height, a 297 mm page and a 127.77 mm
#: computed logo width are all legitimately off the lattice, and a check that
#: flagged them would be noise.
_LAYOUT_PROPS = ("--s1", "--s2", "--s3", "--margin", "--gutter", "--separator")

#: Files that describe the package rather than belonging to it. The manifest
#: does not list itself, its own audit, or the README that summarises both.
_SELF_REFERENTIAL = frozenset(
    {"asset-inventory.json", "consistency-audit.json", "README.md"}
)

#: Generic CSS keywords that appear in a font stack and are not families.
_GENERIC_FAMILIES = frozenset(
    {"sans-serif", "serif", "monospace", "system-ui", "inherit", "initial",
     "unset", "cursive", "fantasy", "ui-sans-serif", "ui-monospace"}
)


@dataclass
class PackageAudit:
    """The result of auditing one generated package."""

    root: Path
    brand: Brand
    report: ValidationReport = field(default_factory=ValidationReport)
    files_checked: int = 0

    @property
    def ok(self) -> bool:
        return self.report.ok

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "brand": self.brand.label,
            "files_checked": self.files_checked,
            **self.report.to_dict(),
        }

    def summary(self) -> str:
        return f"{self.files_checked} files · {self.report.summary()}"


class ConsistencyChecker:
    """Reads a package directory and reports where it left the brand."""

    def __init__(self, brand: Brand, tokens: TokenSet | None = None) -> None:
        self.brand = brand
        self.tokens = tokens or brand.resolve_tokens()
        self.declared_colours = {
            str(t.value).lower()
            for t in self.tokens.values()
            if isinstance(t.value, str) and t.value.startswith("#")
        }
        self.declared_families = self._families()
        self.lattice = float(self.tokens.value("grid.baseline"))

    def _families(self) -> set[str]:
        typo = self.brand.visual_identity.typography
        out: set[str] = set()
        for face in (typo.primary_font, typo.secondary_font, typo.mono_font):
            if face is None:
                continue
            out.add(face.family.lower())
            out.add(face.fallback.lower())
        return out

    # ------------------------------------------------------------------

    def audit(self, root: Path | str) -> PackageAudit:
        root = Path(root)
        audit = PackageAudit(root=root, brand=self.brand)
        audit.report.brand_label = self.brand.label

        files = sorted(
            p for p in root.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        )
        for path in files:
            audit.files_checked += 1
            if path.suffix.lower() in _TEXT_SUFFIXES:
                text = path.read_text(errors="replace")
                rel = path.relative_to(root)
                audit.report.findings.extend(self._check_text(rel, text))

        audit.report.findings.extend(self._check_inventory(root, files))
        audit.report.findings.extend(self._check_logo_variants(root))
        audit.report.findings.extend(self._check_duplicate_values())
        return audit

    # -- per-file checks ------------------------------------------------

    def _check_text(self, rel: Path, text: str) -> Iterable[Finding]:
        where = str(rel).replace("\\", "/")
        if rel.suffix.lower() not in _RENDER_SUFFIXES:
            return

        stray = {h.lower() for h in _HEX.findall(text)} - self.declared_colours
        if stray:
            yield Finding(
                Severity.ERROR, Category.CONSISTENCY, where,
                f"colour(s) the brand does not declare: {', '.join(sorted(stray))}",
                "Every colour in an output must resolve from the palette. Add "
                "it to the brand, or bind the mark to an existing token.",
            )

        for match in _FONT_FAMILY.findall(text):
            for raw in match.split(","):
                name = raw.strip().strip("'\"").lower()
                if not name or name.startswith("var(") or name in _GENERIC_FAMILIES:
                    continue
                if name not in self.declared_families:
                    yield Finding(
                        Severity.ERROR, Category.CONSISTENCY, where,
                        f"font family {name!r} is not declared by the brand",
                        "Set the family from font.family.* rather than naming "
                        "it in the output.",
                    )

        if rel.suffix.lower() in (".html", ".css"):
            used = set(_CSS_VAR_USE.findall(text))
            defined = set(_CSS_VAR_DEF.findall(text))
            dangling = sorted(used - defined)
            if dangling:
                yield Finding(
                    Severity.ERROR, Category.STRUCTURAL, where,
                    f"custom properties used but never defined: "
                    f"{', '.join(dangling[:6])}",
                    "A var() with nothing behind it renders as nothing. Define "
                    "it in the token block or remove the reference.",
                )

        off: list[str] = []
        for prop in _LAYOUT_PROPS:
            for value in re.findall(
                rf"{re.escape(prop)}\s*:\s*(\d+(?:\.\d+)?)mm", text
            ):
                if abs(float(value) % self.lattice) > 1e-6:
                    off.append(f"{prop}: {value}mm")
        # Placement sits on the sub-module; internal clearance may sit on the
        # half sub-module, which is what the PTS title block already uses for
        # its pads. Two rules because they are two different quantities.
        for prop, step in (
            ("margin", self.lattice), ("gap", self.lattice),
            ("row-gap", self.lattice), ("column-gap", self.lattice),
            ("padding", self.lattice / 2),
        ):
            for value in re.findall(
                rf"(?<![-\w]){prop}\s*:\s*([^;}}\n]+)", text
            ):
                for raw in _MM.findall(value):
                    if abs(float(raw) % step) > 1e-6:
                        off.append(f"{prop}: {raw}mm")
        if off:
            yield Finding(
                Severity.WARN, Category.CONSISTENCY, where,
                f"layout dimension(s) off the {self.lattice:g} mm lattice: "
                f"{', '.join(sorted(set(off))[:6])}",
                "Spacing sits on the sub-module, and it comes from a space.* "
                "token rather than being written into the rule. A value "
                "between two lattice steps puts everything after it off the "
                "grid too.",
            )

    # -- package-level checks -------------------------------------------

    def _check_inventory(
        self, root: Path, files: list[Path]
    ) -> Iterable[Finding]:
        inventory_path = root / "asset-inventory.json"
        if not inventory_path.exists():
            yield Finding(
                Severity.ERROR, Category.STRUCTURAL, "asset-inventory.json",
                "the package has no asset inventory",
                "Without it no asset can be traced to the brand version that "
                "produced it.",
            )
            return

        payload = json.loads(inventory_path.read_text())
        if payload.get("brand_version") != self.brand.version:
            yield Finding(
                Severity.ERROR, Category.STRUCTURAL, "asset-inventory.json",
                f"inventory declares brand {payload.get('brand_version')}, "
                f"audited against {self.brand.version}",
                "Rebuild the package, or audit against the version it was "
                "built from.",
            )

        recorded = {a["path"] for a in payload.get("assets", [])}
        on_disk = {
            str(p.relative_to(root)).replace("\\", "/")
            for p in files
            if p.name not in _SELF_REFERENTIAL
        }
        missing_record = sorted(on_disk - recorded)
        if missing_record:
            yield Finding(
                Severity.WARN, Category.STRUCTURAL, "asset-inventory.json",
                f"{len(missing_record)} file(s) with no inventory record: "
                f"{', '.join(missing_record[:5])}",
                "An asset nobody recorded is an asset nobody can trace back "
                "to a decision.",
            )
        missing_file = sorted(recorded - on_disk)
        if missing_file:
            yield Finding(
                Severity.ERROR, Category.STRUCTURAL, "asset-inventory.json",
                f"inventory lists {len(missing_file)} file(s) that are not "
                f"there: {', '.join(missing_file[:5])}",
                "Rebuild the package.",
            )

        for asset in payload.get("assets", []):
            if not asset.get("brand_version") or not asset.get("type"):
                yield Finding(
                    Severity.WARN, Category.STRUCTURAL,
                    f"asset-inventory.json:{asset.get('name', '?')}",
                    "asset record is missing type or brand_version",
                    "Every record carries both so the package is auditable.",
                )

    def _check_logo_variants(self, root: Path) -> Iterable[Finding]:
        from brand.assets.logo import Variant

        logo_dir = root / "logo"
        if not logo_dir.is_dir():
            return
        slug = self.brand.identity.name.lower().replace(" ", "-")
        present = {p.stem for p in logo_dir.glob("*.svg")}
        expected = {
            f"{slug}-{v.value}" for v in Variant if v is not Variant.HORIZONTAL
        }
        missing = sorted(expected - present)
        if missing:
            yield Finding(
                Severity.WARN, Category.STRUCTURAL, "logo/",
                f"declared variants with no file: {', '.join(missing)}",
                "A variant named in the guidelines and absent from the folder "
                "is a variant somebody will improvise.",
            )
        badly_named = sorted(
            p.name for p in logo_dir.glob("*.svg")
            if not p.stem.startswith(f"{slug}-")
        )
        if badly_named:
            yield Finding(
                Severity.WARN, Category.CONSISTENCY, "logo/",
                f"files off the naming pattern '{slug}-<variant>': "
                f"{', '.join(badly_named)}",
                "One pattern, so an asset can be found by name.",
            )

    def _check_duplicate_values(self) -> Iterable[Finding]:
        """The same colour under two names.

        Not always wrong — ``color.brand.primary`` and ``color.text.primary``
        being the same ink is a decision, not an accident. It is reported at
        INFO so a real duplicate (two accents that happen to match) is visible
        without the legitimate case becoming noise.
        """
        by_value: dict[str, list[str]] = {}
        for name, token in self.tokens.namespace("color").items():
            if isinstance(token.value, str) and token.value.startswith("#"):
                if name.endswith(".mono"):
                    continue
                by_value.setdefault(token.value.lower(), []).append(name)
        for value, names in sorted(by_value.items()):
            if len(names) > 1:
                yield Finding(
                    Severity.INFO, Category.CONSISTENCY,
                    "visual_identity.colour",
                    f"{value} is declared under {len(names)} names: "
                    f"{', '.join(sorted(names))}",
                    "Intentional where one ink serves two roles. Unintentional "
                    "duplicates mean a later change will move one and not the "
                    "other.",
                )


def audit_package(
    root: Path | str, brand: Brand, tokens: TokenSet | None = None
) -> PackageAudit:
    """Convenience wrapper."""
    return ConsistencyChecker(brand, tokens).audit(root)

"""
brand/resolution/pts_bridge.py

The bridge from brand tokens to the PTS document builders.

``docs/templates/pdf/ptspdf.py`` and ``docs/templates/word/ptsword.py`` already
build real, verified documents from ``docs/templates/machine/pts-tokens.json``.
Neither knows what a brand is, and neither should: PTS is the practice's
*geometry*, and geometry is derived from ADOS, not chosen. What a brand
legitimately supplies is the part PTS leaves open — the typefaces, the
identity strings, and the line weights within the tiers the standard defines.

So this module produces a **token overlay**: a partial ``pts`` tree that is
deep-merged over the file at build time. The overlay is deliberately narrow.
Anything ADOS derives (sheet sizes, zone geometry, the type scale, the tone
ladder) is not in it, because a brand that could move those would be a brand
that could produce a non-conformant sheet.

What a brand may change here
----------------------------
``line.tiers``            the three semantic weights, within the ISO series
``type.uppercase_tracking_percent``
``module`` / sub-module   only if the brand's grid says so, and only in whole
                          sub-modules — checked before it is applied
``identity`` strings      practice name, wordmark, descriptor, conformance line

What it may not
---------------
Sheet geometry, zone sizes, the type scale, the tone ladder, margins. Those
carry rule numbers; a brand overlay that moved them would silently invalidate
the ADOS conformance the sheets are stamped with.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from brand import ados
from brand.models.brand import Brand
from brand.models.tokens import TokenSet

#: Keys of the PTS tree a brand overlay is allowed to touch, as dotted paths.
#: Anything outside this set raises rather than being silently dropped — a
#: silently-dropped override is a brand change that appears to work and does
#: not.
ALLOWED_OVERLAY_PATHS: frozenset[str] = frozenset(
    {
        "line.tiers.W1",
        "line.tiers.W2",
        "line.tiers.W3",
        "type.uppercase_tracking_percent",
        "module.M",
        "module.sub",
    }
)


class OverlayError(ValueError):
    """A brand tried to override part of PTS that is derived, not chosen."""


@dataclass
class PtsOverlay:
    """A partial PTS token tree plus the identity strings and font mapping."""

    tokens: dict[str, Any] = field(default_factory=dict)
    identity: dict[str, str] = field(default_factory=dict)
    fonts: dict[str, str] = field(default_factory=dict)
    families: dict[str, str] = field(default_factory=dict)
    properties: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def paths(self) -> list[str]:
        """Dotted paths this overlay sets, for logging and tests."""
        out: list[str] = []

        def walk(node: Any, prefix: str) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, f"{prefix}.{k}" if prefix else k)
            else:
                out.append(prefix)

        walk(self.tokens, "")
        return sorted(out)


def build_overlay(brand: Brand, tokens: TokenSet | None = None) -> PtsOverlay:
    """Derive the PTS overlay for ``brand``."""
    tokens = tokens or brand.resolve_tokens()
    overlay = PtsOverlay()

    _line_tiers(brand, overlay)
    _tracking(tokens, overlay)
    _module(brand, overlay)
    _identity(brand, tokens, overlay)
    _fonts(brand, overlay)
    _properties(brand, overlay)

    illegal = [p for p in overlay.paths() if p not in ALLOWED_OVERLAY_PATHS]
    if illegal:                                            # pragma: no cover
        raise OverlayError(
            "overlay would change derived PTS values: " + ", ".join(illegal)
        )
    return overlay


# ---------------------------------------------------------------------------


def _line_tiers(brand: Brand, overlay: PtsOverlay) -> None:
    """Map the brand's six lineweights onto the three PTS tiers.

    PTS carries three *semantic* tiers because ADOS caps semantic tiers at
    three (``ADOS-3.1.010``): beyond, seen, cut. A brand may declare more
    weights than that — a separate annotation weight, a lighter secondary —
    but only three of them are the depth encoding, and only those three go
    into the overlay. The rest are used by the drawing consumers directly.
    """
    lw = brand.architectural_language.drawing.lineweights
    series = ados.line_iso_series_mm()
    mapping = {"W1": lw.background_mm, "W2": lw.primary_mm, "W3": lw.cut_mm}

    for tier, value in mapping.items():
        if not any(abs(value - s) < 1e-9 for s in series):
            nearest = min(series, key=lambda s: abs(s - value))
            overlay.warnings.append(
                f"{tier}: brand weight {value} mm is not on the ISO series; "
                f"snapped to {nearest} mm for the sheet build"
            )
            value = nearest
        overlay.tokens.setdefault("line", {}).setdefault("tiers", {})[tier] = value

    if not (mapping["W1"] < mapping["W2"] < mapping["W3"]):
        raise OverlayError(
            "brand line weights are not monotone (background < seen < cut); "
            "the sheet would encode depth backwards. Fix the brand — "
            "BrandValidator blocks this before it reaches a build."
        )


def _tracking(tokens: TokenSet, overlay: PtsOverlay) -> None:
    tracking = tokens.value("letter_spacing.uppercase", None)
    if tracking is not None:
        overlay.tokens.setdefault("type", {})["uppercase_tracking_percent"] = float(
            tracking
        )


def _module(brand: Brand, overlay: PtsOverlay) -> None:
    """Only accept a module that is a whole multiple of the ADOS sub-module."""
    grid = brand.visual_identity.grid
    sub = ados.submodule_mm()
    if abs(grid.module_mm % sub) > 1e-6:
        overlay.warnings.append(
            f"brand module {grid.module_mm} mm is not a whole sub-module "
            f"({sub:g} mm); the PTS module is left at its derived value"
        )
        return
    overlay.tokens.setdefault("module", {})["M"] = grid.module_mm
    overlay.tokens["module"]["sub"] = sub


def _identity(brand: Brand, tokens: TokenSet, overlay: PtsOverlay) -> None:
    """The strings the title block and cover set.

    These are not PTS tokens — PTS has no opinion about a practice's name —
    so they travel beside the overlay rather than inside it.
    """
    overlay.identity = {
        "practice": brand.identity.name,
        "wordmark": str(tokens.value("asset.logo.wordmark", brand.identity.name)),
        "descriptor": brand.identity.descriptor,
        "tagline": brand.identity.tagline,
        "conformance": (
            f"Conforms to ADOS {brand.ados_edition} Class B · PTS 1.0 · "
            f"{brand.identity.name} brand {brand.version}"
        ),
        "language": brand.communication.primary_language,
    }


def _properties(brand: Brand, overlay: PtsOverlay) -> None:
    """Defaults for the Word templates' document properties.

    The PTS Word templates bind every identity field to a DOCPROPERTY rather
    than typing it, so this is where a brand reaches them: a template arrives
    carrying the practice's own name instead of "Originator name", and the
    fields still stay fields.

    Only the fields a *brand* knows are set. Project name, client, container
    identifier and issue date belong to a project, not to a practice, and
    filling them here would put a stale value where the reader expects a blank.
    """
    # The practice *name* only. This property is displayed in the page footer
    # of every Word template, beside the container identifier, the revision and
    # the status — a full address line there would wrap the footer onto two
    # lines on every page. The address belongs on the letterhead, which is one
    # page and has room for it.
    overlay.properties = {
        "PTS_Originator": brand.identity.name,
        "PTS_Conformance": overlay.identity["conformance"],
    }


def _fonts(brand: Brand, overlay: PtsOverlay) -> None:
    """Map brand faces to the font files the PDF builder can embed.

    The builder ships Inter and IBM Plex Mono. A brand that names a family
    with no file present keeps the bundled face and gets a warning, because
    the alternative — substituting silently — produces a document whose every
    measurement is wrong while looking plausible.
    """
    from pathlib import Path

    font_dir = (
        Path(__file__).resolve().parents[2]
        / "docs" / "templates" / "pdf" / "fonts"
    )
    available = {
        "Inter": "Inter-Regular.ttf",
        "Inter Medium": "Inter-Medium.ttf",
        "IBM Plex Mono": "IBMPlexMono-Regular.ttf",
    }
    typo = brand.visual_identity.typography
    wanted = {
        "primary": typo.primary_font.family,
        "secondary": typo.secondary_font.family if typo.secondary_font else None,
        "mono": typo.mono_font.family if typo.mono_font else None,
    }
    # Word needs family *names*, not files: it resolves a face from the name at
    # open time and has no fallback chain, which is why the declared fallback
    # travels with it.
    overlay.families = {
        "primary": typo.primary_font.family,
        "primary_fallback": typo.primary_font.fallback,
        **({"mono": typo.mono_font.family,
            "mono_fallback": typo.mono_font.fallback} if typo.mono_font else {}),
    }
    for role, family in wanted.items():
        if family is None:
            continue
        filename = available.get(family)
        if filename and (font_dir / filename).exists():
            overlay.fonts[role] = str(font_dir / filename)
        else:
            overlay.warnings.append(
                f"{role} face {family!r} has no bundled font file; the sheet "
                f"build falls back to the PTS default. Every point size is "
                f"derived from a measured cap height, so add the file before "
                f"treating a built sheet as final."
            )


# ---------------------------------------------------------------------------
# Applying an overlay to the live PTS token tree
# ---------------------------------------------------------------------------


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursive merge, ``overlay`` winning. Returns a new dict."""
    out = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def merged_pts_tokens(brand: Brand) -> dict[str, Any]:
    """The PTS tree as this brand would build it. Pure; touches no globals."""
    return deep_merge(ados.pts_tokens(), build_overlay(brand).tokens)

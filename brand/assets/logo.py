"""
brand/assets/logo.py

The logo system, generated from the brand.

Nothing here decides what the mark looks like. The proportions come from
``visual_identity.logo.construction`` (in modules, on the same lattice the
sheets are set on), the letterforms come from the practice's own licensed
typeface, and the colours come from the palette. Change the module and the
mark rebuilds; change the typeface and the wordmark is re-set in it.

That is the point. A logo drawn once in a vector editor is a file; a logo
derived from the brand is a *system*, and it stays true when the brand moves.

The two halves
--------------
**The wordmark** is real type. Glyph outlines are pulled from the font binary
with fontTools and written as SVG paths, so the mark is the typeface — not a
traced approximation of it, and not a `<text>` element that renders differently
on every machine that lacks the font.

**The symbol** is constructed geometry: a square aperture, drawn at the
practice's own cut lineweight, on the module. It is the one mark that carries
the identity when the wordmark is absent — on a favicon, a title block, a
social avatar.

Everything is emitted as SVG. Rasterisation and PDF live in ``brand/export``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from brand.models.brand import Brand
from brand.models.tokens import TokenSet

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Font families the system can read outlines from, and where the file is.
#: A family that is not here still resolves — the wordmark falls back to a
#: `<text>` element and the manifest records that the SVG is not self-contained,
#: which is honest and visible rather than silently wrong.
BUNDLED_FACES: dict[str, Path] = {
    "Inter": _REPO_ROOT / "docs/templates/pdf/fonts/Inter-Regular.ttf",
    "Inter Medium": _REPO_ROOT / "docs/templates/pdf/fonts/Inter-Medium.ttf",
    "IBM Plex Mono": _REPO_ROOT / "docs/templates/pdf/fonts/IBMPlexMono-Regular.ttf",
}

#: Weight → the bundled file that carries it, per family.
_WEIGHT_FILES: dict[tuple[str, int], str] = {
    ("Inter", 400): "Inter-Regular.ttf",
    ("Inter", 500): "Inter-Medium.ttf",
    ("Inter", 600): "Inter-Medium.ttf",
}


class Variant(str, Enum):
    """The variants of the system. Each exists for a stated situation."""

    PRIMARY = "primary"              # wordmark + symbol, horizontal
    SECONDARY = "secondary"          # wordmark alone
    MONOGRAM = "monogram"            # the short form, set in the face
    SYMBOL = "symbol"                # the aperture, no letters
    COMPACT = "compact"              # symbol + monogram, square-ish
    HORIZONTAL = "horizontal"        # alias of primary, named for layout use
    STACKED = "stacked"              # symbol over wordmark
    REVERSED = "reversed"            # primary, knocked out of the ink


@dataclass
class RenderedLogo:
    """One SVG plus the metadata the asset manifest needs."""

    variant: Variant
    svg: str
    width_mm: float
    height_mm: float
    background: str                  # "light" | "dark"
    outlined: bool                   # True when glyphs are real paths
    brand_version: str
    notes: list[str] = field(default_factory=list)

    @property
    def filename(self) -> str:
        return f"{self.slug}.svg"

    slug: str = ""

    def write(self, directory: Path | str) -> Path:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        path = d / self.filename
        path.write_text(self.svg)
        return path

    def metadata(self, brand_name: str) -> dict[str, Any]:
        return {
            "name": self.slug,
            "type": "logo",
            "variant": self.variant.value,
            "background": self.background,
            "format": "svg",
            "width_mm": round(self.width_mm, 3),
            "height_mm": round(self.height_mm, 3),
            "outlined": self.outlined,
            "brand": brand_name,
            "brand_version": self.brand_version,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Type outlines
# ---------------------------------------------------------------------------


@dataclass
class Outline:
    """A run of text as SVG path data, in millimetres, baseline at y=0."""

    path: str
    advance_mm: float
    cap_mm: float
    available: bool = True


def text_outline(
    text: str, *, family: str, weight: int, cap_mm: float,
    tracking_percent: float = 0.0,
) -> Outline:
    """Glyph outlines for ``text``, scaled so the cap height is ``cap_mm``.

    The scale is derived from the font's own ``OS/2.sCapHeight``, which is the
    same quantity the type scale is derived from. A wordmark set by eye to
    "about 8 mm" is a wordmark that does not match the type on the page beside
    it; this one does, by construction.

    Returns an unavailable :class:`Outline` rather than raising when the family
    is not bundled — the caller falls back to live text and records it.
    """
    path_file = _font_file(family, weight)
    if path_file is None or not path_file.exists():
        return Outline(path="", advance_mm=0.0, cap_mm=cap_mm, available=False)

    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont

    font = TTFont(path_file)
    upem = font["head"].unitsPerEm
    cap_units = getattr(font["OS/2"], "sCapHeight", None) or int(upem * 0.72)
    scale = cap_mm / cap_units                      # font units → mm

    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    hmtx = font["hmtx"]

    parts: list[str] = []
    x = 0.0
    tracking_units = (tracking_percent / 100.0) * upem
    for i, char in enumerate(text):
        name = cmap.get(ord(char))
        if name is None:                                   # pragma: no cover
            x += upem * 0.35 + tracking_units
            continue
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        d = pen.getCommands()
        if d:
            # SVG y grows downward; font y grows upward. One flip on the group
            # rather than a transform per glyph keeps the path data readable.
            parts.append(f'<path d="{d}" transform="translate({x:.2f} 0)"/>')
        x += hmtx[name][0]
        if i < len(text) - 1:
            x += tracking_units

    advance_units = x
    group = (
        f'<g transform="scale({scale:.6f} {-scale:.6f})">' + "".join(parts) + "</g>"
    )
    return Outline(
        path=group, advance_mm=advance_units * scale, cap_mm=cap_mm, available=True
    )


def _font_file(family: str, weight: int) -> Path | None:
    key = (family, weight)
    if key in _WEIGHT_FILES:
        return _REPO_ROOT / "docs/templates/pdf/fonts" / _WEIGHT_FILES[key]
    if family in BUNDLED_FACES:
        return BUNDLED_FACES[family]
    return None


# ---------------------------------------------------------------------------
# The generator
# ---------------------------------------------------------------------------


class LogoSystem:
    """Builds every variant of one brand's mark."""

    def __init__(self, brand: Brand, tokens: TokenSet | None = None) -> None:
        self.brand = brand
        self.tokens = tokens or brand.resolve_tokens()
        c = brand.visual_identity.logo.construction
        self.u = c.module_mm
        self.cap = c.cap_modules * self.u
        self.field = c.field_modules * self.u
        self.wall = c.aperture_stroke_modules * self.u
        self.gap = c.letter_gap_modules * self.u
        self.tracking = c.tracking_percent
        self.family = str(self.tokens.value("font.family.primary"))
        self.weight = int(self.tokens.value("font.weight.medium"))
        self._ink = str(self.tokens.value("color.text.primary"))
        self._paper = str(self.tokens.value("color.background"))
        self._inverted = False
        self.wordmark = str(self.tokens.value("asset.logo.wordmark"))
        self.monogram = str(self.tokens.value("asset.logo.monogram"))

    # -- ink -------------------------------------------------------------

    @property
    def ink(self) -> str:
        """The colour the mark is drawn in. Swaps under inversion."""
        return self._paper if self._inverted else self._ink

    @property
    def ground(self) -> str:
        return self._ink if self._inverted else self._paper

    # -- public ---------------------------------------------------------

    def build(self, variant: Variant) -> RenderedLogo:
        return {
            Variant.PRIMARY: self._primary,
            Variant.HORIZONTAL: self._primary,
            Variant.SECONDARY: self._secondary,
            Variant.MONOGRAM: self._monogram,
            Variant.SYMBOL: self._symbol,
            Variant.COMPACT: self._compact,
            Variant.STACKED: self._stacked,
            Variant.REVERSED: self._reversed,
        }[variant](variant)

    def build_all(self) -> list[RenderedLogo]:
        seen: set[str] = set()
        out: list[RenderedLogo] = []
        for variant in Variant:
            logo = self.build(variant)
            if logo.slug in seen:
                continue
            seen.add(logo.slug)
            out.append(logo)
        return out

    def clear_space_mm(self) -> float:
        """The exclusion zone around the mark.

        Expressed as a multiple of the cap height rather than an absolute, so
        it scales with the mark. This is the same idea as the ADOS text clear
        zone (``ADOS-3.4.080``) applied to a graphic.
        """
        return self.cap * float(self.tokens.value("asset.logo.clear_space"))

    def min_width_mm(self) -> float:
        return float(self.tokens.value("asset.logo.min_width"))

    # -- variants -------------------------------------------------------

    def _primary(self, variant: Variant) -> RenderedLogo:
        sym = self._aperture(0, 0, self.field)
        word, w_adv, outlined, notes = self._wordmark_svg(self.wordmark)
        x = self.field + self.gap * 2
        # The wordmark's cap is centred on the field, so the two halves share
        # an optical centre line rather than a baseline they do not share.
        y = (self.field + self.cap) / 2
        body = sym + f'<g transform="translate({x:.3f} {y:.3f})">{word}</g>'
        return self._doc(
            variant, "primary", body, x + w_adv, self.field,
            "light", outlined, notes,
        )

    def _secondary(self, variant: Variant) -> RenderedLogo:
        word, w_adv, outlined, notes = self._wordmark_svg(self.wordmark)
        body = f'<g transform="translate(0 {self.cap:.3f})">{word}</g>'
        return self._doc(variant, "secondary", body, w_adv, self.cap,
                         "light", outlined, notes)

    def _monogram(self, variant: Variant) -> RenderedLogo:
        word, w_adv, outlined, notes = self._wordmark_svg(
            self.monogram, cap=self.field * 0.5
        )
        cap = self.field * 0.5
        body = f'<g transform="translate(0 {cap:.3f})">{word}</g>'
        return self._doc(variant, "monogram", body, w_adv, cap,
                         "light", outlined, notes)

    def _symbol(self, variant: Variant) -> RenderedLogo:
        body = self._aperture(0, 0, self.field)
        return self._doc(variant, "symbol", body, self.field, self.field,
                         "light", True, [])

    def _compact(self, variant: Variant) -> RenderedLogo:
        """Symbol with the monogram inside the aperture.

        For a favicon, an avatar and a title-block corner — the places where
        the wordmark would be below its minimum width. The monogram sits in
        the void because that is what the void is for.
        """
        inner = self.field - 2 * self.wall
        # Fit the monogram to the void rather than assuming a cap height fits
        # it: "OM" is two wide glyphs and "I" is one narrow one, and a cap
        # chosen as a fraction of the void makes the first touch the walls.
        # Measured once at a trial size, then scaled to leave a margin equal
        # to the aperture wall — the same clearance the mark uses everywhere.
        trial = inner * 0.5
        probe = text_outline(
            self.monogram, family=self.family, weight=self.weight,
            cap_mm=trial, tracking_percent=0.0,
        )
        target = max(inner - 2 * self.wall, inner * 0.5)
        cap = trial
        if probe.available and probe.advance_mm > 0:
            cap = min(trial, trial * target / probe.advance_mm)
        word, w_adv, outlined, notes = self._wordmark_svg(
            self.monogram, cap=cap, tracking=0.0
        )
        cx = self.wall + (inner - w_adv) / 2
        cy = self.wall + (inner + cap) / 2
        body = (
            self._aperture(0, 0, self.field)
            + f'<g transform="translate({cx:.3f} {cy:.3f})">{word}</g>'
        )
        return self._doc(variant, "compact", body, self.field, self.field,
                         "light", outlined, notes)

    def _stacked(self, variant: Variant) -> RenderedLogo:
        word, w_adv, outlined, notes = self._wordmark_svg(self.wordmark)
        body = (
            self._aperture(0, 0, self.field)
            + f'<g transform="translate(0 {self.field + self.gap * 2 + self.cap:.3f})">'
            + word + "</g>"
        )
        height = self.field + self.gap * 2 + self.cap
        return self._doc(variant, "stacked", body, max(self.field, w_adv), height,
                         "light", outlined, notes)

    def _reversed(self, variant: Variant) -> RenderedLogo:
        """The primary lockup knocked out of the ink.

        Built by inverting the palette and re-drawing, not by string-replacing
        colours in the finished SVG: a replacement that stops matching — a
        changed attribute order, a colour that appears in two roles — fails
        silently and ships a mark that is simply not reversed.

        The ground carries the clear space. A reversed lockup with the type
        against the edge of its panel is a black bar, not a logo.
        """
        self._inverted = True
        try:
            base = self._primary(Variant.PRIMARY)
        finally:
            self._inverted = False

        pad = self.clear_space_mm()
        w, h = base.width_mm + 2 * pad, base.height_mm + 2 * pad
        inner = base.svg.split("</desc>", 1)[1].rsplit("</svg>", 1)[0]
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{w:.3f}mm" height="{h:.3f}mm" '
            f'viewBox="0 0 {w:.3f} {h:.3f}" role="img" '
            f'aria-label="{self.brand.identity.name}">'
            f'<title>{self.brand.identity.name} — reversed</title>'
            f'<desc>Generated by the ADOS Brand System from brand '
            f'{self.brand.version}. Ground carries {pad:g} mm clear space.</desc>'
            f'<rect x="0" y="0" width="{w:.3f}" height="{h:.3f}" '
            f'fill="{self._ink}"/>'
            f'<g transform="translate({pad:.3f} {pad:.3f})">{inner}</g></svg>'
        )
        return RenderedLogo(
            variant=variant, svg=svg, width_mm=w, height_mm=h,
            background="dark", outlined=base.outlined,
            brand_version=self.brand.version, notes=base.notes,
            slug=self._slug("reversed"),
        )

    # -- pieces ---------------------------------------------------------

    def _aperture(self, x: float, y: float, size: float) -> str:
        """The square aperture: the identity's one constructed mark.

        Drawn with the even-odd fill rule as a single path with two rectangles,
        so the void is genuinely a hole. A stroked square would change weight
        when the mark is scaled by a layout tool; a filled ring does not.
        """
        w = self.wall
        outer = f"M{x} {y}h{size}v{size}h{-size}z"
        inner = (
            f"M{x + w} {y + w}v{size - 2 * w}h{size - 2 * w}v{-(size - 2 * w)}z"
        )
        return (
            f'<path fill-rule="evenodd" fill="{self.ink}" '
            f'd="{outer}{inner}"/>'
        )

    def _wordmark_svg(
        self, text: str, *, cap: float | None = None, tracking: float | None = None
    ) -> tuple[str, float, bool, list[str]]:
        cap = self.cap if cap is None else cap
        tracking = self.tracking if tracking is None else tracking
        outline = text_outline(
            text, family=self.family, weight=self.weight, cap_mm=cap,
            tracking_percent=tracking,
        )
        if outline.available:
            return (
                f'<g fill="{self.ink}">{outline.path}</g>',
                outline.advance_mm, True, [],
            )
        # Fallback: live text. The SVG is then only correct on a machine that
        # has the face, which the manifest says out loud.
        fallback = str(self.tokens.value("font.fallback.primary"))
        note = (
            f"{self.family} is not bundled, so this SVG sets the wordmark as "
            f"live text with a {fallback} fallback. It is not self-contained: "
            f"add the font file before issuing it."
        )
        pt = cap / float(self.tokens.value("font.cap_ratio.primary")) / (25.4 / 72)
        svg = (
            f'<text x="0" y="0" fill="{self.ink}" '
            f'font-family="{self.family}, {fallback}, sans-serif" '
            f'font-size="{pt * 25.4 / 72:.3f}" font-weight="{self.weight}" '
            f'letter-spacing="{cap * tracking / 100:.3f}">{text}</text>'
        )
        return svg, len(text) * cap * 0.78, False, [note]

    def _doc(
        self, variant: Variant, slug_part: str, body: str,
        width: float, height: float, background: str,
        outlined: bool, notes: list[str],
    ) -> RenderedLogo:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width:.3f}mm" height="{height:.3f}mm" '
            f'viewBox="0 0 {width:.3f} {height:.3f}" '
            f'role="img" aria-label="{self.brand.identity.name}">'
            f"<title>{self.brand.identity.name} — {variant.value}</title>"
            f"<desc>Generated by the ADOS Brand System from brand "
            f"{self.brand.version}. Module {self.u} mm.</desc>"
            f"{body}</svg>"
        )
        return RenderedLogo(
            variant=variant, svg=svg, width_mm=width, height_mm=height,
            background=background, outlined=outlined,
            brand_version=self.brand.version, notes=notes,
            slug=self._slug(slug_part),
        )

    def _slug(self, part: str) -> str:
        base = self.brand.identity.name.lower().replace(" ", "-")
        return f"{base}-{part}"


def build_logo_system(
    brand: Brand, tokens: TokenSet | None = None
) -> list[RenderedLogo]:
    """Every variant, ready to write."""
    return LogoSystem(brand, tokens).build_all()

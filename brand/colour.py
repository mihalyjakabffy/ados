"""
brand/colour.py

Colour arithmetic for brand validation.

ADOS states its colour and tone constraints in **CIE L\\*** and in contrast
ratio, not in hex or in percentages, because those are the quantities that
survive a change of output device.  A brand is authored in hex, so this module
is the conversion between the two, and it is deliberately the only place in the
Brand System that knows what a hex string means.

No third-party colour library: the sRGB → XYZ → L\\*a\\*b\\* transform is a
dozen lines and adding a dependency for it would be the larger cost.
"""

from __future__ import annotations

import math
import re

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# sRGB D65 → XYZ (IEC 61966-2-1)
_M = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)
# D65 reference white
_WHITE = (0.95047, 1.00000, 1.08883)


def is_hex(value: str) -> bool:
    """True for ``#rgb`` and ``#rrggbb``. Case-insensitive."""
    return bool(_HEX_RE.match(value or ""))


def to_rgb(hex_colour: str) -> tuple[int, int, int]:
    """Hex string to 8-bit RGB."""
    if not is_hex(hex_colour):
        raise ValueError(f"not a hex colour: {hex_colour!r}")
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _linearise(channel_8bit: int) -> float:
    c = channel_8bit / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour: str) -> float:
    """WCAG relative luminance, 0.0 (black) to 1.0 (white)."""
    r, g, b = (_linearise(c) for c in to_rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    """WCAG 2.x contrast ratio between two colours, 1.0 to 21.0."""
    la, lb = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def to_lab(hex_colour: str) -> tuple[float, float, float]:
    """Hex string to CIE L\\*a\\*b\\* under D65."""
    rgb = tuple(_linearise(c) for c in to_rgb(hex_colour))
    xyz = tuple(sum(_M[i][j] * rgb[j] for j in range(3)) for i in range(3))
    x, y, z = (xyz[i] / _WHITE[i] for i in range(3))

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def l_star(hex_colour: str) -> float:
    """CIE L\\* — the axis the ADOS tone ladder is defined on."""
    return to_lab(hex_colour)[0]


def delta_l(a: str, b: str) -> float:
    """Absolute L\\* difference. The ADOS measure of 'tells apart by lightness'."""
    return abs(l_star(a) - l_star(b))


def delta_e76(a: str, b: str) -> float:
    """CIE76 colour difference.

    Deliberately CIE76 rather than CIEDE2000: ADOS states its own thresholds
    against a Euclidean Lab distance, and a more accurate metric with
    differently-calibrated thresholds would be less correct here, not more.
    """
    la, aa, ba = to_lab(a)
    lb, ab, bb = to_lab(b)
    return math.sqrt((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2)


def nearest_tone_token(hex_colour: str, ladder: dict[str, float]) -> tuple[str, float]:
    """The tone-ladder step a colour is closest to, and its L\\* distance.

    Used to tell a brand author which rung of the ADOS ladder their chosen
    grey actually lands on — a brand grey that sits between two rungs is a
    grey that will not reproduce as either.
    """
    target = l_star(hex_colour)
    token, best = min(ladder.items(), key=lambda kv: abs(kv[1] - target))
    return token, abs(best - target)


def to_greyscale_hex(hex_colour: str) -> str:
    """The colour as it prints on a monochrome device.

    Every ADOS drawing output is monochrome, so a brand palette whose members
    collapse to the same grey is a palette that carries no information on a
    plotted sheet. This is how that is measured.
    """
    y = relative_luminance(hex_colour)
    # Inverse of the sRGB transfer function, applied to luminance.
    c = 12.92 * y if y <= 0.0031308 else 1.055 * (y ** (1 / 2.4)) - 0.055
    v = max(0, min(255, round(c * 255)))
    return f"#{v:02x}{v:02x}{v:02x}"

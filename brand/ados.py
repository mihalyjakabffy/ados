"""
brand/ados.py

The binding between the Brand System and the ADOS standard.

ADOS is the constraint layer: it states what any conforming practice may
choose, and every value in it is derived from a root fact (visual acuity,
working-memory capacity, device pitch, ISO 216).  A brand is a *choice within*
those constraints, not an alternative to them, so this module is the single
place the Brand System reads the standard.

Nothing here is copied from the specification prose.  The values are loaded
from the machine artefacts that the ADOS conformance checker already
validates:

    docs/ados/machine/ados-tokens.json     the standard
    docs/templates/machine/pts-tokens.json  the practice geometry overlay

If either file moves or a key is renamed, this module fails loudly at import
of the first accessor rather than silently validating against defaults — a
brand validated against a guess is worse than one not validated at all.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# Repository root, found from this file rather than the working directory so
# that the CLI, pytest, and the FastAPI app all resolve the same artefacts.
_REPO_ROOT = Path(__file__).resolve().parent.parent

ADOS_TOKENS_PATH = _REPO_ROOT / "docs" / "ados" / "machine" / "ados-tokens.json"
PTS_TOKENS_PATH = _REPO_ROOT / "docs" / "templates" / "machine" / "pts-tokens.json"


class AdosBindingError(RuntimeError):
    """The standard could not be read, or does not carry an expected key."""


@lru_cache(maxsize=1)
def ados_tokens() -> dict[str, Any]:
    """The ADOS standard token tree (the contents of the ``ados`` key)."""
    return _load(ADOS_TOKENS_PATH, "ados")


@lru_cache(maxsize=1)
def pts_tokens() -> dict[str, Any]:
    """The PTS practice-geometry token tree (the contents of the ``pts`` key)."""
    return _load(PTS_TOKENS_PATH, "pts")


def _load(path: Path, root_key: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except FileNotFoundError as exc:                       # pragma: no cover
        raise AdosBindingError(
            f"ADOS artefact missing: {path}. The Brand System validates against "
            f"the standard and cannot fall back to defaults."
        ) from exc
    except json.JSONDecodeError as exc:                    # pragma: no cover
        raise AdosBindingError(f"ADOS artefact is not valid JSON: {path}") from exc
    if root_key not in payload:
        raise AdosBindingError(f"{path} has no {root_key!r} root key")
    return payload[root_key]


def ados_edition() -> str:
    """The edition string of the standard this brand system validates against."""
    payload = json.loads(ADOS_TOKENS_PATH.read_text())
    return str(payload.get("edition", "unknown"))


# ---------------------------------------------------------------------------
# Typed accessors
#
# Each one names the ADOS rule it serves so that a validation message can cite
# the clause rather than assert a number.
# ---------------------------------------------------------------------------


def type_steps() -> dict[str, float]:
    """Cap heights of the type scale, by step name (``ADOS-2.4.020``)."""
    return {k: float(v) for k, v in _need(ados_tokens(), "type", "steps").items()}


def type_scale_mm() -> list[float]:
    """The cap heights of the scale, ascending."""
    return sorted(type_steps().values())


def min_cap_height_mm() -> float:
    """Smallest cap height permitted for primary content (``ADOS-2.4.010``)."""
    return float(_need(ados_tokens(), "type", "min_cap_height_mm"))


def absolute_cap_floor_mm() -> float:
    """Smallest cap height permitted for anything at all."""
    return float(_need(ados_tokens(), "type", "absolute_floor_mm"))


def line_tiers() -> dict[str, float]:
    """Semantic line tiers in mm, by tier name (``ADOS-3.1.010``)."""
    tiers = _need(ados_tokens(), "line", "tiers")
    return {k: float(v["width_mm"]) for k, v in tiers.items()}


def line_iso_series_mm() -> list[float]:
    """The ISO 128 line-width series a chosen weight must land on."""
    return [float(v) for v in _need(ados_tokens(), "line", "iso_series_mm")]


def line_tier_ratio() -> float:
    """Required ratio between adjacent semantic tiers (``ADOS-3.1.020``)."""
    return float(_need(ados_tokens(), "line", "tier_ratio"))


def min_issued_line_mm() -> float:
    """Thinnest line that survives issue and copying (``ADOS-3.1.030``)."""
    return float(_need(ados_tokens(), "line", "min_issued_mm"))


def max_semantic_tiers() -> int:
    """Most semantic line tiers a drawing may carry."""
    return int(_need(ados_tokens(), "line", "max_semantic_tiers"))


def tone_ladder() -> dict[str, float]:
    """The tone ladder as CIE L\\* values, by token (``ADOS-3.7.010``)."""
    ladder = _need(ados_tokens(), "tone", "ladder")
    return {k: float(v["L_star"]) for k, v in ladder.items()}


def min_discriminable_delta_l() -> float:
    """Smallest L\\* difference two tones may have and still be told apart."""
    return float(_need(ados_tokens(), "tone", "delta_L_min_discriminable"))


def max_tones_per_sheet() -> int:
    return int(_need(ados_tokens(), "tone", "max_tones_per_sheet"))


def text_permitted_backgrounds() -> list[str]:
    """Tone tokens text may be set on (``ADOS-3.7.040``)."""
    return list(_need(ados_tokens(), "tone", "text_permitted_backgrounds"))


def min_delta_l_between_meanings() -> float:
    """Two colours that mean different things must differ by at least this L\\*."""
    return float(_need(ados_tokens(), "colour", "min_delta_L_between_meanings"))


def text_contrast_ratio_min() -> float:
    """WCAG-style contrast floor for text (``ADOS-3.8.030``)."""
    return float(_need(ados_tokens(), "colour", "text_contrast_ratio_min"))


def permitted_colour_uses() -> list[str]:
    """The closed list of things colour is allowed to do in ADOS."""
    return list(_need(ados_tokens(), "colour", "permitted_uses"))


def module_mm() -> float:
    return float(_need(ados_tokens(), "sheet", "module_mm"))


# ---------------------------------------------------------------------------
# Density and the layout solver (ADOS Volume 7)
#
# These are what the Creative Layer's composer reads. They exist in the
# standard already: ADOS-7.5 specifies a deterministic solver with an explicit
# objective and tie-break, and ADOS-3.7/3.11 give the density limits its hard
# constraints check. The composer must not carry its own copies of these
# numbers — a second set would be a second standard.
# ---------------------------------------------------------------------------


def fill_ratio_bounds() -> tuple[float, float]:
    """Permitted fill ratio for a composed page — ``H13`` / ``ADOS-3.7.010``."""
    d = _need(ados_tokens(), "density")
    return float(d["fill_ratio_min"]), float(d["fill_ratio_max"])


def fill_ratio_target() -> float:
    """The value a direction's ``text_density`` defaults towards."""
    return float(_need(ados_tokens(), "density", "fill_ratio_target"))


def local_coverage_max() -> float:
    """Ink coverage ceiling in one window — ``H12`` / ``ADOS-3.7.020``."""
    return float(_need(ados_tokens(), "density", "local_coverage_max"))


def coverage_window_mm() -> float:
    """Side of the window ``local_coverage_max`` is measured over."""
    return float(_need(ados_tokens(), "density", "coverage_window_mm"))


def alignment_edges_max_per_axis() -> int:
    """Distinct alignment edges allowed — ``H14`` / ``ADOS-3.11.040``."""
    return int(_need(ados_tokens(), "density", "alignment_edges_max_per_axis"))


def emphasis_area_max() -> float:
    """Share of a page that may be emphasised (``ADOS-3.7.030``)."""
    return float(_need(ados_tokens(), "density", "emphasis_area_max"))


def solver_lattice_mm() -> float:
    """The placement lattice the solver works on (``ADOS-7.5.010``)."""
    return float(_need(ados_tokens(), "solver", "lattice_mm"))


def solver_objective_weights() -> dict[str, float]:
    """The objective's declared weights (``ADOS-7.5.040``)."""
    return {
        k: float(v)
        for k, v in _need(ados_tokens(), "solver", "objective_weights").items()
    }


def solver_tie_break() -> list[str]:
    """The tie-break order, applied when two candidates score equally.

    Stated in the standard rather than left to sort stability, because a sort
    that is stable by accident is a sort that changes when the input order
    changes (``ADOS-7.5.050``).
    """
    return list(_need(ados_tokens(), "solver", "tie_break"))


def solver_escalation_order() -> list[str]:
    """What to do with an infeasible layout, in order (``ADOS-7.5.070``).

    Step 4 — *split the sheet* — is the one a document composer reaches for
    most: a page that will not hold its content becomes two pages, never a
    page with smaller text on it.
    """
    return list(_need(ados_tokens(), "solver", "escalation_order"))


def solver_prohibited_remedies() -> list[str]:
    """Things the solver may not do to make an infeasible page fit.

    Reducing text size or line width would trade a legibility rule for a
    density one, and the standard forbids it outright: an infeasible page is
    reported, not shrunk (``ADOS-7.5.070``).
    """
    return list(_need(ados_tokens(), "solver", "prohibited_remedies"))


def submodule_mm() -> float:
    """The placement lattice and baseline pitch (``ADOS-3.3.030``)."""
    return float(_need(ados_tokens(), "sheet", "submodule_mm"))


def _need(tree: dict[str, Any], *path: str) -> Any:
    node: Any = tree
    for key in path:
        if not isinstance(node, dict) or key not in node:
            raise AdosBindingError(
                "ADOS token tree has no " + ".".join(path) + " — the Brand System "
                "cannot validate against a standard it cannot read."
            )
        node = node[key]
    return node

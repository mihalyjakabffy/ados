"""
The finding registry: brand/creative/finding_registry.py.

Two things this suite exists to guarantee, per the module's own docstring:
that every finding code brand.creative.evaluate can actually emit (with a
non-empty `code`) is registered here — not a second, drifting copy of the
same knowledge — and that "registered" and "actionable" stay genuinely
different questions with genuinely different answers.
"""

from __future__ import annotations

import pytest

from brand.creative.composer import compose
from brand.creative.directions import DIRECTIONS, get_direction
from brand.creative.evaluate import evaluate
from brand.creative.finding_registry import (
    FINDING_REGISTRY,
    UnknownFindingCodeError,
    describe,
    get_finding_definition,
    is_actionable,
)
from brand.creative.scope import ScopeType
from brand.examples.malthouse import malthouse_content
from brand.examples.studio_nord import studio_nord as build_studio_nord
from brand.examples.studio_om import studio_om as build_studio_om
from brand.validation.brand_validator import Severity


@pytest.fixture(scope="module")
def content():
    return malthouse_content()


# ---------------------------------------------------------------------------
# Every registered finding has valid metadata
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code", sorted(FINDING_REGISTRY))
def test_every_registered_finding_has_valid_metadata(code):
    definition = get_finding_definition(code)
    assert definition.code == code
    assert definition.metric
    assert isinstance(definition.severity, Severity)
    assert isinstance(definition.threshold, float)
    assert isinstance(definition.scope, ScopeType)
    assert definition.description


def test_describe_merges_actionability_from_the_capability_registry():
    d = describe("FILL_RATIO_LOW")
    assert d["actionable"] is True
    assert d["metric"] == "fill_ratio"


# ---------------------------------------------------------------------------
# Unknown codes are rejected
# ---------------------------------------------------------------------------


def test_an_unknown_finding_code_is_rejected():
    with pytest.raises(UnknownFindingCodeError):
        get_finding_definition("NOT_A_REAL_CODE")


def test_is_actionable_is_false_for_an_unknown_code_rather_than_raising():
    assert is_actionable("NOT_A_REAL_CODE") is False


# ---------------------------------------------------------------------------
# registered != actionable
# ---------------------------------------------------------------------------


def test_fill_ratio_low_is_actionable():
    assert is_actionable("FILL_RATIO_LOW") is True


def test_fill_ratio_high_is_registered_but_not_actionable():
    """A real, meaningful finding — the H13 hard-ceiling check — with no
    proven capability yet. Registered and actionable are different claims."""
    assert "FILL_RATIO_HIGH" in FINDING_REGISTRY
    assert is_actionable("FILL_RATIO_HIGH") is False


# ---------------------------------------------------------------------------
# No drift between what evaluate() actually emits and what is registered
# ---------------------------------------------------------------------------


def test_every_code_evaluate_actually_emits_is_registered(content):
    """Scans real evaluations across every shipped brand/direction
    combination — not the source code — so this fails the moment a new
    check sets `code=...` without a matching FINDING_REGISTRY entry,
    which is exactly the drift the registry exists to prevent."""
    seen_codes: set[str] = set()
    for build in (build_studio_nord, build_studio_om):
        brand = build()
        for direction_id in DIRECTIONS:
            direction = get_direction(direction_id)
            plan = compose(content, direction, brand)
            ev = evaluate(plan, direction, brand.resolve_tokens())
            seen_codes.update(f.code for f in ev.report.findings if f.code)

    assert seen_codes, "the sweep itself must have found at least one coded finding"
    unregistered = seen_codes - set(FINDING_REGISTRY)
    assert not unregistered, f"evaluate() emits code(s) with no FINDING_REGISTRY entry: {unregistered}"

"""
The validator, category by category.

Each architectural test builds a brand that is *wrong in exactly one way* and
asserts that the validator finds that fault and classifies it correctly. The
point is not coverage of the code but coverage of the failure modes: these are
the mistakes that produce an unreadable drawing, and a validator that misses
one of them is worse than no validator, because it is trusted.
"""

from __future__ import annotations

import pytest

from brand.models.architectural_language import (
    DiagramLanguage,
    DrawingLanguage,
    Lineweights,
    RenderLanguage,
    RenderMood,
)
from brand.models.brand import Brand
from brand.models.identity import PersonalityAxis
from brand.models.visual_identity import (
    ColourSystem,
    FontFace,
    Grid,
    RoleClass,
    Spacing,
    Typography,
    TypeRole,
    VisualIdentity,
)
from brand.validation.brand_validator import BrandValidator, Category, Severity


def _with_drawing(base: Brand, **kwargs) -> Brand:
    drawing = base.architectural_language.drawing.model_copy(update=kwargs)
    return base.model_copy(
        update={
            "architectural_language": base.architectural_language.model_copy(
                update={"drawing": drawing}
            )
        }
    )


def _findings(brand: Brand, field_prefix: str):
    return [
        f for f in BrandValidator().validate(brand).findings
        if f.field.startswith(field_prefix)
    ]


# ---------------------------------------------------------------------------
# The example
# ---------------------------------------------------------------------------


def test_the_worked_example_validates(studio_nord):
    report = studio_nord.check()
    assert report.ok, report.summary()
    assert not report.blocking


def test_the_worked_example_still_has_something_to_say(studio_nord):
    """An example with zero findings teaches nothing about the validator."""
    assert studio_nord.check().findings


# ---------------------------------------------------------------------------
# Architectural — line weights
# ---------------------------------------------------------------------------


def test_reversed_lineweight_hierarchy_blocks(studio_nord):
    """The failure that makes a drawing say the opposite of what is built."""
    bad = _with_drawing(
        studio_nord,
        lineweights=Lineweights(
            cut_mm=0.18, primary_mm=0.35, secondary_mm=0.25, background_mm=0.18
        ),
    )
    report = bad.check()
    blocking = report.blocking
    assert blocking, "a reversed cut/seen pair must block publication"
    assert any("reversed" in f.message for f in blocking)
    assert all(f.category is Category.ARCHITECTURAL for f in blocking)
    assert not report.ok


def test_equal_adjacent_weights_error(studio_nord):
    bad = _with_drawing(
        studio_nord,
        lineweights=Lineweights(
            cut_mm=0.35, primary_mm=0.35, secondary_mm=0.25, background_mm=0.18
        ),
    )
    errors = [f for f in bad.check().findings if f.severity is Severity.ERROR]
    assert any("no hierarchy" in f.message for f in errors)


def test_weight_off_the_iso_series_warns(studio_nord):
    bad = _with_drawing(
        studio_nord,
        lineweights=Lineweights(
            cut_mm=0.62, primary_mm=0.35, secondary_mm=0.25, background_mm=0.18
        ),
    )
    findings = _findings(bad, "architectural_language.drawing.lineweights.cut_mm")
    assert any("ISO 128" in f.message for f in findings)
    assert any("0.7" in (f.suggestion or "") for f in findings)


def test_weight_below_the_issue_minimum_errors(studio_nord):
    bad = _with_drawing(
        studio_nord,
        lineweights=Lineweights(
            cut_mm=0.7, primary_mm=0.35, secondary_mm=0.25, background_mm=0.13
        ),
    )
    findings = bad.check().findings
    assert any(
        f.severity is Severity.ERROR and "minimum for an issued line" in f.message
        for f in findings
    )


# ---------------------------------------------------------------------------
# Architectural — type
# ---------------------------------------------------------------------------


def test_body_text_below_the_cap_floor_errors(studio_nord):
    typo = studio_nord.visual_identity.typography
    bad_typo = typo.model_copy(
        update={"body_styles": {**typo.body_styles, "body": TypeRole(step="t1")}}
    )
    bad = studio_nord.model_copy(
        update={
            "visual_identity": studio_nord.visual_identity.model_copy(
                update={"typography": bad_typo}
            )
        }
    )
    findings = _findings(bad, "visual_identity.typography.body_styles.body")
    assert any(f.severity is Severity.ERROR for f in findings)
    assert any("role_class='tertiary'" in (f.suggestion or "") for f in findings)


def test_tertiary_role_may_use_the_small_step(studio_nord):
    """The counterpart: ADOS permits 1.8 mm for provenance, and so must we."""
    assert not [
        f for f in studio_nord.check().findings
        if f.field.endswith("body_styles.legal")
    ]


def test_role_in_an_undeclared_face_errors():
    b = Brand.create(name="A")
    typo = b.visual_identity.typography.model_copy(
        update={"body_styles": {"body": TypeRole(step="t2", face="mono")}}
    )
    bad = b.model_copy(
        update={
            "visual_identity": b.visual_identity.model_copy(
                update={"typography": typo}
            )
        }
    )
    findings = bad.check().findings
    assert any("mono face, which is not declared" in f.message for f in findings)


def test_baseline_off_the_sub_module_warns(studio_nord):
    typo = studio_nord.visual_identity.typography.model_copy(
        update={"baseline_mm": 4.0}
    )
    grid = studio_nord.visual_identity.grid.model_copy(update={"baseline_mm": 4.0})
    bad = studio_nord.model_copy(
        update={
            "visual_identity": studio_nord.visual_identity.model_copy(
                update={"typography": typo, "grid": grid}
            )
        }
    )
    assert any(
        "sub-module" in f.message
        for f in _findings(bad, "visual_identity.typography.baseline_mm")
    )


# ---------------------------------------------------------------------------
# Architectural — colour and tone
# ---------------------------------------------------------------------------


def test_low_contrast_text_is_flagged():
    b = Brand.create(
        name="A",
        colour=ColourSystem(text_primary="#9a9a9a", background="#ffffff"),
    )
    findings = [f for f in b.check().findings if "contrast" in f.message]
    assert findings
    assert findings[0].severity in (Severity.ERROR, Severity.WARN)


def test_indistinct_accent_warns():
    b = Brand.create(
        name="A", colour=ColourSystem(primary="#111111", accent="#181818")
    )
    assert any(
        "accent" in f.field and "ΔL*" in f.message for f in b.check().findings
    )


def test_diagram_palette_outside_the_brand_errors(studio_nord):
    arch = studio_nord.architectural_language
    bad = studio_nord.model_copy(
        update={
            "architectural_language": arch.model_copy(
                update={
                    "diagrams": arch.diagrams.model_copy(
                        update={"palette": ("#ff00ff",)}
                    )
                }
            )
        }
    )
    findings = _findings(bad, "architectural_language.diagrams.palette")
    assert any(f.severity is Severity.ERROR for f in findings)
    assert any("#ff00ff" in f.message for f in findings)


def test_too_many_tones_errors(studio_nord):
    arch = studio_nord.architectural_language
    bad = studio_nord.model_copy(
        update={
            "architectural_language": arch.model_copy(
                update={
                    "diagrams": arch.diagrams.model_copy(
                        update={"fill_tones": ("T0", "T1", "T2", "T3", "T4")}
                    )
                }
            )
        }
    )
    assert any(
        "permits 4 per sheet" in f.message or "per sheet" in f.message
        for f in _findings(bad, "architectural_language.diagrams.fill_tones")
    )


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------


def test_spacing_scale_that_does_not_separate_groups_warns():
    b = Brand.create(name="A")
    bad = b.model_copy(
        update={
            "visual_identity": b.visual_identity.model_copy(
                update={"spacing": Spacing(scale=(1, 1.5, 2, 3))}
            )
        }
    )
    assert any(
        "twice a within-group gap" in (f.suggestion or "")
        for f in _findings(bad, "visual_identity.spacing.scale")
    )


def test_two_heading_levels_on_one_step_warn():
    b = Brand.create(name="A")
    typo = b.visual_identity.typography.model_copy(
        update={
            "heading_styles": {
                "h1": TypeRole(step="t4"),
                "h2": TypeRole(step="t4"),
            }
        }
    )
    bad = b.model_copy(
        update={
            "visual_identity": b.visual_identity.model_copy(
                update={"typography": typo}
            )
        }
    )
    assert any(
        "one level" in (f.suggestion or "")
        for f in _findings(bad, "visual_identity.typography.heading_styles")
    )


def test_disagreeing_baselines_error():
    b = Brand.create(name="A")
    bad = b.model_copy(
        update={
            "visual_identity": b.visual_identity.model_copy(
                update={"grid": Grid(baseline_mm=10.0)}
            )
        }
    )
    assert any(
        f.severity is Severity.ERROR
        for f in _findings(bad, "visual_identity.grid.baseline_mm")
    )


def test_brand_copy_using_its_own_forbidden_word_warns(studio_nord):
    ident = studio_nord.identity.model_copy(
        update={"tagline": "Bespoke architecture"}
    )
    bad = studio_nord.model_copy(update={"identity": ident})
    assert any(
        "forbidden words" in f.message
        for f in _findings(bad, "communication.forbidden_words")
    )


# ---------------------------------------------------------------------------
# Structural
# ---------------------------------------------------------------------------


def test_unlicensed_face_errors():
    b = Brand.create(
        name="A", primary_font=FontFace(family="Söhne", licensed=False)
    )
    assert any(
        f.severity is Severity.ERROR and "unlicensed" in f.message
        for f in b.check().findings
    )


def test_missing_mono_face_warns(minimal_brand):
    assert any(
        f.field.endswith("mono_font") and f.severity is Severity.WARN
        for f in minimal_brand.check().findings
    )


# ---------------------------------------------------------------------------
# Render coherence
# ---------------------------------------------------------------------------


def test_dramatic_renders_contradict_a_quiet_practice(studio_nord):
    arch = studio_nord.architectural_language
    bad = studio_nord.model_copy(
        update={
            "architectural_language": arch.model_copy(
                update={
                    "renders": arch.renders.model_copy(
                        update={"mood": RenderMood.DRAMATIC}
                    )
                }
            )
        }
    )
    assert any(
        "quiet" in f.message
        for f in _findings(bad, "architectural_language.renders.mood")
    )


# ---------------------------------------------------------------------------
# Report shape
# ---------------------------------------------------------------------------


def test_warnings_do_not_block(studio_nord):
    """A practice may make a considered choice the system would not have made."""
    from brand.validation.brand_validator import Finding, ValidationReport

    report = ValidationReport(findings=[
        Finding(Severity.WARN, Category.CONSISTENCY, "x", "y")
    ])
    assert report.ok


def test_errors_block():
    from brand.validation.brand_validator import Finding, ValidationReport

    report = ValidationReport(findings=[
        Finding(Severity.ERROR, Category.ARCHITECTURAL, "x", "y")
    ])
    assert not report.ok


def test_report_serialises(studio_nord):
    payload = studio_nord.check().to_dict()
    assert set(payload) == {"brand", "ok", "counts", "findings"}
    for finding in payload["findings"]:
        assert finding["field"] and finding["message"]


def test_every_finding_proposes_a_fix(studio_nord):
    """A validator that reports without remedy just moves the work."""
    bad = _with_drawing(
        studio_nord,
        lineweights=Lineweights(
            cut_mm=0.18, primary_mm=0.35, secondary_mm=0.25, background_mm=0.18
        ),
    )
    serious = [
        f for f in bad.check().findings
        if f.severity in (Severity.BLOCK, Severity.ERROR)
    ]
    assert serious
    assert all(f.suggestion for f in serious)

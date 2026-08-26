"""
ADOS-M3.1 — brand/llm/vocabulary.py.

The controlled vocabulary itself, and that document_type resolution
reaches the one real, canonical Document Type registry rather than a
second, duplicated list.
"""

from __future__ import annotations

from brand.llm.vocabulary import Action, SemanticField, Target, known_document_type_ids


def test_action_vocabulary_matches_ados_m3_1():
    assert {a.value for a in Action} == {
        "create", "modify", "regenerate", "revise", "extend",
        "summarize", "transform", "compare", "review",
    }


def test_target_vocabulary_matches_ados_m3_1():
    assert {t.value for t in Target} == {
        "document", "project", "section", "page", "brand", "content",
        "presentation", "portfolio", "report", "template",
    }


def test_semantic_field_covers_every_minimum_field():
    names = {f.value for f in SemanticField}
    for required in ("action", "target", "purpose", "audience", "content_requirements",
                      "style_requirements", "design_requirements", "constraints",
                      "references", "modifiers"):
        assert required in names


def test_known_document_type_ids_resolves_the_real_registry():
    from brand.project.document_types import DOCUMENT_TYPES

    ids = known_document_type_ids()
    assert ids == frozenset(DOCUMENT_TYPES)
    assert "portfolio" in ids
    assert "investor-deck" in ids  # ADOS-M2.5's projections, added as pure data
    assert "tender-document" in ids
    assert len(ids) == 11


def test_known_document_type_ids_is_not_a_second_hardcoded_list():
    """A new type registered later must appear here with zero code change —
    proving this function really delegates rather than caching a copy."""
    from brand.project import document_types as dt_module

    original = dict(dt_module.DOCUMENT_TYPES)
    try:
        fake = original["portfolio"].model_copy(update={"id": "zzz-test-only"})
        dt_module.DOCUMENT_TYPES = {**original, "zzz-test-only": fake}
        assert "zzz-test-only" in known_document_type_ids()
    finally:
        dt_module.DOCUMENT_TYPES = original

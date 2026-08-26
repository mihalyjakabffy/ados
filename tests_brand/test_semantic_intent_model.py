"""
ADOS-M3.1 — brand/llm/semantic_intent.py.

The domain model's own invariants: a field lives in exactly one of
explicit/inferred/ambiguous, JSON round-trips cleanly, and the accessor
helpers never blur which bucket a value came from.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from brand.llm.semantic_intent import SCHEMA_VERSION, SemanticFieldValues, SemanticIntent
from brand.llm.vocabulary import SemanticField


def test_default_intent_is_empty_and_valid():
    si = SemanticIntent()
    assert si.schema_version == SCHEMA_VERSION
    assert si.ambiguous == ()
    assert si.confidence == 0.5
    assert si.resolved(SemanticField.ACTION) is None


def test_round_trips_through_json():
    si = SemanticIntent(
        explicit=SemanticFieldValues(action="create", target="document", subject="Riverside project"),
        confidence=0.8,
    )
    payload = json.loads(json.dumps(si.to_dict()))
    rebuilt = SemanticIntent.model_validate(payload)
    assert rebuilt == si


def test_explicit_wins_over_inferred_in_resolved():
    si = SemanticIntent(
        explicit=SemanticFieldValues(action="create"),
        inferred=SemanticFieldValues(target="document"),
    )
    assert si.resolved(SemanticField.ACTION) == "create"
    assert si.is_explicit(SemanticField.ACTION)
    assert not si.is_inferred(SemanticField.ACTION)
    assert si.resolved(SemanticField.TARGET) == "document"
    assert si.is_inferred(SemanticField.TARGET)
    assert not si.is_explicit(SemanticField.TARGET)


def test_unresolved_field_is_neither_explicit_nor_inferred_nor_ambiguous():
    si = SemanticIntent(explicit=SemanticFieldValues(action="create"))
    assert not si.is_explicit(SemanticField.AUDIENCE)
    assert not si.is_inferred(SemanticField.AUDIENCE)
    assert not si.is_ambiguous(SemanticField.AUDIENCE)
    assert si.resolved(SemanticField.AUDIENCE) is None


def test_a_field_cannot_be_both_explicit_and_inferred():
    with pytest.raises(ValidationError, match="both explicit and inferred"):
        SemanticIntent(
            explicit=SemanticFieldValues(action="create"),
            inferred=SemanticFieldValues(action="modify"),
        )


def test_a_field_cannot_be_valued_and_ambiguous():
    with pytest.raises(ValidationError, match="also listed as ambiguous"):
        SemanticIntent(
            explicit=SemanticFieldValues(action="create"),
            ambiguous=(SemanticField.ACTION,),
        )


def test_ambiguity_notes_must_reference_an_ambiguous_field():
    with pytest.raises(ValidationError, match="not listed in ambiguous"):
        SemanticIntent(ambiguity_notes={"action": "no idea"})


def test_ambiguity_notes_key_must_be_a_known_field():
    with pytest.raises(ValidationError, match="not a known SemanticField"):
        SemanticIntent(ambiguous=(SemanticField.ACTION,), ambiguity_notes={"nonsense_field": "x"})


def test_confidence_is_bounded():
    with pytest.raises(ValidationError):
        SemanticIntent(confidence=1.5)
    with pytest.raises(ValidationError):
        SemanticIntent(confidence=-0.1)


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        SemanticIntent.model_validate({"not_a_real_field": True})
    with pytest.raises(ValidationError):
        SemanticFieldValues.model_validate({"page_count": 12})


def test_intent_and_field_values_are_frozen():
    si = SemanticIntent()
    with pytest.raises(ValidationError):
        si.confidence = 0.9  # type: ignore[misc]


def test_list_valued_fields_default_to_empty_tuple():
    values = SemanticFieldValues()
    assert values.content_requirements == ()
    assert values.references == ()


def test_set_fields_ignores_empty_and_none_values():
    values = SemanticFieldValues(action="create", audience="", references=())
    assert values.set_fields() == {SemanticField.ACTION}

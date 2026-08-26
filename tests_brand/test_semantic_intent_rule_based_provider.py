"""
ADOS-M3.1 — brand/llm/providers/rule_based_provider.py.

The deterministic fallback used whenever no LLM is configured — which
is every automated test run in this repository. Covers ADOS-M3.1 §17's
own test list: basic intents, every document type, ambiguity, explicit
vs inferred, invalid/unclear requests failing deterministically (never
crashing), and context sensitivity.
"""

from __future__ import annotations

import pytest

from brand.llm.context import SemanticContext, build_semantic_context
from brand.llm.prompt import build_system_prompt
from brand.llm.providers.rule_based_provider import RuleBasedProvider
from brand.llm.validation import validate_semantic_intent
from brand.llm.vocabulary import Action, SemanticField, Target
from brand.project.document_types import DOCUMENT_TYPES

_SYSTEM_PROMPT = build_system_prompt()
_PROVIDER = RuleBasedProvider()


def _extract(text: str, **kwargs):
    ctx = build_semantic_context(text, **kwargs)
    intent, metadata = _PROVIDER.extract(_SYSTEM_PROMPT, ctx)
    return intent, metadata, ctx


# ---------------------------------------------------------------------------
# Basic intents (ADOS-M3.1 §17)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text,expected_action", [
    ("Create a new project report.", Action.CREATE),
    ("Modify the existing brief.", Action.MODIFY),
    ("Regenerate the whole document.", Action.REGENERATE),
    ("Revise the last section.", Action.REVISE),
    ("Extend the case study with more detail.", Action.EXTEND),
    ("Summarize this report for me.", Action.SUMMARIZE),
    ("Turn this into a client-ready version.", Action.TRANSFORM),
    ("Compare the two design options.", Action.COMPARE),
    ("Review the current draft.", Action.REVIEW),
])
def test_basic_action_recognition(text, expected_action):
    intent, _, _ = _extract(text)
    assert intent.resolved(SemanticField.ACTION) == expected_action.value
    assert intent.is_explicit(SemanticField.ACTION)


def test_provider_never_raises_on_gibberish():
    intent, metadata, ctx = _extract("asdkjaslkdj random gibberish not a real request")
    assert intent.is_ambiguous(SemanticField.ACTION)
    assert intent.is_ambiguous(SemanticField.TARGET)
    report = validate_semantic_intent(intent, ctx)
    assert report.ok  # honestly ambiguous, not silently wrong
    assert metadata.provider == "rule-based"


def test_provider_never_raises_on_empty_string():
    intent, _, ctx = _extract("")
    report = validate_semantic_intent(intent, ctx)
    assert report.ok


# ---------------------------------------------------------------------------
# Document type resolution — every currently supported ADOS document type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("type_id", sorted(DOCUMENT_TYPES))
def test_document_type_resolves_for_every_registered_type(type_id):
    name = DOCUMENT_TYPES[type_id].name
    intent, _, ctx = _extract(f"Create a new {name}.")
    assert intent.resolved(SemanticField.DOCUMENT_TYPE) == type_id
    assert intent.resolved(SemanticField.TARGET) == Target.DOCUMENT.value
    report = validate_semantic_intent(intent, ctx)
    assert report.ok


# ---------------------------------------------------------------------------
# Ambiguity
# ---------------------------------------------------------------------------


def test_document_type_missing_is_ambiguous_when_target_is_referential_and_no_context():
    intent, _, ctx = _extract("Turn this into something I can send to the client.")
    assert intent.is_ambiguous(SemanticField.TARGET)
    assert not intent.is_explicit(SemanticField.TARGET)
    assert intent.resolved(SemanticField.AUDIENCE) == "client"
    assert intent.is_explicit(SemanticField.AUDIENCE)


def test_unclear_action_is_ambiguous_not_invented():
    intent, _, _ = _extract("Use the same branding as the last presentation but make this one much more visual.")
    assert intent.is_ambiguous(SemanticField.ACTION)
    # never a fabricated compound value
    assert intent.resolved(SemanticField.ACTION) is None


def test_no_project_context_never_fabricates_project_context():
    _, _, ctx = _extract("Create a portfolio.")
    assert ctx.project_context is None


# ---------------------------------------------------------------------------
# Explicit vs inferred — never presented as the same thing
# ---------------------------------------------------------------------------


def test_inferred_values_are_never_in_the_explicit_bucket():
    intent, _, _ = _extract(
        "Turn this into something I can send to the client.",
        design_state=None,
    )
    # With no design_state, target lands in ambiguous, not a guessed explicit value
    assert not intent.is_explicit(SemanticField.TARGET)


def test_context_sensitivity_same_request_different_context():
    """ADOS-M3.1 §17 — the same request must resolve differently once real
    context changes. Here: whether a document is currently open."""
    text = "Turn this into something I can send to the client."

    without_context, _, _ = _extract(text)
    assert without_context.is_ambiguous(SemanticField.TARGET)

    ctx_with_document = SemanticContext(
        request=text,
        design_state_context={"document_id": "doc-1", "output_type": "design-report"},
    )
    with_context, _ = _PROVIDER.extract(_SYSTEM_PROMPT, ctx_with_document)
    assert with_context.resolved(SemanticField.TARGET) == Target.DOCUMENT.value
    assert with_context.is_inferred(SemanticField.TARGET)
    assert not with_context.is_explicit(SemanticField.TARGET)


# ---------------------------------------------------------------------------
# Style / brand reference / quality / design direction — free text, not
# invented specificity (ADOS-M3.1 §14/§16)
# ---------------------------------------------------------------------------


def test_style_and_quality_direction_are_captured_without_inventing_layout_detail():
    intent, _, _ = _extract(
        "Create a portfolio about the Riverside project. Make it feel like our "
        "existing studio materials but more premium."
    )
    assert intent.resolved(SemanticField.SUBJECT) == "Riverside project"
    assert intent.resolved(SemanticField.STYLE_REFERENCE) == "existing studio materials"
    assert intent.resolved(SemanticField.QUALITY_DIRECTION) == "premium"
    # never invented: page_count, font, grid, colour, image count, layout
    # are not even fields on the schema — nothing to assert false for,
    # which is itself the point (ADOS-M3.1 §14).


def test_design_direction_is_captured_as_free_text_not_a_numeric_setting():
    intent, _, _ = _extract(
        "Use the same branding as the last presentation but make this one much more visual."
    )
    assert intent.resolved(SemanticField.DESIGN_DIRECTION) == "more visual"
    assert isinstance(intent.resolved(SemanticField.DESIGN_DIRECTION), str)

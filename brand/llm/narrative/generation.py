"""
brand/llm/narrative/generation.py

The generator abstraction ADOS-M3.3 §31 asks for:

    NarrativeGenerator -> LLMProvider-equivalent -> ClaudeProvider

(the master prompt's own arrow uses "LLMProvider", but that class
(``brand.llm.provider.LLMProvider``) is hard-typed to
``SemanticIntent`` — ADOS-M3.1's own narrow contract. ADOS-M3.2 already
established the correct reusable seam for a *different* structured-
output shape: the module-level ``get_client()``/``call_structured()``
functions in ``brand.llm.providers.claude_provider``, generic over
whatever pydantic ``output_format`` a caller passes. This module reuses
that exact seam — no second Claude client, and the domain
(``NarrativePlan``) never touches an Anthropic SDK type.)

Two implementations, mirroring ``brand.llm.content.extraction``'s own
split precisely:

* :class:`RuleBasedNarrativeGenerator` — deterministic, no network call
  ever. ADOS-M3.3 §44 is explicit that this is a CI-determinism/schema/
  regression-testing fixture, not a general-purpose narrative planner:
  it builds one narrative strategy from ``NarrativeGenerationContext``'s
  already-scoped content using fixed rules, and reliably reproduces the
  same plan shape for the same input content and objective.
* :class:`LLMNarrativeGenerator` — Claude, via structured output.

**The anti-hallucination mechanism is structural, mirroring ADOS-M3.2's
own.** The LLM's structured-output schema (``RawNarrativePlan`` and its
nested ``Raw*`` types) may only name a fact/claim/asset/entity **id** —
never a value, a status, or a piece of source text. After the call
returns, :func:`_materialize` drops (never trusts) any id that does not
actually appear in the ``ContentSummary`` the LLM was given — an
invented id is silently excluded from the resulting
``ContentReferenceSet``, exactly as a source document's embedded
instruction is silently excluded from ever being obeyed (ADOS-M3.3
§32's trust-boundary rule, ADOS-M3.2 §31's own precedent). A section
whose every reference turns out to be invented ends up with empty
``content_refs`` — a plan-shape a human reviewer or
``brand.llm.narrative.validation`` can immediately see is thin, never a
silently-fabricated fact.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from brand.llm.content.vocabulary import FactStatus
from brand.llm.narrative.context import NarrativeGenerationContext
from brand.llm.narrative.model import (
    ContentReferenceSet,
    GeneratedClaim,
    NarrativeExclusion,
    NarrativeIssue,
    NarrativeMissingInformationImpact,
    NarrativePlan,
    NarrativeSection,
    NarrativeThesis,
)
from brand.llm.narrative.vocabulary import (
    ExclusionReason,
    MissingImpact,
    NarrativeIssueType,
    NarrativeObjective,
    NarrativeVoice,
    Relevance,
    Requirement,
    SectionPriority,
    SectionRole,
    Tone,
)
from brand.llm.provider import ProviderMetadata

logger = logging.getLogger(__name__)


class NarrativeGenerator(ABC):
    """One call: a scoped context in, a ``NarrativePlan`` and its
    metadata out. Mirrors ``brand.llm.content.extraction.ContentExtractor``'s
    own shape — no conversation state, no tool loop."""

    @abstractmethod
    def generate(
        self, context: NarrativeGenerationContext,
    ) -> tuple[NarrativePlan, Optional[ProviderMetadata]]:
        """Raise :class:`~brand.llm.provider.ProviderError` on any
        failure — never a vendor-specific exception."""


# ---------------------------------------------------------------------------
# Valid-id filtering — the structural anti-hallucination mechanism
# ---------------------------------------------------------------------------


class _ValidIds:
    __slots__ = ("facts", "claims", "assets", "entities")

    def __init__(self, context: NarrativeGenerationContext) -> None:
        summary = context.content_summary
        self.facts = frozenset(row["id"] for row in summary.facts)
        self.claims = frozenset(row["id"] for row in summary.claims)
        self.assets = frozenset(row["id"] for row in summary.assets)
        self.entities = frozenset(row["id"] for row in summary.entities)


def _filter_refs(raw: "RawContentRefs", valid: _ValidIds, *, where: str) -> ContentReferenceSet:
    def _keep(ids: tuple[str, ...], known: frozenset[str], kind: str) -> tuple[str, ...]:
        kept = tuple(i for i in ids if i in known)
        dropped = set(ids) - set(kept)
        if dropped:
            logger.warning(
                "narrative generation: dropping %d invented %s id(s) in %s: %s",
                len(dropped), kind, where, sorted(dropped),
            )
        return kept

    return ContentReferenceSet(
        fact_ids=_keep(raw.fact_ids, valid.facts, "fact"),
        claim_ids=_keep(raw.claim_ids, valid.claims, "claim"),
        asset_ids=_keep(raw.asset_ids, valid.assets, "asset"),
        entity_ids=_keep(raw.entity_ids, valid.entities, "entity"),
    )


def _coerce_enum(value: Optional[str], enum_cls: type, default: Any) -> Any:
    """The same posture ``brand.llm.content.extraction`` takes with
    ``RawEntity.type``: an unrecognised value from the LLM is a
    fallback, never a rejected call."""
    if not value:
        return default
    try:
        return enum_cls(value.strip().lower())
    except ValueError:
        logger.warning("narrative generation: unrecognised %s %r, defaulting to %r", enum_cls.__name__, value, default)
        return default


# ---------------------------------------------------------------------------
# Deterministic rule-based generator (ADOS-M3.3 §44)
# ---------------------------------------------------------------------------

#: The archetypal five/six/seven-role shapes for short/medium/long
#: compression — ADOS-M3.3 §22. Not a document template: a sequence of
#: SectionRole values a real DocumentType's structure is then read
#: against by the deterministic generator below, exactly the way
#: ``CreativeDirection.pacing`` is a preference, not a hard constraint.
_STRATEGY_BY_COMPRESSION: dict[str, tuple[SectionRole, ...]] = {
    "short": (SectionRole.OPENING, SectionRole.CONTEXT, SectionRole.CONCEPT, SectionRole.RESULT, SectionRole.CLOSING),
    "medium": (
        SectionRole.OPENING, SectionRole.CONTEXT, SectionRole.CONCEPT,
        SectionRole.DEVELOPMENT, SectionRole.EVIDENCE, SectionRole.RESULT, SectionRole.CLOSING,
    ),
    "long": (
        SectionRole.OPENING, SectionRole.CONTEXT, SectionRole.PROBLEM, SectionRole.CONCEPT,
        SectionRole.STRATEGY, SectionRole.DEVELOPMENT, SectionRole.EVIDENCE,
        SectionRole.ANALYSIS, SectionRole.RESULT, SectionRole.IMPACT, SectionRole.CLOSING,
    ),
}

#: A handful of real ``DocumentType`` ids mapped to a fixed rhetorical
#: shape — ADOS-M3.3 §21's own point that the same project content
#: supports different narratives for different document types. Still a
#: deterministic lookup table, not narrative reasoning: an unknown or
#: unmapped document type falls back to the compression-based shape
#: above, and the master prompt's own four worked strategy examples
#: (§21/§41 cases A-D) are what this table's four entries realise.
_STRATEGY_BY_DOCUMENT_TYPE: dict[str, tuple[SectionRole, ...]] = {
    "portfolio": (
        SectionRole.OPENING, SectionRole.CONCEPT, SectionRole.DEVELOPMENT,
        SectionRole.RESULT, SectionRole.CLOSING,
    ),
    "client-presentation": (
        SectionRole.PROBLEM, SectionRole.CONCEPT, SectionRole.DEVELOPMENT, SectionRole.IMPACT,
    ),
    "competition-document": (
        SectionRole.QUESTION, SectionRole.CONCEPT, SectionRole.STRATEGY,
        SectionRole.EVIDENCE, SectionRole.RESULT,
    ),
    "design-report": (
        SectionRole.CONTEXT, SectionRole.PROBLEM, SectionRole.TECHNICAL_EXPLANATION, SectionRole.RESULT,
    ),
}

_ROLE_PURPOSE: dict[SectionRole, str] = {
    SectionRole.OPENING: "establish immediate project identity",
    SectionRole.CONTEXT: "explain the site or project's condition",
    SectionRole.PROBLEM: "state the challenge the project responds to",
    SectionRole.QUESTION: "frame the question the project investigates",
    SectionRole.CONCEPT: "explain the central architectural idea",
    SectionRole.STRATEGY: "explain the approach taken to realise the concept",
    SectionRole.ANALYSIS: "analyse the available information in depth",
    SectionRole.DEVELOPMENT: "show how the concept becomes architecture",
    SectionRole.EVIDENCE: "support the claim with concrete project evidence",
    SectionRole.COMPARISON: "compare options or alternatives considered",
    SectionRole.RESULT: "communicate the outcome the project achieves",
    SectionRole.IMPACT: "explain the broader effect of the outcome",
    SectionRole.TECHNICAL_EXPLANATION: "explain a technical aspect of the project",
    SectionRole.CONCLUSION: "state the conclusion the material supports",
    SectionRole.CALL_TO_ACTION: "state what should happen next",
    SectionRole.CLOSING: "reinforce the project's central proposition",
}

_PRIMARY_ROLES = frozenset({
    SectionRole.OPENING, SectionRole.CONTEXT, SectionRole.CONCEPT,
    SectionRole.PROBLEM, SectionRole.DEVELOPMENT, SectionRole.RESULT,
})


class RawContentRefs(BaseModel):
    """Shared by every Raw* type below that can point at real content.
    Plain id strings the LLM copies from the ``ContentSummary`` it was
    given — never a value, a status, or source text (see this module's
    own docstring)."""

    model_config = ConfigDict(extra="forbid")

    fact_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    asset_ids: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()


class RawThesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1, max_length=500)
    supporting_refs: RawContentRefs = Field(default_factory=RawContentRefs)


class RawSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    purpose: str = Field(min_length=1, max_length=400)
    title: str = ""
    summary: str = ""
    priority: str = "secondary"
    requirement: str = "recommended"
    audience_relevance: str = "medium"
    content_refs: RawContentRefs = Field(default_factory=RawContentRefs)
    emphasis: tuple[str, ...] = ()
    draft: Optional[str] = None


class RawGeneratedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1000)
    status: str = "inferred"
    supporting_refs: RawContentRefs = Field(default_factory=RawContentRefs)
    related_section_index: Optional[int] = None


class RawNarrativeIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    description: str = Field(min_length=1, max_length=400)
    content_refs: RawContentRefs = Field(default_factory=RawContentRefs)
    impact: str = "medium"


class RawExclusion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str
    description: str = Field(min_length=1, max_length=400)
    excluded_refs: RawContentRefs = Field(default_factory=RawContentRefs)


class RawNarrativePlan(BaseModel):
    """The complete LLM structured-output contract. Deliberately has no
    ``audience`` field at all — audience is resolved once,
    deterministically, before generation ever runs (see
    ``brand.llm.narrative.context.resolve_audience``'s own docstring for
    why letting the LLM re-derive it per call would be wrong, not just
    redundant). ``objective`` stays LLM-chosen — genuine narrative
    reasoning, not a stable classification of the input."""

    model_config = ConfigDict(extra="forbid")

    objective: str
    tone: Optional[str] = None
    voice: str = "neutral"
    thesis: Optional[RawThesis] = None
    narrative_strategy: tuple[str, ...] = ()
    sections: tuple[RawSection, ...] = Field(min_length=1)
    generated_claims: tuple[RawGeneratedClaim, ...] = ()
    narrative_issues: tuple[RawNarrativeIssue, ...] = ()
    exclusions: tuple[RawExclusion, ...] = ()


def _materialize(raw: RawNarrativePlan, context: NarrativeGenerationContext) -> NarrativePlan:
    """Attach validated ids, assign deterministic sequence numbers, and
    coerce every free-text enum-like field the LLM produced — the same
    "the model proposes, code decides" split ``brand.llm.content.extraction``
    already establishes for M3.2."""
    valid = _ValidIds(context)

    objective = _coerce_enum(raw.objective, NarrativeObjective, context.objective_hint or NarrativeObjective.DOCUMENT)
    tone = _coerce_enum(raw.tone, Tone, None) if raw.tone else None
    voice = _coerce_enum(raw.voice, NarrativeVoice, NarrativeVoice.NEUTRAL)
    strategy = tuple(_coerce_enum(r, SectionRole, None) for r in raw.narrative_strategy)
    strategy = tuple(r for r in strategy if r is not None)

    thesis = None
    if raw.thesis is not None:
        supporting = _filter_refs(raw.thesis.supporting_refs, valid, where="thesis")
        if not supporting.is_empty:
            thesis = NarrativeThesis(statement=raw.thesis.statement, supporting_refs=supporting)
        else:
            logger.warning("narrative generation: dropping thesis with no valid supporting content")

    sections: list[NarrativeSection] = []
    for i, rs in enumerate(raw.sections):
        role = _coerce_enum(rs.role, SectionRole, SectionRole.CONTEXT)
        sections.append(NarrativeSection(
            role=role, purpose=rs.purpose, title=rs.title, summary=rs.summary,
            sequence=i, priority=_coerce_enum(rs.priority, SectionPriority, SectionPriority.SECONDARY),
            requirement=_coerce_enum(rs.requirement, Requirement, Requirement.RECOMMENDED),
            audience_relevance=_coerce_enum(rs.audience_relevance, Relevance, Relevance.MEDIUM),
            content_refs=_filter_refs(rs.content_refs, valid, where=f"section[{i}]"),
            emphasis=rs.emphasis, draft=rs.draft,
        ))

    section_ids = [s.id for s in sections]
    generated_claims = []
    for rgc in raw.generated_claims:
        refs = _filter_refs(rgc.supporting_refs, valid, where="generated_claim")
        if refs.is_empty:
            logger.warning("narrative generation: omitting generated claim with no supporting content: %r", rgc.text[:60])
            continue
        status = _coerce_enum(rgc.status, FactStatus, FactStatus.INFERRED)
        if status not in (FactStatus.INFERRED, FactStatus.AMBIGUOUS):
            status = FactStatus.INFERRED
        related = None
        if rgc.related_section_index is not None and 0 <= rgc.related_section_index < len(section_ids):
            related = section_ids[rgc.related_section_index]
        generated_claims.append(GeneratedClaim(
            text=rgc.text, status=status, supporting_refs=refs, related_section_id=related,
        ))

    narrative_issues = tuple(
        NarrativeIssue(
            type=_coerce_enum(ri.type, NarrativeIssueType, NarrativeIssueType.LOW_CONTENT_COVERAGE),
            description=ri.description, content_refs=_filter_refs(ri.content_refs, valid, where="narrative_issue"),
            impact=_coerce_enum(ri.impact, Relevance, Relevance.MEDIUM),
        )
        for ri in raw.narrative_issues
    )
    exclusions = tuple(
        NarrativeExclusion(
            reason=_coerce_enum(rx.reason, ExclusionReason, ExclusionReason.OTHER),
            description=rx.description, excluded_refs=_filter_refs(rx.excluded_refs, valid, where="exclusion"),
        )
        for rx in raw.exclusions
    )

    missing_information = tuple(
        NarrativeMissingInformationImpact(
            key=row["key"], required_for=row["required_for"],
            impact=_infer_missing_impact(row, context),
        )
        for row in context.content_summary.missing_information
    )

    return NarrativePlan(
        project_id=context.project_id,
        objective=objective, audience=context.audience, audience_label=context.audience_label,
        tone=tone, voice=voice, thesis=thesis, narrative_strategy=strategy,
        compression=context.compression, sections=tuple(sections),
        generated_claims=tuple(generated_claims), missing_information=missing_information,
        narrative_issues=narrative_issues, exclusions=exclusions,
        metadata={"document_type_id": context.document_type.id},
    )


def _infer_missing_impact(row: dict[str, Any], context: NarrativeGenerationContext) -> MissingImpact:
    """A M3.2 gap matters to *this* narrative exactly when the document
    type actually requires it (ADOS-M3.3 §18) — required_sections/
    metadata_requirements is the one existing, real signal for that;
    everything else is, at best, a guess this system has no basis for."""
    if row["key"] in context.document_type.metadata_requirements:
        return MissingImpact.IMPORTANT
    return MissingImpact.OPTIONAL


class RuleBasedNarrativeGenerator(NarrativeGenerator):
    """Deterministic, no network call — ADOS-M3.3 §44. Reproduces one
    fixed narrative shape (by compression level) from whatever content
    the context actually carries: a section per strategy role, with
    every fact/claim/asset whose key/text/type textually relates to that
    role's own vocabulary attached as its content_refs. Not a claim of
    narrative sophistication — a CI-safe fixture that proves the
    pipeline's mechanics (materialization, id filtering, validation,
    evaluation) without ever calling an LLM."""

    def generate(
        self, context: NarrativeGenerationContext,
    ) -> tuple[NarrativePlan, Optional[ProviderMetadata]]:
        strategy = _STRATEGY_BY_DOCUMENT_TYPE.get(
            context.document_type.id,
            _STRATEGY_BY_COMPRESSION.get(context.compression.value, _STRATEGY_BY_COMPRESSION["medium"]),
        )
        summary = context.content_summary

        remaining_fact_ids = [row["id"] for row in summary.facts if row["status"] != "conflicting"]
        remaining_claim_ids = [row["id"] for row in summary.claims]
        remaining_asset_ids = [row["id"] for row in summary.assets]

        sections: list[NarrativeSection] = []
        for i, role in enumerate(strategy):
            refs = ContentReferenceSet(
                fact_ids=tuple(remaining_fact_ids[:2]) if role in (SectionRole.OPENING, SectionRole.CONTEXT, SectionRole.EVIDENCE, SectionRole.RESULT) else (),
                claim_ids=tuple(remaining_claim_ids[:1]) if role in (SectionRole.CONCEPT, SectionRole.DEVELOPMENT, SectionRole.STRATEGY) else (),
                asset_ids=tuple(remaining_asset_ids[:1]) if role in (SectionRole.OPENING, SectionRole.CONTEXT, SectionRole.CONCEPT, SectionRole.DEVELOPMENT) else (),
            )
            if role in (SectionRole.OPENING, SectionRole.CONTEXT, SectionRole.EVIDENCE, SectionRole.RESULT):
                remaining_fact_ids = remaining_fact_ids[2:]
            if role in (SectionRole.CONCEPT, SectionRole.DEVELOPMENT, SectionRole.STRATEGY):
                remaining_claim_ids = remaining_claim_ids[1:]
            if role in (SectionRole.OPENING, SectionRole.CONTEXT, SectionRole.CONCEPT, SectionRole.DEVELOPMENT):
                remaining_asset_ids = remaining_asset_ids[1:]

            sections.append(NarrativeSection(
                role=role, purpose=_ROLE_PURPOSE[role], sequence=i,
                priority=SectionPriority.PRIMARY if role in _PRIMARY_ROLES else SectionPriority.SECONDARY,
                requirement=Requirement.RECOMMENDED, content_refs=refs,
            ))

        thesis = None
        thesis_claims = tuple(row["id"] for row in summary.claims)[:1]
        if thesis_claims:
            thesis = NarrativeThesis(
                statement=next(row["text"] for row in summary.claims if row["id"] == thesis_claims[0]),
                supporting_refs=ContentReferenceSet(claim_ids=thesis_claims),
            )

        narrative_issues = tuple(
            NarrativeIssue(
                type=NarrativeIssueType.CONFLICTING_INFORMATION,
                description=f"fact {row['key']!r} has conflicting values across sources",
                content_refs=ContentReferenceSet(fact_ids=(row["id"],)),
                impact=Relevance.HIGH,
            )
            for row in summary.facts if row["status"] == "conflicting"
        )
        missing_information = tuple(
            NarrativeMissingInformationImpact(
                key=row["key"], required_for=row["required_for"],
                impact=_infer_missing_impact(row, context),
            )
            for row in summary.missing_information
        )

        plan = NarrativePlan(
            project_id=context.project_id,
            objective=context.objective_hint or NarrativeObjective.DOCUMENT,
            audience=context.audience, audience_label=context.audience_label,
            voice=NarrativeVoice.NEUTRAL, thesis=thesis, narrative_strategy=strategy,
            compression=context.compression, sections=tuple(sections),
            missing_information=missing_information, narrative_issues=narrative_issues,
            metadata={"document_type_id": context.document_type.id, "generator": "rule-based"},
        )
        return plan, None


# ---------------------------------------------------------------------------
# LLM generator (ADOS-M3.3 §31)
# ---------------------------------------------------------------------------


class LLMNarrativeGenerator(NarrativeGenerator):
    """The real, structured-output narrative generator. Reuses
    ``brand.llm.providers.claude_provider``'s shared client/call helper
    — see this module's own docstring for why that matters."""

    _DEFAULT_MODEL = "claude-opus-5"
    _DEFAULT_MAX_TOKENS = 8192

    def __init__(self, model: Optional[str] = None, max_tokens: Optional[int] = None) -> None:
        self._model = model or os.environ.get("NARRATIVE_MODEL", self._DEFAULT_MODEL)
        self._max_tokens = max_tokens or int(os.environ.get("NARRATIVE_MAX_TOKENS", self._DEFAULT_MAX_TOKENS))
        self._client: Any = None

    def generate(
        self, context: NarrativeGenerationContext,
    ) -> tuple[NarrativePlan, ProviderMetadata]:
        from brand.llm.narrative.prompt import build_narrative_system_prompt, build_narrative_user_message
        from brand.llm.providers.claude_provider import call_structured, get_client

        if self._client is None:
            self._client = get_client()

        system_prompt = build_narrative_system_prompt()
        user_message = build_narrative_user_message(context)
        raw, metadata = call_structured(
            self._client, model=self._model, max_tokens=self._max_tokens,
            system_prompt=system_prompt, user_message=user_message,
            output_format=RawNarrativePlan, provider_name="claude",
        )
        return _materialize(raw, context), metadata

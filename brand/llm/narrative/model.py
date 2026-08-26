"""
brand/llm/narrative/model.py

ADOS-M3.3's canonical domain object: :class:`NarrativePlan`. Adapted
from the master prompt's §4/§10/§35 conceptual schemas to repository
convention — see ``brand/llm/narrative/vocabulary.py`` for which
vocabularies are reused (``Audience``) versus newly introduced, and
this package's own docstring for the boundary every field below
respects: no page, no coordinate, no grid, no font, no
``CommandIntent``.

**Provenance is by reference, not by copy (ADOS-M3.3 §12/§13).** A
section never carries a fact's text or an asset's caption; it carries
the *id* of a real ``brand.llm.content.model`` object
(``Fact``/``Claim``/``AssetContent``/``Entity``), via
:class:`ContentReferenceSet`. The chain the master prompt asks for —

    NarrativeSection -> ContentReference -> ContentItem -> SourceReference

is realised without inventing a redundant indirection layer: a M3.2
``Fact``/``Claim``/``AssetContent`` already *is* the addressable content
item and already carries its own ``source_refs`` inline, so
"NarrativeSection references content id X" plus "X's own
ContentIntelligenceModel entry carries source_refs" already is that
chain. Whether every id referenced here actually resolves in a given
``ContentIntelligenceModel`` is a fact about a *pairing* of a plan and a
content model, not about the plan alone — checked by
``brand.llm.narrative.validation``, not by a model_validator here (this
model must stay constructible and inspectable on its own, e.g. when
read back out of a trace, without a content model in hand).

**A `NarrativePlan` must remain valid with every `draft` field deleted**
(ADOS-M3.3 §36) — the only mandatory content carrier on
:class:`NarrativeSection` is ``purpose`` plus its content references;
``draft`` is additive, capped, and never a substitute for either.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brand.llm.content.vocabulary import FactStatus
from brand.llm.narrative.vocabulary import (
    Audience,
    ExclusionReason,
    MissingImpact,
    NarrativeCompression,
    NarrativeIssueType,
    NarrativeObjective,
    NarrativeVoice,
    Relevance,
    Requirement,
    SectionPriority,
    SectionRole,
    Tone,
)

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Bumped when the shape changes in a way a stored NarrativePlan or
#: trace would notice — brand/llm/content/model.py's own convention.
SCHEMA_VERSION = "3.3"

#: A freshly generated claim is always interpretive (ADOS-M3.3 §15): it
#: may be confidently inferred, or explicitly flagged as only weakly
#: supported, but it may never be VERIFIED (that would claim a source
#: states it outright, which a *generated* claim by definition does
#: not) and CONFLICTING/MISSING do not apply to something newly written.
_GENERATED_CLAIM_STATUSES = frozenset({FactStatus.INFERRED, FactStatus.AMBIGUOUS})


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ContentReferenceSet(BaseModel):
    """Which real M3.2 items back one section or claim — ADOS-M3.3 §12.
    Plain id strings, not embedded copies: the id is the only thing a
    section needs to point at a real ``Fact``/``Claim``/``AssetContent``/
    ``Entity`` in the ``ContentIntelligenceModel`` this plan was resolved
    against."""

    model_config = _Frozen

    fact_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    asset_ids: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.fact_ids or self.claim_ids or self.asset_ids or self.entity_ids)

    def all_ids(self) -> tuple[str, ...]:
        return self.fact_ids + self.claim_ids + self.asset_ids + self.entity_ids


class NarrativeThesis(BaseModel):
    """The plan's central communication proposition — ADOS-M3.3 §8.
    Grounded in real content: ``supporting_refs`` must be non-empty
    (enforced by ``brand.llm.narrative.validation``, not here, for the
    same reason ``ContentReferenceSet`` resolution isn't checked here —
    it needs a ContentIntelligenceModel in hand). When the available
    content cannot support a meaningful thesis, ``NarrativePlan.thesis``
    is ``None`` rather than a hedged, unsupported sentence — representing
    the limitation directly instead of writing around it."""

    model_config = _Frozen

    statement: str = Field(min_length=1, max_length=500)
    supporting_refs: ContentReferenceSet = Field(default_factory=ContentReferenceSet)


class GeneratedClaim(BaseModel):
    """A new interpretive claim the narrative planner proposes —
    ADOS-M3.3 §15. Never a substitute for a M3.2 ``Claim``; this exists
    for narrative-specific interpretation MAY be introduced but must
    stay explicitly marked as generated. If it cannot be supported at
    all, the correct move is to omit it, not construct one with no
    refs — enforced below."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    text: str = Field(min_length=1, max_length=1000)
    status: FactStatus = FactStatus.INFERRED
    supporting_refs: ContentReferenceSet = Field(default_factory=ContentReferenceSet)
    related_section_id: Optional[str] = None

    @model_validator(mode="after")
    def _generated_claims_are_never_verified_and_never_unsupported(self) -> "GeneratedClaim":
        if self.status not in _GENERATED_CLAIM_STATUSES:
            raise ValueError(
                f"a generated claim's status must be one of "
                f"{sorted(s.value for s in _GENERATED_CLAIM_STATUSES)}, got "
                f"{self.status.value!r} — a generated claim is interpretive by "
                f"construction and can never be VERIFIED, and CONFLICTING/"
                f"MISSING describe M3.2 facts, not something newly written here"
            )
        if self.supporting_refs.is_empty:
            raise ValueError(
                f"generated claim {self.text[:60]!r} has no supporting_refs — "
                f"ADOS-M3.3 §15: a claim that cannot be traced to any real "
                f"content must be omitted, not constructed unsupported"
            )
        return self


class NarrativeSection(BaseModel):
    """One unit of the narrative — ADOS-M3.3 §10. ``purpose`` is more
    important than ``title``: it is the answer to "why does this section
    exist", which is the question the master prompt says matters more
    than the section's name."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    role: SectionRole
    purpose: str = Field(min_length=1, max_length=400)
    title: str = Field(default="", max_length=160)
    summary: str = Field(default="", max_length=800)
    sequence: int = Field(ge=0)
    priority: SectionPriority = SectionPriority.SECONDARY
    requirement: Requirement = Requirement.RECOMMENDED
    audience_relevance: Relevance = Relevance.MEDIUM
    content_refs: ContentReferenceSet = Field(default_factory=ContentReferenceSet)
    emphasis: tuple[str, ...] = Field(default=(), max_length=12)
    #: Nested sections — ADOS-M3.3 §23's hierarchical expansion (e.g.
    #: "Concept" expanding into site/massing/landscape/spatial-experience
    #: sub-sections). Each child is a full NarrativeSection with its own
    #: sequence, scoped within its parent rather than the plan's flat list.
    subsections: tuple["NarrativeSection", ...] = ()
    #: Optional, subordinate limited draft text (ADOS-M3.3 §5/§37) — the
    #: plan must remain fully meaningful with this field deleted.
    draft: Optional[str] = Field(default=None, max_length=2000)


NarrativeSection.model_rebuild()


class NarrativeMissingInformationImpact(BaseModel):
    """One M3.2 ``MissingInformation`` gap, read for what it costs *this*
    narrative — ADOS-M3.3 §18. ``key``/``required_for``/``reason`` mirror
    the M3.2 item by value (not a live reference) since a narrative plan
    must stay self-describing when read back out of a trace."""

    model_config = _Frozen

    key: str = Field(min_length=1, max_length=120)
    required_for: str = Field(default="", max_length=120)
    impact: MissingImpact
    affected_section_id: Optional[str] = None


class NarrativeIssue(BaseModel):
    """Something the narrative planner flagged rather than silently
    absorbed — ADOS-M3.3 §20's own worked example."""

    model_config = _Frozen

    type: NarrativeIssueType
    description: str = Field(min_length=1, max_length=400)
    content_refs: ContentReferenceSet = Field(default_factory=ContentReferenceSet)
    impact: Relevance = Relevance.MEDIUM


class NarrativeExclusion(BaseModel):
    """Content the plan deliberately does not use — ADOS-M3.3 §19. This
    prevents M3.4 (or a later regeneration) from treating an omission as
    an oversight and quietly pulling the excluded item back in."""

    model_config = _Frozen

    reason: ExclusionReason
    description: str = Field(min_length=1, max_length=400)
    excluded_refs: ContentReferenceSet = Field(default_factory=ContentReferenceSet)


class NarrativePlan(BaseModel):
    """The root object ADOS-M3.3 exists to produce. Independent of
    layout (ADOS-M3.3 §36): every field here answers "what should we
    say, in what order, with what emphasis, from which real content" —
    never "where on the page"."""

    model_config = _Frozen

    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=_short_id)
    project_id: str
    #: The ContentIntelligenceModel this plan was resolved against —
    #: ADOS-M3.3 §46. ``None`` when resolved against the project's live,
    #: uncommitted content (the same convention
    #: ``ContentIntelligenceModel.version_number`` itself uses).
    content_model_version: Optional[int] = None
    #: The exact moment the content model this plan reasoned over was
    #: resolved — so a later regeneration against drifted content is
    #: never mistaken for "the same" content, even when both happen to
    #: carry ``content_model_version=None``.
    content_resolved_at: Optional[datetime] = None

    objective: NarrativeObjective
    audience: Audience
    #: The specific audience label the request actually used (e.g.
    #: "prospective_client", "competition_jury") — ADOS-M3.3 §7 lists a
    #: richer set of possible audiences than the closed ``Audience``
    #: enum (ADOS-M2.5/M1's own canonical vocabulary, reused per §7's
    #: instruction) can distinguish on its own. ``audience`` stays the
    #: closed, M3.4-compatible signal; this preserves the nuance.
    audience_label: str = Field(default="", max_length=80)
    tone: Optional[Tone] = None
    voice: NarrativeVoice = NarrativeVoice.NEUTRAL
    thesis: Optional[NarrativeThesis] = None
    #: The rhetorical strategy as an ordered sequence of section roles —
    #: ADOS-M3.3 §9, represented the same way
    #: ``CreativeDirection.narrative_order`` already orders
    #: ``BlockRole`` values: an ordered tuple of a role enum, not a named
    #: template. A concrete ``sections`` list may realise more sections
    #: than roles named here (ADOS-M3.3 §23's expansion) or fewer
    #: (§22's compression) — this field names the shape, not a fixed
    #: page-by-page script.
    narrative_strategy: tuple[SectionRole, ...] = Field(default=(), min_length=0)
    compression: NarrativeCompression = NarrativeCompression.MEDIUM

    sections: tuple[NarrativeSection, ...] = ()
    generated_claims: tuple[GeneratedClaim, ...] = ()
    missing_information: tuple[NarrativeMissingInformationImpact, ...] = ()
    narrative_issues: tuple[NarrativeIssue, ...] = ()
    exclusions: tuple[NarrativeExclusion, ...] = ()

    #: Small, free-form bag for things that do not need their own typed
    #: field — document_type_id, requested compression rationale, the
    #: generator that produced this plan. Never read by anything this
    #: package validates against; purely descriptive, like
    #: ``brand.project.model.Document.metadata``.
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)

    def section(self, section_id: str) -> Optional[NarrativeSection]:
        for s in self.sections:
            if s.id == section_id:
                return s
            for sub in s.subsections:
                if sub.id == section_id:
                    return sub
        return None

    def all_sections(self) -> tuple[NarrativeSection, ...]:
        """Flattened, including subsections — the shape most validation
        and evaluation code actually wants to walk."""
        out: list[NarrativeSection] = []
        for s in self.sections:
            out.append(s)
            out.extend(s.subsections)
        return tuple(out)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

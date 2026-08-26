"""
brand/llm/content/model.py

ADOS-M3.2's domain model. See ``brand/llm/content/__init__.py`` for why
the root object is named :class:`ContentIntelligenceModel`, not
``ContentModel``.

Every truth-bearing item (a :class:`Fact` or :class:`Claim` whose
status is not itself the record of an absence) carries at least one
:class:`SourceReference` — enforced twice, once structurally here
(``model_validator``) and once again, independently, in
``brand.llm.content.validation`` (ADOS-M3.2 §8/§28: an unsupported
project fact is a serious failure, not a style nit, so it is caught by
two layers that do not share code).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brand.llm.content.vocabulary import TRUTH_BEARING_STATUSES, EntityType, FactStatus, SourceType

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Bumped when the shape changes in a way a stored ContentIntelligenceModel
#: or trace would notice — brand/llm/semantic_intent.py's own convention.
SCHEMA_VERSION = "3.2"


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SourceReference(BaseModel):
    """Where one piece of content came from — ADOS-M3.2 §6, verbatim
    field list. Every field but ``source_id`` and ``source_type`` is
    optional because most sources cannot support all of them (a
    project-metadata fact has no page number; an uploaded PDF might)."""

    model_config = _Frozen

    source_id: str
    source_type: SourceType
    document_id: Optional[str] = None
    file_id: Optional[str] = None
    page: Optional[int] = Field(default=None, ge=1)
    section: str = ""
    location: str = ""
    version: Optional[int] = None
    #: e.g. "structured_data", "llm_extraction:claude-opus-5:content-v3.2.0",
    #: "image_metadata" — what actually produced this reference, for the
    #: observability trail ADOS-M3.2 §33 asks for.
    extraction_method: str = ""

    @property
    def dedup_key(self) -> tuple[str, SourceType]:
        """Two references to the *same source artifact* dedupe even when
        their page/section differ — ADOS-M3.2 §15 dedupes information,
        not locations within a source."""
        return (self.source_id, self.source_type)


class Entity(BaseModel):
    """A named thing the project is about (ADOS-M3.2 §5). ``aliases``
    is how entity resolution (§16) is represented once accepted — never
    a silent rename, always an additive list the original name stays
    inside."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    type: EntityType
    name: str = Field(min_length=1, max_length=200)
    aliases: tuple[str, ...] = ()
    status: FactStatus = FactStatus.VERIFIED
    source_refs: tuple[SourceReference, ...] = ()

    @model_validator(mode="after")
    def _truth_bearing_entities_need_a_source(self) -> "Entity":
        if self.status in TRUTH_BEARING_STATUSES and not self.source_refs:
            raise ValueError(
                f"entity {self.name!r} has status {self.status.value!r} but no "
                f"source_refs — an entity ADOS believes exists must say where "
                f"that belief comes from"
            )
        return self


class Fact(BaseModel):
    """One piece of objective, sourced information (ADOS-M3.2 §5). Also
    how this package represents a "metric" (ADOS-M3.2 §5's separate
    category) — a metric is simply a Fact whose value is numeric; see
    :meth:`ContentIntelligenceModel.metrics`. Keeping one type avoids a
    second, near-identical model and the metric/fact boundary
    duplicated-validation-rules that would come with it.

    ``status=CONFLICTING`` facts carry every distinct value sources
    disagreed on in ``conflicting_values`` and leave ``value`` unset —
    ADOS-M3.2 §14's "must not choose one silently", enforced structurally:
    there is no field a caller could read to get "the" value of a fact
    this package itself says it does not have one for.
    """

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    key: str = Field(min_length=1, max_length=120)
    value: Optional[float | str | bool] = None
    unit: str = Field(default="", max_length=24)
    status: FactStatus
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_refs: tuple[SourceReference, ...] = ()
    #: Populated only when status is CONFLICTING — the distinct
    #: (value, unit, source_refs) triples sources actually stated,
    #: never merged into one.
    conflicting_values: tuple["ConflictingValue", ...] = ()
    #: Set when a later, user-confirmed fact supersedes this one
    #: (ADOS-M3.2 §24) — the id of the fact that replaced it. A
    #: superseded fact is never deleted; see brand/llm/content/resolution.py.
    superseded_by: Optional[str] = None

    @model_validator(mode="after")
    def _truth_bearing_facts_need_a_source(self) -> "Fact":
        if self.status in TRUTH_BEARING_STATUSES and not self.source_refs:
            raise ValueError(
                f"fact {self.key!r} has status {self.status.value!r} but no "
                f"source_refs — ADOS-M3.2 §8: a fact must never be "
                f"indistinguishable from an invented one"
            )
        if self.status is FactStatus.CONFLICTING:
            if self.value is not None:
                raise ValueError(
                    f"fact {self.key!r} is conflicting but still carries a "
                    f"single value — a conflicting fact has no single value "
                    f"by definition (ADOS-M3.2 §14)"
                )
            if len(self.conflicting_values) < 2:
                raise ValueError(
                    f"fact {self.key!r} is marked conflicting but names fewer "
                    f"than two distinct values"
                )
        elif self.conflicting_values:
            raise ValueError(
                f"fact {self.key!r} carries conflicting_values but its status "
                f"is {self.status.value!r}, not conflicting"
            )
        return self

    @property
    def is_metric(self) -> bool:
        return isinstance(self.value, (int, float)) and not isinstance(self.value, bool)


class ConflictingValue(BaseModel):
    """One of the distinct answers sources gave for the same fact key."""

    model_config = _Frozen

    value: float | str | bool
    unit: str = Field(default="", max_length=24)
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)


Fact.model_rebuild()


class Claim(BaseModel):
    """An interpretive statement a source supports but that requires
    judgement to state as fact (ADOS-M3.2 §5/§17) — "the project creates
    a strong relationship with the public realm" as against "site area
    is 4,200 m²". Always carries provenance for the same reason a Fact
    does; it is the *interpretive* nature of a claim that is preserved
    here, not an exemption from sourcing."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    text: str = Field(min_length=1, max_length=2000)
    status: FactStatus = FactStatus.INFERRED
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_refs: tuple[SourceReference, ...] = ()
    related_entity_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _truth_bearing_claims_need_a_source(self) -> "Claim":
        if self.status in TRUTH_BEARING_STATUSES and not self.source_refs:
            raise ValueError(
                f"claim {self.text[:60]!r}... has status {self.status.value!r} "
                f"but no source_refs"
            )
        return self


class Relationship(BaseModel):
    """A stated connection between two entities (ADOS-M3.2 §3).
    ``predicate`` is free text (e.g. "located_in", "designed_by",
    "part_of") rather than a closed vocabulary — ADOS-M3.2 does not ask
    for a relationship ontology, only that relationships be
    representable and sourced like everything else here."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    subject_entity_id: str
    predicate: str = Field(min_length=1, max_length=80)
    object_entity_id: str
    status: FactStatus = FactStatus.VERIFIED
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_refs: tuple[SourceReference, ...] = ()

    @model_validator(mode="after")
    def _truth_bearing_relationships_need_a_source(self) -> "Relationship":
        if self.status in TRUTH_BEARING_STATUSES and not self.source_refs:
            raise ValueError(
                f"relationship {self.subject_entity_id}--{self.predicate}--> "
                f"{self.object_entity_id} has status {self.status.value!r} but "
                f"no source_refs"
            )
        return self


class AssetContent(BaseModel):
    """The semantic layer over one real, already-uploaded
    ``brand.project.model.Asset`` (ADOS-M3.2 §18) — never a copy of that
    asset's own file metadata (filename, content-type, pixel dimensions
    already live there; see that model's own docstring). This model
    only adds what is *not* already on the file record: what the image
    is understood to be about, and how that understanding was reached.
    ``description``/``subject`` are populated only from real, already-
    available information (a caption a user typed, a filename, an
    associated document's own text) — never fabricated from visual
    appearance alone (ADOS-M3.2 §18: "do not overbuild image
    understanding")."""

    model_config = _Frozen

    asset_id: str
    #: "image" | "drawing" | "diagram" | "document" | "pdf" — free text,
    #: not a closed enum: the real Asset's content_type already carries
    #: the authoritative technical answer; this is the semantic reading.
    type: str = "image"
    caption: str = Field(default="", max_length=400)
    description: str = Field(default="", max_length=2000)
    subject: str = Field(default="", max_length=200)
    project_phase: str = Field(default="", max_length=80)
    orientation: str = Field(default="", max_length=20)
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    source_refs: tuple[SourceReference, ...] = ()


class MissingInformation(BaseModel):
    """A gap ADOS knows it has (ADOS-M3.2 §23) — deliberately not a Fact
    with ``status=MISSING``: a Fact object implies a value exists to
    reason about (even a conflicting one); a gap has none, and giving it
    the same shape as a real fact is exactly the kind of ambiguity that
    invites a downstream layer to treat "missing" as just another kind
    of value."""

    model_config = _Frozen

    key: str = Field(min_length=1, max_length=120)
    required_for: str = Field(default="", max_length=120)
    reason: str = Field(default="", max_length=400)


class ContentIntelligenceModel(BaseModel):
    """ADOS-M3.2's canonical semantic content layer — see this package's
    own docstring for the name and the boundary it sits behind. A pure
    read model, exactly like ``brand.design_state.model.DesignState``:
    built fresh from real sources on every resolution, never a second
    store a caller writes to directly."""

    model_config = _Frozen

    schema_version: str = SCHEMA_VERSION
    project_id: str
    #: The ProjectVersion this reflects, when resolved against a saved
    #: one — ADOS-M3.2 §34. ``None`` for a resolution against the
    #: project's live, uncommitted state.
    version_number: Optional[int] = None
    entities: tuple[Entity, ...] = ()
    facts: tuple[Fact, ...] = ()
    claims: tuple[Claim, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    assets: tuple[AssetContent, ...] = ()
    missing_information: tuple[MissingInformation, ...] = ()
    #: The distinct sources (by source_id) that contributed anything to
    #: this model — ADOS-M3.2 §3's own top-level "sources" member. A
    #: catalogue, not a duplicate of every inline source_refs entry.
    sources: tuple[SourceReference, ...] = ()
    resolved_at: datetime = Field(default_factory=_now)

    @property
    def metrics(self) -> tuple[Fact, ...]:
        """Facts whose value is numeric — ADOS-M3.2 §5's "Metrics" view,
        computed rather than duplicated (see :class:`Fact`'s docstring)."""
        return tuple(f for f in self.facts if f.is_metric)

    def entity(self, entity_id: str) -> Entity:
        for e in self.entities:
            if e.id == entity_id:
                return e
        raise KeyError(f"no entity {entity_id!r}")

    def fact(self, key: str) -> Optional[Fact]:
        for f in self.facts:
            if f.key == key and f.superseded_by is None:
                return f
        return None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

"""
brand/llm/content/extraction.py

ADOS-M3.2 §9/§10/§11 — the deterministic pipeline around the LLM.

    Source -> source normalization -> content extraction ->
    semantic extraction -> schema validation -> provenance assignment
    -> ContentIntelligenceModel

Every ``ContentExtractor`` implementation here does exactly one thing:
turn one :class:`ContentSource` into an :class:`ExtractionResult` whose
items already carry the correct :class:`~brand.llm.content.model.SourceReference`
— attached mechanically by this module's own code, never by the LLM.
This is the single design decision that makes source attribution
accuracy structural rather than aspirational: an ``LLMContentExtractor``
is never asked to say *which* source it read (it only ever sees one),
so it cannot mis-attribute a fact to the wrong one.

Four extractors, matching ADOS-M3.2 §10's own suggested shape:

* :class:`StructuredDataExtractor` — project metadata and structured
  ``ContentItem`` (kind fact/metric) records. Deterministic, no LLM.
* :class:`ImageMetadataExtractor` — real, already-known asset metadata.
  Deterministic, no LLM, no vision API (ADOS-M3.2 §18: "do not overbuild
  image understanding").
* :class:`RuleBasedContentExtractor` — a conservative, keyword/regex
  extractor over free text, used whenever no LLM is configured
  (ADOS-M3.2 §29's CI determinism requirement — every automated test in
  this repository runs through this path).
* :class:`LLMContentExtractor` — the real, structured-output extractor
  over free text, built on the exact same Anthropic client
  ``brand.llm.providers.claude_provider`` already constructs (ADOS-M3.2
  §11: "do not create a second Claude client").
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

from brand.llm.content.model import (
    AssetContent,
    Claim,
    Entity,
    Fact,
    Relationship,
    SourceReference,
)
from brand.llm.content.vocabulary import EntityType, FactStatus, SourceType
from brand.llm.provider import ProviderError, ProviderMetadata

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Descriptive only (ADOS-M3.2 §4: "these sources do NOT have equal
#: authority") — never used to silently pick a winner in a conflict
#: (§14 forbids that outright). Lower is more authoritative.
_DEFAULT_TRUST_LEVEL: dict[SourceType, int] = {
    SourceType.USER_STATEMENT: 0,
    SourceType.PROJECT_METADATA: 1,
    SourceType.STRUCTURED_PROJECT_DATA: 1,
    SourceType.PROJECT_STATE: 1,
    SourceType.UPLOADED_DOCUMENT: 2,
    SourceType.UPLOADED_IMAGE: 2,
    SourceType.DESIGN_STATE: 2,
    SourceType.BRAND_CONTEXT: 3,
    SourceType.ADOS_DOCUMENT: 4,  # ADOS-M3.2 §19: generated document != primary source
    SourceType.LLM_INFERENCE: 5,
}


def default_trust_level(source_type: SourceType) -> int:
    return _DEFAULT_TRUST_LEVEL.get(source_type, 3)


class ContentSource(BaseModel):
    """One raw thing to extract from — ADOS-M3.2 §4's source hierarchy,
    as data. Exactly one of ``text``/``structured_payload``/``asset_id``
    is populated, matching whichever extractor actually handles this
    source_type; a source carries no more than it needs to."""

    model_config = _Frozen

    source_id: str
    source_type: SourceType
    label: str = ""
    document_id: Optional[str] = None
    file_id: Optional[str] = None
    version: Optional[int] = None
    text: str = ""
    structured_payload: Optional[dict[str, Any]] = None
    asset_id: Optional[str] = None
    #: ``None`` means "use the default for source_type" (see
    #: :func:`default_trust_level`) — a real override is an explicit int.
    explicit_trust_level: Optional[int] = None

    @property
    def trust_level(self) -> int:
        return (
            self.explicit_trust_level if self.explicit_trust_level is not None
            else default_trust_level(self.source_type)
        )

    def reference(self, *, extraction_method: str, page: Optional[int] = None, section: str = "") -> SourceReference:
        """The SourceReference every item this source produces should
        carry — built once per extractor call, not re-derived per item."""
        return SourceReference(
            source_id=self.source_id, source_type=self.source_type,
            document_id=self.document_id, file_id=self.file_id, version=self.version,
            page=page, section=section, extraction_method=extraction_method,
        )


class ContentExtractionContext(BaseModel):
    """What an extractor is told beyond the source itself — ADOS-M3.2
    §11: "should NOT receive unrelated project data simply because it
    is available". Scoped on purpose: just enough to avoid inventing a
    duplicate entity for something already known."""

    model_config = _Frozen

    project_name: str = ""
    known_entity_names: tuple[str, ...] = ()


class ExtractionResult(BaseModel):
    """One extractor call's output — already provenance-tagged, not yet
    merged against any other source's output (that is
    ``brand.llm.content.resolution``'s job)."""

    model_config = _Frozen

    entities: tuple[Entity, ...] = ()
    facts: tuple[Fact, ...] = ()
    claims: tuple[Claim, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    assets: tuple[AssetContent, ...] = ()


class ContentExtractor(ABC):
    @abstractmethod
    def extract(
        self, source: ContentSource, context: ContentExtractionContext,
    ) -> tuple[ExtractionResult, Optional[ProviderMetadata]]:
        """Raise :class:`~brand.llm.provider.ProviderError` for any
        provider-backed failure (network, schema, refusal) — deterministic
        extractors never raise it, since they have nothing to fail over
        to."""


# ---------------------------------------------------------------------------
# StructuredDataExtractor — project metadata + structured ContentItems
# ---------------------------------------------------------------------------


class StructuredDataExtractor(ContentExtractor):
    """Deterministic. A ``project_data`` dict entry, or a fact/metric
    ``ContentItem``, was typed in directly — that is as close to
    ``VERIFIED`` as this pipeline's source hierarchy gets (ADOS-M3.2 §4),
    and needs no LLM to read."""

    def extract(
        self, source: ContentSource, context: ContentExtractionContext,
    ) -> tuple[ExtractionResult, Optional[ProviderMetadata]]:
        if source.source_type not in (SourceType.PROJECT_METADATA, SourceType.STRUCTURED_PROJECT_DATA):
            raise ValueError(f"StructuredDataExtractor cannot handle {source.source_type.value!r}")
        payload = source.structured_payload or {}
        ref = source.reference(extraction_method="structured_data")

        facts: list[Fact] = []
        if source.source_type is SourceType.PROJECT_METADATA:
            for key, value in payload.items():
                if value in (None, "", [], {}):
                    continue
                if isinstance(value, (str, int, float, bool)):
                    facts.append(Fact(
                        key=str(key), value=value, status=FactStatus.VERIFIED,
                        confidence=1.0, source_refs=(ref,),
                    ))
        else:  # STRUCTURED_PROJECT_DATA -- content_items of kind fact/metric
            for item in payload.get("content_items", []):
                kind = item.get("kind")
                if kind not in ("fact", "metric") or item.get("value") is None:
                    continue
                key = _slugify(item.get("label") or item.get("id") or "fact")
                facts.append(Fact(
                    key=key, value=item["value"], unit=item.get("unit", ""),
                    status=FactStatus.VERIFIED, confidence=1.0, source_refs=(ref,),
                ))

        return ExtractionResult(facts=tuple(facts)), None


def _slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_") or "fact"


# ---------------------------------------------------------------------------
# ImageMetadataExtractor -- real asset metadata, no vision call
# ---------------------------------------------------------------------------


class ImageMetadataExtractor(ContentExtractor):
    """Deterministic. Makes an already-uploaded asset discoverable and
    referenceable (ADOS-M3.2 §18) from information that already exists
    — a caption a user typed, a filename — never from inferred visual
    content."""

    def extract(
        self, source: ContentSource, context: ContentExtractionContext,
    ) -> tuple[ExtractionResult, Optional[ProviderMetadata]]:
        if source.source_type is not SourceType.UPLOADED_IMAGE:
            raise ValueError(f"ImageMetadataExtractor cannot handle {source.source_type.value!r}")
        payload = source.structured_payload or {}
        ref = source.reference(extraction_method="image_metadata")

        asset = AssetContent(
            asset_id=source.asset_id or source.source_id,
            type=payload.get("type", "image"),
            caption=payload.get("caption", ""),
            description=payload.get("description", ""),
            source_refs=(ref,),
        )
        return ExtractionResult(assets=(asset,)), None


# ---------------------------------------------------------------------------
# RuleBasedContentExtractor -- deterministic fallback over free text
# ---------------------------------------------------------------------------


#: (key, unit, regex) -- regex must capture the numeric value in group 1.
#: Conservative on purpose: a pattern that doesn't match produces nothing,
#: never a guess (ADOS-M3.2 §6/§8).
_NUMERIC_PATTERNS: tuple[tuple[str, str, re.Pattern], ...] = (
    ("apartments", "", re.compile(r"\b([\d,]+)\s+apartments?\b", re.I)),
    ("units", "", re.compile(r"\b([\d,]+)\s+(?:residential\s+)?units\b", re.I)),
    ("gross_floor_area", "m2", re.compile(r"\b([\d,]+(?:\.\d+)?)\s*m²\s*(?:GFA|gross floor area)?\b", re.I)),
    ("gross_floor_area", "m2", re.compile(r"\bGFA\s*(?:of|=|:)?\s*([\d,]+(?:\.\d+)?)\s*m²\b", re.I)),
    ("site_area", "m2", re.compile(r"\bsite area\s*(?:of|=|:)?\s*([\d,]+(?:\.\d+)?)\s*m²\b", re.I)),
    ("height", "m", re.compile(r"\bheight\s*(?:of|=|:)?\s*([\d,]+(?:\.\d+)?)\s*m\b", re.I)),
    ("completion_year", "", re.compile(r"\bcompletion\s+(?:year\s+)?(?:of|=|:)?\s*(\d{4})\b", re.I)),
)

_LOCATION_PATTERN = re.compile(
    r"\bin\s+([A-Z][a-zA-Zá-őÁ-Ő]+(?:\s[A-Z][a-zA-Zá-őÁ-Ő]+)?)\b"
)
_PROGRAM_CUES: tuple[str, ...] = ("residential", "office", "mixed-use", "retail", "hospitality", "cultural", "educational")

#: A sentence "reads as a claim" when it uses evaluative/interpretive
#: language rather than stating a checkable quantity — conservative:
#: anything not matched is simply not extracted as a claim, never forced.
_CLAIM_CUES: tuple[str, ...] = (
    "creates", "strengthens", "establishes", "connection", "relationship",
    "responds to", "celebrates", "reinforces", "sense of", "quality of",
)


class RuleBasedContentExtractor(ContentExtractor):
    """No network call, ever. Deliberately narrow — a small, well-defined
    set of patterns rather than a general-purpose parser, so every match
    it produces is one a reviewer can trace back to an exact regex, and
    everything it does not recognise is honestly absent rather than
    guessed at."""

    def extract(
        self, source: ContentSource, context: ContentExtractionContext,
    ) -> tuple[ExtractionResult, Optional[ProviderMetadata]]:
        text = source.text
        ref = source.reference(extraction_method="rule_based:pattern-v1")

        facts: list[Fact] = []
        matched_keys: set[str] = set()
        for key, unit, pattern in _NUMERIC_PATTERNS:
            if key in matched_keys:
                continue  # a later, more specific pattern for the same key already matched
            match = pattern.search(text)
            if not match:
                continue
            matched_keys.add(key)
            raw = match.group(1).replace(",", "")
            value: float | int = float(raw) if "." in raw else int(raw)
            facts.append(Fact(
                key=key, value=value, unit=unit, status=FactStatus.VERIFIED,
                confidence=0.7, source_refs=(ref,),
            ))

        entities: list[Entity] = []
        loc_match = _LOCATION_PATTERN.search(text)
        if loc_match:
            location_name = loc_match.group(1)
            facts.append(Fact(
                key="location", value=location_name, status=FactStatus.VERIFIED,
                confidence=0.6, source_refs=(ref,),
            ))
            entities.append(Entity(
                type=EntityType.LOCATION, name=location_name, source_refs=(ref,),
            ))

        lowered = text.lower()
        for cue in _PROGRAM_CUES:
            if cue in lowered:
                facts.append(Fact(
                    key="program", value=cue, status=FactStatus.VERIFIED,
                    confidence=0.6, source_refs=(ref,),
                ))
                break

        claims: list[Claim] = []
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            sentence = sentence.strip()
            if not sentence:
                continue
            if any(cue in sentence.lower() for cue in _CLAIM_CUES):
                claims.append(Claim(
                    text=sentence, status=FactStatus.INFERRED, confidence=0.55,
                    source_refs=(ref,),
                ))

        return ExtractionResult(facts=tuple(facts), entities=tuple(entities), claims=tuple(claims)), None


# ---------------------------------------------------------------------------
# LLMContentExtractor -- structured extraction over free text
# ---------------------------------------------------------------------------


class RawEntity(BaseModel):
    """The LLM's structured-output schema for one entity. No status, no
    confidence, no source_refs — those are assigned by
    :func:`_materialize`, deterministically, from the one
    :class:`ContentSource` this extraction call was scoped to (ADOS-M3.2
    §11's "keep context scoped", applied to output as well as input)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    #: A value from brand.llm.content.vocabulary.EntityType — kept as a
    #: plain string at the schema level (not a strict Enum) so an
    #: unrecognised value is a domain-validation finding, not a rejected
    #: API call — the same reasoning ADOS-M3.1's SemanticFieldValues
    #: applies to action/target.
    type: str
    aliases: tuple[str, ...] = ()


class RawFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=120)
    value: float | str | bool
    unit: str = ""
    #: True: the source states this value in essentially these words —
    #: becomes status=VERIFIED. False: reaching this value required
    #: interpretation — becomes status=INFERRED. The LLM decides this
    #: per-fact because only it read the source text; the status *label*
    #: itself is still assigned by code, never by the model directly.
    directly_stated: bool = True
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class RawClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)
    related_entity_names: tuple[str, ...] = ()
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class RawRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=200)
    predicate: str = Field(min_length=1, max_length=80)
    object: str = Field(min_length=1, max_length=200)
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class RawExtraction(BaseModel):
    """The complete LLM structured-output contract for one source. Never
    returned to a caller of :class:`LLMContentExtractor` directly — only
    :func:`_materialize`'s fully-sourced, fully-typed
    :class:`ExtractionResult` is."""

    model_config = ConfigDict(extra="forbid")

    entities: tuple[RawEntity, ...] = ()
    facts: tuple[RawFact, ...] = ()
    claims: tuple[RawClaim, ...] = ()
    relationships: tuple[RawRelationship, ...] = ()


def _materialize(raw: RawExtraction, source: ContentSource) -> ExtractionResult:
    """Attach real provenance to everything the LLM returned, and assign
    the status label the LLM itself never sets directly."""
    from brand.llm.content.prompt import PROMPT_VERSION

    ref = source.reference(extraction_method=f"llm_extraction:content-{PROMPT_VERSION}")

    entities: list[Entity] = []
    name_to_id: dict[str, str] = {}
    for raw_entity in raw.entities:
        try:
            entity_type = EntityType(raw_entity.type.strip().lower())
        except ValueError:
            logger.warning(
                "LLMContentExtractor: dropping entity %r with unrecognised type %r",
                raw_entity.name, raw_entity.type,
            )
            continue
        entity = Entity(
            type=entity_type, name=raw_entity.name, aliases=raw_entity.aliases,
            status=FactStatus.INFERRED, source_refs=(ref,),
        )
        entities.append(entity)
        name_to_id[raw_entity.name.strip().lower()] = entity.id

    facts = tuple(
        Fact(
            key=rf.key, value=rf.value, unit=rf.unit,
            status=FactStatus.VERIFIED if rf.directly_stated else FactStatus.INFERRED,
            confidence=rf.confidence, source_refs=(ref,),
        )
        for rf in raw.facts
    )

    claims = tuple(
        Claim(
            text=rc.text, status=FactStatus.INFERRED, confidence=rc.confidence,
            source_refs=(ref,),
            related_entity_ids=tuple(
                name_to_id[n.strip().lower()] for n in rc.related_entity_names
                if n.strip().lower() in name_to_id
            ),
        )
        for rc in raw.claims
    )

    relationships: list[Relationship] = []
    for rr in raw.relationships:
        subject_id = name_to_id.get(rr.subject.strip().lower())
        object_id = name_to_id.get(rr.object.strip().lower())
        if subject_id is None or object_id is None:
            logger.warning(
                "LLMContentExtractor: dropping relationship %r--%s-->%r "
                "(entity not among this call's own extracted entities)",
                rr.subject, rr.predicate, rr.object,
            )
            continue
        relationships.append(Relationship(
            subject_entity_id=subject_id, predicate=rr.predicate, object_entity_id=object_id,
            status=FactStatus.INFERRED, confidence=rr.confidence, source_refs=(ref,),
        ))

    return ExtractionResult(
        entities=tuple(entities), facts=facts, claims=claims, relationships=tuple(relationships),
    )


class LLMContentExtractor(ContentExtractor):
    """The real, structured-output content extractor. Reuses
    ``brand.llm.providers.claude_provider``'s shared client/call helper
    — see this module's own docstring for why that matters."""

    _DEFAULT_MODEL = "claude-opus-5"
    _DEFAULT_MAX_TOKENS = 4096

    def __init__(self, model: Optional[str] = None, max_tokens: Optional[int] = None) -> None:
        self._model = model or os.environ.get("CONTENT_INTELLIGENCE_MODEL", self._DEFAULT_MODEL)
        self._max_tokens = max_tokens or int(
            os.environ.get("CONTENT_INTELLIGENCE_MAX_TOKENS", self._DEFAULT_MAX_TOKENS)
        )
        self._client: Any = None

    def extract(
        self, source: ContentSource, context: ContentExtractionContext,
    ) -> tuple[ExtractionResult, ProviderMetadata]:
        from brand.llm.content.prompt import build_content_system_prompt, build_content_user_message
        from brand.llm.providers.claude_provider import call_structured, get_client

        if self._client is None:
            self._client = get_client()

        system_prompt = build_content_system_prompt()
        user_message = build_content_user_message(source, context)
        raw, metadata = call_structured(
            self._client, model=self._model, max_tokens=self._max_tokens,
            system_prompt=system_prompt, user_message=user_message,
            output_format=RawExtraction, provider_name="claude",
        )
        return _materialize(raw, source), metadata

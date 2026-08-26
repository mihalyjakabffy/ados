"""
brand/llm/content/resolution.py

ADOS-M3.2 §20 — orchestrates real extractors over a project's real
sources into one :class:`ContentIntelligenceModel`. This module does
not re-implement content retrieval: for a document's own composable
content it is a thin gatherer of the same
``Document.content_items``/``Project.content_items`` pool
``brand.project.content_resolution`` already resolves for the Composer
(ADOS-M2.5 §6) — it does not call that module directly (its output type
is the *other*, composer-facing ``ContentModel``), but it reads the
identical source fields, so a fact this pipeline extracts and a block
the Composer places both trace back to the one real ContentItem.

    real sources -> the right ContentExtractor for each
        -> raw, per-source ExtractionResult
        -> conflict detection + deduplication + conservative entity
           resolution + missing-information derivation
        -> ContentIntelligenceModel

Never a second retrieval system (ADOS-M3.2 §20's own instruction) —
this module's only new idea is turning what ``content_resolution``
already gathers into *semantic* content (facts, claims, entities)
instead of *composable* content (blocks).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Optional

from brand.llm.content.extraction import (
    ContentExtractionContext,
    ContentExtractor,
    ContentSource,
    ExtractionResult,
    ImageMetadataExtractor,
    RuleBasedContentExtractor,
    StructuredDataExtractor,
)
from brand.llm.content.model import (
    AssetContent,
    Claim,
    ConflictingValue,
    ContentIntelligenceModel,
    Entity,
    Fact,
    MissingInformation,
    Relationship,
    SourceReference,
)
from brand.llm.content.vocabulary import FactStatus, SourceType
from brand.llm.provider import ProviderError

if TYPE_CHECKING:
    from brand.project.model import Document, Project

_TEXT_LLM_ENABLED_ENV = "CONTENT_INTELLIGENCE_LLM_ENABLED"


def _default_text_extractor() -> ContentExtractor:
    """LLM when configured and enabled, the deterministic rule-based
    extractor otherwise — the identical gating
    ``brand.llm.extractor._resolve_default_provider`` already applies to
    ``SemanticIntentExtractor``, applied here to content extraction."""
    enabled = os.environ.get(_TEXT_LLM_ENABLED_ENV, "true").lower() != "false"
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not enabled or not api_key:
        return RuleBasedContentExtractor()
    from brand.llm.content.extraction import LLMContentExtractor

    return LLMContentExtractor()


# ---------------------------------------------------------------------------
# Gathering real sources
# ---------------------------------------------------------------------------


def _gather_sources(
    project: "Project", document: Optional["Document"], raw_documents: tuple[dict[str, Any], ...],
) -> list[ContentSource]:
    sources: list[ContentSource] = []

    if project.project_data:
        sources.append(ContentSource(
            source_id=f"project-metadata:{project.id}", source_type=SourceType.PROJECT_METADATA,
            label="Project metadata", structured_payload=dict(project.project_data),
        ))

    items = list(project.content_items)
    if document is not None:
        shared_by_id = {i.id: i for i in project.content_items}
        selected = [shared_by_id[i] for i in document.content_selection if i in shared_by_id]
        items = list(document.content_items) + selected

    fact_like = [i.model_dump(mode="json") for i in items if i.kind.value in ("fact", "metric")]
    if fact_like:
        sources.append(ContentSource(
            source_id=f"content-items:{document.id if document else project.id}",
            source_type=SourceType.STRUCTURED_PROJECT_DATA,
            label="Structured content items",
            document_id=document.id if document else None,
            structured_payload={"content_items": fact_like},
        ))

    for item in items:
        if item.kind.value == "text" and item.text.strip():
            sources.append(ContentSource(
                source_id=f"content-item:{item.id}", source_type=SourceType.UPLOADED_DOCUMENT,
                label=item.label or "Narrative content item",
                document_id=document.id if document else None,
                text=item.text,
            ))

    for asset in project.assets:
        caption = next(
            (i.caption for i in items if i.kind.value == "image" and i.asset_id == asset.id and i.caption), "",
        )
        sources.append(ContentSource(
            source_id=f"asset:{asset.id}", source_type=SourceType.UPLOADED_IMAGE,
            label=asset.filename, asset_id=asset.id,
            structured_payload={"caption": caption},
        ))

    for raw_doc in raw_documents:
        text = raw_doc.get("text", "")
        if not text.strip():
            continue
        sources.append(ContentSource(
            source_id=raw_doc.get("source_id") or f"raw-document:{len(sources)}",
            source_type=SourceType(raw_doc.get("source_type", SourceType.UPLOADED_DOCUMENT.value)),
            label=raw_doc.get("label", ""), text=text,
        ))

    return sources


def _run_extractors(
    sources: list[ContentSource], context: ContentExtractionContext, text_extractor: ContentExtractor,
) -> tuple[list[ExtractionResult], dict[str, str]]:
    results: list[ExtractionResult] = []
    source_extractors: dict[str, str] = {}
    for source in sources:
        if source.source_type in (SourceType.PROJECT_METADATA, SourceType.STRUCTURED_PROJECT_DATA):
            result, meta = StructuredDataExtractor().extract(source, context)
        elif source.source_type is SourceType.UPLOADED_IMAGE:
            result, meta = ImageMetadataExtractor().extract(source, context)
        else:
            try:
                result, meta = text_extractor.extract(source, context)
            except ProviderError:
                result, meta = RuleBasedContentExtractor().extract(source, context)
        results.append(result)
        source_extractors[source.source_id] = f"{meta.provider}:{meta.model}" if meta else "deterministic"
    return results, source_extractors


# ---------------------------------------------------------------------------
# Merging across sources: dedup, conflicts, conservative entity resolution
# ---------------------------------------------------------------------------


def _dedupe_refs(refs: tuple[SourceReference, ...]) -> tuple[SourceReference, ...]:
    seen: dict[tuple[str, SourceType], SourceReference] = {}
    for ref in refs:
        seen.setdefault(ref.dedup_key, ref)
    return tuple(seen.values())


_STATUS_RANK = {FactStatus.VERIFIED: 0, FactStatus.INFERRED: 1, FactStatus.AMBIGUOUS: 2, FactStatus.CONFLICTING: 3}


def _merge_facts(all_facts: list[Fact]) -> tuple[Fact, ...]:
    by_key: dict[str, list[Fact]] = {}
    for fact in all_facts:
        by_key.setdefault(fact.key, []).append(fact)

    merged: list[Fact] = []
    for key, group in by_key.items():
        distinct: dict[tuple[Any, str], list[Fact]] = {}
        for f in group:
            distinct.setdefault((f.value, f.unit), []).append(f)

        if len(distinct) == 1:
            (value, unit), members = next(iter(distinct.items()))
            best_status = min((m.status for m in members), key=lambda s: _STATUS_RANK[s])
            refs = _dedupe_refs(tuple(r for m in members for r in m.source_refs))
            merged.append(Fact(
                key=key, value=value, unit=unit, status=best_status,
                confidence=max(m.confidence for m in members), source_refs=refs,
            ))
        else:
            conflicting = tuple(
                ConflictingValue(value=value, unit=unit, source_refs=_dedupe_refs(tuple(
                    r for m in members for r in m.source_refs
                )))
                for (value, unit), members in distinct.items()
            )
            all_refs = _dedupe_refs(tuple(r for m in group for r in m.source_refs))
            merged.append(Fact(
                key=key, status=FactStatus.CONFLICTING, conflicting_values=conflicting,
                confidence=max(m.confidence for m in group), source_refs=all_refs,
            ))
    return tuple(merged)


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _merge_entities(all_entities: list[Entity]) -> tuple[tuple[Entity, ...], dict[str, str]]:
    """Conservative entity resolution (ADOS-M3.2 §16): merges only on an
    exact (normalized) name-or-alias match. Returns the merged entities
    plus a map from every original entity id to the id it now resolves
    to, so relationships extracted before merging can be remapped."""
    merged: list[Entity] = []
    id_map: dict[str, str] = {}
    #: normalized name/alias -> index into `merged`
    key_to_index: dict[str, int] = {}

    for entity in all_entities:
        names = {_normalize_name(entity.name), *(_normalize_name(a) for a in entity.aliases)}
        existing_index = next((key_to_index[n] for n in names if n in key_to_index), None)

        if existing_index is None:
            merged.append(entity)
            index = len(merged) - 1
            for n in names:
                key_to_index[n] = index
            id_map[entity.id] = entity.id
        else:
            base = merged[existing_index]
            new_aliases = tuple(
                a for a in (entity.name, *entity.aliases)
                if _normalize_name(a) != _normalize_name(base.name) and a not in base.aliases
            )
            merged[existing_index] = base.model_copy(update={
                "aliases": base.aliases + new_aliases,
                "source_refs": _dedupe_refs(base.source_refs + entity.source_refs),
            })
            for n in names:
                key_to_index[n] = existing_index
            id_map[entity.id] = base.id

    return tuple(merged), id_map


def _remap_and_dedupe_relationships(
    all_relationships: list[Relationship], id_map: dict[str, str],
) -> tuple[Relationship, ...]:
    remapped = [
        r.model_copy(update={
            "subject_entity_id": id_map.get(r.subject_entity_id, r.subject_entity_id),
            "object_entity_id": id_map.get(r.object_entity_id, r.object_entity_id),
        })
        for r in all_relationships
    ]
    by_triple: dict[tuple[str, str, str], list[Relationship]] = {}
    for r in remapped:
        by_triple.setdefault((r.subject_entity_id, r.predicate, r.object_entity_id), []).append(r)

    merged = []
    for (subj, pred, obj), members in by_triple.items():
        refs = _dedupe_refs(tuple(r for m in members for r in m.source_refs))
        merged.append(members[0].model_copy(update={
            "source_refs": refs, "confidence": max(m.confidence for m in members),
        }))
    return tuple(merged)


def _remap_claim_entities(claims: list[Claim], id_map: dict[str, str]) -> tuple[Claim, ...]:
    remapped = [
        c.model_copy(update={
            "related_entity_ids": tuple(id_map.get(e, e) for e in c.related_entity_ids),
        })
        for c in claims
    ]
    by_text: dict[str, list[Claim]] = {}
    for c in remapped:
        by_text.setdefault(c.text, []).append(c)
    return tuple(
        members[0].model_copy(update={
            "source_refs": _dedupe_refs(tuple(r for m in members for r in m.source_refs)),
            "confidence": max(m.confidence for m in members),
        })
        for members in by_text.values()
    )


def _derive_missing_information(
    facts: tuple[Fact, ...], document_type_id: str,
) -> tuple[MissingInformation, ...]:
    if not document_type_id:
        return ()
    from brand.project.document_types import UnknownDocumentTypeError, get_document_type

    try:
        document_type = get_document_type(document_type_id)
    except UnknownDocumentTypeError:
        return ()

    known_keys = {f.key for f in facts if f.superseded_by is None}
    return tuple(
        MissingInformation(key=req, required_for=document_type.id, reason="no authoritative source stated this")
        for req in document_type.metadata_requirements
        if req not in known_keys
    )


# ---------------------------------------------------------------------------
# User corrections (ADOS-M3.2 §24)
# ---------------------------------------------------------------------------


def _apply_user_corrections(
    facts: tuple[Fact, ...], corrections: tuple[dict[str, Any], ...], project_id: str,
) -> tuple[Fact, ...]:
    """A correction never overwrites — the prior fact is kept, tagged
    ``superseded_by``, and the new, user-confirmed fact is added
    alongside it (ADOS-M3.2 §24: "old fact -> superseded -> new
    user-confirmed fact")."""
    if not corrections:
        return facts

    out = list(facts)
    for correction in corrections:
        key = correction["key"]
        ref = SourceReference(
            source_id=f"user-correction:{project_id}:{key}", source_type=SourceType.USER_STATEMENT,
            extraction_method="user_correction",
        )
        new_fact = Fact(
            key=key, value=correction["value"], unit=correction.get("unit", ""),
            status=FactStatus.VERIFIED, confidence=1.0, source_refs=(ref,),
        )
        current_index = next(
            (i for i, f in enumerate(out) if f.key == key and f.superseded_by is None), None,
        )
        if current_index is not None:
            out[current_index] = out[current_index].model_copy(update={"superseded_by": new_fact.id})
        out.append(new_fact)
    return tuple(out)


def resolve_content(
    project: "Project",
    *,
    document: Optional["Document"] = None,
    document_type_id: str = "",
    version_number: Optional[int] = None,
    user_corrections: tuple[dict[str, Any], ...] = (),
    text_extractor: Optional[ContentExtractor] = None,
    raw_documents: tuple[dict[str, Any], ...] = (),
    request_id: Optional[str] = None,
) -> ContentIntelligenceModel:
    """Resolve everything ADOS actually knows about ``project`` (and,
    when given, one of its documents) into a single
    :class:`ContentIntelligenceModel`. ``version_number`` only labels the
    result (ADOS-M3.2 §34) — it does not itself pin the sources read;
    callers wanting a truly historical resolution pass a snapshotted
    ``document``/``project`` (see ``brand.project.versioning``, the same
    convention ``brand.design_state.build`` already follows).
    """
    import time

    start = time.perf_counter()
    extractor = text_extractor or _default_text_extractor()
    context = ContentExtractionContext(project_name=project.name)

    sources = _gather_sources(project, document, raw_documents)
    results, source_extractors = _run_extractors(sources, context, extractor)

    all_entities = [e for r in results for e in r.entities]
    all_facts = [f for r in results for f in r.facts]
    all_claims = [c for r in results for c in r.claims]
    all_relationships = [rel for r in results for rel in r.relationships]
    all_assets = [a for r in results for a in r.assets]

    merged_entities, id_map = _merge_entities(all_entities)
    merged_facts = _merge_facts(all_facts)
    merged_facts = _apply_user_corrections(merged_facts, user_corrections, project.id)
    merged_claims = _remap_claim_entities(all_claims, id_map)
    merged_relationships = _remap_and_dedupe_relationships(all_relationships, id_map)
    missing = _derive_missing_information(merged_facts, document_type_id)

    all_refs = tuple(
        r for coll in (merged_entities, merged_facts, merged_claims, merged_relationships, all_assets)
        for item in coll for r in item.source_refs
    )
    source_catalog = _dedupe_refs(tuple(
        r.model_copy(update={"page": None, "section": "", "location": ""}) for r in all_refs
    ))

    content = ContentIntelligenceModel(
        project_id=project.id, version_number=version_number,
        entities=merged_entities, facts=merged_facts, claims=merged_claims,
        relationships=merged_relationships, assets=tuple(all_assets),
        missing_information=missing, sources=source_catalog,
    )

    from brand.llm.content.observability import record_content_trace
    from brand.llm.content.prompt import PROMPT_VERSION
    from brand.llm.content.validation import validate_content_model

    validation = validate_content_model(content, project)
    record_content_trace(
        content=content, validation=validation, source_extractors=source_extractors,
        prompt_version=PROMPT_VERSION, latency_ms=(time.perf_counter() - start) * 1000,
        document_id=document.id if document else None, request_id=request_id,
    )
    return content

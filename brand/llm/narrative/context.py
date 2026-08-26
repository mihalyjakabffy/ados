"""
brand/llm/narrative/context.py

The deterministic context-assembly layer ADOS-M3.3 §33 asks for:

    SemanticIntent -> Content Resolution -> relevant ContentView -> NarrativeGenerator

This module does not resolve content itself — that is still
``brand.llm.content.resolution.resolve_content`` (M3.2), called by
``brand.llm.narrative.planning`` before this module ever runs. What
this module does is take an already-resolved
``ContentIntelligenceModel`` and shrink it to what a narrative
generator actually needs to see: ids, keys, statuses, short text — not
the whole project dumped into the prompt (ADOS-M3.3 §33: "do not
blindly send the entire project"). Full fact/claim text is short enough
in this domain that no separate relevance-ranking pass is warranted yet;
scoping here means *shape* (a summary, not the full model with every
optional field), not a smaller subset of items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from brand.llm.narrative.vocabulary import Audience, NarrativeCompression, NarrativeObjective

if TYPE_CHECKING:
    from brand.llm.content.model import ContentIntelligenceModel
    from brand.llm.semantic_intent import SemanticIntent

#: Free-text audience labels a user or SemanticIntent extractor might
#: produce, mapped onto ADOS's one canonical, closed audience vocabulary
#: (ADOS-M3.3 §7: "do not hardcode these independently if the
#: repository already has a canonical audience vocabulary" — it does,
#: ``brand.creative.direction.Audience``, reused as-is). This mapping is
#: deterministic and applied identically regardless of which
#: NarrativeGenerator runs — audience must never vary between two
#: otherwise-identical requests (ADOS-M3.3 §7: "must NOT alter factual
#: truth", and more generally must not vary at all for the same input).
_AUDIENCE_KEYWORDS: tuple[tuple[str, Audience], ...] = (
    ("investor", Audience.CLIENT),
    ("prospective_client", Audience.CLIENT),
    ("prospective client", Audience.CLIENT),
    ("client", Audience.CLIENT),
    ("customer", Audience.CLIENT),
    ("competition_jury", Audience.AUTHORITY),
    ("competition jury", Audience.AUTHORITY),
    ("jury", Audience.AUTHORITY),
    ("authority", Audience.AUTHORITY),
    ("regulator", Audience.AUTHORITY),
    ("planning", Audience.AUTHORITY),
    ("architect", Audience.PEER),
    ("engineer", Audience.PEER),
    ("consultant", Audience.PEER),
    ("peer", Audience.PEER),
    ("academic", Audience.PEER),
    ("internal_team", Audience.INTERNAL),
    ("internal team", Audience.INTERNAL),
    ("internal", Audience.INTERNAL),
    ("team", Audience.INTERNAL),
    ("general_audience", Audience.PUBLIC),
    ("general audience", Audience.PUBLIC),
    ("public", Audience.PUBLIC),
)

#: No audience was stated or inferred at all — the most conservative
#: default: assume the widest, least-specialised reader rather than
#: presuming a commercial (CLIENT) relationship the request never named.
_DEFAULT_AUDIENCE = Audience.PUBLIC


def resolve_audience(semantic_intent: "SemanticIntent") -> tuple[Audience, str]:
    """The closed ``Audience`` plus the original free-text label
    (ADOS-M3.3 §7) — both preserved, since the enum alone would lose
    "prospective_client" vs. "investor" even though both map to CLIENT."""
    from brand.llm.vocabulary import SemanticField

    label = (semantic_intent.resolved(SemanticField.AUDIENCE) or "").strip()
    if not label:
        return _DEFAULT_AUDIENCE, ""
    lowered = label.lower()
    for keyword, audience in _AUDIENCE_KEYWORDS:
        if keyword in lowered:
            return audience, label
    return _DEFAULT_AUDIENCE, label


#: Keyword -> objective, checked against SemanticIntent's free-text
#: ``purpose``/``action`` fields. A *hint*, not a hard rule: the LLM
#: generator may still choose differently when it has a better read of
#: the actual request; the deterministic RuleBasedNarrativeGenerator
#: (ADOS-M3.3 §44) uses it directly, since it has no reasoning of its
#: own to fall back on.
_OBJECTIVE_KEYWORDS: tuple[tuple[str, NarrativeObjective], ...] = (
    ("introduce", NarrativeObjective.INTRODUCE),
    ("persuade", NarrativeObjective.PERSUADE),
    ("sell", NarrativeObjective.PERSUADE),
    ("pitch", NarrativeObjective.PERSUADE),
    ("convince", NarrativeObjective.PERSUADE),
    ("compare", NarrativeObjective.COMPARE),
    ("summarize", NarrativeObjective.SUMMARIZE),
    ("summarise", NarrativeObjective.SUMMARIZE),
    ("summary", NarrativeObjective.SUMMARIZE),
    ("present", NarrativeObjective.PRESENT),
    ("demonstrate", NarrativeObjective.DEMONSTRATE),
    ("showcase", NarrativeObjective.DEMONSTRATE),
    ("explain", NarrativeObjective.EXPLAIN),
    ("educate", NarrativeObjective.EXPLAIN),
    ("document", NarrativeObjective.DOCUMENT),
    ("record", NarrativeObjective.DOCUMENT),
)

#: The safest default when no hint resolves at all: state what is known,
#: without presuming a persuasive or comparative intent the request
#: never signalled.
_DEFAULT_OBJECTIVE = NarrativeObjective.DOCUMENT


def resolve_objective_hint(semantic_intent: "SemanticIntent") -> Optional[NarrativeObjective]:
    from brand.llm.vocabulary import Action, SemanticField

    purpose = (semantic_intent.resolved(SemanticField.PURPOSE) or "").lower()
    for keyword, objective in _OBJECTIVE_KEYWORDS:
        if keyword in purpose:
            return objective

    action = semantic_intent.resolved(SemanticField.ACTION)
    if action == Action.COMPARE.value:
        return NarrativeObjective.COMPARE
    if action == Action.SUMMARIZE.value:
        return NarrativeObjective.SUMMARIZE
    return None


@dataclass(frozen=True)
class DocumentTypeCapabilities:
    """The subset of a real ``brand.project.document_types.DocumentType``
    a narrative generator can actually use — never the whole registry
    entry, and never a second, independently-maintained copy of it."""

    id: str = ""
    name: str = ""
    purpose: str = ""
    audience: str = ""
    default_structure: tuple[str, ...] = ()
    required_sections: tuple[str, ...] = ()
    asset_expectations: tuple[str, ...] = ()
    metadata_requirements: tuple[str, ...] = ()


def resolve_document_type_capabilities(document_type_id: str) -> DocumentTypeCapabilities:
    if not document_type_id:
        return DocumentTypeCapabilities()
    from brand.project.document_types import UnknownDocumentTypeError, get_document_type

    try:
        dt = get_document_type(document_type_id)
    except UnknownDocumentTypeError:
        return DocumentTypeCapabilities()
    return DocumentTypeCapabilities(
        id=dt.id, name=dt.name, purpose=dt.purpose, audience=dt.audience,
        default_structure=dt.default_structure, required_sections=dt.required_sections,
        asset_expectations=dt.asset_expectations, metadata_requirements=dt.metadata_requirements,
    )


@dataclass(frozen=True)
class ContentSummary:
    """A scoped, LLM-facing view of a ``ContentIntelligenceModel`` — ids
    and the minimum a generator needs to select responsibly from them,
    never the full model (no per-source page/section/extraction_method
    detail, which the generator has no use for and which only grows the
    prompt). Superseded facts are omitted entirely: they are not current
    project knowledge (ADOS-M3.2 §24)."""

    entities: tuple[dict[str, Any], ...] = ()
    facts: tuple[dict[str, Any], ...] = ()
    claims: tuple[dict[str, Any], ...] = ()
    assets: tuple[dict[str, Any], ...] = ()
    missing_information: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities": list(self.entities), "facts": list(self.facts),
            "claims": list(self.claims), "assets": list(self.assets),
            "missing_information": list(self.missing_information),
        }


def summarize_content(content: "ContentIntelligenceModel") -> ContentSummary:
    entities = tuple(
        {"id": e.id, "type": e.type.value, "name": e.name, "status": e.status.value}
        for e in content.entities
    )
    facts = []
    for f in content.facts:
        if f.superseded_by is not None:
            continue
        row: dict[str, Any] = {"id": f.id, "key": f.key, "status": f.status.value, "unit": f.unit}
        if f.status.value == "conflicting":
            row["conflicting_values"] = [
                {"value": cv.value, "unit": cv.unit} for cv in f.conflicting_values
            ]
        else:
            row["value"] = f.value
        facts.append(row)
    claims = tuple(
        {"id": c.id, "text": c.text, "status": c.status.value} for c in content.claims
    )
    assets = tuple(
        {"id": a.asset_id, "type": a.type, "caption": a.caption, "subject": a.subject}
        for a in content.assets
    )
    missing = tuple(
        {"key": m.key, "required_for": m.required_for} for m in content.missing_information
    )
    return ContentSummary(entities=entities, facts=tuple(facts), claims=claims, assets=assets, missing_information=missing)


@dataclass(frozen=True)
class NarrativeGenerationContext:
    """Everything a ``NarrativeGenerator`` actually receives — ADOS-M3.3
    §33. Built only from real objects a caller already has; nothing here
    fetches anything on a generator's behalf."""

    semantic_intent: "SemanticIntent"
    content_summary: ContentSummary
    document_type: DocumentTypeCapabilities = field(default_factory=DocumentTypeCapabilities)
    compression: NarrativeCompression = NarrativeCompression.MEDIUM
    #: A short, human-readable brand name only — never a token set. M3.3
    #: does not make visual decisions, so it has no use for anything more
    #: (ADOS-M3.3 §1's own boundary).
    brand_name: str = ""
    project_name: str = ""
    project_id: str = ""
    #: Resolved once, deterministically, here — not re-derived by each
    #: generator (see ``resolve_audience``'s own docstring for why).
    audience: Audience = _DEFAULT_AUDIENCE
    audience_label: str = ""
    objective_hint: Optional[NarrativeObjective] = None


def assemble_narrative_context(
    semantic_intent: "SemanticIntent",
    content: "ContentIntelligenceModel",
    *,
    document_type_id: str = "",
    compression: NarrativeCompression = NarrativeCompression.MEDIUM,
    brand_name: str = "",
    project_name: str = "",
) -> NarrativeGenerationContext:
    audience, audience_label = resolve_audience(semantic_intent)
    return NarrativeGenerationContext(
        semantic_intent=semantic_intent,
        content_summary=summarize_content(content),
        document_type=resolve_document_type_capabilities(document_type_id),
        compression=compression,
        brand_name=brand_name,
        project_name=project_name,
        project_id=content.project_id,
        audience=audience,
        audience_label=audience_label,
        objective_hint=resolve_objective_hint(semantic_intent),
    )

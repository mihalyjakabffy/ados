"""
brand/llm/content

ADOS-M3.2 — Content Intelligence. Sits between real project sources and
the future M3.3 narrative layer:

    Project Sources -> Content Resolution -> Content Intelligence
        -> ContentIntelligenceModel -> validated, traceable project knowledge

The central discipline this package enforces: ADOS must know what is
actually known about a project, where that knowledge came from, how
certain it is, and what is still unknown — *before* anything decides
what to say about it. This package answers the first question only.

Naming note — read before reaching for "ContentModel": the master
prompt for this milestone names its root object "ContentModel", but
that name already belongs to :class:`brand.content.model.ContentModel`
— a different, pre-existing, heavily-used type (a flat, layout-ready
list of ``ContentBlock``s that feeds ``brand.creative.composer.compose``
directly). This package's root object is a semantically much richer
knowledge graph (entities, facts, claims, provenance, conflicts,
missing information) that exists *before* any decision about what a
document should say — a different concept at a different layer, so it
is named :class:`~brand.llm.content.model.ContentIntelligenceModel`
instead. Nothing in this package modifies or extends
``brand.content.model`` — the two coexist, unrelated in shape and
purpose, disambiguated by name as well as by module path.

Submodules:

* ``vocabulary`` — closed EntityType/SourceType vocabularies.
* ``model`` — the domain model itself (Entity, Fact, Claim,
  Relationship, AssetContent, MissingInformation, SourceReference,
  ContentIntelligenceModel).
* ``extraction`` — the ``ContentExtractor`` abstraction and its
  deterministic (structured data, image metadata) and LLM-backed
  implementations.
* ``resolution`` — orchestrates extractors over a project's real
  sources into one ``ContentIntelligenceModel``, with conflict
  detection, deduplication, conservative entity resolution, and
  missing-information derivation.
* ``validation`` — deterministic domain validation, including the
  hard hallucination guard: no fact or claim may carry a truth-bearing
  status without at least one real source reference.
* ``prompt`` — the versioned Content Intelligence system prompt.
* ``observability`` — extends ``brand.llm.observability`` with a
  content-resolution trace.
* ``evaluation`` — the ADOS-M3.2 evaluation harness and dataset runner.

Nothing in this package produces a NarrativePlan, a DesignIntent, a
PagePlan, or a CommandIntent, and nothing in it calls
``brand.creative.intent`` or ``brand.creative.composer`` — checked
structurally in ``tests_brand/test_content_intelligence_boundaries.py``,
the same discipline ADOS-M3.1 established for its own boundary.
"""

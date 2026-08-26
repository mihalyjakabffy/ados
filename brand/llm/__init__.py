"""
brand/llm

ADOS-M3.1 — Semantic Intent. The first LLM layer in ADOS, and the only
one: this package turns natural language into a typed, validated
``SemanticIntent`` and stops there. It does not touch ``brand.creative``
(Composer, CommandIntent, PagePlan) — those remain the deterministic
engine this package feeds, in a later phase, through a boundary this
package does not itself cross.

    Natural Language -> LLM -> SemanticIntent -> deterministic validation

Nothing in this package mutates a Project, a Brand, a Document or a
PagePlan. Nothing in this package calls ``brand.creative.composer.compose``
or ``brand.creative.intent.apply_intent``. A caller that wants those
still calls them directly, exactly as before this package existed.

Submodules:

* ``vocabulary`` — the controlled Action/Target/SemanticField vocabulary.
* ``semantic_intent`` — the ``SemanticIntent`` domain model itself.
* ``context`` — ``SemanticContext``, built only from real, existing data.
* ``validation`` — deterministic checks, reusing
  ``brand.validation.brand_validator``'s Finding/Severity/Category.
* ``provider`` — the vendor-neutral ``LLMProvider`` interface.
* ``providers/`` — concrete providers (Claude; a deterministic
  rule-based fallback that never calls a network).
* ``prompt`` — the versioned system prompt.
* ``extractor`` — orchestrates provider -> schema validation -> domain
  validation -> ``SemanticIntent``. The one public entry point.
* ``observability`` — traces every extraction for later inspection.
"""

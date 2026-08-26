"""
brand/llm/command — ADOS-M3.5, Command Generation.

Compiles a :class:`~brand.llm.design.model.DesignIntent` (M3.4) into zero
or more :class:`~brand.creative.intent.CommandIntent` objects — the
existing, shipped command schema (M1.2) — and re-validates each one
through the existing ``brand.creative.intent.validate_intent()`` before
it is ever handed to ``apply_intent()``/``compose()``.

**This package is a compiler, not an agent.** It never composes a page,
never mutates a ``Project``/``Document``/``DesignState`` directly, never
invents a ninth ``IntentType``, and never calls the Composer itself — the
API router does that, by calling the same ``apply_intent`` +
``compose``/``compose_scoped`` pair the M1.2/M1.3 UI path already calls.
This module's only job is deciding *which* of the eight existing,
already-validated command types (if any) the semantic decisions in a
``DesignIntent`` call for, and only when the current, real
``DesignState`` doesn't already reflect them.

**Why this compiles at document/page scope, not per narrative section**
(the honest boundary this package draws, discovered during ADOS-M3.5's
own repository audit): ``brand.llm.design.model.SectionDesign`` references
a ``NarrativePlan`` section id, whose own ``content_refs`` are M3.2 fact/
claim/asset ids. ``brand.content.model.ContentBlock.id`` is a disjoint id
space (pattern ``[a-z]{3}-\\d{2,3}``) with no field connecting the two —
no shipped code resolves a fact or claim id to the content block it
became. Inventing that bridge here would be exactly the kind of
unproven, second mapping the M3.1-M3.4 anti-hallucination discipline
forbids elsewhere. So this package only emits document-scoped and
page-scoped commands, derived from a structural diff between a
``DesignIntent``'s document-level fields and the current
``brand.design_state.model.DesignState.visual_language`` — a real,
already-resolved comparison surface — plus a small number of
content-block-targeted commands where a ``DesignConstraint`` names a real
block id explicitly. A section-level design decision that has no
document-wide or explicitly-named-block expression is recorded as
*skipped*, with a reason, rather than silently guessed at.
"""

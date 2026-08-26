"""
brand/llm/loop — ADOS-M3.6, the LLM -> ADOS Closed Loop.

Orchestrates the existing M3.1-M3.5 layers plus the pre-existing
deterministic Composer/Evaluator (M1.x) into one controlled loop:

    DesignIntent -> M3.5 CommandPlan -> validate_intent() -> apply_intent()
        -> compose() -> evaluate() -> Finding[] -> Recommendation
        -> DesignIntentPatch -> revised DesignIntent -> M3.5 -> ...

**This package is an orchestrator, not a second execution engine.**
Every domain object it produces (a revised ``DesignIntent``, a
``CommandPlan``) is the exact same real type M3.4/M3.5 already define —
never a parallel schema. The one thing this package is *allowed* to do
that M3.1-M3.5 deliberately never do is call the real
``brand.creative.intent.apply_intent`` and ``brand.creative.composer
.compose`` — that is the entire point of closing the loop, and it
happens in exactly one module (``execution.py``), reusing the same two
functions ``api/routers/brand.py``'s own ``/intent`` endpoint and
``api/routers/command.py``'s ``/commands/apply`` endpoint already call.

**The LLM never controls the loop.** It may propose one bounded,
closed-vocabulary ``DesignIntentPatch`` when no deterministic
recommendation exists for a finding (``recommend.py``'s own bounded
tie-breaker, mirroring ``brand.llm.command.generation
.LLMCommandGenerator``'s exact pattern) — never a command, never
arbitrary code, never a decision about whether the loop continues. Stop
conditions, regression/no-progress/oscillation detection, and every
approval gate are computed by plain, deterministic Python
(``orchestrator.py``), never by asking a model whether to keep going.

**This package inherits M3.5's own honestly-stated scope boundary**
(see ``brand/llm/command/__init__.py``): there is still no structural
bridge between M3.2-M3.4's content-reference id space and
``ContentModel.ContentBlock.id``, so every ``DesignIntentPatch`` this
package can apply targets a document-level ``DesignIntent`` field
(``composition_strategy``, ``density``, ``typography_hierarchy``, …) —
never a per-section or per-block correction. A finding that would
require one is recorded as a ``SkippedRecommendation`` with reason
``UNSUPPORTED_SCOPE``, never guessed at.
"""

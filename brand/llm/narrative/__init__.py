"""
brand/llm/narrative

ADOS-M3.3 — Narrative Generation: the first genuinely generative layer
in the ADOS intelligence pipeline, and the last one bounded to answering
"what should we say" before "how should it look" (M3.4) and "which
commands execute it" (M3.5) begin.

    SemanticIntent (M3.1) + ContentIntelligenceModel (M3.2)
        -> Narrative reasoning
        -> NarrativePlan

This package never produces, imports, or names a ``DesignIntent``, a
``PagePlan``, a layout/grid/typography decision, or a ``CommandIntent``
— checked structurally in ``tests_brand/test_narrative_boundaries.py``,
mirroring ADOS-M3.2's own AST-walk boundary test. It never calls
``brand.creative.composer`` and never mutates a ``Project``/``Document``.

A ``NarrativePlan`` is valid architecture only if it would still make
sense with every ``draft`` field deleted (master prompt §36): the plan
is what a section is *for*, which real M3.2 content backs it, in what
order, and with what relative importance — never the final sentence.
"""

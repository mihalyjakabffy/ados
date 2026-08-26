"""
brand/llm/design

ADOS-M3.4 — Design Intent: the layer that decides how a narrative
should be communicated visually, and stops exactly there — before "what
exact PagePlan" (the deterministic Composer) or "which commands
execute it" (M3.5) begin.

    NarrativePlan (M3.3) + Brand DNA + CreativeDirection + DesignState
        -> visual communication reasoning
        -> DesignIntent

This package never produces, imports, or names a ``PagePlan``, a
``Slot``, a ``Page``, or a ``CommandIntent`` — checked structurally in
``tests_brand/test_design_intent_boundaries.py``, mirroring
ADOS-M3.2/M3.3's own AST-walk boundary tests. It never calls
``brand.creative.composer``, never calls a renderer
(``render_page_plan``/``html_to_pdf``), and never mutates a
``Project``/``Document``/``Brand``.

Every field in ``DesignIntent`` is semantic (a role, a level, a
strategy) — never a coordinate, a pixel value, a font name, or a hex
colour, unless that value is itself a real, already-existing ADOS
brand token or role name. M3.4 consumes the brand's design system; it
does not invent a second one.
"""

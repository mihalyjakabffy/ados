"""
brand — the ADOS Brand System.

The identity layer of the ADOS design-system stack.  ADOS states what is
*legal* (type scale, line tiers, tone ladder, contrast floors); the Brand
states what this *practice chooses* within that; the resolver turns the
choice into design tokens; the tokens drive every downstream artefact::

    ADOS tokens ──constrain──► Brand ──resolve──► Design tokens
                                                       │
                        ┌──────────────────────────────┼───────────────┐
                        ▼                              ▼               ▼
                   Documents                       Drawings        Renders
              (PTS PDF / Word)                   (Archicad)       (pipeline)

Design rules for this package
-----------------------------
1. **The Brand is the source of truth.**  No module may hold its own copy of a
   brand value; it resolves tokens instead.
2. **Tokens are the only bridge.**  A template binds to ``color.text.primary``,
   never to ``#111111``.
3. **AI proposes, the user approves.**  ``BrandAgent`` returns a
   ``BrandProposal``; only an explicit approval turns one into a ``Brand``.
4. **Everything published is versioned and immutable.**  A document built in
   2024 still resolves the brand it was built against.

Public entry points::

    from brand import Brand, BrandAgent, BrandResolver, BrandValidator
    from brand import STUDIO_NORD          # the worked example

    brand   = Brand.create(name="Studio Nord", ...)
    report  = brand.validate()
    tokens  = brand.resolve_tokens()
    doc     = brand.apply_to(template)
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "Brand",
    "BrandAgent",
    "BrandProposal",
    "BrandResolver",
    "BrandValidator",
    "TokenSet",
    "ValidationReport",
    "studio_nord",
    "STUDIO_NORD",
]

__version__ = "1.0.0"


def __getattr__(name: str):
    """Lazy re-exports.

    Keeps ``import brand`` free of the pydantic/jsonschema import cost for
    callers that only want ``__version__`` (the API health probe does), and
    avoids a circular import between ``brand.models`` and ``brand.resolution``.
    """
    if name in ("Brand",):
        from brand.models.brand import Brand

        return Brand
    if name in ("BrandAgent", "BrandProposal"):
        from brand.agents.brand_agent import BrandAgent, BrandProposal

        return {"BrandAgent": BrandAgent, "BrandProposal": BrandProposal}[name]
    if name == "BrandResolver":
        from brand.resolution.brand_resolver import BrandResolver

        return BrandResolver
    if name in ("BrandValidator", "ValidationReport"):
        from brand.validation.brand_validator import BrandValidator, ValidationReport

        return {"BrandValidator": BrandValidator, "ValidationReport": ValidationReport}[name]
    if name == "TokenSet":
        from brand.models.tokens import TokenSet

        return TokenSet
    if name in ("studio_nord", "STUDIO_NORD"):
        from brand.examples.studio_nord import STUDIO_NORD, studio_nord

        return {"studio_nord": studio_nord, "STUDIO_NORD": STUDIO_NORD}[name]
    raise AttributeError(f"module 'brand' has no attribute {name!r}")

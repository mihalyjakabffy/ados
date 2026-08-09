"""
brand/consumers.py

The contract a downstream consumer implements — Phase 5, deliberately thin.

The Brand System is meant to be platform infrastructure: Archicad, the render
pipeline, a portfolio generator and a website generator should all be able to
take a brand and produce their own artefact. That future is easy to
over-engineer now, and an abstraction designed against zero implementations is
almost always the wrong one.

So this module contains one Protocol and two worked adapters that produce
plain dictionaries. They exist to prove the surface is sufficient — a consumer
needs the token set and nothing else — and to give the eventual real
integrations a shape to grow into, not to be that integration.

What is deliberately *not* here: file writing, a plugin registry, an event
bus, an async interface. Each of those is a guess about how a consumer will
want to be called, and the repository already has an event bus
(``construmind/core/event_bus.py``) if one turns out to be needed.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from brand.models.tokens import TokenSet


@runtime_checkable
class BrandConsumer(Protocol):
    """Anything that turns brand tokens into an artefact.

    The single argument is the resolved :class:`TokenSet`, not the ``Brand``.
    That is the whole discipline of the system: a consumer that took the brand
    would reach past the token layer, and the next change to the brand model
    would break it.

    The one sanctioned exception is ``brand.resolution.pts_bridge``, which is a
    bridge rather than a consumer and needs fields the flat layer collapses.
    """

    name: str

    def consume(self, tokens: TokenSet, **context: Any) -> Any:
        """Produce this consumer's artefact from the tokens."""
        ...


class ArchicadAttributeMap:
    """Brand tokens as an Archicad attribute set.

    Archicad's graphic identity lives in pens, line types, fills and text
    styles. The mapping is direct because ADOS and Archicad happen to agree on
    the important thing — that a pen is a *weight in millimetres*, not a
    colour — so the three semantic tiers become three pens and the rest of the
    pen table is the apparatus.

    Returns a dictionary rather than writing a ``.aat``: the file format is
    version-specific and the mapping is not, and it is the mapping that needed
    proving.
    """

    name = "archicad"

    #: ADOS pen numbers. Fixed so that a drawing exchanged between two
    #: practices using ADOS reads the same, which is the point of a standard.
    PEN_NUMBERS = {"cut": 1, "seen": 2, "beyond": 3, "annotation": 4,
                   "dimension": 5, "apparatus": 6}

    def consume(self, tokens: TokenSet, **context: Any) -> dict[str, Any]:
        return {
            "pens": [
                {"index": self.PEN_NUMBERS["cut"], "name": "ADOS cut",
                 "width_mm": tokens.value("stroke.cut"), "colour": "black"},
                {"index": self.PEN_NUMBERS["seen"], "name": "ADOS seen",
                 "width_mm": tokens.value("stroke.primary"), "colour": "black"},
                {"index": self.PEN_NUMBERS["beyond"], "name": "ADOS beyond",
                 "width_mm": tokens.value("stroke.background"), "colour": "black"},
                {"index": self.PEN_NUMBERS["annotation"], "name": "ADOS annotation",
                 "width_mm": tokens.value("stroke.annotation"), "colour": "black"},
                {"index": self.PEN_NUMBERS["dimension"], "name": "ADOS dimension",
                 "width_mm": tokens.value("stroke.dimension"), "colour": "black"},
            ],
            "text_styles": [
                {"name": f"ADOS {step}", "font": tokens.value("font.family.primary"),
                 "size_mm": tokens.value(f"font.size.{step}"),
                 "size_pt": tokens.value(f"font.size.{step}.pt")}
                for step in ("xs", "sm", "md", "lg", "xl")
            ],
            "fills": [
                {"name": f"ADOS {token}", "l_star": tokens.value(f"tone.{token}")}
                for token in ("T0", "T1", "T2", "T3", "T4", "T5")
            ],
            "grid": {
                "module_mm": tokens.value("grid.module"),
                "submodule_mm": tokens.value("grid.baseline"),
            },
            "provenance": {
                "brand_id": tokens.brand_id,
                "brand_version": tokens.brand_version,
            },
        }


class RenderParameters:
    """Brand tokens as render-engine parameters.

    Deliberately shaped like ``VisualState`` in ``schemas/v2_models.py`` —
    camera with a focal length and a sensor width, a lighting scenario, render
    settings — because that is the object this repository's render pipeline
    already consumes. A brand should supply the defaults for a state, not a
    parallel vocabulary for the same thing.
    """

    name = "render"

    def consume(self, tokens: TokenSet, **context: Any) -> dict[str, Any]:
        return {
            "camera": {
                "focal_length_mm": tokens.value("render.camera.focal_length"),
                "sensor_width_mm": tokens.value("render.camera.sensor_width"),
                "eye_height_m": tokens.value("render.camera.height"),
                "keep_verticals": tokens.value("render.camera.two_point"),
            },
            "lighting": {"scenario": tokens.value("render.lighting"),
                         "sky": tokens.value("render.sky")},
            "grade": {"contrast": tokens.value("render.contrast"),
                      "saturation": tokens.value("render.saturation")},
            "style": {
                "mood": tokens.value("render.mood"),
                "material_expression": tokens.value("render.material_expression"),
                "people": tokens.value("render.people"),
            },
            "provenance": {
                "brand_id": tokens.brand_id,
                "brand_version": tokens.brand_version,
            },
        }


#: The adapters that exist today. Not a plugin registry — a list.
CONSUMERS: dict[str, BrandConsumer] = {
    c.name: c for c in (ArchicadAttributeMap(), RenderParameters())
}

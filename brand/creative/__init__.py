"""
brand/creative

The Creative Layer: how a project's content becomes a particular document.

Three things live here and nothing else:

``direction``
    What varies between two documents made from the same content and the same
    brand — emphasis, density, pacing. Never appearance.
``archetypes``
    The closed set of page shapes a page may take.
``composer``
    The deterministic solver that enumerates candidates, discards the
    infeasible against ADOS's hard constraints, ranks the rest against the
    direction's targets, and emits a :class:`~brand.creative.plan.PagePlan`.

There is no engine here, and no renderer. ``brand/templates/renderers.py``
already turns things into documents; what it lacked was something to render.
"""

from brand.creative.composer import CompositionError, compose
from brand.creative.direction import (
    Audience,
    CreativeDirection,
    DirectionError,
    Goal,
    LeadWith,
)
from brand.creative.directions import DIRECTIONS, get_direction
from brand.creative.plan import Page, PagePlan, Rejection, Slot

__all__ = [
    "Audience",
    "CompositionError",
    "CreativeDirection",
    "DIRECTIONS",
    "DirectionError",
    "Goal",
    "LeadWith",
    "Page",
    "PagePlan",
    "Rejection",
    "Slot",
    "compose",
    "get_direction",
]

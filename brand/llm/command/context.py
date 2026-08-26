"""
brand/llm/command/context.py

The deterministic context-assembly layer this package's generation step
needs:

    DesignIntent (M3.4) + DesignState (M2.5, the real "what currently is")
        -> scoped CommandGenerationContext

Nothing here decides a command — it only extracts, from two real
objects a caller already has, the small comparison surface a
deterministic diff actually needs: what the DesignIntent wants
(``composition_strategy``, ``density``) against what a real, already-
composed ``DesignState`` currently reflects (``document.direction_id``,
``visual_language.text_density``/``image_ratio``). The same
"shrink and organise, never re-derive" discipline
``brand.llm.design.context`` already applies to a Brand/CreativeDirection
pair is applied here to a DesignIntent/DesignState pair.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from brand.design_state.model import DesignState
    from brand.llm.design.model import DesignIntent


@dataclass(frozen=True)
class CurrentVisualState:
    """What a real, already-composed ``DesignState`` currently reflects
    — the "before" side of every diff this package computes. Absent
    (``has_state=False``) only when no DesignState was ever built for
    this document, in which case every lever is a fresh INTRODUCE and
    nothing in the current state to compare against exists yet."""

    has_state: bool = False
    version_number: Optional[int] = None
    direction_id: str = ""
    text_density: Optional[float] = None
    image_ratio: Optional[float] = None
    page_count: int = 0


def resolve_current_visual_state(design_state: Optional["DesignState"]) -> CurrentVisualState:
    if design_state is None:
        return CurrentVisualState()
    return CurrentVisualState(
        has_state=True,
        version_number=design_state.version.number,
        direction_id=design_state.document.direction_id,
        text_density=design_state.visual_language.text_density,
        image_ratio=design_state.visual_language.image_ratio,
        page_count=len(design_state.pages),
    )


@dataclass(frozen=True)
class CommandGenerationContext:
    """Everything a :class:`~brand.llm.command.generation.CommandGenerator`
    actually receives. Built only from a real ``DesignIntent`` and a real
    ``DesignState`` the caller already has — never fetched here."""

    design_intent: "DesignIntent"
    current: CurrentVisualState
    project_id: str = ""


def assemble_command_context(
    design_intent: "DesignIntent",
    design_state: Optional["DesignState"] = None,
) -> CommandGenerationContext:
    return CommandGenerationContext(
        design_intent=design_intent,
        current=resolve_current_visual_state(design_state),
        project_id=design_intent.project_id,
    )

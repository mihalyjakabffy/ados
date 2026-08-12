"""
brand/creative/intent.py

The structured intent layer between a user's command and the existing
Composer. Nothing here lays out a page — this module only prepares the
two inputs ``compose()`` already takes (a ``ContentModel`` and a
``CreativeDirection``) from a typed, validated ``CommandIntent``. The
Composer remains the sole authority over layout; this module is not a
second one.

Three things are deliberately kept apart, per the architecture this module
implements:

**Command** — what the user asked for. Lives in the frontend, in prose or
a button label. Never reaches this module.

**Intent** — a structured, typed, validated representation of that
request (:class:`CommandIntent`). This is what this module accepts.

**Composition** — the actual layout decision. Stays
``brand.creative.composer.compose``'s job, called by the router after
this module has done its work, not by this module itself.

Hard constraint (ADOS's own, restated for this layer): an intent may
never carry a coordinate, a colour, a font, or a grid value. Every
transformation below reaches for a lever ``CreativeDirection`` or
``ContentModel`` already exposes — a text-density target, an image-ratio
target, a block's priority — never a value ``brand/creative/direction.py``
would itself reject.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from brand import ados
from brand.content.model import ContentModel
from brand.creative.direction import CreativeDirection, DirectionError, FORBIDDEN_FIELD_STEMS
from brand.creative.directions import get_direction

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Same denylist the direction schema itself is checked against
#: (ADOS-7.2.020's vocabulary and the brand-restatement guard) — reused,
#: not duplicated, and applied here to intent *parameters* rather than to
#: direction fields, because a parameter is exactly where a command could
#: try to sneak a colour or a font past the schema.
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_DIMENSION = re.compile(r"\b\d+(?:\.\d+)?\s?(mm|cm|pt|px|em|rem|%)\b", re.I)


class IntentType(str, Enum):
    REDUCE_TEXT_DENSITY = "reduce_text_density"
    INCREASE_TEXT_DENSITY = "increase_text_density"
    INCREASE_IMAGE_EMPHASIS = "increase_image_emphasis"
    DECREASE_IMAGE_EMPHASIS = "decrease_image_emphasis"
    RECOMPOSE_PAGE = "recompose_page"
    PRESERVE_CONTENT = "preserve_content"
    REMOVE_CONTENT = "remove_content"
    CHANGE_PAGE_DIRECTION = "change_page_direction"


#: Intents whose only real lever is a document-wide CreativeDirection
#: field. There is no page-scoped recomposition in brand.creative.composer
#: today — compose() always regenerates every page from content + one
#: direction. Naming that honestly here (see IntentResolution.notes)
#: matters more than pretending a page-local knob exists.
_DENSITY_TYPES = (IntentType.REDUCE_TEXT_DENSITY, IntentType.INCREASE_TEXT_DENSITY)
_EMPHASIS_TYPES = (IntentType.INCREASE_IMAGE_EMPHASIS, IntentType.DECREASE_IMAGE_EMPHASIS)


class TargetType(str, Enum):
    DOCUMENT = "document"
    PAGE = "page"
    REGION = "region"
    CONTENT_BLOCK = "contentBlock"


class IntentTarget(BaseModel):
    """What the command was pointed at.

    Carried through for audit and UI context even where, honestly, the
    resulting transformation is document-wide (see ``_DENSITY_TYPES`` /
    ``_EMPHASIS_TYPES`` above) — the target records *what the user was
    looking at*, which is real information, without pretending the
    Composer can act on that page in isolation.
    """

    model_config = _Frozen

    type: TargetType
    id: str = Field(default="", max_length=80)


class PreserveConstraint(BaseModel):
    model_config = _Frozen

    type: str = Field(default="preserve_content", pattern=r"^preserve_content$")
    content_ids: tuple[str, ...] = Field(min_length=1, max_length=40)


class CommandIntent(BaseModel):
    """A structured, deterministic representation of one user command.

    Every field is a closed type, a bounded number, or a reference to an
    existing id — never free text that reaches the Composer, and never a
    geometry or Brand value. ``source`` exists now so the future LLM
    boundary (natural language -> LLM -> CommandIntent -> here) is a type
    the schema already distinguishes, not a retrofit.
    """

    model_config = _Frozen

    type: IntentType
    target: IntentTarget
    parameters: dict[str, Any] = Field(default_factory=dict)
    constraints: tuple[PreserveConstraint, ...] = ()
    source: str = Field(default="ui", pattern=r"^(ui|future_llm)$")


class IntentValidationError(ValueError):
    """The intent failed domain validation and must not reach the Composer."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class IntentResolution(BaseModel):
    """What applying an intent decided, kept apart from the PagePlan itself.

    ``direction_changed`` / ``content_changed`` let the caller show an
    honest before/after summary without diffing two large objects, and
    ``notes`` is where this module discloses a simplification — e.g. that
    a page-targeted density change is, today, applied to the whole
    document — rather than hiding it.
    """

    model_config = _Frozen

    direction_changed: bool
    content_changed: bool
    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_intent(
    content: ContentModel,
    intent: CommandIntent,
    page_count: int | None,
) -> list[str]:
    """Domain checks pydantic's schema alone cannot express.

    Returns a list of human-readable errors; empty means the intent may
    proceed to :func:`apply_intent`. Nothing here calls the Composer.
    """

    errors: list[str] = []

    # -- the hard constraint: no geometry, no Brand values, ever ----------
    for key, value in intent.parameters.items():
        lowered = key.lower()
        if any(stem in lowered for stem in FORBIDDEN_FIELD_STEMS):
            errors.append(
                f"parameter {key!r} is not permitted — geometry, colour, "
                f"font and grid values are set by the Brand and the "
                f"Composer, never by an intent."
            )
        if isinstance(value, str):
            if _HEX.search(value):
                errors.append(f"parameter {key!r} names a colour, which an intent may not do")
            if _DIMENSION.search(value):
                errors.append(f"parameter {key!r} names a dimension, which an intent may not do")

    # -- target existence ---------------------------------------------------
    if intent.target.type is TargetType.PAGE and intent.target.id:
        if not intent.target.id.lstrip("-").isdigit():
            errors.append("a page target's id must be the page's numeric index")
        elif page_count is not None:
            idx = int(intent.target.id)
            if not (0 <= idx < page_count):
                errors.append(f"target page {idx} does not exist in a {page_count}-page plan")

    if intent.target.type is TargetType.CONTENT_BLOCK and intent.target.id:
        if not any(b.id == intent.target.id for b in content.blocks):
            errors.append(f"target content block {intent.target.id!r} does not exist")

    # -- per-type parameter checks ------------------------------------------
    if intent.type in (*_DENSITY_TYPES, *_EMPHASIS_TYPES):
        strength = intent.parameters.get("strength", 0.5)
        if not isinstance(strength, (int, float)) or isinstance(strength, bool) or not (0.0 <= strength <= 1.0):
            errors.append("parameter 'strength' must be a number between 0 and 1")

    if intent.type in (IntentType.PRESERVE_CONTENT, IntentType.REMOVE_CONTENT):
        ids = intent.parameters.get("content_ids")
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
            errors.append("parameter 'content_ids' must be a non-empty list of content block ids")
        else:
            known = {b.id for b in content.blocks}
            unknown = [i for i in ids if i not in known]
            if unknown:
                errors.append(f"unknown content_ids: {', '.join(unknown)}")
            if intent.type is IntentType.REMOVE_CONTENT and len(ids) >= len(content.blocks):
                errors.append("remove_content cannot remove every block in the content model")

    if intent.type is IntentType.CHANGE_PAGE_DIRECTION:
        new_id = intent.parameters.get("direction_id")
        if not isinstance(new_id, str) or not new_id:
            errors.append("parameter 'direction_id' is required")
        else:
            try:
                get_direction(new_id)
            except KeyError:
                errors.append(f"unknown direction_id {new_id!r}")

    for constraint in intent.constraints:
        known = {b.id for b in content.blocks}
        unknown = [i for i in constraint.content_ids if i not in known]
        if unknown:
            errors.append(f"unknown preserve_content content_ids in constraints: {', '.join(unknown)}")

    return errors


# ---------------------------------------------------------------------------
# Application — prepares Composer inputs, does not compose
# ---------------------------------------------------------------------------


def apply_intent(
    content: ContentModel,
    base_direction: CreativeDirection,
    intent: CommandIntent,
) -> tuple[ContentModel, CreativeDirection, IntentResolution]:
    """Turn a validated intent into (ContentModel, CreativeDirection).

    Call :func:`validate_intent` first — this function trusts its input
    and will raise :class:`IntentValidationError` only for the one thing
    validation cannot fully anticipate: the *combination* of adjustments
    producing a CreativeDirection the schema itself then refuses (e.g. a
    density pushed, after clamping, to a value ``check_ados`` still
    rejects for an unrelated reason).
    """

    notes: list[str] = []
    new_content = content
    new_direction = base_direction
    content_changed = False
    direction_changed = False

    boosted = {i for c in intent.constraints for i in c.content_ids}
    if intent.type is IntentType.PRESERVE_CONTENT:
        boosted |= set(intent.parameters.get("content_ids", []))
    if boosted:
        new_content = new_content.model_copy(
            update={
                "blocks": tuple(
                    b.model_copy(update={"priority": 1}) if b.id in boosted else b
                    for b in new_content.blocks
                )
            }
        )
        content_changed = True
        notes.append(
            f"{len(boosted)} block(s) promoted to priority 1 (lead) — this raises the "
            f"likelihood of early placement; it is not a guarantee of inclusion, because "
            f"inclusion is the Composer's feasibility decision, not this layer's."
        )

    if intent.type is IntentType.REMOVE_CONTENT:
        remove_ids = set(intent.parameters.get("content_ids", []))
        new_content = new_content.model_copy(
            update={"blocks": tuple(b for b in new_content.blocks if b.id not in remove_ids)}
        )
        content_changed = True
        notes.append(f"{len(remove_ids)} block(s) removed from the content model before composing.")

    if intent.type in (*_DENSITY_TYPES, *_EMPHASIS_TYPES, IntentType.CHANGE_PAGE_DIRECTION):
        if intent.target.type is TargetType.PAGE:
            notes.append(
                "brand.creative.composer.compose has no page-scoped recomposition today — "
                "it regenerates the whole document from one CreativeDirection. This "
                "adjustment therefore applies document-wide, not to the targeted page alone."
            )

    strength = float(intent.parameters.get("strength", 0.5))
    low, high = ados.fill_ratio_bounds()

    if intent.type is IntentType.REDUCE_TEXT_DENSITY:
        target = base_direction.text_density - strength * (base_direction.text_density - low)
        new_direction = _derive(base_direction, text_density=round(max(low, target), 3))
        direction_changed = True

    elif intent.type is IntentType.INCREASE_TEXT_DENSITY:
        target = base_direction.text_density + strength * (high - base_direction.text_density)
        new_direction = _derive(base_direction, text_density=round(min(high, target), 3))
        direction_changed = True

    elif intent.type is IntentType.INCREASE_IMAGE_EMPHASIS:
        target = base_direction.image_ratio + strength * (1.0 - base_direction.image_ratio)
        new_direction = _derive(base_direction, image_ratio=round(min(1.0, target), 3))
        direction_changed = True

    elif intent.type is IntentType.DECREASE_IMAGE_EMPHASIS:
        target = base_direction.image_ratio - strength * base_direction.image_ratio
        new_direction = _derive(base_direction, image_ratio=round(max(0.0, target), 3))
        direction_changed = True

    elif intent.type is IntentType.CHANGE_PAGE_DIRECTION:
        new_direction = get_direction(str(intent.parameters["direction_id"]))
        direction_changed = new_direction.id != base_direction.id

    elif intent.type is IntentType.RECOMPOSE_PAGE:
        notes.append(
            "recompose_page re-runs the Composer over unchanged inputs — a deterministic "
            "no-op that proves the same content, direction and Brand still produce the "
            "same document."
        )

    return new_content, new_direction, IntentResolution(
        direction_changed=direction_changed,
        content_changed=content_changed,
        notes=tuple(notes),
    )


def _derive(base: CreativeDirection, **updates: Any) -> CreativeDirection:
    """A new, unregistered CreativeDirection — full validation, not model_copy.

    ``model_copy`` skips validators; a derived direction must pass the same
    ``field_validator``/``model_validator`` gates a shipped one does (the
    ADOS density bound, the pacing/archetype check, the brand-restatement
    guard), or an intent could produce a direction the schema would have
    rejected if authored by hand.
    """

    payload = {**base.model_dump(mode="json"), **updates, "id": (f"{base.id}-adj")[:40]}
    try:
        return CreativeDirection.model_validate(payload)
    except (ValidationError, DirectionError) as exc:
        raise IntentValidationError([f"resulting direction is invalid: {exc}"]) from exc

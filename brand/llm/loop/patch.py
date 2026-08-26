"""
brand/llm/loop/patch.py

Applies one validated :class:`~brand.llm.loop.model.DesignIntentPatch`
to a real :class:`~brand.llm.design.model.DesignIntent`, producing a new
one — ADOS-M3.6 §19/§20/§51. Mirrors
``brand.creative.intent._derive``'s own discipline exactly: a patch is
applied via ``DesignIntent.model_validate`` (full pydantic construction,
every validator re-run), never ``model_copy`` (which would skip them),
and the result is additionally re-checked by the real
``brand.llm.design.validation.validate_design_intent`` before this
function ever returns it — a patch that produces a
``DesignIntent`` M3.4's own validator would reject is refused here, not
downstream.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from pydantic import ValidationError

from brand.llm.design.model import DesignIntent
from brand.llm.design.validation import validate_design_intent
from brand.llm.design.vocabulary import (
    ColorStrategy,
    CompositionStrategy,
    GridStrategy,
    Rhythm,
    TextDensity,
    TypographyHierarchy,
    WhitespaceStrategy,
)
from brand.llm.loop.model import PATCHABLE_FIELDS, DesignIntentPatch

if TYPE_CHECKING:
    from brand.llm.narrative.model import NarrativePlan

#: target field name -> the real enum type that field holds. The only
#: place this mapping needs to exist — patch.py is the sole writer of
#: a DesignIntent's root fields on this loop's behalf.
_FIELD_ENUM: dict[str, type] = {
    "composition_strategy": CompositionStrategy,
    "density": TextDensity,
    "typography_hierarchy": TypographyHierarchy,
    "color_strategy": ColorStrategy,
    "grid_strategy": GridStrategy,
    "whitespace_strategy": WhitespaceStrategy,
    "rhythm": Rhythm,
}


class PatchTargetError(ValueError):
    """``patch.target`` is not one of ``PATCHABLE_FIELDS``."""


class PatchValueError(ValueError):
    """``patch.value`` is not a real member of the target field's enum."""


class PatchValidationError(ValueError):
    """The patched DesignIntent failed M3.4's own construction or
    deterministic validation. Carries the real errors/findings so a
    caller can report exactly what M3.4 objected to."""

    def __init__(self, message: str, errors: list[str]):
        self.errors = errors
        super().__init__(message)


def apply_design_intent_patch(
    design_intent: DesignIntent,
    patch: DesignIntentPatch,
    narrative_plan: "NarrativePlan",
) -> DesignIntent:
    if patch.target not in PATCHABLE_FIELDS:
        raise PatchTargetError(
            f"{patch.target!r} is not a patchable DesignIntent field — allowed: {PATCHABLE_FIELDS}"
        )
    enum_cls = _FIELD_ENUM[patch.target]
    try:
        coerced = enum_cls(patch.value)
    except ValueError:
        raise PatchValueError(
            f"{patch.value!r} is not a real {enum_cls.__name__} value"
        ) from None

    payload = design_intent.model_dump(mode="json")
    payload[patch.target] = coerced.value
    payload["id"] = uuid.uuid4().hex[:12]
    payload["metadata"] = {
        **design_intent.metadata,
        "patched_from": design_intent.id,
        "patch_target": patch.target,
        "patch_value": coerced.value,
    }

    try:
        patched = DesignIntent.model_validate(payload)
    except ValidationError as exc:
        raise PatchValidationError(
            f"patched DesignIntent fails schema validation: {exc}", [str(exc)]
        ) from exc

    report = validate_design_intent(patched, narrative_plan)
    if not report.ok:
        raise PatchValidationError(
            "patched DesignIntent fails deterministic validation",
            [f"{f.code}: {f.message}" for f in report.findings if f.severity.value in ("BLOCK", "ERROR")],
        )
    return patched

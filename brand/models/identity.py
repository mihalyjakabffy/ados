"""
brand/models/identity.py

Who the practice is, in structured form.

Identity is the only part of a brand that is mostly prose, and it is still
modelled rather than stored as a paragraph: ``BrandAgent`` writes into these
fields, ``BrandValidator`` checks them, and the communication layer draws its
vocabulary from them. A free-text blob would be readable by neither.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

_Frozen = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class PracticeScale(str, Enum):
    """Studio size band. Drives sensible defaults, not judgements."""

    SOLO = "solo"
    SMALL = "small"            # 2-10
    MEDIUM = "medium"          # 11-50
    LARGE = "large"            # 51+


class PersonalityAxis(str, Enum):
    """The adjective vocabulary a practice may describe itself with.

    A closed list rather than free text because personality has to be
    machine-consumable: the render language, the diagram style and the writing
    tone are all derived from it. ``keywords`` on ``Identity`` carries anything
    this list cannot express.
    """

    PRECISE = "precise"
    QUIET = "quiet"
    MATERIAL = "material"
    EDITORIAL = "editorial"
    WARM = "warm"
    RIGOROUS = "rigorous"
    EXPERIMENTAL = "experimental"
    CIVIC = "civic"
    CRAFT = "craft"
    PRAGMATIC = "pragmatic"
    MONUMENTAL = "monumental"
    PLAYFUL = "playful"


class Identity(BaseModel):
    """The non-visual half of a brand."""

    model_config = _Frozen

    name: str = Field(min_length=1, max_length=120)
    descriptor: str = Field(
        default="",
        max_length=200,
        description="What the practice is, in one line. 'Architecture and "
        "adaptive reuse' — not a slogan.",
    )
    tagline: str = Field(default="", max_length=200)
    positioning: str = Field(
        default="",
        max_length=600,
        description="What this practice does that a client cannot get elsewhere.",
    )
    mission: str = Field(default="", max_length=600)
    vision: str = Field(default="", max_length=600)
    values: tuple[str, ...] = Field(default=())
    personality: tuple[PersonalityAxis, ...] = Field(
        default=(),
        description="Two to four axes. More than four is not a personality.",
    )
    keywords: tuple[str, ...] = Field(default=())
    practice_scale: PracticeScale = Field(default=PracticeScale.SMALL)
    founded: int | None = Field(default=None, ge=1800, le=2200)
    locations: tuple[str, ...] = Field(default=())

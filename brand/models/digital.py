"""
brand/models/digital.py

Art direction for the surfaces a practice does not print: the website and
social media.

These are modelled for the same reason the drawing language is. A website
built without a stated direction acquires one anyway — from whichever template
was bought — and it will not be the practice's. What is here is the small set
of decisions that actually differ between an architecture studio's site and a
SaaS landing page: how much is on the first screen, whether images are framed
or bleed, whether anything moves, and how a project is announced.

Motion is a first-class field because it is the decision most often made by
default. A studio whose drawings do not animate has already decided.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

_Frozen = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class MotionLevel(str, Enum):
    """How much a page is allowed to move."""

    NONE = "none"
    FADE = "fade"                # opacity only, no travel
    RESTRAINED = "restrained"    # short travel, one property at a time
    EXPRESSIVE = "expressive"


class NavStyle(str, Enum):
    MINIMAL_TOP = "minimal-top"
    SIDE_INDEX = "side-index"
    OVERLAY = "overlay"


class WebDirection(BaseModel):
    """The website, before anyone opens a design tool."""

    model_config = _Frozen

    sections: tuple[str, ...] = Field(
        default=("Hero", "Projects", "Studio", "Approach", "Contact"),
        description="Top-level structure, in order.",
    )
    nav: NavStyle = Field(default=NavStyle.MINIMAL_TOP)
    hero: str = Field(
        default="single image, full width, no overlaid text",
        max_length=200,
        description="What is on the first screen. Text over an image is the "
        "commonest way an architecture site starts looking like an advert.",
    )
    project_card: str = Field(
        default="image, name, year, type — no hover caption",
        max_length=200,
    )
    grid_columns: int = Field(default=12, ge=1, le=24)
    max_content_width_px: int = Field(default=1440, ge=600, le=2400)
    image_treatment: str = Field(
        default="framed", pattern=r"^(framed|bleed|inset)$",
    )
    motion: MotionLevel = Field(default=MotionLevel.FADE)
    transition_ms: int = Field(default=180, ge=0, le=1000)
    hover: str = Field(
        default="opacity to 0.7, no scale, no shadow", max_length=160,
    )
    dark_mode: bool = Field(
        default=False,
        description="False unless the practice means it. A print identity "
        "inverted is a different identity.",
    )
    notes: str = Field(default="", max_length=600)


class SocialDirection(BaseModel):
    """Social media, kept deliberately narrow."""

    model_config = _Frozen

    platforms: tuple[str, ...] = Field(default=("instagram", "linkedin"))
    post_formats: tuple[str, ...] = Field(default=("1:1", "4:5"))
    post_types: tuple[str, ...] = Field(
        default=(
            "project announcement", "construction progress", "finished project",
            "drawing", "diagram", "competition", "studio news",
        ),
    )
    caption_max_words: int = Field(default=60, ge=10, le=400)
    watermark: bool = Field(
        default=False,
        description="False. A watermark on a photograph of a building says "
        "the image is the asset; the building is.",
    )
    grid_discipline: str = Field(
        default="one project per three posts, in sequence", max_length=200,
    )
    notes: str = Field(default="", max_length=600)


class DigitalDirection(BaseModel):
    model_config = _Frozen

    web: WebDirection = Field(default_factory=WebDirection)
    social: SocialDirection = Field(default_factory=SocialDirection)

"""
brand/models/communication.py

How the practice writes.

This exists for the same reason the architectural layer does: an RFI, a site
report and a portfolio caption written in three different voices read as three
different practices. ADOS already constrains document language in places
(``ADOS-4.8.050`` on note language); this is the practice's choice within it.

The fields a generator actually consumes are ``tone``, ``person``,
``sentence_length_max``, ``terminology`` and ``forbidden_words``. The rest is
guidance for a human author.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

_Frozen = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class Tone(str, Enum):
    NEUTRAL = "neutral"
    PRECISE = "precise"
    EDITORIAL = "editorial"
    WARM = "warm"
    FORMAL = "formal"
    DIRECT = "direct"


class Person(str, Enum):
    FIRST_PLURAL = "first_plural"      # "we"
    THIRD = "third"                    # "the practice"
    IMPERSONAL = "impersonal"          # "the work"


class Communication(BaseModel):
    model_config = _Frozen

    tone: Tone = Field(default=Tone.PRECISE)
    person: Person = Field(default=Person.FIRST_PLURAL)
    writing_style: str = Field(default="", max_length=600)
    sentence_length_max: int = Field(
        default=28, ge=8, le=60,
        description="Words. A cap, not a target — technical documents are read "
        "under time pressure and a 40-word sentence is read twice or not at all.",
    )
    vocabulary: tuple[str, ...] = Field(
        default=(), description="Words the practice reaches for.",
    )
    forbidden_words: tuple[str, ...] = Field(
        default=(),
        description="Words it does not use. Checked by the consistency pass, "
        "so keep it to words rather than phrases.",
    )
    terminology: dict[str, str] = Field(
        default_factory=dict,
        description="Preferred term → what it replaces. 'adaptive reuse': "
        "'refurbishment'.",
    )
    primary_language: str = Field(default="en-GB", pattern=r"^[a-z]{2}(-[A-Z]{2})?$")
    secondary_languages: tuple[str, ...] = Field(default=())
    date_format: str = Field(default="YYYY-MM-DD", max_length=20)
    number_format: str = Field(default="1 234,5", max_length=20)

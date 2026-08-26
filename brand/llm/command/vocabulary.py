"""
brand/llm/command/vocabulary.py

ADOS-M3.5's own closed vocabularies, plus the deterministic lookup
tables this package uses to translate a semantic ``DesignIntent`` field
into a lever ``brand.creative.intent``/``brand.creative.direction``
already exposes. Nothing here is a competing command schema — see this
package's ``__init__`` docstring; ``IntentType``/``TargetType`` are
imported and reused directly, never re-declared.
"""

from __future__ import annotations

from enum import Enum

from brand.creative.intent import IntentType, TargetType  # noqa: F401  (re-exported)
from brand.creative.scope import ScopeType  # noqa: F401  (re-exported)
from brand.llm.design.vocabulary import CompositionStrategy, TextDensity


class CommandSafetyLevel(str, Enum):
    """ADOS-M3.5's required safety classification, applied per generated
    command. ``SAFE`` commands only ever nudge a continuous value or swap
    to an already-authored, already-validated ``CreativeDirection``.
    ``DESTRUCTIVE`` is reserved for ``REMOVE_CONTENT`` alone — the one
    ``IntentType`` that can make previously-composed content disappear."""

    SAFE = "safe"
    REVIEW_RECOMMENDED = "review_recommended"
    DESTRUCTIVE = "destructive"


#: Every IntentType this package may ever emit is SAFE except REMOVE_CONTENT,
#: which is DESTRUCTIVE, and CHANGE_PAGE_DIRECTION, which is REVIEW_RECOMMENDED
#: (it changes narrative_order/pacing/emphasis for the *whole* targeted scope,
#: not one continuous value) — a fixed table, not a judgement call made
#: fresh per command, so CMD-009 (see validation.py) has something
#: independent to check a claimed safety_level against.
SAFETY_BY_INTENT_TYPE: dict[IntentType, CommandSafetyLevel] = {
    IntentType.REDUCE_TEXT_DENSITY: CommandSafetyLevel.SAFE,
    IntentType.INCREASE_TEXT_DENSITY: CommandSafetyLevel.SAFE,
    IntentType.INCREASE_IMAGE_EMPHASIS: CommandSafetyLevel.SAFE,
    IntentType.DECREASE_IMAGE_EMPHASIS: CommandSafetyLevel.SAFE,
    IntentType.RECOMPOSE_PAGE: CommandSafetyLevel.SAFE,
    IntentType.PRESERVE_CONTENT: CommandSafetyLevel.SAFE,
    IntentType.CHANGE_PAGE_DIRECTION: CommandSafetyLevel.REVIEW_RECOMMENDED,
    IntentType.REMOVE_CONTENT: CommandSafetyLevel.DESTRUCTIVE,
}


class CommandProvenance(str, Enum):
    """Where a generated command's justification came from — carried on
    every :class:`~brand.llm.command.model.GeneratedCommand` so a reviewer
    never has to guess whether a command was a direct read of one
    ``DesignIssue``/``DesignConstraint`` or an inferred structural diff."""

    DESIGN_ISSUE = "design_issue"
    DESIGN_CONSTRAINT = "design_constraint"
    STRUCTURAL_DIFF = "structural_diff"
    VERIFICATION = "verification"
    #: A structural diff whose deterministic lookup was ambiguous (e.g.
    #: ``CompositionStrategy.BALANCED`` maps to no single shipped
    #: direction) and was resolved by the LLM tie-breaker choosing among
    #: the closed set of already-registered ``CreativeDirection`` ids —
    #: never a value the deterministic pass could not have also named.
    LLM_DISAMBIGUATION = "llm_disambiguation"


class CommandRejectionReason(str, Enum):
    """Why a candidate lever named by the ``DesignIntent`` did *not*
    become a command — recorded, never silently dropped (ADOS-M3.5's own
    "no deletion by implication" principle, generalised to "no decision
    by implication")."""

    NO_CHANGE_NEEDED = "no_change_needed"
    AMBIGUOUS_MAPPING = "ambiguous_mapping"
    NO_BRIDGE_TO_CONTENT_BLOCK = "no_bridge_to_content_block"
    UNKNOWN_DIRECTION = "unknown_direction"
    STALE_DESIGN_STATE = "stale_design_state"
    WOULD_DUPLICATE_EXISTING = "would_duplicate_existing"
    VALIDATION_FAILED = "validation_failed"
    #: A real DesignIssue (e.g. a brand conflict) was flagged, but no
    #: existing IntentType can address it safely and automatically —
    #: ADOS-M3.5's "compiler, not agent" boundary: some findings are for
    #: a person to resolve, not for this package to guess a fix for.
    NO_SAFE_COMMAND_EXISTS = "no_safe_command_exists"


#: CompositionStrategy -> the one shipped CreativeDirection id it maps to,
#: or absent for a strategy with no confident single-direction reading
#: (BALANCED/ASYMMETRIC/MODULAR/SEQUENTIAL/IMMERSIVE) — those are recorded
#: as CommandRejectionReason.AMBIGUOUS_MAPPING, never guessed at, per
#: this package's own anti-hallucination posture.
DIRECTION_BY_COMPOSITION_STRATEGY: dict[CompositionStrategy, str] = {
    CompositionStrategy.IMAGE_LED: "image-led",
    CompositionStrategy.DIAGRAM_LED: "technical-dense",
    CompositionStrategy.DATA_LED: "technical-dense",
    CompositionStrategy.DENSE: "technical-dense",
    CompositionStrategy.TEXT_LED: "editorial-quiet",
    CompositionStrategy.SPARSE: "editorial-quiet",
}

#: TextDensity -> the target CreativeDirection.text_density float this
#: package compares the current DesignState against. Anchored to the
#: three shipped directions' own text_density values (0.45 / 0.62 / 0.78)
#: and extended linearly to the two extremes of the five-step scale —
#: not a value invented independent of real, shipped data.
TARGET_TEXT_DENSITY_BY_LEVEL: dict[TextDensity, float] = {
    TextDensity.MINIMAL: 0.25,
    TextDensity.LOW: 0.40,
    TextDensity.MEDIUM: 0.55,
    TextDensity.HIGH: 0.72,
    TextDensity.VERY_HIGH: 0.85,
}

#: TextDensity -> the target CreativeDirection.image_ratio float, used as
#: the aggregate signal for image emphasis (SectionDesign.image_density,
#: mode across all sections). Anchored the same way as
#: TARGET_TEXT_DENSITY_BY_LEVEL, against the three shipped directions'
#: own image_ratio values (0.12 / 0.50-0.62 / 0.72).
TARGET_IMAGE_RATIO_BY_LEVEL: dict[TextDensity, float] = {
    TextDensity.MINIMAL: 0.10,
    TextDensity.LOW: 0.25,
    TextDensity.MEDIUM: 0.45,
    TextDensity.HIGH: 0.65,
    TextDensity.VERY_HIGH: 0.80,
}

#: A text_density (or image_ratio) gap below this is "already there" —
#: compose()/CreativeDirection round to 3 decimals (brand/creative/intent.py
#: _derive), so a gap smaller than that is not a real difference to act on.
NEGLIGIBLE_GAP = 0.02

"""
brand/llm/narrative/vocabulary.py

The controlled vocabularies ADOS-M3.3 asks for (master prompt §6/§7/
§9/§11/§16/§17/§18/§19/§22/§29/§30), each kept as small as the master
prompt itself allows ("do not create an unnecessarily large uncontrolled
vocabulary") and reusing an existing ADOS vocabulary wherever one
already covers the concept.

**Audience is not redeclared here.** ``brand.creative.direction.Audience``
(client/peer/authority/public/internal) is already ADOS's canonical
audience vocabulary — it is what the very next layer (M3.4's eventual
``CreativeDirection`` selection) reads. Re-exported below rather than
importing it ad hoc at every call site.

**Objective is a new, small vocabulary.** No existing ADOS enum names a
document's communication objective at this granularity —
``brand.creative.direction.Goal`` (inform/persuade/record/instruct)
is a coarser, layout-facing concept (it drives ``CreativeDirection``
emphasis), not the same idea. Introducing ``NarrativeObjective`` is
the same kind of call ADOS-M3.1 made for its own ``Action``/``Target``
enums: a small, closed, demonstrably-used vocabulary, not a duplicate of
something that already exists. ``sell``/``educate`` from the master
prompt's own list are folded into ``persuade``/``explain`` respectively
— distinct English words, not a distinct communication objective.
"""

from __future__ import annotations

from enum import Enum

from brand.creative.direction import Audience

__all__ = [
    "Audience",
    "NarrativeObjective",
    "SectionRole",
    "SectionPriority",
    "Requirement",
    "Relevance",
    "Tone",
    "NarrativeVoice",
    "MissingImpact",
    "ExclusionReason",
    "NarrativeIssueType",
    "NarrativeCompression",
]


class NarrativeObjective(str, Enum):
    """What the document is fundamentally trying to do — ADOS-M3.3 §6."""

    INTRODUCE = "introduce"
    EXPLAIN = "explain"
    PERSUADE = "persuade"
    DOCUMENT = "document"
    PRESENT = "present"
    COMPARE = "compare"
    SUMMARIZE = "summarize"
    DEMONSTRATE = "demonstrate"


class SectionRole(str, Enum):
    """The rhetorical purpose one narrative section plays — ADOS-M3.3
    §11's own list, verbatim. This is deliberately not
    ``brand.content.model.BlockRole`` (context/problem/intervention/
    outcome/evidence/detail/provenance): that enum names a single
    *ContentBlock's* role inside an already-composed page, a physical-
    composition-layer concept; this one names a whole *section's*
    rhetorical purpose in a pre-layout narrative plan. The two overlap
    in a few names because both are, at bottom, rhetorical vocabulary —
    that overlap does not make them the same field."""

    OPENING = "opening"
    CONTEXT = "context"
    PROBLEM = "problem"
    QUESTION = "question"
    CONCEPT = "concept"
    STRATEGY = "strategy"
    ANALYSIS = "analysis"
    DEVELOPMENT = "development"
    EVIDENCE = "evidence"
    COMPARISON = "comparison"
    RESULT = "result"
    IMPACT = "impact"
    TECHNICAL_EXPLANATION = "technical_explanation"
    CONCLUSION = "conclusion"
    CALL_TO_ACTION = "call_to_action"
    CLOSING = "closing"


class SectionPriority(str, Enum):
    """Semantic importance, never visual hierarchy — ADOS-M3.3 §16.
    M3.4 reads this to decide what should visually dominate; M3.3 itself
    names no font size, position, or page."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUPPORTING = "supporting"
    OPTIONAL = "optional"


class Requirement(str, Enum):
    """Whether a section (or a piece of content it wants) is load-
    bearing — ADOS-M3.3 §17. Missing ``optional``/``recommended``
    content must never block an otherwise-valid plan."""

    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class Relevance(str, Enum):
    """How relevant a section is to the stated audience — ADOS-M3.3
    §10/§12's own worked example (``audience_relevance: high``). A
    three-step scale, not a float: the master prompt's own example uses
    a word, and a manufactured two-decimal precision here would claim
    a confidence this system does not have."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Tone(str, Enum):
    """Communication intent, never typography — ADOS-M3.3 §29's own
    list, verbatim."""

    PRECISE = "precise"
    CONFIDENT = "confident"
    RESTRAINED = "restrained"
    TECHNICAL = "technical"
    EDITORIAL = "editorial"
    PERSUASIVE = "persuasive"
    ACADEMIC = "academic"
    ACCESSIBLE = "accessible"


class NarrativeVoice(str, Enum):
    """ADOS-M3.3 §30. No existing ADOS vocabulary names narrative voice,
    so this is new, and kept to the master prompt's own five values."""

    FIRST_PERSON_STUDIO = "first_person_studio"
    THIRD_PERSON = "third_person"
    NEUTRAL = "neutral"
    EDITORIAL = "editorial"
    TECHNICAL = "technical"


class MissingImpact(str, Enum):
    """How much a piece of missing ContentIntelligenceModel information
    actually matters to *this* narrative — ADOS-M3.3 §18. Distinct from
    M3.2's ``MissingInformation`` itself (which only records that
    something is unknown, not how much any particular narrative would
    miss it)."""

    BLOCKING = "blocking"
    IMPORTANT = "important"
    OPTIONAL = "optional"
    IRRELEVANT = "irrelevant"


class ExclusionReason(str, Enum):
    """Why the narrative planner deliberately left something out —
    ADOS-M3.3 §19's own bullet list."""

    UNSUPPORTED_CLAIM = "unsupported_claim"
    CONFLICTING_METRIC = "conflicting_metric"
    IRRELEVANT_DETAIL = "irrelevant_detail"
    INTERNAL_ONLY = "internal_only"
    OBSOLETE_VERSION = "obsolete_version"
    OTHER = "other"


class NarrativeIssueType(str, Enum):
    """ADOS-M3.3 §20's own example (``conflicting_information``) plus
    the other cases a narrative plan must be able to flag rather than
    silently absorb."""

    CONFLICTING_INFORMATION = "conflicting_information"
    UNSUPPORTED_CLAIM_OMITTED = "unsupported_claim_omitted"
    INSUFFICIENT_CONTENT_FOR_THESIS = "insufficient_content_for_thesis"
    LOW_CONTENT_COVERAGE = "low_content_coverage"


class NarrativeCompression(str, Enum):
    """ADOS-M3.3 §22 — variable narrative depth, explicitly never page
    count (that belongs to M3.4)."""

    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

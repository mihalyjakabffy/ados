"""
brand/llm/content/vocabulary.py

The closed vocabularies ADOS-M3.2 §5/§7 ask for. Kept separate from
``model.py`` for the same reason ``brand.llm.vocabulary`` is separate
from ``brand.llm.semantic_intent`` — a vocabulary changes for different
reasons than the shapes built from it.
"""

from __future__ import annotations

from enum import Enum


class EntityType(str, Enum):
    """ADOS-M3.2 §5's own list — a closed set because a composer, and
    later M3.3, switches on it. Not exhaustive of every noun a project
    document could mention; exhaustive of the ones this milestone's
    extraction pipeline is asked to recognise."""

    PROJECT = "project"
    BUILDING = "building"
    SITE = "site"
    CLIENT = "client"
    ARCHITECT = "architect"
    ORGANIZATION = "organization"
    LOCATION = "location"
    PERSON = "person"
    MATERIAL = "material"
    SPACE = "space"
    PROGRAM = "program"
    PHASE = "phase"


class SourceType(str, Enum):
    """ADOS-M3.2 §4's source hierarchy. Order here is declaration order,
    not authority order — authority is a property of the *source*
    (``Source.trust_level``, set at resolution time from real facts
    about where it came from), never inferred from the enum's position."""

    PROJECT_STATE = "project_state"
    PROJECT_METADATA = "project_metadata"
    STRUCTURED_PROJECT_DATA = "structured_project_data"
    UPLOADED_DOCUMENT = "uploaded_document"
    UPLOADED_IMAGE = "uploaded_image"
    ADOS_DOCUMENT = "ados_document"
    BRAND_CONTEXT = "brand_context"
    DESIGN_STATE = "design_state"
    USER_STATEMENT = "user_statement"
    LLM_INFERENCE = "llm_inference"


class FactStatus(str, Enum):
    """ADOS-M3.2 §7. A status is never inferred from confidence alone
    (§22) — it is set by the extraction/resolution pipeline from what is
    actually known about a value's sourcing, and validated
    independently of any confidence number attached to it.

    ``MISSING`` exists for schema completeness with §7's own list, but
    this package's resolution pipeline never constructs a ``Fact`` with
    this status — an absent value is represented as a
    :class:`~brand.llm.content.model.MissingInformation` entry instead
    (see that model's own docstring for why a "fact with no value" is
    the wrong shape for "we don't have this").
    """

    VERIFIED = "verified"
    INFERRED = "inferred"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"
    CONFLICTING = "conflicting"


#: Statuses that assert something is true (as opposed to merely absent) —
#: every item carrying one of these must have real provenance. This is
#: the set brand.llm.content.validation's hallucination guard checks.
TRUTH_BEARING_STATUSES: frozenset[FactStatus] = frozenset({
    FactStatus.VERIFIED, FactStatus.INFERRED, FactStatus.AMBIGUOUS, FactStatus.CONFLICTING,
})

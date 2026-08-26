"""
brand/llm/vocabulary.py

The controlled vocabulary ADOS-M3.1 §5 asks for. Three closed
enumerations (``Action``, ``Target``, ``SemanticField``) plus one
resolver function — nothing here is a second document-type registry.
``document_type`` is deliberately *not* one of these closed enums: it
resolves against ``brand.project.document_types.DOCUMENT_TYPES``, the
one canonical registry, so a new Document Type added there (as pure
data, per ADOS-M2.5) needs no change here to become a valid semantic
target.
"""

from __future__ import annotations

from enum import Enum


class Action(str, Enum):
    """What the user wants done. ADOS-M3.1 §5."""

    CREATE = "create"
    MODIFY = "modify"
    REGENERATE = "regenerate"
    REVISE = "revise"
    EXTEND = "extend"
    SUMMARIZE = "summarize"
    TRANSFORM = "transform"
    COMPARE = "compare"
    REVIEW = "review"


class Target(str, Enum):
    """What the action is pointed at. ADOS-M3.1 §5.

    Deliberately includes both structural targets (document, project,
    section, page, brand, content) and a handful of the names a user
    would actually say (presentation, portfolio, report, template) —
    the master prompt lists both. Where one of the latter also names a
    real ``document_type`` in the registry, ``document_type`` carries
    the precise value; ``target`` stays the coarser "what kind of
    thing is this about" signal.
    """

    DOCUMENT = "document"
    PROJECT = "project"
    SECTION = "section"
    PAGE = "page"
    BRAND = "brand"
    CONTENT = "content"
    PRESENTATION = "presentation"
    PORTFOLIO = "portfolio"
    REPORT = "report"
    TEMPLATE = "template"


class SemanticField(str, Enum):
    """Every field a :class:`~brand.llm.semantic_intent.SemanticIntent`
    can carry in its ``explicit``/``inferred`` buckets, and the only
    names ``ambiguous`` may name. Bounded on purpose (ADOS-M3.1 §4: "do
    not overdesign the schema") — each entry here has a demonstrated
    role in the master prompt's own worked examples (§14-§16) or its
    minimum-fields list (§4).
    """

    ACTION = "action"
    TARGET = "target"
    DOCUMENT_TYPE = "document_type"
    PURPOSE = "purpose"
    AUDIENCE = "audience"
    SUBJECT = "subject"
    STYLE_REFERENCE = "style_reference"
    BRAND_REFERENCE = "brand_reference"
    QUALITY_DIRECTION = "quality_direction"
    DESIGN_DIRECTION = "design_direction"
    CONTENT_REQUIREMENTS = "content_requirements"
    STYLE_REQUIREMENTS = "style_requirements"
    DESIGN_REQUIREMENTS = "design_requirements"
    CONSTRAINTS = "constraints"
    REFERENCES = "references"
    MODIFIERS = "modifiers"


#: Fields whose value is a list of free-text items rather than one string.
#: Kept as plain strings, not a second structured schema — ADOS-M3.1 §14
#: is explicit that page_count/font/grid/colour/layout do not belong in
#: M3.1's output at all, so there is nothing to structure yet.
LIST_VALUED_FIELDS: frozenset[SemanticField] = frozenset({
    SemanticField.CONTENT_REQUIREMENTS,
    SemanticField.STYLE_REQUIREMENTS,
    SemanticField.DESIGN_REQUIREMENTS,
    SemanticField.CONSTRAINTS,
    SemanticField.REFERENCES,
    SemanticField.MODIFIERS,
})

#: Fields whose value, when present, must be a member of a closed enum.
ENUM_VALUED_FIELDS: dict[SemanticField, type[Enum]] = {
    SemanticField.ACTION: Action,
    SemanticField.TARGET: Target,
}


def known_document_type_ids() -> frozenset[str]:
    """The one canonical registry (ADOS-M2.2/M2.5) — never duplicated."""
    from brand.project.document_types import DOCUMENT_TYPES

    return frozenset(DOCUMENT_TYPES)

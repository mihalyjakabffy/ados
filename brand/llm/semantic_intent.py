"""
brand/llm/semantic_intent.py

``SemanticIntent`` — the domain-level representation ADOS-M3.1 §4 asks
for. It describes what a user wants, not how ADOS will execute it: no
coordinate, no colour, no font, no page count, no CommandIntent — the
same "an intent may never carry a geometry or Brand value" discipline
``brand.creative.intent.CommandIntent`` already enforces one layer down,
applied here one layer up, before natural language has even become a
CommandIntent's business.

Preserving user meaning (ADOS-M3.1 §6) is the one structural idea this
module encodes: every field lives in exactly one of three buckets —

* ``explicit``   — what the user directly said.
* ``inferred``   — what was inferred from context, and could be wrong.
* ``ambiguous``  — what could not be safely resolved at all.

A field never appears in more than one bucket (enforced below); a
downstream reader that only calls :meth:`SemanticIntent.resolved` without
checking :meth:`SemanticIntent.is_explicit` cannot silently treat an
inference as a user requirement, because there is no single "the value"
accessor that hides which bucket it came from.

This model is also the JSON-schema source for the LLM's structured
output (``brand.llm.providers.claude_provider`` passes it straight to
``client.messages.parse(output_format=SemanticIntent)``) — one
definition, not two, matching ``brand/schemas/brand_schema.py``'s own
"generated from the model, not hand-duplicated" principle.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brand.llm.vocabulary import SemanticField

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Bumped when the shape changes in a way a stored trace would notice —
#: brand/schemas/brand_schema.py's SCHEMA_VERSION convention.
SCHEMA_VERSION = "3.1"


class SemanticFieldValues(BaseModel):
    """One bucket's worth of values — every field ADOS-M3.1 §4/§5 names,
    all optional, because a bucket only holds what actually landed in it.

    List-valued fields (``content_requirements`` and friends) stay plain
    strings, not a second structured schema: ADOS-M3.1 §14 is explicit
    that page count, font, grid, colour and layout do not belong in this
    milestone's output at all, so there is nothing yet to give them
    structure beyond "a requirement the user stated in their own words".
    """

    model_config = _Frozen

    action: Optional[str] = None
    target: Optional[str] = None
    document_type: Optional[str] = None
    purpose: Optional[str] = None
    audience: Optional[str] = None
    subject: Optional[str] = None
    style_reference: Optional[str] = None
    brand_reference: Optional[str] = None
    quality_direction: Optional[str] = None
    design_direction: Optional[str] = None
    content_requirements: tuple[str, ...] = ()
    style_requirements: tuple[str, ...] = ()
    design_requirements: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    modifiers: tuple[str, ...] = ()

    def get(self, field: SemanticField) -> Any:
        return getattr(self, field.value)

    def set_fields(self) -> frozenset[SemanticField]:
        """Which fields actually carry a value in this bucket."""
        out = set()
        for field in SemanticField:
            value = self.get(field)
            if value not in (None, (), ""):
                out.add(field)
        return frozenset(out)


class SemanticIntent(BaseModel):
    """A typed representation of what a user wants ADOS to do — not a
    decision about how. ADOS-M3.1's entire architectural boundary is
    that nothing downstream of this model is reached automatically: no
    CommandIntent, no Composer call, no state mutation (see this
    package's own docstring).
    """

    model_config = _Frozen

    schema_version: str = SCHEMA_VERSION
    explicit: SemanticFieldValues = Field(default_factory=SemanticFieldValues)
    inferred: SemanticFieldValues = Field(default_factory=SemanticFieldValues)
    #: Field names that could not be safely resolved into either bucket
    #: above — ADOS-M3.1 §6's "represent uncertainty explicitly" rather
    #: than silently defaulting. A field named here carries no value in
    #: ``explicit`` or ``inferred`` (enforced below).
    ambiguous: tuple[SemanticField, ...] = ()
    #: Why each ambiguous field could not be resolved — human-readable,
    #: shown verbatim in the developer inspection view. Not required for
    #: every ambiguous field (a bare "audience: unknown" is still valid),
    #: but every key here must itself be one of ``ambiguous``. Plain
    #: ``str`` keys, not ``SemanticField`` — an enum-keyed dict schema
    #: needs JSON Schema's ``propertyNames``, a keyword structured-output
    #: engines are not reliably guaranteed to support; membership is
    #: checked in ``_no_field_in_two_places`` instead.
    ambiguity_notes: dict[str, str] = Field(default_factory=dict)
    #: Overall extraction confidence, 0..1 — one number for the whole
    #: intent, not per-field: a per-field confidence score for sixteen
    #: mostly-empty fields is precision the schema does not need yet.
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _no_field_in_two_places(self) -> "SemanticIntent":
        explicit_fields = self.explicit.set_fields()
        inferred_fields = self.inferred.set_fields()
        ambiguous_fields = set(self.ambiguous)

        overlap_ei = explicit_fields & inferred_fields
        if overlap_ei:
            raise ValueError(
                f"field(s) {sorted(f.value for f in overlap_ei)} set in both "
                f"explicit and inferred — a field is one or the other, never both"
            )
        overlap_ea = (explicit_fields | inferred_fields) & ambiguous_fields
        if overlap_ea:
            raise ValueError(
                f"field(s) {sorted(f.value for f in overlap_ea)} carry a value "
                f"and are also listed as ambiguous — ambiguous means no value "
                f"was resolved, not a low-confidence one"
            )
        note_fields: set[str] = set()
        for key in self.ambiguity_notes:
            try:
                note_fields.add(SemanticField(key))
            except ValueError as exc:
                raise ValueError(
                    f"ambiguity_notes key {key!r} is not a known SemanticField"
                ) from exc
        unnoted = note_fields - ambiguous_fields
        if unnoted:
            raise ValueError(
                f"ambiguity_notes name field(s) {sorted(f.value for f in unnoted)} "
                f"that are not listed in ambiguous"
            )
        return self

    # ------------------------------------------------------------------
    # Reading an intent without caring which bucket a field came from
    # ------------------------------------------------------------------

    def resolved(self, field: SemanticField) -> Any:
        """Explicit wins, then inferred, else ``None``. Callers that need
        to know *whether* a value was stated or guessed must use
        :meth:`is_explicit` / :meth:`is_inferred` / :meth:`is_ambiguous`
        instead — this accessor exists for code that only needs a value
        to act on, e.g. rendering a debug summary."""
        value = self.explicit.get(field)
        if value not in (None, (), ""):
            return value
        return self.inferred.get(field)

    def is_explicit(self, field: SemanticField) -> bool:
        return field in self.explicit.set_fields()

    def is_inferred(self, field: SemanticField) -> bool:
        return field in self.inferred.set_fields()

    def is_ambiguous(self, field: SemanticField) -> bool:
        return field in self.ambiguous

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

"""
brand/llm/context.py

The context supplied to the LLM (ADOS-M3.1 §7) — and nothing this
package invents. Every field on :class:`SemanticContext` is built from a
real, already-existing domain object the caller actually has in hand
(``Project``, ``Brand``, ``DesignState``, the Document Type registry);
none of it is fetched, guessed, or padded out to look more complete than
it is. Retrieving arbitrary project data on the LLM's behalf is
explicitly M3.2's job (ADOS-M3.1 §7), not this module's.

``build_semantic_context`` is the one way to construct a
:class:`SemanticContext` — every argument is optional because a request
with no project, no brand and no design state open ("Create a
portfolio...") is a completely ordinary M3.1 input, not an error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, ConfigDict, Field

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Bumped when the shape of what gets sent to the LLM changes — recorded
#: on every trace (ADOS-M3.1 §19's "input_context_version").
CONTEXT_VERSION = "3.1"

if TYPE_CHECKING:
    from brand.design_state.model import DesignState
    from brand.models.brand import Brand
    from brand.project.model import Project


class ConversationTurn(BaseModel):
    """One prior turn, verbatim. No summarisation, no truncation beyond
    what the caller already applied — this module does not rewrite
    history, only carries it."""

    model_config = _Frozen

    role: str = Field(pattern=r"^(user|assistant)$")
    text: str


class DocumentTypeSummary(BaseModel):
    """The parts of a registry entry that matter to intent extraction —
    not the full ``DocumentType`` (default_structure, requirements etc.
    are composition-time detail, out of scope for "what does the user
    want")."""

    model_config = _Frozen

    id: str
    name: str
    description: str
    audience: str
    purpose: str


class SemanticContext(BaseModel):
    """Everything real that was known when a request was interpreted.

    ``context_version`` is :data:`CONTEXT_VERSION` at build time, not a
    fixed default — a trace recorded under an older shape stays
    self-describing even after this module changes.
    """

    model_config = _Frozen

    context_version: str = CONTEXT_VERSION
    request: str
    project_context: Optional[dict[str, Any]] = None
    brand_context: Optional[dict[str, Any]] = None
    design_state_context: Optional[dict[str, Any]] = None
    available_document_types: tuple[DocumentTypeSummary, ...] = ()
    available_capabilities: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    conversation_context: tuple[ConversationTurn, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def _project_context(project: "Project") -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "project_data": dict(project.project_data),
        "document_count": len(project.documents),
        "document_type_ids": sorted({d.document_type_id for d in project.documents if d.document_type_id}),
    }


def _brand_context(brand: "Brand") -> dict[str, Any]:
    return {
        "id": str(brand.brand_id),
        "name": brand.identity.name,
        "descriptor": brand.identity.descriptor,
        "personality": [axis.value for axis in brand.identity.personality],
        "tone": brand.communication.tone.value,
    }


def _design_state_context(design_state: "DesignState") -> dict[str, Any]:
    return {
        "project_id": design_state.project.id,
        "document_id": design_state.document.id,
        "output_type": design_state.document.output_type,
        "audience": design_state.document.audience,
        "purpose": design_state.document.purpose,
        "page_count": len(design_state.pages),
        "version_number": design_state.version.number,
    }


def _available_document_types() -> tuple[DocumentTypeSummary, ...]:
    from brand.project.document_types import DOCUMENT_TYPES

    return tuple(
        DocumentTypeSummary(
            id=dt.id, name=dt.name, description=dt.description,
            audience=dt.audience, purpose=dt.purpose,
        )
        for dt in sorted(DOCUMENT_TYPES.values(), key=lambda d: d.id)
    )


def _available_capabilities() -> dict[str, tuple[str, ...]]:
    from brand.llm.vocabulary import Action, Target

    return {
        "actions": tuple(a.value for a in Action),
        "targets": tuple(t.value for t in Target),
    }


def build_semantic_context(
    request: str,
    *,
    project: Optional["Project"] = None,
    brand: Optional["Brand"] = None,
    design_state: Optional["DesignState"] = None,
    conversation: tuple[ConversationTurn, ...] = (),
) -> SemanticContext:
    """Assemble a :class:`SemanticContext` from whatever real state the
    caller actually has. ``available_document_types`` and
    ``available_capabilities`` are always populated — they are the
    registry and the vocabulary, not situational data, so there is
    nothing conditional about including them."""

    return SemanticContext(
        request=request,
        project_context=_project_context(project) if project is not None else None,
        brand_context=_brand_context(brand) if brand is not None else None,
        design_state_context=_design_state_context(design_state) if design_state is not None else None,
        available_document_types=_available_document_types(),
        available_capabilities=_available_capabilities(),
        conversation_context=conversation,
    )

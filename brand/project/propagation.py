"""
brand/project/propagation.py

ADOS-M4.3 — the fan-out this repository was missing between "a shared
fact changed" and "every document that carries it reflects that"
(docs/architecture/m4-claude-connector.md §6). Not a new engine: every
recompose here calls the exact same ``compose()``/``evaluate()``
``api/routers/ados_project.py``'s own ``compose_document`` endpoint
already calls, run in a loop over ``Project.documents`` instead of one
document at a time. This module becomes the second, explicitly-listed
authorised caller of those two functions, alongside
``api/routers/ados_project.py`` itself and ``brand/llm/loop/execution.py``
(``tests_brand/test_loop_boundaries.py`` already checks the latter;
``tests_mcp``'s own boundary suite checks that nothing under
``ados_mcp/`` calls either directly — this module is where that
authority actually lives).

Two entry points, one shared recompose step:

``propagate_content_change`` — a shared ``ContentItem`` changed (or was
removed); recompose every ``Document`` in the project whose own content
or ``content_selection`` references it. Documents that don't reference
the item are left alone and reported as such, never touched.

``propagate_brand_change`` — the project's brand moved to a new,
immutable version (``Brand.bump()`` is the only way a brand changes at
all, per ``brand/README.md`` Rule 5); every document in the project
shares that one brand, so every document is recomposed.

Neither function does any repository I/O — both take an already-loaded
``Project`` and ``Brand`` and return a new ``Project`` for the caller to
persist, the same "pure domain logic, I/O stays in the router" split
``brand/project/versioning.py`` already keeps. Neither saves a Version:
recomposing refreshes each document's cached ``latest_plan``/
``latest_evaluation`` exactly as ``compose_document`` already does, and
leaves the decision to keep an immutable snapshot to an explicit
``save_version`` call per document — propagation is not a silent,
automatic versioning event any more than a single compose is.

**Deliberate deviation from ``compose_document``'s own precondition,
stated honestly**: a single-document compose treats "no content" as a
hard 422 — the caller asked for exactly this document. A fan-out over
many documents must not abort the whole batch because one of them
happens to be an empty scaffold; that document is instead reported as
``recomposed=False, reason="no_content"`` and the rest proceed. This is
the one place this module's behaviour differs from the endpoint it
otherwise mirrors, and it differs for a stated reason, not by accident.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from brand.creative.composer import CompositionError, compose
from brand.creative.directions import get_direction
from brand.creative.evaluate import evaluate
from brand.project.content_resolution import resolve_document_content

if TYPE_CHECKING:
    from brand.models.brand import Brand
    from brand.project.model import Document, Project


def _now() -> _dt.datetime:
    """A local, independent copy of ``brand.project.model``'s own
    ``_now`` — a two-line helper duplicated rather than imported across
    module-private boundaries, the same posture
    ``brand.project.store``'s ``_atomic_write_text`` docstring already
    argues for between independent siblings under ``brand/``."""
    return _dt.datetime.now(_dt.timezone.utc)


@dataclass(frozen=True)
class DocumentPropagationResult:
    """What happened to one document during a propagation run."""

    document_id: str
    document_name: str
    recomposed: bool
    #: Set only when ``recomposed`` is False — "no_content" or
    #: "composition_infeasible: <detail>", the same two failure modes
    #: ``compose_document`` itself can hit, named the same way.
    reason: str = ""
    findings: tuple[dict, ...] = field(default_factory=tuple)
    requirement_findings: tuple[dict, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PropagationResult:
    """The outcome of one fan-out run. ``project`` is ready to persist
    (``_repo().save(result.project)``) — nothing here writes to storage
    itself."""

    project: "Project"
    touched: tuple[DocumentPropagationResult, ...]
    #: Document ids that don't reference the changed item and were left
    #: completely alone. Always empty for propagate_brand_change, since
    #: every document in a project shares its one brand.
    unaffected: tuple[str, ...] = field(default_factory=tuple)


def _references_item(document: "Document", item_id: str) -> bool:
    if item_id in document.content_selection:
        return True
    return any(item.id == item_id for item in document.content_items)


def _recompose_one(
    document: "Document", project: "Project", brand: "Brand"
) -> tuple["Document", DocumentPropagationResult]:
    """The exact compose→evaluate→check_requirements sequence
    ``api/routers/ados_project.py::compose_document`` runs for one
    document, factored out so both propagation entry points call it
    identically — a fan-out over this, not a reimplementation of it."""
    from brand.project.requirements import check_requirements

    direction = get_direction(document.direction_id)
    content = resolve_document_content(document, project)
    if not content.blocks:
        return document, DocumentPropagationResult(
            document_id=document.id, document_name=document.name,
            recomposed=False, reason="no_content",
        )

    try:
        plan = compose(content, direction, brand)
    except CompositionError as exc:
        return document, DocumentPropagationResult(
            document_id=document.id, document_name=document.name,
            recomposed=False, reason=f"composition_infeasible: {exc}",
        )

    evaluation = evaluate(plan, direction, brand.resolve_tokens())
    new_document = document.model_copy(update={
        "latest_plan": plan.to_dict(),
        "latest_evaluation": evaluation.to_dict(),
        "updated_at": _now(),
    })
    requirement_findings = check_requirements(new_document, project)
    return new_document, DocumentPropagationResult(
        document_id=new_document.id, document_name=new_document.name, recomposed=True,
        findings=tuple(f.to_dict() for f in evaluation.report.findings),
        requirement_findings=tuple(f.to_dict() for f in requirement_findings),
    )


def propagate_content_change(project: "Project", brand: "Brand", changed_item_id: str) -> PropagationResult:
    """Recompose every document in ``project`` whose own content or
    ``content_selection`` references ``changed_item_id`` — the shared
    item may have just been edited (removed and re-added, until
    ADOS-M4.3's own follow-up adds a real in-place update — see
    ``ados_mcp/tools/content.py``'s docstring) or removed outright, in
    which case every referencing document picks up the same fail-soft
    "dangling reference, skipped" behaviour ``resolve_document_content``
    already has for a single compose.

    ``brand`` must be the project's own attached brand, already resolved
    by the caller — this function does no repository lookups. Raising on
    a missing brand is the caller's job (the same ``no_brand_attached``
    precondition ``compose_document`` already enforces), not this one's.
    """
    documents = list(project.documents)
    touched: list[DocumentPropagationResult] = []
    unaffected: list[str] = []

    for index, document in enumerate(documents):
        if not _references_item(document, changed_item_id):
            unaffected.append(document.id)
            continue
        new_document, result = _recompose_one(document, project, brand)
        documents[index] = new_document
        touched.append(result)

    updated_project = project.model_copy(update={"documents": tuple(documents), "updated_at": _now()})
    return PropagationResult(project=updated_project, touched=tuple(touched), unaffected=tuple(unaffected))


def propagate_brand_change(project: "Project", new_brand: "Brand") -> PropagationResult:
    """Point ``project`` at ``new_brand``'s version and recompose every
    one of its documents against it — brands stay immutable per
    published version (``brand/README.md`` Rule 5), so "the palette
    changed" is always "``Brand.bump()`` to a new version somewhere
    else, then propagate", never an in-place edit of an issued brand.

    ``new_brand`` must already be the same ``brand_id`` as
    ``project.brand_id`` — the caller (the one place with repository
    access to resolve "the brand this project points at") is
    responsible for that check; this function only moves the pointer
    and recomposes.
    """
    updated_project = project.model_copy(update={"brand_version": new_brand.version})
    documents = list(updated_project.documents)
    touched: list[DocumentPropagationResult] = []

    for index, document in enumerate(documents):
        new_document, result = _recompose_one(document, updated_project, new_brand)
        documents[index] = new_document
        touched.append(result)

    updated_project = updated_project.model_copy(update={"documents": tuple(documents), "updated_at": _now()})
    return PropagationResult(project=updated_project, touched=tuple(touched), unaffected=())

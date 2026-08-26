"""
brand/project/content_resolution.py

The one place a Document's *composable* content is resolved from wherever
it actually lives — ADOS-M2.5's promotion of content out of any single
Document (a design-state-centric architecture cannot let two projections
of the same project silently diverge because each kept a private copy of
"the project description").

This is a straight extraction, not new behaviour: through ADOS-M2.2.1 this
logic lived as a private function inside ``api/routers/ados_project.py``
(``_document_content_model``) — domain logic sitting in the HTTP layer,
which is exactly the kind of accidental coupling M2.5's dependency
direction (Project Data -> DesignState -> Projection -> Composer) exists
to remove. Moving it here changes nothing about what it computes; it
changes who is allowed to depend on it (``brand/design_state/build.py``
now does too, without duplicating a byte of it) — and, just as important,
this module does not import the router back. Resolving a *referenced*
project (Portfolio's ``project_refs``) needs a project store, but which
store — which storage root, which test's tmp_path — is a concern of
whoever calls this function, not of the resolution logic itself; so the
lookup is injected as a plain callable rather than this module
constructing its own ``FileProjectRepository`` and silently disagreeing
with the caller's (a real bug class: the router's storage root is
monkeypatched per-test, a second, independently-constructed repository
here would not see that and would read/write the wrong directory).

Three content sources are merged, in this order:

1. The document's own ``content_items`` — private, unshared, exactly
   M2.1's original shape.
2. The document's ``content_selection`` — ids into the *project's* own
   shared ``content_items`` pool (ADOS-M2.5 §6). Two documents that both
   select the same shared item are, semantically, presenting the same
   fact — editing the shared item changes what every selecting document
   composes next, the same "reference, not a copy" guarantee
   ADOS-M2.2 §10 already established for Portfolio's ``project_refs``.
3. ``project_refs`` — unchanged from M2.2: other *projects'* own content,
   pulled in live as a portfolio chapter.

A dangling id in ``content_selection`` (the shared item was deleted after
being selected) is skipped rather than raised — the same fail-soft
posture ``project_refs`` already takes on a since-deleted referenced
project, and for the same reason: a stale reference is a fact for the
Requirements Engine to surface, not a 500.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from brand.content.model import ContentModel

if TYPE_CHECKING:
    from brand.project.model import Document, Project

#: id -> the Project it names, or None/raises if it no longer exists. The
#: caller's own store, injected — see the module docstring for why this
#: is never constructed in here.
ProjectResolver = Callable[[str], Optional["Project"]]


def resolve_document_content(
    document: "Document", project: "Project", *, resolve_project: Optional[ProjectResolver] = None,
) -> ContentModel:
    """The real ``ContentModel`` to compose ``document`` against.

    ``resolve_project`` is only consulted when ``document.project_refs``
    is non-empty (Portfolio-style documents); every other document never
    needs it and callers with no project store handy (a unit test
    constructing ``Document``/``Project`` in memory) may omit it freely.
    """
    from brand.project.model import ContentItem, ContentItemKind
    from brand.project.model import Document as _Document

    shared_by_id = {item.id: item for item in project.content_items}
    selected = tuple(
        shared_by_id[item_id] for item_id in document.content_selection if item_id in shared_by_id
    )
    working = document.model_copy(update={"content_items": document.content_items + selected})
    content = working.content_model(project.name)

    if not document.project_refs:
        return content

    counters: dict[str, int] = {}
    blocks = list(content.blocks)
    for block in blocks:
        stem = block.id.split("-")[0]
        counters[stem] = max(counters.get(stem, 0), int(block.id.split("-")[1]))

    for ref_id in document.project_refs:
        ref_project = None
        if resolve_project is not None:
            try:
                ref_project = resolve_project(ref_id)
            except Exception:                                  # noqa: BLE001
                ref_project = None
        if ref_project is None:
            continue                                            # surfaced by PORT-003-style checks, not a 500

        items = tuple(item for d in ref_project.documents for item in d.content_items)
        if not items:
            items = (ContentItem(
                kind=ContentItemKind.TEXT,
                text=ref_project.description or f"{ref_project.name}.",
            ),)
        chapter = _Document(project_id=ref_project.id, name=ref_project.name, content_items=items)
        for block in chapter.content_model(ref_project.name).blocks:
            stem = block.id.split("-")[0]
            counters[stem] = counters.get(stem, 0) + 1
            blocks.append(block.model_copy(update={"id": f"{stem}-{counters[stem]:02d}"}))

    return content.model_copy(update={"blocks": tuple(blocks)})

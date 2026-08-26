"""
brand/project/versioning.py

Where a Version actually gets built, resolved and reconstructed —
extracted from ``api/routers/ados_project.py`` (ADOS-M2.5) for the same
reason ``content_resolution.py`` was: this is domain logic (what makes a
saved snapshot a true, reproducible Version), not an HTTP concern, and
``brand/design_state/build.py`` needs exactly the "resolve version N's
state" logic ADOS-M2.2.1's export pipeline already built — reused here
rather than reimplemented a second time.

No FastAPI import anywhere in this module. Every failure is a plain
domain exception; the router (or any future caller) decides what HTTP
status, if any, it deserves.

**Why content resolution belongs here too.** ADOS-M2.5 §6 made a
Document's content_items a *union* of its own private items and whatever
it has selected from the project's shared pool
(``brand.project.content_resolution``). The shared pool is mutable — a
practice can edit "the project description" tomorrow — so a Version
saved today must freeze the *resolved* union, not the selection ids, or
"what did the project look like at Version 7" would depend on what the
shared pool happens to say when you ask, which is not a version at all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from brand.creative.plan import PagePlan
    from brand.project.model import ContentItem, Document, Project, ProjectVersion


class VersionNotFoundError(LookupError):
    def __init__(self, version_number: int, project_id: str) -> None:
        self.version_number = version_number
        self.project_id = project_id
        super().__init__(f"no version {version_number} in project {project_id!r}")


class VersionDocumentMismatchError(ValueError):
    def __init__(self, version_number: int, document_id: str) -> None:
        self.version_number = version_number
        self.document_id = document_id
        super().__init__(
            f"version {version_number} belongs to a different document than {document_id!r}"
        )


class NoComposedPlanError(ValueError):
    """The document has never been composed — there is nothing to
    version, and no version can be auto-saved from nothing."""


class VersionHasNoPlanError(ValueError):
    """A version exists but was saved with no plan — ``ProjectVersion.plan``
    is ``Optional`` for a caller that wants to snapshot content ahead of
    ever composing; such a version cannot be exported or reconstructed
    into a ``PagePlan``."""


def resolve_full_content(document: "Document", project: "Project") -> tuple["ContentItem", ...]:
    """The document's own ``content_items``, plus its resolved
    ``content_selection`` from the project's shared pool — exactly what a
    Version snapshot must freeze. A dangling selection id (the shared
    item was deleted) is skipped, matching
    ``content_resolution.resolve_document_content``'s own fail-soft
    posture — a version should still be saveable from whatever state
    genuinely exists."""
    shared_by_id = {item.id: item for item in project.content_items}
    selected = tuple(
        shared_by_id[item_id] for item_id in document.content_selection if item_id in shared_by_id
    )
    return document.content_items + selected


def build_version(
    document: "Document", project: "Project", *, label: str = "", plan: Optional[dict] = None,
) -> "ProjectVersion":
    """A new, immutable ``ProjectVersion`` snapshot of ``document``'s
    current, fully-resolved state. ``plan`` defaults to the document's
    own cached ``latest_plan`` — the version should capture what was
    actually last reviewed, not force a silent recompose that could
    differ from what the user saw (unchanged from ADOS-M2.1)."""
    from brand.project.model import ProjectVersion

    resolved_plan = plan if plan is not None else document.latest_plan
    return ProjectVersion(
        number=project.next_version_number,
        label=label,
        document_id=document.id,
        document_name=document.name,
        direction_id=document.direction_id,
        document_type_id=document.document_type_id,
        sections=document.sections,
        content_items=resolve_full_content(document, project),
        plan=resolved_plan,
    )


def resolve_version(
    project: "Project", document: "Document", version_number: Optional[int],
) -> tuple["Project", "ProjectVersion"]:
    """The Version a version-scoped read (export, DesignState-at-version,
    ...) is tied to: the caller's own, already-saved one, or a freshly
    built one from the document's current state. "Export the current
    state" and "export version N" become the same operation once a
    version exists — the invariant ADOS-M2.2.1 §7 relies on for "Version
    N's output must not silently change."

    Returns ``(project, version)`` — ``project`` reflects the newly
    appended version when one had to be built; the caller still owns
    persisting it (alongside whatever else it is about to save, in one
    write).
    """
    if version_number is not None:
        version = next((v for v in project.versions if v.number == version_number), None)
        if version is None:
            raise VersionNotFoundError(version_number, project.id)
        if version.document_id != document.id:
            raise VersionDocumentMismatchError(version_number, document.id)
        return project, version

    if document.latest_plan is None:
        raise NoComposedPlanError(f"document {document.id!r} has not been composed yet")

    version = build_version(document, project)
    project = project.model_copy(update={"versions": project.versions + (version,)})
    return project, version


def plan_from_version(version: "ProjectVersion") -> "PagePlan":
    """Reconstruct the real ``PagePlan`` a Version snapshot names.
    ``PagePlan.to_dict()`` (what a Version actually stores) adds
    ``plan_hash`` as a derived, non-field key — ``PagePlan`` itself is
    ``extra="forbid"``, so that key has to come back off before
    ``model_validate`` or every read of a saved version would fail."""
    from brand.creative.plan import PagePlan

    if version.plan is None:
        raise VersionHasNoPlanError(f"version {version.number} has no plan")
    data = dict(version.plan)
    data.pop("plan_hash", None)
    return PagePlan.model_validate(data)


def snapshot_document_at_version(document: "Document", version: "ProjectVersion") -> "Document":
    """A Document-shaped snapshot of exactly what Version N held: its own
    content/structure/type/plan, plus the *current* document's metadata
    and project references (a ``ProjectVersion`` does not carry those —
    they are the document's brief and portfolio wiring, not its composed
    content). ``content_selection`` is cleared: ``version.content_items``
    is already the fully-resolved union ``resolve_full_content`` produced
    at save time, so re-applying a (possibly since-changed) selection on
    top of it would double-count or drift from what was actually saved.
    """
    return document.model_copy(update={
        "content_items": version.content_items,
        "content_selection": (),
        "sections": version.sections,
        "document_type_id": version.document_type_id,
        "direction_id": version.direction_id,
        "latest_plan": version.plan,
    })

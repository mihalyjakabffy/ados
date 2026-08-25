"""
brand/project/model.py

The Project domain (ADOS M2.1) — the product-level aggregate a real user
thinks in, sitting *above* the engine M1.0–M1.5 already built. Nothing
here is a second Brand, ContentModel, PagePlan or Composer: a
:class:`Project` names a Brand it uses (by id, resolved through the
existing ``brand.store``) and holds :class:`Document`\\ s, each of which
turns its own authored :class:`ContentItem`\\ s into a real
``brand.content.model.ContentModel`` — the exact, unmodified input the
existing Composer already accepts. A Document's "pages" are never
authored directly; they are read from whatever ``PagePlan`` the last real
``compose()``/``compose_scoped()`` call produced (``Document.latest_plan``),
because inventing pages the Composer did not produce would be exactly the
kind of fake capability this whole system refuses to ship.

**Content vs. ContentBlock.** A :class:`ContentItem` is what a person
enters — "the floor area is 1,200 m², from the architect's brief" — not
what the Composer sees. ``Document.content_model()`` is the one, real
translation from a set of ``ContentItem``s into a ``ContentModel``, with
the same validation (a metric needs provenance, a figure needs an aspect
ratio) the Composer has always enforced; there is no second, laxer
content representation hiding behind the product-friendly form.

**Versions vs. autosave.** M2.1 has no autosave loop — a ``Document`` is
simply the current, mutable state of one document's authored content and
its last composed plan. A :class:`ProjectVersion` is only ever created
when a person explicitly asks for one, and it is a full, immutable
snapshot (the content items, the direction, and the composed plan at that
moment) — restoring one is copying that snapshot back onto the live
Document, not replaying a command log.
"""

from __future__ import annotations

import uuid
from datetime import date as _date
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brand.content.model import BlockRole, BlockType, ContentBlock, ContentModel

_Frozen = ConfigDict(frozen=True, extra="forbid")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Assets — real files, minimally catalogued. Not a DAM.
# ---------------------------------------------------------------------------


class Asset(BaseModel):
    """One uploaded file, catalogued at the project level.

    ``path`` is relative to the project's own storage prefix — resolved by
    ``brand.project.store``, never assembled ad hoc by a caller, so an
    asset's file location is exactly as authoritative as a Brand's.

    ``width_px``/``height_px`` are the file's own real pixel dimensions,
    read once at upload time (``api/routers/ados_project.py``'s
    ``upload_asset``) — ``None`` for a non-raster upload (a PDF) or
    whenever the dimensions couldn't be read. ADOS-M2.2.1 P5's IMG-003
    check reads these rather than guessing resolution from ``size_bytes``:
    file size does not reliably predict pixel dimensions (compression
    varies too much to trust), so a check built on it would be exactly
    the kind of untrustworthy heuristic the master prompt refuses."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(default="", max_length=120)
    size_bytes: int = Field(ge=0)
    path: str = Field(min_length=1, max_length=400)
    width_px: Optional[int] = Field(default=None, ge=1)
    height_px: Optional[int] = Field(default=None, ge=1)
    uploaded_at: datetime = Field(default_factory=_now)


# ---------------------------------------------------------------------------
# Content — what a person enters, not what the Composer sees
# ---------------------------------------------------------------------------


class ContentItemKind(str, Enum):
    TEXT = "text"
    FACT = "fact"
    METRIC = "metric"
    IMAGE = "image"


#: Where a ContentItemKind lands in brand.content.model's closed vocabulary
#: — the one place this mapping is stated, reused by content_model() below
#: and by anything that needs to know it (never re-declared elsewhere).
_KIND_TO_BLOCK_TYPE: dict[ContentItemKind, BlockType] = {
    ContentItemKind.TEXT: BlockType.NARRATIVE,
    ContentItemKind.FACT: BlockType.FACT,
    ContentItemKind.METRIC: BlockType.METRIC,
    ContentItemKind.IMAGE: BlockType.IMAGE,
}
#: The 3-letter id stem brand.content.model.ContentBlock.id requires
#: (``^[a-z]{3}-\\d{2,3}$``), one per kind.
_KIND_TO_ID_STEM: dict[ContentItemKind, str] = {
    ContentItemKind.TEXT: "nar",
    ContentItemKind.FACT: "fct",
    ContentItemKind.METRIC: "met",
    ContentItemKind.IMAGE: "img",
}


class ContentItem(BaseModel):
    """One authored fact, in the shape a project form actually collects.

    Not every field applies to every ``kind`` — ``brand.content.model``'s
    own validators are the real, single source of truth for what a given
    kind requires; :meth:`Document.content_model` surfaces their errors
    rather than re-checking the same rules here.
    """

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    kind: ContentItemKind
    label: str = Field(default="", max_length=120)
    text: str = Field(default="", max_length=8000)
    value: float | str | None = None
    unit: str = Field(default="", max_length=24)
    provenance: str = Field(default="", max_length=200)
    asset_id: Optional[str] = None
    caption: str = Field(default="", max_length=400)
    aspect: str = Field(default="", max_length=10)


# ---------------------------------------------------------------------------
# Sections — organisational, not compositional (ADOS-M2.2)
# ---------------------------------------------------------------------------


class Section(BaseModel):
    """A named, ordered grouping of a Document's own ``ContentItem``s.

    The Composer never sees a Section — ``Document.content_model()``
    still emits one flat ``ContentModel``, walking sections in order and
    each section's own ``content_item_ids`` in order, exactly as M2.1's
    unsectioned documents always have. A Section exists so a
    :class:`~brand.project.document_types.DocumentType`'s
    ``required_sections`` has something concrete to check the presence of
    (``brand/project/requirements.py``), and so the Structure panel can
    show the skeleton the document was created with.

    ``kind`` is a free string rather than a closed enum on purpose — new
    document types are added as data
    (``brand/project/document_types.py``), and a Section's kind is
    whatever that type's ``default_structure`` names; a closed enum here
    would mean a code change for every new type, which is exactly the
    duplication M2.2 exists to prevent.
    """

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    kind: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=120)
    order: int = Field(ge=0)
    content_item_ids: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Decisions & Actions — the structured primitives Client Presentation (P3)
# and Internal Documentation (P4) both need, and only need once
# (ADOS-M2.2.1 §7 explicitly: "reuse an existing action/task model if one
# exists... do not build a project-management application"). No task model
# already existed in this codebase, so these are new, but deliberately the
# smallest shape that makes CLI-002/CLI-003/INT-001/INT-002 checkable: a
# status enum, a date, an owner — not effort, priority, dependencies or any
# other project-management field neither P3 nor P4 asked for.
# ---------------------------------------------------------------------------


class OptionStatus(str, Enum):
    PROPOSED = "proposed"
    RECOMMENDED = "recommended"
    REJECTED = "rejected"
    SELECTED = "selected"


class PresentationOption(BaseModel):
    """One option put to the client — Client Presentation's own content,
    not a generic list item. ``status`` is what CLI-001 reads: a
    presentation that lists options but marks none ``recommended`` or
    ``selected`` has not actually made the case it exists to make."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    status: OptionStatus = OptionStatus.PROPOSED


class Decision(BaseModel):
    """One decision, on a Client Presentation directly or inside a Meeting
    (``Meeting.decisions``) — the same shape either way, since a decision
    is a decision regardless of which document type recorded it.
    ``selected_option_id`` is optional (not every decision resolves a
    Client Presentation's options; a Meeting's decisions usually don't),
    but when set it must name a real option — CLI-002."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    selected_option_id: Optional[str] = None
    date: Optional[_date] = None


class ActionStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class ActionItem(BaseModel):
    """One action — Client Presentation's Next Steps, or one line in a
    Meeting's own action log. ``deadline`` is a real ``date`` field, not a
    free-text string: an invalid deadline is rejected by pydantic at the
    moment it is written, which is why INT-003 ("deadlines must be valid
    dates") is not a separate Requirements-Engine check — there is no
    document state in which an ActionItem could hold an unparseable
    deadline for a Finding to discover later."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    description: str = Field(min_length=1, max_length=400)
    responsible: str = Field(default="", max_length=120)
    deadline: Optional[_date] = None
    status: ActionStatus = ActionStatus.OPEN


class Participant(BaseModel):
    model_config = _Frozen

    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="", max_length=120)


class Meeting(BaseModel):
    """Internal Documentation's own record — a dated meeting with who was
    there, what was discussed, what was decided and what happens next.
    ``decisions``/``action_items`` reuse :class:`Decision`/:class:`ActionItem`
    directly rather than a Meeting-specific variant of either."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    title: str = Field(min_length=1, max_length=120)
    date: Optional[_date] = None
    location: str = Field(default="", max_length=200)
    participants: tuple[Participant, ...] = ()
    agenda: tuple[str, ...] = ()
    decisions: tuple[Decision, ...] = ()
    action_items: tuple[ActionItem, ...] = ()


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class Document(BaseModel):
    """One composable document inside a project.

    ``latest_plan`` is a cached ``PagePlan.to_dict()`` — a read-only
    reflection of the last real composition, exactly what the Canvas
    already renders. It is never hand-edited; only ``compose()`` /
    ``compose_scoped()`` (via the existing ``/compose`` and ``/intent``
    /``/iterate`` routes) ever produce a new one.

    ``document_type_id`` is ``""`` for an untyped, free-form document —
    exactly M2.1's shape, still fully supported — or a
    ``brand.project.document_types.DocumentType`` id, in which case
    ``sections`` normally mirrors that type's ``default_structure`` (the
    user may add, remove or reorder from there; ADOS-M2.2 §5 Step 5).

    ``project_refs`` is only meaningful for a document whose type has
    ``supports_multi_project`` (today, only Portfolio): the ids of other
    Projects this document draws on. Their content is never copied here —
    it is fetched live at compose time
    (``api/routers/ados_project.py``'s portfolio content assembly) — so
    editing a referenced project changes what the next composition of
    this document produces, which is the whole point of a reference
    rather than a copy (ADOS-M2.2 §10).

    ``metadata`` carries the document brief — subtitle, author, date,
    audience, purpose, desired length, language, instructions — as a
    plain bag rather than a dozen named optional fields, since which of
    them apply varies by document type and none of them affect
    composition (ADOS-M2.2 §2 lists Metadata itself as a shared
    primitive, not nine per-type schemas).

    ``presentation_options``/``decisions``/``action_items``/``meetings``
    are ADOS-M2.2.1 P3/P4's structured data — like ``project_refs``, they
    are generic fields any document could carry, but only Client
    Presentation (options/decisions/action_items) and Internal
    Documentation (meetings, which carry their own nested decisions and
    action_items) actually populate or check them
    (``brand/project/requirements.py``'s CLI-*/INT-* rules). None of them
    feed composition — the Composer still only ever sees ``content_items``.
    """

    model_config = _Frozen

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    name: str = Field(min_length=1, max_length=120)
    direction_id: str = Field(default="editorial-quiet", max_length=40)
    document_type_id: str = Field(default="", max_length=40)
    sections: tuple[Section, ...] = ()
    project_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_items: tuple[ContentItem, ...] = ()
    presentation_options: tuple[PresentationOption, ...] = ()
    decisions: tuple[Decision, ...] = ()
    action_items: tuple[ActionItem, ...] = ()
    meetings: tuple[Meeting, ...] = ()
    latest_plan: Optional[dict[str, Any]] = None
    latest_evaluation: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    def _ordered_content_items(self) -> tuple[ContentItem, ...]:
        """Section order, then item order within a section; anything not
        in any section is appended at the end, in its own stored order —
        never silently dropped."""
        if not self.sections:
            return self.content_items
        by_id = {item.id: item for item in self.content_items}
        seen: set[str] = set()
        ordered: list[ContentItem] = []
        for section in sorted(self.sections, key=lambda s: s.order):
            for item_id in section.content_item_ids:
                item = by_id.get(item_id)
                if item is not None and item_id not in seen:
                    ordered.append(item)
                    seen.add(item_id)
        for item in self.content_items:
            if item.id not in seen:
                ordered.append(item)
                seen.add(item.id)
        return tuple(ordered)

    def content_model(self, project_name: str) -> ContentModel:
        """The one real translation from authored content to what the
        Composer accepts. Raises ``pydantic.ValidationError`` with the
        Composer's own messages (a metric with no provenance, a figure
        with no aspect ratio) — this function does not soften them."""
        counters: dict[str, int] = {}
        blocks: list[ContentBlock] = []
        for item in self._ordered_content_items():
            stem = _KIND_TO_ID_STEM[item.kind]
            counters[stem] = counters.get(stem, 0) + 1
            block_id = f"{stem}-{counters[stem]:02d}"
            block_type = _KIND_TO_BLOCK_TYPE[item.kind]

            kwargs: dict[str, Any] = dict(
                id=block_id,
                type=block_type,
                role=BlockRole.CONTEXT,
                priority=3,
                provenance=item.provenance,
            )
            if item.kind is ContentItemKind.TEXT:
                kwargs["text"] = item.text
            elif item.kind is ContentItemKind.FACT:
                kwargs["label"] = item.label
                kwargs["value"] = item.value
            elif item.kind is ContentItemKind.METRIC:
                kwargs["label"] = item.label
                kwargs["value"] = item.value
                kwargs["unit"] = item.unit
            elif item.kind is ContentItemKind.IMAGE:
                kwargs["path"] = item.asset_id or ""
                kwargs["aspect"] = item.aspect
                kwargs["caption"] = item.caption

            blocks.append(ContentBlock(**kwargs))

        return ContentModel(
            project_id=uuid.UUID(self.project_id) if _looks_like_uuid(self.project_id) else uuid.uuid5(uuid.NAMESPACE_URL, self.project_id),
            project_name=project_name,
            blocks=tuple(blocks),
        )

    def section_by_kind(self, kind: str) -> Optional["Section"]:
        for section in self.sections:
            if section.kind == kind:
                return section
        return None


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Versions — explicit, immutable, never confused with autosave
# ---------------------------------------------------------------------------


class ProjectVersion(BaseModel):
    model_config = _Frozen

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int = Field(ge=1)
    label: str = Field(default="", max_length=120)
    document_id: str
    document_name: str
    direction_id: str
    document_type_id: str = ""
    sections: tuple[Section, ...] = ()
    content_items: tuple[ContentItem, ...]
    plan: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=_now)


# ---------------------------------------------------------------------------
# Export — a production artifact, always tied to one immutable Version
# ---------------------------------------------------------------------------


class ExportStatus(str, Enum):
    """ADOS-M2.2.1 §9. ``READY``/``EXPORTING`` are transient states a
    synchronous export never actually persists in — this pipeline renders
    inline within the request, so a saved ``Export`` record is always
    already ``COMPLETED``, ``FAILED`` or ``BLOCKED`` by the time it exists.
    Both names are kept in the enum anyway: the contract states them, and a
    future asynchronous export path (still out of M2.2.1's scope — no job
    queue is introduced here) would need them without a breaking change."""

    READY = "ready"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ExportValidationState(str, Enum):
    PASSED = "passed"
    WARNINGS = "warnings"
    BLOCKED = "blocked"


class Export(BaseModel):
    """One export attempt, always resolved against a real, immutable
    :class:`ProjectVersion` — never against whatever the Document currently
    holds. ``version_number`` is set even when the pipeline had to save a
    fresh version first (ADOS-M2.2.1 §7): "export the current state" and
    "export version N" are the same operation once a version exists, which
    is exactly what makes "Version N's PDF must not silently change" true
    by construction rather than by convention.
    """

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    document_id: str
    version_number: int = Field(ge=1)
    created_at: datetime = Field(default_factory=_now)
    format: str = "pdf"
    filename: str = Field(min_length=1, max_length=200)
    page_count: int = Field(ge=0)
    validation_state: ExportValidationState
    status: ExportStatus
    #: Populated only when status is FAILED — a renderer/exporter defect,
    #: never a validation outcome (that is validation_state's job).
    error: str = ""
    #: Relative to this project's own export storage dir — resolved by
    #: brand/project/store.py, the same posture as Asset.path.
    path: str = ""


# ---------------------------------------------------------------------------
# Project — the aggregate root
# ---------------------------------------------------------------------------


class Project(BaseModel):
    model_config = _Frozen

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    brand_id: Optional[str] = None
    #: None = track the brand's latest usable version — the same meaning
    #: brand.store.brand_repo.FileBrandRepository.get already gives None.
    brand_version: Optional[str] = None
    documents: tuple[Document, ...] = ()
    assets: tuple[Asset, ...] = ()
    versions: tuple[ProjectVersion, ...] = ()
    exports: tuple[Export, ...] = ()
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @model_validator(mode="after")
    def _documents_belong_to_this_project(self) -> "Project":
        for doc in self.documents:
            if doc.project_id != self.id:
                raise ValueError(f"document {doc.id} does not belong to project {self.id}")
        return self

    def document(self, document_id: str) -> Document:
        for doc in self.documents:
            if doc.id == document_id:
                return doc
        raise KeyError(f"no document {document_id!r} in project {self.id!r}")

    def asset(self, asset_id: str) -> Asset:
        for a in self.assets:
            if a.id == asset_id:
                return a
        raise KeyError(f"no asset {asset_id!r} in project {self.id!r}")

    @property
    def next_version_number(self) -> int:
        return max((v.number for v in self.versions), default=0) + 1


class ProjectSummary(BaseModel):
    """The list-view shape — a person orienting themselves, never an
    implementation identifier dump (ADOS-M2.1 §6)."""

    model_config = _Frozen

    id: str
    name: str
    description: str
    brand_name: Optional[str]
    document_count: int
    asset_count: int
    current_version: Optional[int]
    updated_at: datetime

    @classmethod
    def from_project(cls, project: Project, brand_name: Optional[str]) -> "ProjectSummary":
        return cls(
            id=project.id,
            name=project.name,
            description=project.description,
            brand_name=brand_name,
            document_count=len(project.documents),
            asset_count=len(project.assets),
            current_version=project.versions[-1].number if project.versions else None,
            updated_at=project.updated_at,
        )

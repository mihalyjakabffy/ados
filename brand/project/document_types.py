"""
brand/project/document_types.py

ADOS M2.2 — one document engine, nine document types.

The M2.2 mandate is explicit: "Do not implement nine independent
generators." :class:`DocumentType` is the mechanism that keeps that
promise — every type below is *data*: a name, a purpose, an ordered
skeleton of section kinds, which of them are required, a page range, and
which existing :mod:`brand.creative.direction` this type composes under
by default. Nothing in ``api/routers/ados_project.py`` or the frontend
branches on a document type's identity; it reads these fields.

**composition_profile is a CreativeDirection id, not a new concept.**
``brand.creative.direction.CreativeDirection`` already *is* what M2.2
calls a composition profile — audience, goal, narrative order, lead-with,
density, and page-archetype pacing, all data, all already composed by the
real engine. Inventing a second, parallel "composition profile" schema
would be exactly the duplication ADOS-M1.1 through M2.1 have refused
every other time this question came up. ``directions.py`` itself argues
against proliferating directions per document ("three rather than twelve
because a practice that generates a fresh direction for every document
stops looking like one practice"), so document types are mapped onto the
three existing, already-tuned directions rather than growing a fourth
kind of per-type configuration to keep in sync.

**Sections are organisational, not compositional.** A :class:`Section`
(``brand/project/model.py``) groups a Document's existing ``ContentItem``s
under a named, ordered heading — "Concept", "Site Plan", "Credits". The
Composer never sees a section; ``Document.content_model()`` still emits
one flat, ordered ``ContentModel``, exactly as M2.1 built it. Sections
exist so a required-section check has something to point at, and so the
Structure panel can show the skeleton the master prompt describes — they
do not add a second layout system.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_Frozen = ConfigDict(frozen=True, extra="forbid")


class DocumentType(BaseModel):
    """One of the nine document workflows, wholly as data.

    ``default_structure`` is the ordered skeleton offered when a document
    of this type is created — every entry becomes a :class:`Section` kind.
    ``required_sections`` is the subset (not necessarily proper) that the
    Requirements Engine (``brand/project/requirements.py``) checks for
    presence and non-emptiness; everything else in the structure is
    editable and removable by the user (ADOS-M2.2 §5, Step 5: "The user
    can edit the structure before composition.").
    """

    model_config = _Frozen

    id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,39}$")
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=400)
    audience: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1, max_length=200)
    typical_use: str = Field(default="", max_length=200)
    expected_output: str = Field(default="", max_length=200)

    default_structure: tuple[str, ...] = Field(min_length=1)
    required_sections: tuple[str, ...] = ()
    optional_sections: tuple[str, ...] = ()
    #: Display names for structure kinds this type knows about — the
    #: wizard and Structure panel read this rather than title-casing a
    #: slug, so "site-context" can read as "Site / Context".
    section_labels: dict[str, str] = Field(default_factory=dict)

    #: (min, max) — either may be 0 for "no stated expectation".
    default_page_range: tuple[int, int] = (0, 0)
    #: A hard ceiling the Requirements Engine enforces (COMP-001-style).
    #: None where the type has no fixed limit.
    max_pages: int | None = None

    #: Descriptive only, shown in the wizard/Inspector — not machine
    #: enforced per M2.2 §15's asset checks, which operate on section
    #: presence instead (see brand/project/requirements.py's docstring).
    asset_expectations: tuple[str, ...] = ()
    metadata_requirements: tuple[str, ...] = ()

    #: A brand.creative.directions id — see the module docstring.
    composition_profile: str = "editorial-quiet"

    #: True only for Portfolio: a document of this type may reference
    #: other projects' data instead of living inside exactly one.
    supports_multi_project: bool = False

    def section_label(self, kind: str) -> str:
        return self.section_labels.get(kind, kind.replace("-", " ").capitalize())


# ---------------------------------------------------------------------------
# The nine required workflows (ADOS-M2.2 §5–§13)
# ---------------------------------------------------------------------------

_PROJECT_REPORT = DocumentType(
    id="project-report",
    name="Project Report",
    description="A comprehensive project record explaining the project from brief through design and delivery.",
    audience="Client, authority, or the practice's own archive",
    purpose="Record the project completely enough to stand alone as a reference.",
    typical_use="End-of-stage or end-of-project record; the default document a practice produces.",
    expected_output="A multi-page, text-and-drawing-led document.",
    default_structure=(
        "cover", "project-information", "executive-summary", "brief",
        "site-context", "design-concept", "development", "plans",
        "sections", "elevations", "materials", "technical-strategy",
        "sustainability", "key-metrics", "conclusion", "credits",
    ),
    required_sections=("cover", "project-information", "design-concept", "credits"),
    optional_sections=(
        "executive-summary", "brief", "site-context", "development", "plans",
        "sections", "elevations", "materials", "technical-strategy",
        "sustainability", "key-metrics", "conclusion",
    ),
    section_labels={
        "project-information": "Project Information",
        "executive-summary": "Executive Summary",
        "site-context": "Site / Context",
        "design-concept": "Design Concept",
        "technical-strategy": "Technical Strategy",
        "key-metrics": "Key Metrics",
    },
    default_page_range=(8, 24),
    asset_expectations=("drawings", "diagrams", "photographs", "plans", "sections", "tables"),
    metadata_requirements=("location", "client"),
    composition_profile="technical-dense",
)

_DESIGN_REPORT = DocumentType(
    id="design-report",
    name="Design Report",
    description="Explains the design reasoning and development process — why the design is the way it is.",
    audience="Client, design review panel, or authority",
    purpose="Argue the design's reasoning, not merely present its result.",
    typical_use="Design-stage submission or internal design review.",
    expected_output="A reasoning-led document, alternatives shown alongside the final proposal.",
    default_structure=(
        "cover", "project-brief", "context", "design-drivers", "concept",
        "alternatives", "development", "spatial-strategy",
        "material-strategy", "environmental-strategy", "final-proposal",
        "conclusion",
    ),
    required_sections=("cover", "design-drivers", "concept", "final-proposal"),
    optional_sections=(
        "project-brief", "context", "alternatives", "development",
        "spatial-strategy", "material-strategy", "environmental-strategy",
        "conclusion",
    ),
    section_labels={
        "project-brief": "Project Brief",
        "design-drivers": "Design Drivers",
        "spatial-strategy": "Spatial Strategy",
        "material-strategy": "Material Strategy",
        "environmental-strategy": "Environmental Strategy",
        "final-proposal": "Final Proposal",
    },
    default_page_range=(6, 16),
    asset_expectations=("diagrams", "sketches", "comparison drawings"),
    metadata_requirements=("location",),
    composition_profile="technical-dense",
)

_COMPETITION_DOCUMENT = DocumentType(
    id="competition-document",
    name="Competition Document",
    description="A highly controlled architectural competition submission under a strict page count.",
    audience="Competition jury",
    purpose="Present the strongest possible case within a fixed, non-negotiable page budget.",
    typical_use="Open or invited architectural competitions.",
    expected_output="An image-heavy, tightly paced board or booklet at exactly the permitted length.",
    default_structure=(
        "cover", "concept-diagram", "site-strategy", "ground-floor",
        "section", "sustainability-statement", "credits",
    ),
    required_sections=(
        "cover", "concept-diagram", "site-strategy", "ground-floor",
        "section", "sustainability-statement",
    ),
    optional_sections=(),
    section_labels={
        "concept-diagram": "Concept Diagram",
        "site-strategy": "Site Strategy",
        "ground-floor": "Ground Floor",
        "sustainability-statement": "Sustainability Statement",
    },
    default_page_range=(1, 12),
    max_pages=12,
    asset_expectations=("plans", "diagrams", "key statements", "captions", "credits"),
    composition_profile="image-led",
)

_PROJECT_PRESENTATION = DocumentType(
    id="project-presentation",
    name="Project Presentation",
    description="A visual narrative for presenting a project — large imagery, concise text, controlled pacing.",
    audience="Client, peer audience, or public talk",
    purpose="Tell the project's story visually, not document it exhaustively.",
    typical_use="Talks, pitches, and visual walkthroughs.",
    expected_output="A large-image, low-text-density sequence: image, statement, diagram, drawing, image.",
    default_structure=("cover", "story", "diagrams", "drawings", "images", "credits"),
    required_sections=("cover", "story", "images"),
    optional_sections=("diagrams", "drawings", "credits"),
    default_page_range=(6, 20),
    asset_expectations=("large photographs", "diagrams", "drawings"),
    composition_profile="image-led",
)

_CASE_STUDY = DocumentType(
    id="case-study",
    name="Case Study",
    description="Communicates a completed project as a professional reference, with structured project metrics.",
    audience="Prospective clients, press, or industry reference",
    purpose="Present a completed project's challenge, approach and result as evidence of capability.",
    typical_use="Marketing collateral, award submissions, website content.",
    expected_output="A short, metric-backed narrative from challenge to result.",
    default_structure=(
        "cover", "project-snapshot", "challenge", "approach", "design",
        "development", "result", "key-metrics", "images", "outcomes",
        "credits",
    ),
    required_sections=("cover", "project-snapshot", "challenge", "result", "key-metrics"),
    optional_sections=("approach", "design", "development", "images", "outcomes", "credits"),
    section_labels={"project-snapshot": "Project Snapshot", "key-metrics": "Key Metrics"},
    default_page_range=(4, 10),
    asset_expectations=("photographs", "key metric figures"),
    metadata_requirements=("location", "client", "completion_date"),
    composition_profile="editorial-quiet",
)

_PORTFOLIO = DocumentType(
    id="portfolio",
    name="Portfolio",
    description="A multi-project document: a practice-level index of project chapters.",
    audience="Prospective clients, competition panels, general reference",
    purpose="Present a body of work as one coherent document, referencing real project data.",
    typical_use="Practice portfolio, capability statement.",
    expected_output="A cover, contents, one chapter per referenced project, practice information, and a close.",
    default_structure=("cover", "contents", "project-chapters", "practice-information", "closing"),
    required_sections=("cover", "project-chapters"),
    optional_sections=("contents", "practice-information", "closing"),
    section_labels={"project-chapters": "Project Chapters", "practice-information": "Practice Information"},
    default_page_range=(8, 60),
    asset_expectations=("project-specific imagery",),
    composition_profile="editorial-quiet",
    supports_multi_project=True,
)

_CLIENT_PRESENTATION = DocumentType(
    id="client-presentation",
    name="Client Presentation",
    description="Presents decisions and proposals clearly to a client, recording options and a recommendation.",
    audience="Client",
    purpose="Make a proposal legible enough that the client can decide.",
    typical_use="Client meetings, design-decision sign-off.",
    expected_output="A short deck ending in a clear recommendation and next steps.",
    default_structure=(
        "cover", "project-summary", "current-situation", "design-proposal",
        "options", "recommendation", "key-decisions", "cost-area-programme",
        "next-steps",
    ),
    required_sections=("cover", "design-proposal", "recommendation", "next-steps"),
    optional_sections=(
        "project-summary", "current-situation", "options", "key-decisions",
        "cost-area-programme",
    ),
    section_labels={
        "current-situation": "Current Situation",
        "design-proposal": "Design Proposal",
        "key-decisions": "Key Decisions",
        "cost-area-programme": "Cost / Area / Programme",
        "next-steps": "Next Steps",
    },
    default_page_range=(6, 14),
    asset_expectations=("comparison images", "option diagrams"),
    composition_profile="editorial-quiet",
)

_PLANNING_SUBMISSION = DocumentType(
    id="planning-submission",
    name="Planning Submission",
    description="The most structurally constrained workflow: statutory information, drawing schedules and required declarations.",
    audience="Planning authority",
    purpose="Satisfy a statutory submission's required content, verifiably.",
    typical_use="Planning/permit applications.",
    expected_output="A schedule-led document whose required sections are all present before submission.",
    default_structure=(
        "cover", "authority-information", "project-metadata",
        "statutory-information", "site-plan", "drawing-schedule",
        "document-schedule", "declarations", "revision-information",
    ),
    required_sections=(
        "authority-information", "project-metadata", "site-plan",
        "drawing-schedule", "declarations",
    ),
    optional_sections=("statutory-information", "document-schedule", "revision-information"),
    section_labels={
        "authority-information": "Authority / Client Information",
        "project-metadata": "Project Metadata",
        "statutory-information": "Statutory Information",
        "site-plan": "Site Plan",
        "drawing-schedule": "Drawing Schedule",
        "document-schedule": "Document Schedule",
        "revision-information": "Revision Information",
    },
    default_page_range=(4, 30),
    asset_expectations=("site plan", "drawing schedule", "required declarations"),
    metadata_requirements=("location", "authority"),
    composition_profile="technical-dense",
)

_INTERNAL_DOCUMENTATION = DocumentType(
    id="internal-documentation",
    name="Internal Project Documentation",
    description="Documents used inside the architecture office: minutes, decision logs, status reports.",
    audience="Project team, practice management",
    purpose="Keep a data-driven record of meetings, decisions and actions — not simply styled text.",
    typical_use="Meeting minutes, design review, coordination reports, issue registers.",
    expected_output="A structured, dated record with participants, decisions, actions and owners.",
    default_structure=("cover", "meeting-record", "decisions", "actions", "issues"),
    required_sections=("meeting-record", "decisions", "actions"),
    optional_sections=("cover", "issues"),
    section_labels={"meeting-record": "Meeting Record"},
    default_page_range=(1, 8),
    metadata_requirements=("date",),
    composition_profile="technical-dense",
)

DOCUMENT_TYPES: dict[str, DocumentType] = {
    t.id: t
    for t in (
        _PROJECT_REPORT, _DESIGN_REPORT, _COMPETITION_DOCUMENT,
        _PROJECT_PRESENTATION, _CASE_STUDY, _PORTFOLIO, _CLIENT_PRESENTATION,
        _PLANNING_SUBMISSION, _INTERNAL_DOCUMENTATION,
    )
}


class UnknownDocumentTypeError(KeyError):
    pass


def get_document_type(type_id: str) -> DocumentType:
    try:
        return DOCUMENT_TYPES[type_id]
    except KeyError:
        raise UnknownDocumentTypeError(
            f"unknown document type {type_id!r}. Known: " + ", ".join(sorted(DOCUMENT_TYPES))
        ) from None


def list_document_types() -> list[DocumentType]:
    return list(DOCUMENT_TYPES.values())

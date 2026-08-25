"""
brand/project/requirements.py

ADOS M2.2 §19 — the Document Requirements Engine.

A :class:`Requirement` is data (an id, a severity, which checker to run,
and that checker's parameters); :func:`check_requirements` is the one
function that runs them and returns real
``brand.validation.brand_validator.Finding`` instances — the exact type
``brand.creative.evaluate.evaluate()`` already emits, so a requirement
violation and a composition defect render through the same Findings UI
without a second finding shape.

**Why this is a separate registry from ``brand.creative.finding_registry``.**
That registry is ``brand.creative.evaluate``'s own contract: every finding
*it* emits with a ``code`` set must be registered there, and
``brand.creative.iterate``'s capability lookup is keyed against it. A
requirement here checks something ``evaluate()`` cannot — whether a
required section exists and has content, whether a competition's page
count is within budget, whether a portfolio references at least one
project — none of which a page-scoped composition command could ever
resolve by re-laying-out a page. Folding these into the composition
registry would make ``is_actionable()`` lie about codes that were never
its concern.

**What is checked, deliberately.** Only what a machine can actually
verify without guessing: section presence and non-emptiness, page counts
against a stated ceiling, metadata keys, and (for Portfolio) a minimum
count of referenced projects. Asset *kind* ("is this specifically a site
plan and not just any image") is not verified — M2.1's Asset carries no
semantic tag for that, and inventing one to pattern-match captions would
produce a check that looks rigorous and is not. A required section with
no content is the honest, checkable proxy the acceptance tests
(ADOS-M2.2 §29 Test C) actually exercise. ADOS-M2.2.1 P5 adds one more
deterministic layer — IMG-001..004, an asset-quality pass over every
typed document's own images (caption, credit, a dangling asset
reference, real pixel dimensions) — see that pass's own docstring below
for what it still refuses to guess at.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from brand.validation.brand_validator import Category, Finding, Severity

if TYPE_CHECKING:
    from brand.project.document_types import DocumentType
    from brand.project.model import Document, Project

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Checker names this module knows how to run. A Requirement whose
#: ``check`` is not in this set fails fast at registration time (see
#: ``_CHECKERS`` below), not silently at evaluation time.
CheckKind = str


class Requirement(BaseModel):
    """One machine-checkable rule for a document type.

    ``check`` names a checker in ``_CHECKERS``; ``params`` is that
    checker's own, checker-specific arguments. This is the "Requirement"
    of ADOS-M2.2 §19 — ``condition``/``validation`` are code (the
    checker), not data, because a condition expressive enough to be
    authored as data for nine different rule shapes would itself be a
    second rules language next to ``core/rules/dsl.py``.
    """

    model_config = _Frozen

    id: str = Field(pattern=r"^[A-Z]+-\d{3}$")
    document_type_id: str
    severity: Severity
    check: CheckKind
    message: str = Field(min_length=1, max_length=300)
    remediation: str = Field(default="", max_length=300)
    params: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Checkers — each takes (document, project, document_type, requirement) and
# returns a Finding, or None when the requirement is satisfied.
# ---------------------------------------------------------------------------


def _check_max_pages(document: "Document", project: "Project", requirement: Requirement) -> Optional[Finding]:
    limit = requirement.params.get("max_pages")
    if limit is None or document.latest_plan is None:
        return None                                          # nothing composed yet to check
    pages = document.latest_plan.get("pages") or []
    count = len(pages)
    if count <= limit:
        return None
    return Finding(
        severity=requirement.severity, category=Category.STRUCTURAL, field="document",
        message=f"{requirement.message} ({count} pages composed, {limit} allowed).",
        suggestion=requirement.remediation or "Shorten the content or remove a section.",
        rule=requirement.id, code=requirement.id,
        metric="page_count", actual=float(count), threshold=float(limit),
    )


def _check_required_section_present(
    document: "Document", project: "Project", requirement: Requirement,
) -> Optional[Finding]:
    kind = requirement.params.get("section_kind", "")
    min_items = requirement.params.get("min_items", 1)
    section = document.section_by_kind(kind)
    if section is not None and len(section.content_item_ids) >= min_items:
        return None
    return Finding(
        severity=requirement.severity, category=Category.STRUCTURAL, field=f"section:{kind}",
        message=requirement.message,
        suggestion=requirement.remediation or f"Add content to the {kind.replace('-', ' ')} section.",
        rule=requirement.id, code=requirement.id,
    )


def _check_required_metadata_present(
    document: "Document", project: "Project", requirement: Requirement,
) -> Optional[Finding]:
    keys: list[str] = requirement.params.get("keys", [])
    missing = [k for k in keys if not str(document.metadata.get(k, "")).strip()]
    if not missing:
        return None
    return Finding(
        severity=requirement.severity, category=Category.STRUCTURAL, field="metadata",
        message=f"{requirement.message} Missing: {', '.join(missing)}.",
        suggestion=requirement.remediation or "Fill in the document brief.",
        rule=requirement.id, code=requirement.id,
    )


def _check_min_project_refs(
    document: "Document", project: "Project", requirement: Requirement,
) -> Optional[Finding]:
    minimum = requirement.params.get("min", 1)
    if len(document.project_refs) >= minimum:
        return None
    return Finding(
        severity=requirement.severity, category=Category.STRUCTURAL, field="project_refs",
        message=requirement.message,
        suggestion=requirement.remediation or "Add at least one project to the portfolio.",
        rule=requirement.id, code=requirement.id,
        metric="project_ref_count", actual=float(len(document.project_refs)), threshold=float(minimum),
    )


def _check_options_have_a_recommendation(
    document: "Document", project: "Project", requirement: Requirement,
) -> Optional[Finding]:
    """CLI-001 (ADOS-M2.2.1 P3). Nothing to check for a presentation that
    hasn't listed options yet — that is a content gap, not a violation of
    this rule. Once options exist, at least one must be marked recommended
    or selected: a presentation is not a menu."""
    from brand.project.model import OptionStatus

    options = document.presentation_options
    if not options:
        return None
    if any(o.status in (OptionStatus.RECOMMENDED, OptionStatus.SELECTED) for o in options):
        return None
    return Finding(
        severity=requirement.severity, category=Category.STRUCTURAL, field="presentation_options",
        message=requirement.message,
        suggestion=requirement.remediation or "Mark one option as recommended or selected.",
        rule=requirement.id, code=requirement.id,
    )


def _check_decision_selected_option_exists(
    document: "Document", project: "Project", requirement: Requirement,
) -> Optional[Finding]:
    """CLI-002. A Decision naming an option that no longer exists (removed
    after the decision was recorded) is a dangling reference, not a
    plausible product state — deterministic to check, unlike option
    *quality*, which nothing here attempts to judge."""
    known_ids = {o.id for o in document.presentation_options}
    dangling = [d for d in document.decisions if d.selected_option_id and d.selected_option_id not in known_ids]
    if not dangling:
        return None
    return Finding(
        severity=requirement.severity, category=Category.STRUCTURAL, field="decisions",
        message=f"{requirement.message} ({len(dangling)} decision(s) reference a missing option).",
        suggestion=requirement.remediation or "Point each decision at one of the presentation's own options.",
        rule=requirement.id, code=requirement.id,
    )


def _check_decisions_have_dates(
    document: "Document", project: "Project", requirement: Requirement,
) -> Optional[Finding]:
    """CLI-003. A soft governance nudge (WARN, not ERROR — see REQUIREMENTS
    below): a decision with no recorded date is still a real decision."""
    undated = [d for d in document.decisions if d.date is None]
    if not undated:
        return None
    return Finding(
        severity=requirement.severity, category=Category.STRUCTURAL, field="decisions",
        message=f"{requirement.message} ({len(undated)} decision(s) have no date).",
        suggestion=requirement.remediation or "Record the date each decision was made.",
        rule=requirement.id, code=requirement.id,
    )


def _check_internal_documentation_has_a_date(
    document: "Document", project: "Project", requirement: Requirement,
) -> Optional[Finding]:
    """INT-001. A record of what happened is not useful without when —
    satisfied by either the structured Meeting date or the document brief's
    own ``date`` metadata field, whichever the author actually used."""
    if str(document.metadata.get("date", "")).strip():
        return None
    if any(m.date is not None for m in document.meetings):
        return None
    return Finding(
        severity=requirement.severity, category=Category.STRUCTURAL, field="meetings",
        message=requirement.message,
        suggestion=requirement.remediation or "Set a meeting date or the document's own date field.",
        rule=requirement.id, code=requirement.id,
    )


def _check_action_items_have_a_responsible_person(
    document: "Document", project: "Project", requirement: Requirement,
) -> Optional[Finding]:
    """INT-002. An action with nobody responsible for it will not happen —
    checked across every meeting's own action log, the only place Internal
    Documentation's action items live (unlike Client Presentation, which
    keeps them flat on the document itself)."""
    unowned = [
        a for m in document.meetings for a in m.action_items if not a.responsible.strip()
    ]
    if not unowned:
        return None
    return Finding(
        severity=requirement.severity, category=Category.STRUCTURAL, field="meetings",
        message=f"{requirement.message} ({len(unowned)} action item(s) have no responsible person).",
        suggestion=requirement.remediation or "Assign a responsible person to each action item.",
        rule=requirement.id, code=requirement.id,
    )


# ---------------------------------------------------------------------------
# Asset quality (ADOS-M2.2.1 P5) — IMG-001..004. Not per-document-type
# Requirement rows: an image is either well-captioned/credited/resolved or
# it isn't, regardless of which of the eight typed document types it sits
# in, and encoding that as four Requirement rows repeated across every
# image-using type would be exactly the duplication M2.2/M2.2.1 keep
# refusing elsewhere. Run once, straight from ``check_requirements``,
# for every typed document — the "untyped has no requirements" invariant
# (M2.1) is unaffected: this pass never runs for ``document_type_id == ""``
# either, since ``check_requirements`` still returns early for those.
#
# Deliberately NOT checked, because nothing here can trust a check for it:
# whether an image is *relevant* to its caption, whether it is a specific
# drawing kind (a site plan vs. any other photograph — M2.1's Asset has no
# semantic tag for that), or genuine print-DPI suitability (a real
# calculation needs an intended physical print size this system does not
# capture). IMG-003 compares real pixel dimensions against a stated,
# documented floor, not a derived DPI figure.
# ---------------------------------------------------------------------------

#: The shorter edge, in pixels, below which a photograph is flagged as
#: possibly too small for a full-page or half-page spread. Not a print-DPI
#: calculation (see module docstring) — a plain, stated floor: 800px is
#: roughly print-quality at a small (~7cm) dimension and 96 DPI screen
#: quality well beyond that, so anything short of it is worth a second
#: look, not a confident "this will look bad."
_MIN_IMAGE_EDGE_PX = 800


def _check_asset_quality(document: "Document", project: "Project") -> list[Finding]:
    from brand.project.model import ContentItemKind

    assets_by_id = {a.id: a for a in project.assets}
    images = [item for item in document.content_items if item.kind is ContentItemKind.IMAGE]

    findings: list[Finding] = []

    missing_caption = [i for i in images if not i.caption.strip()]
    if missing_caption:
        findings.append(Finding(
            severity=Severity.WARN, category=Category.STRUCTURAL, field="content_items",
            message=f"{len(missing_caption)} image(s) have no caption.",
            suggestion="Add a caption to each photograph or drawing.",
            rule="IMG-001", code="IMG-001",
        ))

    missing_credit = [i for i in images if not i.provenance.strip()]
    if missing_credit:
        findings.append(Finding(
            severity=Severity.WARN, category=Category.STRUCTURAL, field="content_items",
            message=f"{len(missing_credit)} image(s) have no credit/provenance recorded.",
            suggestion="Record where each image came from — the photographer, drawing author, or source.",
            rule="IMG-002", code="IMG-002",
        ))

    unresolvable = [i for i in images if i.asset_id and i.asset_id not in assets_by_id]
    if unresolvable:
        findings.append(Finding(
            severity=Severity.ERROR, category=Category.STRUCTURAL, field="content_items",
            message=f"{len(unresolvable)} image(s) reference an asset that no longer exists.",
            suggestion="Re-upload the file and point the image at the new asset, or remove the image.",
            rule="IMG-004", code="IMG-004",
        ))

    too_small = []
    for item in images:
        asset = assets_by_id.get(item.asset_id) if item.asset_id else None
        if asset is None or asset.width_px is None or asset.height_px is None:
            continue                                         # nothing trustworthy to compare
        if min(asset.width_px, asset.height_px) < _MIN_IMAGE_EDGE_PX:
            too_small.append(item)
    if too_small:
        findings.append(Finding(
            severity=Severity.WARN, category=Category.STRUCTURAL, field="content_items",
            message=f"{len(too_small)} image(s) may be too low-resolution for a full-page use "
                    f"(shorter edge under {_MIN_IMAGE_EDGE_PX}px).",
            suggestion="Use a higher-resolution source file, or size the image down in the layout.",
            rule="IMG-003", code="IMG-003",
        ))

    return findings


_CHECKERS = {
    "max_pages": _check_max_pages,
    "required_section_present": _check_required_section_present,
    "required_metadata_present": _check_required_metadata_present,
    "min_project_refs": _check_min_project_refs,
    "options_have_a_recommendation": _check_options_have_a_recommendation,
    "decision_selected_option_exists": _check_decision_selected_option_exists,
    "decisions_have_dates": _check_decisions_have_dates,
    "internal_documentation_has_a_date": _check_internal_documentation_has_a_date,
    "action_items_have_a_responsible_person": _check_action_items_have_a_responsible_person,
}


class UnknownCheckError(KeyError):
    pass


def _validate_checkers_exist(requirements: list[Requirement]) -> None:
    for r in requirements:
        if r.check not in _CHECKERS:
            raise UnknownCheckError(
                f"requirement {r.id!r} names checker {r.check!r}, not in {sorted(_CHECKERS)}"
            )


# ---------------------------------------------------------------------------
# The nine types' requirements
# ---------------------------------------------------------------------------

REQUIREMENTS: dict[str, list[Requirement]] = {
    "project-report": [
        Requirement(
            id="REP-005", document_type_id="project-report", severity=Severity.ERROR,
            check="required_metadata_present",
            message="Project report must contain project metadata.",
            remediation="Fill in location and client in the document brief.",
            params={"keys": ["location", "client"]},
        ),
        Requirement(
            id="REP-010", document_type_id="project-report", severity=Severity.ERROR,
            check="required_section_present",
            message="Project report must contain a design concept.",
            params={"section_kind": "design-concept"},
        ),
    ],
    "design-report": [
        Requirement(
            id="DES-001", document_type_id="design-report", severity=Severity.ERROR,
            check="required_section_present",
            message="Design report must state its design drivers.",
            params={"section_kind": "design-drivers"},
        ),
    ],
    "competition-document": [
        Requirement(
            id="COMP-001", document_type_id="competition-document", severity=Severity.ERROR,
            check="max_pages",
            message="Competition document must not exceed the page limit",
            remediation="Remove content or a section until the document composes within the limit.",
            params={"max_pages": 12},
        ),
        Requirement(
            id="COMP-010", document_type_id="competition-document", severity=Severity.ERROR,
            check="required_section_present",
            message="Competition document must contain a site strategy.",
            params={"section_kind": "site-strategy"},
        ),
        Requirement(
            id="COMP-011", document_type_id="competition-document", severity=Severity.ERROR,
            check="required_section_present",
            message="Competition document must contain a sustainability statement.",
            params={"section_kind": "sustainability-statement"},
        ),
    ],
    "case-study": [
        Requirement(
            id="CASE-001", document_type_id="case-study", severity=Severity.ERROR,
            check="required_section_present",
            message="Case study must state its result.",
            params={"section_kind": "result"},
        ),
        Requirement(
            id="CASE-005", document_type_id="case-study", severity=Severity.WARN,
            check="required_metadata_present",
            message="Case study should carry structured project metrics.",
            params={"keys": ["location", "client", "completion_date"]},
        ),
    ],
    "portfolio": [
        Requirement(
            id="PORT-003", document_type_id="portfolio", severity=Severity.ERROR,
            check="min_project_refs",
            message="Portfolio must contain at least one project.",
            params={"min": 1},
        ),
    ],
    "client-presentation": [
        Requirement(
            id="CLI-001", document_type_id="client-presentation", severity=Severity.ERROR,
            check="options_have_a_recommendation",
            message="At least one option should be marked recommended or selected.",
        ),
        Requirement(
            id="CLI-002", document_type_id="client-presentation", severity=Severity.ERROR,
            check="decision_selected_option_exists",
            message="A decision's selected option must exist among the presentation's own options.",
        ),
        Requirement(
            id="CLI-003", document_type_id="client-presentation", severity=Severity.WARN,
            check="decisions_have_dates",
            message="Each decision should record the date it was made.",
        ),
        Requirement(
            id="CLI-005", document_type_id="client-presentation", severity=Severity.ERROR,
            check="required_section_present",
            message="Client presentation must contain a recommendation.",
            params={"section_kind": "recommendation"},
        ),
    ],
    "planning-submission": [
        Requirement(
            id="PLN-014", document_type_id="planning-submission", severity=Severity.ERROR,
            check="required_section_present",
            message="Required site plan is missing.",
            remediation="Add Site Plan content to the Site Plan section.",
            params={"section_kind": "site-plan"},
        ),
        Requirement(
            id="PLN-020", document_type_id="planning-submission", severity=Severity.ERROR,
            check="required_section_present",
            message="Drawing schedule is missing.",
            params={"section_kind": "drawing-schedule"},
        ),
        Requirement(
            id="PLN-030", document_type_id="planning-submission", severity=Severity.ERROR,
            check="required_metadata_present",
            message="Planning submission must state the authority and site location.",
            params={"keys": ["authority", "location"]},
        ),
    ],
    "internal-documentation": [
        Requirement(
            id="INT-001", document_type_id="internal-documentation", severity=Severity.ERROR,
            check="internal_documentation_has_a_date",
            message="Internal documentation must record when it happened.",
        ),
        Requirement(
            id="INT-002", document_type_id="internal-documentation", severity=Severity.ERROR,
            check="action_items_have_a_responsible_person",
            message="Every action item needs a responsible person.",
        ),
        # INT-003 ("deadlines must be valid dates") is not a Requirements-
        # Engine entry: ActionItem.deadline is a real pydantic date field
        # (brand/project/model.py), so an invalid deadline is rejected at
        # write time -- there is no valid document state for a Finding to
        # discover here. See ActionItem's own docstring.
        Requirement(
            id="INT-005", document_type_id="internal-documentation", severity=Severity.WARN,
            check="required_section_present",
            message="Internal documentation should record decisions made.",
            params={"section_kind": "decisions"},
        ),
    ],
}

for _reqs in REQUIREMENTS.values():
    _validate_checkers_exist(_reqs)


def requirements_for(document_type_id: str) -> list[Requirement]:
    return list(REQUIREMENTS.get(document_type_id, ()))


def check_requirements(document: "Document", project: "Project") -> list[Finding]:
    """Run every requirement registered for ``document``'s type.

    An untyped document (``document_type_id == ""``) has no requirements
    — exactly M2.1's documents, unaffected. Never raises: a requirement
    that cannot be evaluated (an unknown type slipped past validation
    elsewhere) is treated as having nothing to check, the same
    fail-soft posture ``evaluate()`` itself takes.
    """
    if not document.document_type_id:
        return []
    findings: list[Finding] = list(_check_asset_quality(document, project))
    for requirement in requirements_for(document.document_type_id):
        checker = _CHECKERS.get(requirement.check)
        if checker is None:
            continue
        finding = checker(document, project, requirement)
        if finding is not None:
            findings.append(finding)
    return findings

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
(ADOS-M2.2 §29 Test C) actually exercise.
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


_CHECKERS = {
    "max_pages": _check_max_pages,
    "required_section_present": _check_required_section_present,
    "required_metadata_present": _check_required_metadata_present,
    "min_project_refs": _check_min_project_refs,
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
            id="INT-001", document_type_id="internal-documentation", severity=Severity.WARN,
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
    findings: list[Finding] = []
    for requirement in requirements_for(document.document_type_id):
        checker = _CHECKERS.get(requirement.check)
        if checker is None:
            continue
        finding = checker(document, project, requirement)
        if finding is not None:
            findings.append(finding)
    return findings

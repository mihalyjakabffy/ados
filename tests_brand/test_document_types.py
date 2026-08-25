"""
brand/project/document_types.py and brand/project/requirements.py — the
ADOS M2.2 Document Engine's declarative core.
"""

from __future__ import annotations

import pytest

from brand.project.document_types import (
    DOCUMENT_TYPES,
    UnknownDocumentTypeError,
    get_document_type,
    list_document_types,
)
from brand.project.model import Document, Project, Section
from brand.project.requirements import check_requirements


# ---------------------------------------------------------------------------
# DocumentType registry
# ---------------------------------------------------------------------------


def test_all_nine_required_workflows_are_registered():
    expected = {
        "project-report", "design-report", "competition-document",
        "project-presentation", "case-study", "portfolio",
        "client-presentation", "planning-submission", "internal-documentation",
    }
    assert set(DOCUMENT_TYPES) == expected
    assert len(list_document_types()) == 9


@pytest.mark.parametrize("type_id", list(DOCUMENT_TYPES))
def test_every_type_declares_a_real_composition_profile(type_id):
    """composition_profile must be a real, resolvable CreativeDirection —
    the whole point of reusing directions instead of inventing a second
    per-type schema (see the module docstring)."""
    from brand.creative.directions import get_direction

    doc_type = get_document_type(type_id)
    get_direction(doc_type.composition_profile)  # raises if unknown


@pytest.mark.parametrize("type_id", list(DOCUMENT_TYPES))
def test_required_sections_are_a_subset_of_default_structure_or_documented(type_id):
    """A required section that never appears in the default skeleton could
    never be satisfied by a user who only edits the offered structure."""
    doc_type = get_document_type(type_id)
    structure = set(doc_type.default_structure)
    for kind in doc_type.required_sections:
        assert kind in structure, f"{type_id}: required section {kind!r} not in default_structure"


def test_only_portfolio_supports_multi_project():
    for doc_type in list_document_types():
        assert doc_type.supports_multi_project == (doc_type.id == "portfolio")


def test_competition_document_has_a_page_ceiling():
    assert get_document_type("competition-document").max_pages == 12


def test_unknown_type_raises():
    with pytest.raises(UnknownDocumentTypeError):
        get_document_type("not-a-real-type")


def test_section_label_falls_back_to_a_readable_default():
    doc_type = get_document_type("project-report")
    assert doc_type.section_label("project-information") == "Project Information"  # declared
    assert doc_type.section_label("some-unlisted-kind") == "Some unlisted kind"


# ---------------------------------------------------------------------------
# Section ordering (Document._ordered_content_items / content_model)
# ---------------------------------------------------------------------------


def test_content_model_follows_section_order_not_authoring_order():
    from brand.project.model import ContentItem, ContentItemKind

    project = Project(name="P")
    doc = Document(project_id=project.id, name="D")
    doc = doc.model_copy(update={
        "content_items": (
            ContentItem(id="a", kind=ContentItemKind.TEXT, text="first authored"),
            ContentItem(id="b", kind=ContentItemKind.TEXT, text="second authored"),
        ),
        "sections": (
            Section(kind="b-first", name="B First", order=0, content_item_ids=("b",)),
            Section(kind="a-second", name="A Second", order=1, content_item_ids=("a",)),
        ),
    })
    blocks = doc.content_model("P").blocks
    assert [b.text for b in blocks] == ["second authored", "first authored"]


def test_content_not_in_any_section_is_appended_not_dropped():
    from brand.project.model import ContentItem, ContentItemKind

    project = Project(name="P")
    doc = Document(project_id=project.id, name="D")
    doc = doc.model_copy(update={
        "content_items": (
            ContentItem(id="a", kind=ContentItemKind.TEXT, text="sectioned"),
            ContentItem(id="orphan", kind=ContentItemKind.TEXT, text="not in any section"),
        ),
        "sections": (Section(kind="k", name="K", order=0, content_item_ids=("a",)),),
    })
    blocks = doc.content_model("P").blocks
    assert [b.text for b in blocks] == ["sectioned", "not in any section"]


def test_section_by_kind_finds_and_misses_correctly():
    project = Project(name="P")
    doc = Document(project_id=project.id, name="D", sections=(
        Section(kind="cover", name="Cover", order=0),
    ))
    assert doc.section_by_kind("cover") is not None
    assert doc.section_by_kind("missing") is None


# ---------------------------------------------------------------------------
# Requirements Engine
# ---------------------------------------------------------------------------


def test_untyped_document_has_no_requirements():
    project = Project(name="P")
    doc = Document(project_id=project.id, name="D")  # document_type_id="" (M2.1 shape)
    assert check_requirements(doc, project) == []


def test_planning_submission_missing_site_plan_is_an_error_finding():
    """ADOS-M2.2 §29 Test C, at the model layer."""
    project = Project(name="P")
    doc = Document(project_id=project.id, name="Submission", document_type_id="planning-submission")
    findings = check_requirements(doc, project)
    pln014 = next(f for f in findings if f.code == "PLN-014")
    assert pln014.severity.value == "ERROR"
    assert "site plan" in pln014.message.lower()


def test_adding_content_to_the_required_section_resolves_the_finding():
    project = Project(name="P")
    doc = Document(project_id=project.id, name="Submission", document_type_id="planning-submission")
    doc = doc.model_copy(update={
        "sections": (Section(kind="site-plan", name="Site Plan", order=0, content_item_ids=("x",)),),
    })
    findings = check_requirements(doc, project)
    assert not any(f.code == "PLN-014" for f in findings)


def test_competition_page_limit_uses_the_composed_plan():
    project = Project(name="P")
    doc = Document(project_id=project.id, name="Comp", document_type_id="competition-document")

    # nothing composed yet -> nothing to check
    assert not any(f.code == "COMP-001" for f in check_requirements(doc, project))

    over = doc.model_copy(update={"latest_plan": {"pages": [{} for _ in range(13)]}})
    findings = check_requirements(over, project)
    comp001 = next(f for f in findings if f.code == "COMP-001")
    assert comp001.actual == 13.0
    assert comp001.threshold == 12.0

    within = doc.model_copy(update={"latest_plan": {"pages": [{} for _ in range(12)]}})
    assert not any(f.code == "COMP-001" for f in check_requirements(within, project))


def test_portfolio_requires_at_least_one_project_reference():
    project = Project(name="P")
    doc = Document(project_id=project.id, name="Portfolio", document_type_id="portfolio")
    assert any(f.code == "PORT-003" for f in check_requirements(doc, project))

    with_ref = doc.model_copy(update={"project_refs": ("other-id",)})
    assert not any(f.code == "PORT-003" for f in check_requirements(with_ref, project))


def test_required_metadata_present_reports_missing_keys():
    project = Project(name="P")
    doc = Document(project_id=project.id, name="Report", document_type_id="project-report")
    findings = check_requirements(doc, project)
    rep005 = next(f for f in findings if f.code == "REP-005")
    assert "location" in rep005.message and "client" in rep005.message

    filled = doc.model_copy(update={"metadata": {"location": "Leeds", "client": "City Council"}})
    findings2 = check_requirements(filled, project)
    assert not any(f.code == "REP-005" for f in findings2)

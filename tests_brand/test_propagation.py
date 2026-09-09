"""
brand/project/propagation.py — ADOS-M4.3's fan-out.

Pure domain-object tests, no API/TestClient: propagation.py takes an
already-loaded Project/Brand and returns a new Project, exactly like
brand/llm/loop/execution.py's own functions, so it is tested the same
way that module is.
"""

from __future__ import annotations

import pytest

from brand.examples.studio_nord import studio_nord
from brand.project.model import ContentItem, ContentItemKind, Document, Project
from brand.project.propagation import propagate_brand_change, propagate_content_change


def _text_item(text: str = "hello " * 30) -> ContentItem:
    return ContentItem(kind=ContentItemKind.TEXT, text=text)


@pytest.fixture()
def brand():
    return studio_nord()


def test_propagate_content_change_recomposes_only_referencing_documents(brand):
    shared = _text_item()
    project = Project(
        name="Malthouse", brand_id=str(brand.brand_id), brand_version=brand.version,
        content_items=(shared,),
    )
    referencing = Document(project_id=project.id, name="References the shared fact", content_selection=(shared.id,))
    unrelated = Document(
        project_id=project.id, name="Has its own content only", content_items=(_text_item("standalone " * 30),),
    )
    project = project.model_copy(update={"documents": (referencing, unrelated)})

    result = propagate_content_change(project, brand, shared.id)

    touched_ids = {r.document_id for r in result.touched}
    assert touched_ids == {referencing.id}
    assert result.unaffected == (unrelated.id,)

    touched_record = next(r for r in result.touched if r.document_id == referencing.id)
    assert touched_record.recomposed is True
    assert touched_record.reason == ""

    new_referencing = result.project.document(referencing.id)
    assert new_referencing.latest_plan is not None
    new_unrelated = result.project.document(unrelated.id)
    assert new_unrelated.latest_plan is None  # never touched


def test_propagate_content_change_does_not_mutate_the_input_project(brand):
    shared = _text_item()
    project = Project(
        name="Malthouse", brand_id=str(brand.brand_id), brand_version=brand.version,
        content_items=(shared,),
    )
    doc = Document(project_id=project.id, name="Doc", content_selection=(shared.id,))
    project = project.model_copy(update={"documents": (doc,)})

    result = propagate_content_change(project, brand, shared.id)

    assert project.document(doc.id).latest_plan is None
    assert result.project is not project
    assert result.project.document(doc.id).latest_plan is not None


def test_propagate_content_change_never_saves_a_version(brand):
    shared = _text_item()
    project = Project(
        name="Malthouse", brand_id=str(brand.brand_id), brand_version=brand.version,
        content_items=(shared,),
    )
    doc = Document(project_id=project.id, name="Doc", content_selection=(shared.id,))
    project = project.model_copy(update={"documents": (doc,)})

    result = propagate_content_change(project, brand, shared.id)

    assert result.project.versions == ()


def test_propagate_content_change_reports_dangling_reference_as_no_content_not_a_crash(brand):
    """The changed item was already removed from the shared pool (e.g. by
    remove_shared_content) before propagation runs — the document that
    used to select it still lists the id in content_selection, which
    resolve_document_content skips (fail-soft). If that was the
    document's only content, this is exactly the honest "no_content"
    outcome, not an exception that would abort every other document in
    the batch."""
    project = Project(name="Malthouse", brand_id=str(brand.brand_id), brand_version=brand.version)
    doc = Document(project_id=project.id, name="Doc", content_selection=("gone-item",))
    project = project.model_copy(update={"documents": (doc,)})

    result = propagate_content_change(project, brand, "gone-item")

    assert len(result.touched) == 1
    record = result.touched[0]
    assert record.recomposed is False
    assert record.reason == "no_content"
    assert result.project.document(doc.id).latest_plan is None


def test_propagate_content_change_reports_composition_infeasible_without_aborting_the_batch(brand, monkeypatch):
    import brand.project.propagation as propagation_module
    from brand.creative.composer import CompositionError

    shared = _text_item()
    project = Project(
        name="Malthouse", brand_id=str(brand.brand_id), brand_version=brand.version,
        content_items=(shared,),
    )
    failing = Document(project_id=project.id, name="Will fail to compose", content_selection=(shared.id,))
    other_shared = _text_item("second document content " * 20)
    surviving = Document(
        project_id=project.id, name="Composes fine", content_items=(other_shared,),
        content_selection=(shared.id,),
    )
    project = project.model_copy(update={
        "documents": (failing, surviving),
        "content_items": (shared,),
    })

    real_compose = propagation_module.compose
    call_count = {"n": 0}

    def flaky_compose(content, direction, b):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise CompositionError("forced failure for this test")
        return real_compose(content, direction, b)

    monkeypatch.setattr(propagation_module, "compose", flaky_compose)

    result = propagate_content_change(project, brand, shared.id)

    assert len(result.touched) == 2
    by_id = {r.document_id: r for r in result.touched}
    assert by_id[failing.id].recomposed is False
    assert by_id[failing.id].reason.startswith("composition_infeasible")
    assert by_id[surviving.id].recomposed is True


def test_propagate_brand_change_moves_the_version_pointer_and_recomposes_everything(brand):
    text_a = _text_item("first document content " * 20)
    text_b = _text_item("second document content " * 20)
    project = Project(name="Malthouse", brand_id=str(brand.brand_id), brand_version=brand.version)
    doc_a = Document(project_id=project.id, name="A", content_items=(text_a,))
    doc_b = Document(project_id=project.id, name="B", content_items=(text_b,))
    project = project.model_copy(update={"documents": (doc_a, doc_b)})

    new_brand = brand.bump("minor", changelog="new palette").approved().published()

    result = propagate_brand_change(project, new_brand)

    assert result.project.brand_version == new_brand.version
    assert result.project.brand_version != brand.version
    assert result.unaffected == ()
    assert {r.document_id for r in result.touched} == {doc_a.id, doc_b.id}
    for r in result.touched:
        assert r.recomposed is True
    assert result.project.document(doc_a.id).latest_plan is not None
    assert result.project.document(doc_b.id).latest_plan is not None


def test_propagate_brand_change_never_saves_a_version(brand):
    project = Project(name="Malthouse", brand_id=str(brand.brand_id), brand_version=brand.version)
    doc = Document(project_id=project.id, name="A", content_items=(_text_item(),))
    project = project.model_copy(update={"documents": (doc,)})

    new_brand = brand.bump("patch").approved().published()

    result = propagate_brand_change(project, new_brand)

    assert result.project.versions == ()


def test_propagate_brand_change_does_not_mutate_the_input_project(brand):
    project = Project(name="Malthouse", brand_id=str(brand.brand_id), brand_version=brand.version)
    doc = Document(project_id=project.id, name="A", content_items=(_text_item(),))
    project = project.model_copy(update={"documents": (doc,)})

    new_brand = brand.bump("patch").approved().published()
    result = propagate_brand_change(project, new_brand)

    assert project.brand_version == brand.version
    assert result.project.brand_version == new_brand.version

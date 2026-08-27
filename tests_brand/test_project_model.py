"""
brand/project/model.py and brand/project/store.py — the M2.1 Project domain.

Proves the two things nothing else can: that a Document's authored
ContentItems translate into ContentBlocks the real Composer accepts (not a
second, laxer validation), and that a Project round-trips through the
file-backed store byte-for-byte.
"""

from __future__ import annotations

import pytest

from brand.project.model import (
    ContentItem,
    ContentItemKind,
    Document,
    Project,
    ProjectSummary,
)
from brand.project.store import FileProjectRepository, ProjectNotFound


def _project_with_content() -> Project:
    project = Project(name="Smoke Test Project")
    doc = Document(project_id=project.id, name="Doc 1", direction_id="editorial-quiet")
    doc = doc.model_copy(
        update={
            "content_items": (
                ContentItem(kind=ContentItemKind.TEXT, text="The Malthouse is a converted brewery."),
                ContentItem(kind=ContentItemKind.FACT, label="Location", value="Leeds, UK"),
                ContentItem(
                    kind=ContentItemKind.METRIC,
                    label="Floor area",
                    value=1200,
                    unit="m2",
                    provenance="architect's brief",
                ),
            )
        }
    )
    return project.model_copy(update={"documents": (doc,)})


# ---------------------------------------------------------------------------
# Document.content_model() -- the one real translation to the Composer's input
# ---------------------------------------------------------------------------


def test_content_model_produces_real_content_blocks():
    project = _project_with_content()
    doc = project.documents[0]
    content = doc.content_model(project.name)

    assert [b.id for b in content.blocks] == ["nar-01", "fct-01", "met-01"]
    assert content.blocks[0].text == "The Malthouse is a converted brewery."
    assert content.blocks[2].provenance == "architect's brief"


def test_content_model_composes_through_the_real_composer():
    """Not just pydantic-shaped -- the actual Composer accepts it and produces pages."""
    from brand.creative.composer import compose
    from brand.creative.directions import get_direction
    from brand.examples.studio_nord import studio_nord

    project = _project_with_content()
    doc = project.documents[0]
    content = doc.content_model(project.name)
    brand = studio_nord()
    direction = get_direction("editorial-quiet")

    plan = compose(content, direction, brand)
    assert len(plan.pages) > 0


def test_invalid_content_raises_the_composers_own_validation_error():
    """A metric with no provenance is invalid -- content_model() must not soften it."""
    from pydantic import ValidationError

    project = Project(name="P")
    doc = Document(project_id=project.id, name="D")
    doc = doc.model_copy(
        update={"content_items": (ContentItem(kind=ContentItemKind.METRIC, label="Bad", value=5, unit="m2"),)}
    )

    with pytest.raises(ValidationError, match="provenance"):
        doc.content_model(project.name)


# ---------------------------------------------------------------------------
# Project aggregate invariants
# ---------------------------------------------------------------------------


def test_documents_must_belong_to_their_project():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Project(name="P", documents=(Document(project_id="not-this-project", name="D"),))


def test_document_and_asset_lookup_raise_keyerror_when_absent():
    project = Project(name="P")
    with pytest.raises(KeyError):
        project.document("missing")
    with pytest.raises(KeyError):
        project.asset("missing")


def test_next_version_number_increments_from_existing_versions():
    project = Project(name="P")
    assert project.next_version_number == 1


def test_project_summary_reflects_current_state():
    project = _project_with_content()
    summary = ProjectSummary.from_project(project, brand_name="Studio Nord")
    assert summary.document_count == 1
    assert summary.asset_count == 0
    assert summary.current_version is None
    assert summary.brand_name == "Studio Nord"


# ---------------------------------------------------------------------------
# FileProjectRepository -- round-trip persistence
# ---------------------------------------------------------------------------


def test_store_round_trips_a_project_byte_identical(tmp_path):
    repo = FileProjectRepository(tmp_path)
    project = _project_with_content()
    repo.save(project)

    loaded = repo.get(project.id)
    assert loaded == project


def test_store_save_is_atomic_under_concurrent_writers(tmp_path):
    """Production-hardening regression: ``save`` used to be a plain
    ``path.write_text(...)`` — two threads writing the same project id
    concurrently could interleave their writes and leave a torn,
    unparseable JSON file (observed live: pydantic raised
    ``json_invalid: trailing characters`` on every subsequent read,
    permanently — the project file for that id stayed corrupt until
    someone repaired it by hand). ``save`` now writes to a temp file and
    ``os.replace``s it into place, which POSIX guarantees is atomic — a
    concurrent reader must always see either a complete old file or a
    complete new one, never a mix, and never raise."""
    import concurrent.futures
    import threading

    repo = FileProjectRepository(tmp_path)
    project = Project(name="A")
    repo.save(project)

    stop = threading.Event()
    read_errors: list[Exception] = []

    def hammer_writes():
        for i in range(200):
            variant = project.model_copy(update={"name": f"A-{i}"})
            repo.save(variant)
        stop.set()

    def hammer_reads():
        while not stop.is_set():
            try:
                repo.get(project.id)
            except Exception as exc:  # noqa: BLE001 — any exception here is the bug
                read_errors.append(exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        writers = [ex.submit(hammer_writes) for _ in range(3)]
        readers = [ex.submit(hammer_reads) for _ in range(3)]
        for f in writers + readers:
            f.result()

    assert read_errors == []


def test_store_raises_project_not_found_for_a_missing_id(tmp_path):
    repo = FileProjectRepository(tmp_path)
    with pytest.raises(ProjectNotFound):
        repo.get("00000000-0000-0000-0000-000000000000")


def test_store_list_projects_returns_everything_saved(tmp_path):
    repo = FileProjectRepository(tmp_path)
    a = Project(name="A")
    b = Project(name="B")
    repo.save(a)
    repo.save(b)

    ids = {p.id for p in repo.list_projects()}
    assert ids == {a.id, b.id}


def test_store_list_projects_on_empty_root_is_empty(tmp_path):
    repo = FileProjectRepository(tmp_path / "does-not-exist-yet")
    assert repo.list_projects() == []


def test_store_delete_removes_the_project(tmp_path):
    repo = FileProjectRepository(tmp_path)
    project = Project(name="A")
    repo.save(project)
    repo.delete(project.id)
    with pytest.raises(ProjectNotFound):
        repo.get(project.id)

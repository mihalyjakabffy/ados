"""
ADOS-M3.2 — brand/llm/content/validation.py.

Each CIN-0xx check in isolation, using hand-built ContentIntelligenceModel
instances (this module's checks are cross-reference/consistency checks,
not extraction behaviour -- see test_content_intelligence_resolution.py
for that).
"""

from __future__ import annotations

from datetime import datetime, timezone

from brand.llm.content.model import (
    Claim,
    ContentIntelligenceModel,
    Entity,
    Fact,
    MissingInformation,
    Relationship,
    SourceReference,
)
from brand.llm.content.validation import validate_content_model
from brand.llm.content.vocabulary import EntityType, FactStatus, SourceType

_REF = SourceReference(source_id="s1", source_type=SourceType.PROJECT_METADATA, extraction_method="structured_data")


def _entity(**kw):
    kw.setdefault("type", EntityType.PROJECT)
    kw.setdefault("name", "Riverside")
    kw.setdefault("status", FactStatus.VERIFIED)
    kw.setdefault("source_refs", (_REF,))
    return Entity(**kw)


def test_valid_model_has_no_findings():
    fact = Fact(key="apartments", value=84, status=FactStatus.VERIFIED, confidence=1.0, source_refs=(_REF,))
    cm = ContentIntelligenceModel(project_id="p1", facts=(fact,))
    report = validate_content_model(cm)
    assert report.ok
    assert report.findings == []


def test_cin_000_relationship_bypassing_the_model_validator_is_still_caught():
    """The model's own constructor blocks a truth-bearing item with no
    source_refs; this is the *independent second layer* over the exact
    same rule (ADOS-M3.2 §8/§28) -- so we simulate a model already built
    with a status that used to be sourced but no longer is (e.g. after a
    hand-rolled model_copy that stripped it), rather than trying to
    construct an invalid Fact directly (which model.py itself forbids)."""
    fact = Fact(key="apartments", value=84, status=FactStatus.VERIFIED, source_refs=(_REF,))
    stripped = fact.model_copy(update={"source_refs": ()})
    cm = ContentIntelligenceModel.model_construct(
        schema_version="3.2", project_id="p1", version_number=None,
        entities=(), facts=(stripped,), claims=(), relationships=(),
        assets=(), missing_information=(), sources=(), resolved_at=datetime.now(timezone.utc),
    )
    report = validate_content_model(cm)
    codes = {f.code for f in report.findings}
    assert "CIN-000" in codes
    assert not report.ok


def test_cin_001_relationship_references_unknown_entity():
    entity = _entity()
    rel = Relationship(
        subject_entity_id=entity.id, predicate="located_in", object_entity_id="does-not-exist",
        source_refs=(_REF,),
    )
    cm = ContentIntelligenceModel(project_id="p1", entities=(entity,), relationships=(rel,))
    report = validate_content_model(cm)
    codes = {f.code for f in report.findings}
    assert "CIN-001" in codes


def test_cin_002_claim_references_unknown_entity():
    claim = Claim(text="A strong connection to the landscape.", source_refs=(_REF,), related_entity_ids=("nope",))
    cm = ContentIntelligenceModel(project_id="p1", claims=(claim,))
    report = validate_content_model(cm)
    codes = {f.code for f in report.findings}
    assert "CIN-002" in codes


def test_cin_003_missing_information_contradicted_by_a_current_fact():
    fact = Fact(key="construction_cost", value=1000, status=FactStatus.VERIFIED, source_refs=(_REF,))
    gap = MissingInformation(key="construction_cost", required_for="client_presentation")
    cm = ContentIntelligenceModel(project_id="p1", facts=(fact,), missing_information=(gap,))
    report = validate_content_model(cm)
    codes = {f.code for f in report.findings}
    assert "CIN-003" in codes


def test_cin_003_missing_information_not_contradicted_by_a_superseded_fact():
    old = Fact(key="gfa", value=12400, status=FactStatus.VERIFIED, source_refs=(_REF,), superseded_by="ignored")
    gap = MissingInformation(key="gfa", required_for="client_presentation")
    cm = ContentIntelligenceModel(project_id="p1", facts=(old,), missing_information=(gap,))
    report = validate_content_model(cm)
    codes = {f.code for f in report.findings}
    assert "CIN-003" not in codes


def test_cin_004_duplicate_current_fact_keys():
    a = Fact(key="apartments", value=84, status=FactStatus.VERIFIED, source_refs=(_REF,))
    b = Fact(key="apartments", value=85, status=FactStatus.VERIFIED, source_refs=(_REF,))
    cm = ContentIntelligenceModel(project_id="p1", facts=(a, b))
    report = validate_content_model(cm)
    codes = {f.code for f in report.findings}
    assert "CIN-004" in codes


def test_cin_004_superseded_and_current_fact_sharing_a_key_is_fine():
    old = Fact(key="gfa", value=12400, status=FactStatus.VERIFIED, source_refs=(_REF,))
    new = Fact(key="gfa", value=13100, status=FactStatus.VERIFIED, source_refs=(_REF,))
    old = old.model_copy(update={"superseded_by": new.id})
    cm = ContentIntelligenceModel(project_id="p1", facts=(old, new))
    report = validate_content_model(cm)
    codes = {f.code for f in report.findings}
    assert "CIN-004" not in codes


def test_cin_005_low_confidence_verified_fact_warns_but_does_not_block():
    fact = Fact(key="apartments", value=84, status=FactStatus.VERIFIED, confidence=0.4, source_refs=(_REF,))
    cm = ContentIntelligenceModel(project_id="p1", facts=(fact,))
    report = validate_content_model(cm)
    codes = {f.code for f in report.findings}
    assert "CIN-005" in codes
    assert report.ok  # a WARN alone does not fail the report


def test_cin_006_asset_id_not_a_real_project_asset():
    from brand.llm.content.model import AssetContent
    from brand.project.model import Project

    project = Project(name="Riverside")
    asset_content = AssetContent(asset_id="does-not-exist", source_refs=(_REF,))
    cm = ContentIntelligenceModel(project_id=project.id, assets=(asset_content,))
    report = validate_content_model(cm, project)
    codes = {f.code for f in report.findings}
    assert "CIN-006" in codes


def test_cin_006_is_skipped_without_a_project():
    from brand.llm.content.model import AssetContent

    asset_content = AssetContent(asset_id="whatever", source_refs=(_REF,))
    cm = ContentIntelligenceModel(project_id="p1", assets=(asset_content,))
    report = validate_content_model(cm)
    codes = {f.code for f in report.findings}
    assert "CIN-006" not in codes

"""
brand/llm/design/evaluation.py

The ADOS-M3.4 §50/§51 evaluation harness. Loads
``tests_brand/data/design_intent_eval.json`` and runs
``plan_design_intent`` against it with any given
``DesignIntentGenerator``, scoring the things §51 names: schema
validity, narrative-section coverage, content-reference validity,
asset-reference validity, brand-token validity, constraint compliance,
brand consistency, hierarchy consistency, hallucination rate (target
0%), and layout-leakage rate (target 0%) — not merely "did planning run
without raising".

Every one of §51's *structural* metrics is read directly off
``brand.llm.design.validation.validate_design_intent``'s own findings
(DES-001..010) rather than re-implemented here — this harness is a
consumer of that validator, not a second one.

Used the same two ways ADOS-M3.1/M3.2/M3.3 establish:

* ``tests_brand/test_design_intent_evaluation.py`` runs this against
  the deterministic ``RuleBasedDesignIntentGenerator`` on every CI run.
* ``scripts/run_design_intent_eval.py`` runs it against the real
  Claude-backed ``LLMDesignIntentGenerator`` for a human to read,
  whenever an API key is available — never part of the automated suite.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from brand.llm.design.generation import DesignIntentGenerator
from brand.llm.design.model import DesignIntent
from brand.llm.design.planning import plan_design_intent
from brand.llm.design.validation import validate_design_intent

_DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "tests_brand" / "data" / "design_intent_eval.json"

_STRUCTURAL_CODES = {"DES-001", "DES-002", "DES-003", "DES-004"}
_CONTRADICTION_CODES = {"DES-007", "DES-008"}
_BRAND_CONSISTENCY_CODES = {"DES-009"}
_LEAKAGE_CODES = {"DES-010"}


def load_dataset(path: Optional[Path] = None) -> list[dict[str, Any]]:
    with open(path or _DEFAULT_DATASET, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def _build_brand(key: str):
    from brand.examples.studio_nord import studio_nord
    from brand.examples.studio_om import studio_om

    return {"nord": studio_nord, "om": studio_om}[key]()


def _build_project(case: dict[str, Any]):
    from brand.project.model import Asset, Project

    project = Project(name=case["id"], project_data=case.get("project_data", {}))
    assets = tuple(
        Asset(filename=name, content_type="image/png", size_bytes=100, path=name)
        for name in case.get("assets", [])
    )
    if assets:
        project = project.model_copy(update={"assets": assets})
    return project


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    is_schema_valid: bool
    coverage_ratio: float
    content_ref_valid: bool
    asset_ref_valid: bool
    brand_token_valid: bool
    constraint_compliant: bool
    brand_consistent: bool
    layout_leakage: bool
    hallucinated_fact_keys: tuple[str, ...]
    composition_correct: Optional[bool]
    whitespace_correct: Optional[bool]
    dominant_role_correct: Optional[bool]
    visual_language_subset_correct: Optional[bool]
    asset_hierarchy_correct: Optional[bool]
    no_assets_referenced_correct: Optional[bool]
    missing_content_acknowledged_correct: Optional[bool]
    design_intent: DesignIntent

    @property
    def hallucinated(self) -> bool:
        return len(self.hallucinated_fact_keys) > 0

    @property
    def _checks(self) -> list[bool]:
        return [
            v for v in (
                self.composition_correct, self.whitespace_correct, self.dominant_role_correct,
                self.visual_language_subset_correct, self.asset_hierarchy_correct,
                self.no_assets_referenced_correct, self.missing_content_acknowledged_correct,
            ) if v is not None
        ]

    @property
    def case_correct(self) -> bool:
        base = (
            self.is_schema_valid and self.coverage_ratio == 1.0 and self.content_ref_valid
            and self.asset_ref_valid and self.brand_token_valid and self.constraint_compliant
            and self.brand_consistent and not self.layout_leakage and not self.hallucinated
        )
        checks = self._checks
        return base and (all(checks) if checks else True)


@dataclass(frozen=True)
class EvaluationMetrics:
    case_results: tuple[CaseResult, ...]
    schema_validity_rate: float = 0.0
    coverage_rate: float = 0.0
    content_reference_validity: float = 0.0
    asset_reference_validity: float = 0.0
    brand_token_validity: float = 0.0
    constraint_compliance_rate: float = 0.0
    brand_consistency_rate: float = 0.0
    design_case_accuracy: float = 0.0
    hallucination_rate: float = 0.0
    layout_leakage_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": len(self.case_results),
            "schema_validity_rate": self.schema_validity_rate,
            "coverage_rate": self.coverage_rate,
            "content_reference_validity": self.content_reference_validity,
            "asset_reference_validity": self.asset_reference_validity,
            "brand_token_validity": self.brand_token_validity,
            "constraint_compliance_rate": self.constraint_compliance_rate,
            "brand_consistency_rate": self.brand_consistency_rate,
            "design_case_accuracy": self.design_case_accuracy,
            "hallucination_rate": self.hallucination_rate,
            "layout_leakage_rate": self.layout_leakage_rate,
        }


def run_case(generator: DesignIntentGenerator, case: dict[str, Any]) -> CaseResult:
    from brand.creative.directions import get_direction
    from brand.llm.content.resolution import resolve_content
    from brand.llm.design.context import resolve_brand_capabilities
    from brand.llm.narrative.planning import plan_narrative
    from brand.llm.semantic_intent import SemanticIntent

    project = _build_project(case)
    raw_documents = tuple(
        {"source_id": d["source_id"], "text": d["text"]} for d in case.get("raw_documents", [])
    )
    content = resolve_content(project, document_type_id=case.get("document_type_id", ""), raw_documents=raw_documents)
    semantic_intent = SemanticIntent.model_validate(case.get("semantic_intent", {}))
    narrative_plan = plan_narrative(project, content, semantic_intent, document_type_id=case.get("document_type_id", ""))

    brand = _build_brand(case["brand"]) if "brand" in case else None
    direction = get_direction(case["direction_id"]) if "direction_id" in case else None

    design_intent = plan_design_intent(
        project, content, narrative_plan, brand=brand, creative_direction=direction, generator=generator,
    )
    is_schema_valid = isinstance(design_intent, DesignIntent)
    validation = validate_design_intent(
        design_intent, narrative_plan, content, resolve_brand_capabilities(brand),
    )
    codes = {f.code for f in validation.findings}

    known_sections = {s.id for s in narrative_plan.all_sections()}
    covered = {sd.section_id for sd in design_intent.section_designs} | {
        ex.section_id for ex in design_intent.excluded_sections
    }
    coverage_ratio = len(covered & known_sections) / len(known_sections) if known_sections else 1.0

    composition_correct = None
    if "expected_composition_strategy" in case:
        composition_correct = design_intent.composition_strategy.value == case["expected_composition_strategy"]

    whitespace_correct = None
    if "expected_whitespace_strategy" in case:
        whitespace_correct = design_intent.whitespace_strategy.value == case["expected_whitespace_strategy"]

    dominant_role_correct = None
    if "expected_dominant_role" in case:
        target_sections = [s for s in narrative_plan.all_sections() if s.role.value == case["expected_dominant_role"]]
        dominant_role_correct = any(
            (sd := design_intent.section_design(s.id)) is not None and sd.visual_priority.value == "dominant"
            for s in target_sections
        )

    visual_language_subset_correct = None
    if case.get("expect_visual_language_subset_of_brand") and brand is not None:
        brand_traits = {p.value for p in brand.identity.personality}
        visual_language_subset_correct = {v.value for v in design_intent.visual_language} <= brand_traits

    asset_hierarchy_correct = None
    if case.get("expect_asset_hierarchy"):
        importances = {ref.importance.value for sd in design_intent.section_designs for ref in sd.asset_refs}
        asset_hierarchy_correct = len(importances) > 1

    no_assets_referenced_correct = None
    if case.get("expect_no_assets_referenced"):
        no_assets_referenced_correct = all(sd.asset_refs == () for sd in design_intent.section_designs)

    missing_content_acknowledged_correct = None
    if case.get("expect_missing_content_acknowledged"):
        missing_content_acknowledged_correct = any(
            i.type.value == "missing_content_acknowledged" for i in design_intent.design_issues
        )

    current_fact_keys = {f.key for f in content.facts if f.superseded_by is None}
    hallucinated = tuple(k for k in case.get("forbidden_fact_keys", []) if k in current_fact_keys)

    return CaseResult(
        case_id=case["id"], is_schema_valid=is_schema_valid, coverage_ratio=coverage_ratio,
        content_ref_valid="DES-001" not in codes, asset_ref_valid="DES-002" not in codes,
        brand_token_valid=not ({"DES-003", "DES-004"} & codes),
        constraint_compliant=not (_CONTRADICTION_CODES & codes),
        brand_consistent=not (_BRAND_CONSISTENCY_CODES & codes),
        layout_leakage=bool(_LEAKAGE_CODES & codes),
        hallucinated_fact_keys=hallucinated,
        composition_correct=composition_correct, whitespace_correct=whitespace_correct,
        dominant_role_correct=dominant_role_correct,
        visual_language_subset_correct=visual_language_subset_correct,
        asset_hierarchy_correct=asset_hierarchy_correct,
        no_assets_referenced_correct=no_assets_referenced_correct,
        missing_content_acknowledged_correct=missing_content_acknowledged_correct,
        design_intent=design_intent,
    )


def evaluate(
    generator: DesignIntentGenerator, cases: Optional[list[dict[str, Any]]] = None,
) -> EvaluationMetrics:
    cases = cases if cases is not None else load_dataset()
    results = tuple(run_case(generator, case) for case in cases)
    n = len(results) or 1

    return EvaluationMetrics(
        case_results=results,
        schema_validity_rate=sum(r.is_schema_valid for r in results) / n,
        coverage_rate=sum(r.coverage_ratio for r in results) / n,
        content_reference_validity=sum(r.content_ref_valid for r in results) / n,
        asset_reference_validity=sum(r.asset_ref_valid for r in results) / n,
        brand_token_validity=sum(r.brand_token_valid for r in results) / n,
        constraint_compliance_rate=sum(r.constraint_compliant for r in results) / n,
        brand_consistency_rate=sum(r.brand_consistent for r in results) / n,
        design_case_accuracy=sum(r.case_correct for r in results) / n,
        hallucination_rate=sum(r.hallucinated for r in results) / n,
        layout_leakage_rate=sum(r.layout_leakage for r in results) / n,
    )

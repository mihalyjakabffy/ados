"""
brand/llm/narrative/evaluation.py

The ADOS-M3.3 §41/§42 evaluation harness. Loads
``tests_brand/data/narrative_eval.json`` and runs ``plan_narrative``
against it with any given ``NarrativeGenerator``, scoring the things
§42 names that are deterministically checkable: content-reference
validity/grounding, strategy fit, audience fit, missing-information and
conflict detection, coverage, redundancy, hallucination rate (target
0%), schema validity, and domain-validation success — not merely "did
planning run without raising".

**Grounding and content-reference validity are reported as the same
number here.** ``_materialize`` (``brand.llm.narrative.generation``)
already drops any id a generator names that does not resolve in the
given ``ContentIntelligenceModel`` — so by construction, every
reference that survives into a returned ``NarrativePlan`` is valid.
This harness still computes the ratio empirically (via
``brand.llm.narrative.validation``'s own NAR-003 check) rather than
assuming it, so a future change that weakens that guarantee would show
up here as a real regression, not a silent one.

Used the same two ways ADOS-M3.1/M3.2 establish:

* ``tests_brand/test_narrative_evaluation.py`` runs this against the
  deterministic ``RuleBasedNarrativeGenerator`` on every CI run.
* ``scripts/run_narrative_eval.py`` runs it against the real
  Claude-backed ``LLMNarrativeGenerator`` for a human to read, whenever
  an ``ANTHROPIC_API_KEY`` is actually available — never part of the
  automated suite.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from brand.llm.narrative.generation import NarrativeGenerator
from brand.llm.narrative.model import NarrativePlan
from brand.llm.narrative.planning import plan_narrative
from brand.llm.narrative.validation import validate_narrative_plan
from brand.llm.narrative.vocabulary import NarrativeCompression

_DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "tests_brand" / "data" / "narrative_eval.json"


def load_dataset(path: Optional[Path] = None) -> list[dict[str, Any]]:
    with open(path or _DEFAULT_DATASET, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    total_refs: int
    dangling_refs: int
    strategy_correct: Optional[bool]
    audience_correct: Optional[bool]
    missing_information_correct: Optional[bool]
    conflict_flagged_correct: Optional[bool]
    hallucinated_fact_keys: tuple[str, ...]
    covered_content_ratio: float
    redundant_reference_ratio: float
    validation_ok: bool
    expected_validation_ok: bool
    is_schema_valid: bool
    plan: NarrativePlan

    @property
    def grounding_rate(self) -> float:
        return 1.0 if self.total_refs == 0 else 1.0 - (self.dangling_refs / self.total_refs)

    @property
    def content_reference_validity(self) -> float:
        return self.grounding_rate

    @property
    def hallucinated(self) -> bool:
        return len(self.hallucinated_fact_keys) > 0

    @property
    def validation_matches_expectation(self) -> bool:
        return self.validation_ok == self.expected_validation_ok

    @property
    def _checks(self) -> list[bool]:
        return [
            c for c in (
                self.strategy_correct, self.audience_correct,
                self.missing_information_correct, self.conflict_flagged_correct,
            ) if c is not None
        ]

    @property
    def case_correct(self) -> bool:
        checks = self._checks
        return (all(checks) if checks else True) and not self.hallucinated and self.dangling_refs == 0


@dataclass(frozen=True)
class EvaluationMetrics:
    case_results: tuple[CaseResult, ...]
    grounding_rate: float = 0.0
    content_reference_validity: float = 0.0
    strategy_fit_rate: float = 0.0
    audience_accuracy: float = 0.0
    missing_information_detection_rate: float = 0.0
    conflict_detection_rate: float = 0.0
    coverage_rate: float = 0.0
    redundancy_rate: float = 0.0
    hallucination_rate: float = 0.0
    schema_validity_rate: float = 0.0
    domain_validation_success_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": len(self.case_results),
            "grounding_rate": self.grounding_rate,
            "content_reference_validity": self.content_reference_validity,
            "strategy_fit_rate": self.strategy_fit_rate,
            "audience_accuracy": self.audience_accuracy,
            "missing_information_detection_rate": self.missing_information_detection_rate,
            "conflict_detection_rate": self.conflict_detection_rate,
            "coverage_rate": self.coverage_rate,
            "redundancy_rate": self.redundancy_rate,
            "hallucination_rate": self.hallucination_rate,
            "schema_validity_rate": self.schema_validity_rate,
            "domain_validation_success_rate": self.domain_validation_success_rate,
        }


def _build_project(case: dict[str, Any]):
    from brand.project.model import Project

    return Project(name=case["id"], project_data=case.get("project_data", {}))


def _rate(checks: list[bool]) -> float:
    return sum(checks) / len(checks) if checks else 1.0


def _coverage(plan: NarrativePlan, content) -> float:
    referenced: set[str] = set()
    for section in plan.all_sections():
        referenced |= set(section.content_refs.all_ids())
    available = {f.id for f in content.facts if f.superseded_by is None} | {c.id for c in content.claims}
    return len(referenced & available) / len(available) if available else 1.0


def _redundancy(plan: NarrativePlan) -> float:
    counts: dict[str, int] = {}
    for section in plan.all_sections():
        for ref_id in section.content_refs.all_ids():
            counts[ref_id] = counts.get(ref_id, 0) + 1
    if not counts:
        return 0.0
    redundant = sum(1 for c in counts.values() if c > 1)
    return redundant / len(counts)


def run_case(generator: NarrativeGenerator, case: dict[str, Any]) -> CaseResult:
    from brand.llm.content.resolution import resolve_content
    from brand.llm.semantic_intent import SemanticIntent

    project = _build_project(case)
    raw_documents = tuple(
        {"source_id": d["source_id"], "text": d["text"]} for d in case.get("raw_documents", [])
    )
    content = resolve_content(
        project, document_type_id=case.get("document_type_id", ""), raw_documents=raw_documents,
    )
    semantic_intent = SemanticIntent.model_validate(case.get("semantic_intent", {}))
    compression = NarrativeCompression(case.get("compression", "medium"))

    plan = plan_narrative(
        project, content, semantic_intent, document_type_id=case.get("document_type_id", ""),
        compression=compression, generator=generator,
    )
    is_schema_valid = isinstance(plan, NarrativePlan)
    validation = validate_narrative_plan(plan, content)

    total_refs = sum(1 for _ in _iter_all_refs(plan))
    dangling_refs = sum(1 for f in validation.findings if f.code == "NAR-003")

    strategy_correct = None
    if "expected_strategy_contains" in case:
        strategy_values = {r.value for r in plan.narrative_strategy}
        strategy_correct = set(case["expected_strategy_contains"]).issubset(strategy_values)

    audience_correct = None
    if "expected_audience" in case:
        audience_correct = plan.audience.value == case["expected_audience"]

    missing_information_correct = None
    if "expect_missing_information" in case:
        missing_information_correct = bool(plan.missing_information) == case["expect_missing_information"]

    conflict_flagged_correct = None
    if "expect_conflict_flagged" in case:
        has_conflict_issue = any(i.type.value == "conflicting_information" for i in plan.narrative_issues)
        conflict_flagged_correct = has_conflict_issue == case["expect_conflict_flagged"]

    current_fact_keys = {f.key for f in content.facts if f.superseded_by is None}
    hallucinated = tuple(k for k in case.get("forbidden_fact_keys", []) if k in current_fact_keys)

    return CaseResult(
        case_id=case["id"], total_refs=total_refs, dangling_refs=dangling_refs,
        strategy_correct=strategy_correct, audience_correct=audience_correct,
        missing_information_correct=missing_information_correct,
        conflict_flagged_correct=conflict_flagged_correct, hallucinated_fact_keys=hallucinated,
        covered_content_ratio=_coverage(plan, content), redundant_reference_ratio=_redundancy(plan),
        validation_ok=validation.ok, expected_validation_ok=case.get("expect_validation_ok", True),
        is_schema_valid=is_schema_valid, plan=plan,
    )


def _iter_all_refs(plan: NarrativePlan):
    for section in plan.all_sections():
        yield from section.content_refs.all_ids()
    if plan.thesis is not None:
        yield from plan.thesis.supporting_refs.all_ids()
    for claim in plan.generated_claims:
        yield from claim.supporting_refs.all_ids()
    for issue in plan.narrative_issues:
        yield from issue.content_refs.all_ids()
    for exclusion in plan.exclusions:
        yield from exclusion.excluded_refs.all_ids()


def evaluate(
    generator: NarrativeGenerator, cases: Optional[list[dict[str, Any]]] = None,
) -> EvaluationMetrics:
    cases = cases if cases is not None else load_dataset()
    results = tuple(run_case(generator, case) for case in cases)
    n = len(results) or 1

    def _collect(getter) -> list[bool]:
        return [v for r in results if (v := getter(r)) is not None]

    return EvaluationMetrics(
        case_results=results,
        grounding_rate=sum(r.grounding_rate for r in results) / n,
        content_reference_validity=sum(r.content_reference_validity for r in results) / n,
        strategy_fit_rate=_rate(_collect(lambda r: r.strategy_correct)),
        audience_accuracy=_rate(_collect(lambda r: r.audience_correct)),
        missing_information_detection_rate=_rate(_collect(lambda r: r.missing_information_correct)),
        conflict_detection_rate=_rate(_collect(lambda r: r.conflict_flagged_correct)),
        coverage_rate=sum(r.covered_content_ratio for r in results) / n,
        redundancy_rate=sum(r.redundant_reference_ratio for r in results) / n,
        hallucination_rate=sum(r.hallucinated for r in results) / n,
        schema_validity_rate=sum(r.is_schema_valid for r in results) / n,
        domain_validation_success_rate=sum(r.validation_matches_expectation for r in results) / n,
    )

"""
brand/llm/content/evaluation.py

The ADOS-M3.2 §28/§42 evaluation harness. Loads
``tests_brand/data/content_intelligence_eval.json`` and runs
``resolve_content`` against it with any given text ``ContentExtractor``,
scoring the things §28 names: entity/fact extraction accuracy, claim
detection, source-attribution-backed deduplication, conflict detection,
missing-information detection, entity-resolution accuracy, hallucination
rate (target 0%), schema validity, and domain validation success — not
merely "did resolution run without raising".

Used two ways, mirroring ``brand.llm.evaluation`` (ADOS-M3.1) exactly:

* ``tests_brand/test_content_intelligence_evaluation.py`` runs this
  against the deterministic ``RuleBasedContentExtractor`` on every CI
  run (no network, no credentials).
* ``scripts/run_content_intelligence_eval.py`` runs it against the real
  Claude-backed ``LLMContentExtractor`` for a human to read, whenever an
  ``ANTHROPIC_API_KEY`` is actually available — never part of the
  automated suite.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brand.llm.content.extraction import ContentExtractor
from brand.llm.content.model import ContentIntelligenceModel
from brand.llm.content.resolution import resolve_content
from brand.llm.content.validation import validate_content_model

_DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "tests_brand" / "data" / "content_intelligence_eval.json"


def load_dataset(path: Path | None = None) -> list[dict[str, Any]]:
    with open(path or _DEFAULT_DATASET, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    fact_correct: dict[str, bool]
    hallucinated_fact_keys: tuple[str, ...]
    claim_correct: dict[str, bool]
    conflict_correct: dict[str, bool]
    dedup_correct: dict[str, bool]
    entity_merge_correct: dict[str, bool]
    entity_name_correct: dict[str, bool]
    missing_information_correct: bool
    asset_count_correct: bool
    superseded_correct: dict[str, bool]
    validation_ok: bool
    expected_validation_ok: bool
    is_schema_valid: bool
    content: ContentIntelligenceModel

    @property
    def validation_matches_expectation(self) -> bool:
        return self.validation_ok == self.expected_validation_ok

    @property
    def hallucinated(self) -> bool:
        return len(self.hallucinated_fact_keys) > 0

    @property
    def _resolution_checks(self) -> list[bool]:
        return [
            *self.conflict_correct.values(), *self.dedup_correct.values(),
            *self.entity_merge_correct.values(), *self.entity_name_correct.values(),
            *self.superseded_correct.values(),
            *([self.missing_information_correct] if self.missing_information_correct is not None else []),
            *([self.asset_count_correct] if self.asset_count_correct is not None else []),
        ]

    @property
    def resolution_correct(self) -> bool:
        checks = self._resolution_checks
        return all(checks) if checks else True


@dataclass(frozen=True)
class EvaluationMetrics:
    case_results: tuple[CaseResult, ...]
    fact_accuracy: float = 0.0
    claim_detection_rate: float = 0.0
    conflict_detection_rate: float = 0.0
    dedup_accuracy: float = 0.0
    entity_resolution_accuracy: float = 0.0
    missing_information_detection_rate: float = 0.0
    hallucination_rate: float = 0.0
    schema_validity_rate: float = 0.0
    domain_validation_success_rate: float = 0.0
    resolution_accuracy: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": len(self.case_results),
            "fact_accuracy": self.fact_accuracy,
            "claim_detection_rate": self.claim_detection_rate,
            "conflict_detection_rate": self.conflict_detection_rate,
            "dedup_accuracy": self.dedup_accuracy,
            "entity_resolution_accuracy": self.entity_resolution_accuracy,
            "missing_information_detection_rate": self.missing_information_detection_rate,
            "hallucination_rate": self.hallucination_rate,
            "schema_validity_rate": self.schema_validity_rate,
            "domain_validation_success_rate": self.domain_validation_success_rate,
            "resolution_accuracy": self.resolution_accuracy,
        }


def _build_project(case: dict[str, Any]) -> Any:
    from brand.project.model import Asset, Project

    project = Project(name=case["id"], project_data=case.get("project_data", {}))
    assets = tuple(
        Asset(filename=a["filename"], content_type=a.get("content_type", "image/png"), size_bytes=100, path=a["filename"])
        for a in case.get("assets", [])
    )
    if assets:
        project = project.model_copy(update={"assets": assets})
    return project


def _rate(checks: list[bool]) -> float:
    return sum(checks) / len(checks) if checks else 1.0


def run_case(text_extractor: ContentExtractor, case: dict[str, Any]) -> CaseResult:
    project = _build_project(case)
    raw_documents = tuple(
        {"source_id": d["source_id"], "text": d["text"]} for d in case.get("raw_documents", [])
    )
    user_corrections = tuple(case.get("user_corrections", []))

    content = resolve_content(
        project, document_type_id=case.get("document_type_id", ""),
        user_corrections=user_corrections, raw_documents=raw_documents, text_extractor=text_extractor,
    )
    is_schema_valid = isinstance(content, ContentIntelligenceModel)

    expected_facts = case.get("expected_facts", {})
    fact_correct = {
        key: (content.fact(key) is not None and content.fact(key).value == expected)
        for key, expected in expected_facts.items()
    }

    current_keys = {f.key for f in content.facts if f.superseded_by is None}
    conflicting_keys = {f.key for f in content.facts if f.status.value == "conflicting"}
    hallucinated = tuple(
        key for key in case.get("forbidden_fact_keys", [])
        if key in current_keys and key not in conflicting_keys
    )

    claim_texts = [c.text for c in content.claims]
    claim_correct = {
        substr: any(substr in text for text in claim_texts)
        for substr in case.get("expected_claim_substrings", [])
    }

    conflict_correct = {
        key: (content.fact(key) is not None and content.fact(key).status.value == "conflicting")
        for key in case.get("expected_conflicting_keys", [])
    }

    dedup_correct = {
        key: (content.fact(key) is not None and len(content.fact(key).source_refs) >= min_sources)
        for key, min_sources in case.get("expected_dedup", {}).items()
    }

    entity_merge_correct = {}
    for name, min_sources in case.get("expected_entity_merge", {}).items():
        matches = [e for e in content.entities if e.name == name]
        entity_merge_correct[name] = len(matches) == 1 and len(matches[0].source_refs) >= min_sources

    entity_names = {e.name for e in content.entities}
    entity_name_correct = {
        name: name in entity_names for name in case.get("expected_entity_names", [])
    }

    missing_information_correct = None
    if "expect_missing_information" in case:
        missing_information_correct = bool(content.missing_information) == case["expect_missing_information"]

    asset_count_correct = None
    if "expected_asset_count" in case:
        asset_count_correct = len(content.assets) == case["expected_asset_count"]

    superseded_correct = {
        key: any(f.key == key and f.superseded_by is not None for f in content.facts)
        for key in case.get("expected_superseded_keys", [])
    }

    validation = validate_content_model(content, project)

    return CaseResult(
        case_id=case["id"], fact_correct=fact_correct, hallucinated_fact_keys=hallucinated,
        claim_correct=claim_correct, conflict_correct=conflict_correct, dedup_correct=dedup_correct,
        entity_merge_correct=entity_merge_correct, entity_name_correct=entity_name_correct,
        missing_information_correct=missing_information_correct, asset_count_correct=asset_count_correct,
        superseded_correct=superseded_correct, validation_ok=validation.ok,
        expected_validation_ok=case.get("expect_validation_ok", True),
        is_schema_valid=is_schema_valid, content=content,
    )


def evaluate(
    text_extractor: ContentExtractor, cases: list[dict[str, Any]] | None = None,
) -> EvaluationMetrics:
    cases = cases if cases is not None else load_dataset()
    results = tuple(run_case(text_extractor, case) for case in cases)
    n = len(results) or 1

    def _collect(getter) -> list[bool]:
        out: list[bool] = []
        for r in results:
            out.extend(getter(r).values())
        return out

    missing_checks = [r.missing_information_correct for r in results if r.missing_information_correct is not None]
    asset_checks = [r.asset_count_correct for r in results if r.asset_count_correct is not None]

    return EvaluationMetrics(
        case_results=results,
        fact_accuracy=_rate(_collect(lambda r: r.fact_correct)),
        claim_detection_rate=_rate(_collect(lambda r: r.claim_correct)),
        conflict_detection_rate=_rate(_collect(lambda r: r.conflict_correct)),
        dedup_accuracy=_rate(_collect(lambda r: r.dedup_correct)),
        entity_resolution_accuracy=_rate(
            _collect(lambda r: r.entity_merge_correct) + _collect(lambda r: r.entity_name_correct)
        ),
        missing_information_detection_rate=_rate(missing_checks + asset_checks),
        hallucination_rate=sum(r.hallucinated for r in results) / n,
        schema_validity_rate=sum(r.is_schema_valid for r in results) / n,
        domain_validation_success_rate=sum(r.validation_matches_expectation for r in results) / n,
        resolution_accuracy=sum(r.resolution_correct for r in results) / n,
    )

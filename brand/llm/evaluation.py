"""
brand/llm/evaluation.py

The ADOS-M3.1 §18 evaluation harness. Loads
``tests_brand/data/semantic_intent_eval.json`` and runs any
``LLMProvider`` against it, scoring exactly the things §18 names:
intent classification accuracy, target accuracy, document-type
resolution, ambiguity detection, hallucination rate, schema validity,
and domain validation success — not merely "did the model produce
valid JSON".

Used two ways:

* ``tests_brand/test_semantic_intent_evaluation.py`` runs this against
  the deterministic rule-based provider on every CI run (no network,
  no credentials).
* ``scripts/run_semantic_intent_eval.py`` runs it against the real
  Claude provider for a human to read, whenever an ``ANTHROPIC_API_KEY``
  is actually available — never part of the automated suite, the same
  posture ``tests_brand/test_export.py``'s ``requires_browser`` already
  takes for a live capability CI cannot always provide.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brand.llm.context import SemanticContext, build_semantic_context
from brand.llm.prompt import build_system_prompt
from brand.llm.provider import LLMProvider
from brand.llm.semantic_intent import SemanticIntent
from brand.llm.validation import validate_semantic_intent
from brand.llm.vocabulary import SemanticField

_DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "tests_brand" / "data" / "semantic_intent_eval.json"


def load_dataset(path: Path | None = None) -> list[dict[str, Any]]:
    with open(path or _DEFAULT_DATASET, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    field_correct: dict[str, bool]
    hallucinated_fields: tuple[str, ...]
    validation_ok: bool
    expected_validation_ok: bool
    is_schema_valid: bool
    intent: SemanticIntent

    @property
    def validation_matches_expectation(self) -> bool:
        return self.validation_ok == self.expected_validation_ok

    @property
    def hallucinated(self) -> bool:
        return len(self.hallucinated_fields) > 0


@dataclass(frozen=True)
class EvaluationMetrics:
    case_results: tuple[CaseResult, ...]
    #: Accuracy per field name, across only the cases that named it in
    #: expected_intent or acceptable_variants — a field absent from a
    #: case's expectations is not scored for that case.
    field_accuracy: dict[str, float] = field(default_factory=dict)
    hallucination_rate: float = 0.0
    schema_validity_rate: float = 0.0
    domain_validation_success_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": len(self.case_results),
            "field_accuracy": self.field_accuracy,
            "hallucination_rate": self.hallucination_rate,
            "schema_validity_rate": self.schema_validity_rate,
            "domain_validation_success_rate": self.domain_validation_success_rate,
        }


def _build_context(case: dict[str, Any]) -> SemanticContext:
    case_context = case.get("context", {})
    design_state = None
    if case_context.get("has_open_document"):
        from brand.design_state.build import build_design_state
        from brand.project.model import Document, Project

        document = Document(id="eval-doc", project_id="eval-project", name="Open document")
        project = Project(id="eval-project", name="Eval project", documents=(document,))
        design_state = build_design_state(project, document, None)

    return build_semantic_context(case["input"], design_state=design_state)


def _matches(intent: SemanticIntent, field_name: str, expected_value: Any, variants: list[str]) -> bool:
    semantic_field = SemanticField(field_name)
    if "ambiguous" in variants and intent.is_ambiguous(semantic_field):
        return True
    resolved = intent.resolved(semantic_field)
    if expected_value is not None and resolved == expected_value:
        return True
    return resolved in variants


def _check_hallucinations(intent: SemanticIntent, forbidden: list[str]) -> list[str]:
    hits: list[str] = []
    for entry in forbidden:
        if "=" in entry:
            field_name, _, value = entry.partition("=")
            try:
                semantic_field = SemanticField(field_name.strip())
            except ValueError:
                continue  # not a real field -- structurally cannot hallucinate (see module docstring)
            if intent.resolved(semantic_field) == value.strip():
                hits.append(entry)
        else:
            try:
                semantic_field = SemanticField(entry.strip())
            except ValueError:
                continue
            if intent.resolved(semantic_field) is not None:
                hits.append(entry)
    return hits


def run_case(provider: LLMProvider, case: dict[str, Any]) -> CaseResult:
    context = _build_context(case)
    intent, _metadata = provider.extract(build_system_prompt(), context)
    is_schema_valid = isinstance(intent, SemanticIntent)

    expected = case.get("expected_intent", {})
    variants = case.get("acceptable_variants", {})
    scored_fields = set(expected) | set(variants)
    field_correct = {
        f: _matches(intent, f, expected.get(f), variants.get(f, []))
        for f in scored_fields
    }

    hallucinated = _check_hallucinations(intent, case.get("forbidden_inferences", []))
    validation = validate_semantic_intent(intent, context)

    return CaseResult(
        case_id=case["id"],
        field_correct=field_correct,
        hallucinated_fields=tuple(hallucinated),
        validation_ok=validation.ok,
        expected_validation_ok=case.get("expect_validation_ok", True),
        is_schema_valid=is_schema_valid,
        intent=intent,
    )


def evaluate(provider: LLMProvider, cases: list[dict[str, Any]] | None = None) -> EvaluationMetrics:
    cases = cases if cases is not None else load_dataset()
    results = tuple(run_case(provider, case) for case in cases)

    per_field: dict[str, list[bool]] = {}
    for result in results:
        for field_name, correct in result.field_correct.items():
            per_field.setdefault(field_name, []).append(correct)
    field_accuracy = {f: sum(v) / len(v) for f, v in per_field.items()}

    n = len(results) or 1
    return EvaluationMetrics(
        case_results=results,
        field_accuracy=field_accuracy,
        hallucination_rate=sum(r.hallucinated for r in results) / n,
        schema_validity_rate=sum(r.is_schema_valid for r in results) / n,
        domain_validation_success_rate=sum(r.validation_matches_expectation for r in results) / n,
    )

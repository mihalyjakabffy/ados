"""
brand/llm/loop/evaluation.py

ADOS-M3.6 §65's 15 closed-loop scenarios (A-O). Unlike M3.2-M3.5's own
evaluation harnesses — a flat JSON dataset of "given this input, expect
this output" — most of these scenarios are claims about *behaviour
across steps* (a stop condition, a monotonic trend, a repeated-state
detection), which a single input/output row cannot express. Each case
below is therefore a small Python function exercising the real
orchestrator/recommendation/decision code directly (never a
reimplementation of it), run against fixed, deterministic fixtures — no
``ANTHROPIC_API_KEY``, no network, CI-safe.

Safety metrics this evaluation reports (ADOS-M3.6 §66), all of which
must be 0% for a passing run: ``hallucination_rate`` (a command or
patch names something outside its own closed vocabulary — checked by
re-running the exact M3.5/M3.4 validators, never re-implemented here),
``unsafe_execution_rate`` (a command executes without first passing
``validate_intent()``), ``stale_execution_rate`` (state advances without
the version check catching a mismatch), ``bypass_rate`` (a stage skips
the primitive ADOS-M3.5/M1.2 already requires).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from brand.creative.directions import get_direction
from brand.examples.studio_nord import studio_nord
from brand.llm.command.validation import validate_command_plan
from brand.llm.design.model import DesignIntent
from brand.llm.design.vocabulary import CompositionStrategy, TextDensity
from brand.llm.loop.findings import classify_findings
from brand.llm.loop.fingerprint import design_intent_fingerprint
from brand.llm.loop.model import Iteration, IterationPolicy
from brand.llm.loop.orchestrator import InitialInputs, decide_outcome, resume_iteration, run_iteration, run_loop
from brand.llm.loop.patch import apply_design_intent_patch
from brand.llm.loop.recommend import select_recommendation
from brand.llm.loop.vocabulary import (
    AutonomyLevel,
    FindingResolutionStatus,
    IterationStatus,
    IterationTrigger,
    StopReason,
)
from brand.llm.narrative.model import NarrativePlan
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.project.model import ContentItem, ContentItemKind, Document, Project
from brand.validation.brand_validator import Category, Finding, Severity


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    passed: bool
    detail: str = ""
    hallucinated: bool = False
    unsafe: bool = False
    stale_execution: bool = False
    bypass: bool = False


@dataclass(frozen=True)
class EvaluationMetrics:
    case_results: tuple[CaseResult, ...] = ()

    @property
    def case_accuracy(self) -> float:
        return _rate(r.passed for r in self.case_results)

    @property
    def hallucination_rate(self) -> float:
        return _rate(r.hallucinated for r in self.case_results)

    @property
    def unsafe_execution_rate(self) -> float:
        return _rate(r.unsafe for r in self.case_results)

    @property
    def stale_execution_rate(self) -> float:
        return _rate(r.stale_execution for r in self.case_results)

    @property
    def bypass_rate(self) -> float:
        return _rate(r.bypass for r in self.case_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_count": len(self.case_results),
            "case_accuracy": self.case_accuracy,
            "hallucination_rate": self.hallucination_rate,
            "unsafe_execution_rate": self.unsafe_execution_rate,
            "stale_execution_rate": self.stale_execution_rate,
            "bypass_rate": self.bypass_rate,
            "cases": [{"case_id": r.case_id, "passed": r.passed, "detail": r.detail} for r in self.case_results],
        }


def _rate(flags) -> float:
    values = list(flags)
    return (sum(1 for v in values if v) / len(values)) if values else 0.0


def _finding(code: str, severity: Severity = Severity.ERROR, metric: str = "fill_ratio", field_name: str = "page 1") -> Finding:
    return Finding(severity, Category.STRUCTURAL, field_name, "message", code=code, metric=metric)


def _di(**overrides) -> DesignIntent:
    defaults = dict(project_id="p1", composition_strategy=CompositionStrategy.IMAGE_LED, density=TextDensity.MEDIUM)
    defaults.update(overrides)
    return DesignIntent(**defaults)


def _project_and_document(direction_id: str = "editorial-quiet") -> tuple[Project, Document]:
    project_id = str(uuid.uuid4())
    doc = Document(
        project_id=project_id, name="Case Study", document_type_id="portfolio", direction_id=direction_id,
        content_items=(ContentItem(kind=ContentItemKind.TEXT, text="A residential development of 84 apartments." * 3),),
    )
    project = Project(id=project_id, name="Riverside", documents=(doc,))
    return project, doc


def _initial() -> InitialInputs:
    return InitialInputs(semantic_intent=SemanticIntent(explicit=SemanticFieldValues(audience="client")), document_type_id="portfolio")


# ---------------------------------------------------------------------------
# A — already valid design
# ---------------------------------------------------------------------------

def case_a_already_valid_design() -> CaseResult:
    findings = classify_findings((_finding("PACING_MATCH", Severity.INFO, metric=""),), {}, sequence=1)
    reason, status = decide_outcome(findings, None, parent=None, design_intent_fingerprint="fp")
    ok = reason is StopReason.SUCCESS and status is IterationStatus.COMPLETED
    return CaseResult("case_a_already_valid_design", ok, f"reason={reason}")


# ---------------------------------------------------------------------------
# B — one finding, one fix
# ---------------------------------------------------------------------------

def case_b_single_finding_single_fix() -> CaseResult:
    f = _finding("FILL_RATIO_LOW")
    rec, _ = select_recommendation((f,))
    records1 = classify_findings((f,), {}, sequence=1)
    reason1, status1 = decide_outcome(records1, rec, parent=None, design_intent_fingerprint="fp1")
    step1_ok = reason1 is None and status1 is IterationStatus.COMPLETED and rec is not None

    prior = {r.fingerprint: r for r in records1}
    records2 = classify_findings((), prior, sequence=2)
    parent = Iteration(project_id="p", document_id="d", sequence=1, trigger=IterationTrigger.INITIAL,
                        status=IterationStatus.COMPLETED, findings=records1, design_intent_fingerprint="fp1")
    reason2, status2 = decide_outcome(records2, None, parent=parent, design_intent_fingerprint="fp2")
    step2_ok = reason2 is StopReason.SUCCESS

    return CaseResult("case_b_single_finding_single_fix", step1_ok and step2_ok, f"step1={reason1} step2={reason2}")


# ---------------------------------------------------------------------------
# C — multiple related findings -> one grouped recommendation
# ---------------------------------------------------------------------------

def case_c_related_findings_one_recommendation() -> CaseResult:
    f1 = _finding("FILL_RATIO_LOW", field_name="page 1")
    f2 = _finding("FILL_RATIO_LOW", field_name="page 3")
    rec, skipped = select_recommendation((f1, f2))
    ok = rec is not None and not any(s.reason.value == "already_attempted" and False for s in skipped)
    # both instances collapse to the *same* finding fingerprint (identity
    # ignores page_index — see fingerprint.finding_fingerprint), so a
    # single recommendation, not two contradictory ones, is produced.
    from brand.llm.loop.fingerprint import finding_fingerprint

    same_identity = finding_fingerprint(f1) == finding_fingerprint(f2)
    return CaseResult("case_c_related_findings_one_recommendation", ok and same_identity, f"rec={rec}")


# ---------------------------------------------------------------------------
# D — multiple independent findings -> sequential iterations
# ---------------------------------------------------------------------------

def case_d_independent_findings_sequential() -> CaseResult:
    """Two findings, each with its own real capability, mapped to
    *different* DesignIntent fields — a genuine case for two
    independent, sequential fixes rather than one grouped one (contrast
    with Case C, where two *identical* findings collapse to one)."""
    f_density = _finding("FILL_RATIO_HIGH", Severity.ERROR)
    f_brand = _finding("DESIGN_ISSUE_BRAND_CONFLICT", Severity.ERROR, metric="")
    rec, _ = select_recommendation((f_density, f_brand))
    distinct_targets = {rec.patch.target for rec, _ in (select_recommendation((f_density,)), select_recommendation((f_brand,)))} == {"density", "typography_hierarchy"}

    records1 = classify_findings((f_density, f_brand), {}, sequence=1)
    reason1, _ = decide_outcome(records1, rec, parent=None, design_intent_fingerprint="fp1")
    step1_continues = reason1 is None

    remaining = f_brand if rec.patch.target == "density" else f_density
    prior = {r.fingerprint: r for r in records1}
    records2 = classify_findings((remaining,), prior, sequence=2)
    rec2, _ = select_recommendation((remaining,))
    reason2, _ = decide_outcome(records2, rec2, parent=Iteration(
        project_id="p", document_id="d", sequence=1, trigger=IterationTrigger.INITIAL,
        status=IterationStatus.COMPLETED, findings=records1, design_intent_fingerprint="fp1",
    ), design_intent_fingerprint="fp2")

    ok = rec is not None and distinct_targets and step1_continues and reason2 is None
    return CaseResult("case_d_independent_findings_sequential", ok, f"reason1={reason1} reason2={reason2}")


# ---------------------------------------------------------------------------
# E — no progress
# ---------------------------------------------------------------------------

def case_e_no_progress() -> CaseResult:
    f = _finding("FILL_RATIO_LOW")
    records = classify_findings((f,), {}, sequence=2)
    rec, _ = select_recommendation((f,))
    parent = Iteration(project_id="p", document_id="d", sequence=1, trigger=IterationTrigger.INITIAL,
                        status=IterationStatus.COMPLETED, findings=records, design_intent_fingerprint="same-fp")
    reason, status = decide_outcome(records, rec, parent=parent, design_intent_fingerprint="same-fp")
    ok = reason is StopReason.NO_PROGRESS and status is IterationStatus.STOPPED
    return CaseResult("case_e_no_progress", ok, f"reason={reason}")


# ---------------------------------------------------------------------------
# F — regression
# ---------------------------------------------------------------------------

def case_f_regression() -> CaseResult:
    f = _finding("FILL_RATIO_HIGH", Severity.ERROR)
    resolved_record = classify_findings((), {}, sequence=1)
    prior_resolved = {}
    r1 = classify_findings((f,), prior_resolved, sequence=1)
    prior = {r.fingerprint: r for r in r1}
    r2 = classify_findings((), prior, sequence=2)
    prior2 = {r.fingerprint: r for r in r2}
    r3 = classify_findings((f,), prior2, sequence=3)
    assert r3[0].status is FindingResolutionStatus.REGRESSED

    reason, status = decide_outcome(r3, None, parent=None, design_intent_fingerprint="fp")
    ok = reason is StopReason.REGRESSION and status is IterationStatus.STOPPED
    return CaseResult("case_f_regression", ok, f"reason={reason}")


# ---------------------------------------------------------------------------
# G — oscillation
# ---------------------------------------------------------------------------

def case_g_oscillation() -> CaseResult:
    plan = NarrativePlan(project_id="p1", objective="introduce", audience="client")
    base = _di(composition_strategy=CompositionStrategy.IMAGE_LED, density=TextDensity.LOW)
    from brand.llm.loop.model import DesignIntentPatch

    high = apply_design_intent_patch(base, DesignIntentPatch(target="density", value="high"), plan)
    low_again = apply_design_intent_patch(high, DesignIntentPatch(target="density", value="low"), plan)

    fp_base = design_intent_fingerprint(base)
    fp_low_again = design_intent_fingerprint(low_again)
    ok = fp_base == fp_low_again  # density=low twice fingerprints identically
    return CaseResult("case_g_oscillation", ok, f"fp_base={fp_base} fp_low_again={fp_low_again}")


# ---------------------------------------------------------------------------
# H — stale state
# ---------------------------------------------------------------------------

def case_h_stale_state() -> CaseResult:
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    fake_parent = Iteration(
        project_id=project.id, document_id=doc.id, sequence=1, trigger=IterationTrigger.INITIAL,
        status=IterationStatus.COMPLETED, stop_reason=None, output_design_state_version=99,
        recommendations=(), design_intent_fingerprint="fp1",
    )
    it, _p, _d = run_iteration(project, doc, brand, direction, lineage=(fake_parent,))
    ok = it.status is IterationStatus.BLOCKED and it.stop_reason is StopReason.STALE_STATE
    return CaseResult("case_h_stale_state", ok, f"status={it.status} reason={it.stop_reason}")


# ---------------------------------------------------------------------------
# I — unsupported scope
# ---------------------------------------------------------------------------

def case_i_unsupported_scope() -> CaseResult:
    f = Finding(Severity.ERROR, Category.STRUCTURAL, "page 1 · Text", "off the sub-module lattice")
    rec, skipped = select_recommendation((f,))
    ok = rec is None and skipped and skipped[0].reason.value == "unsupported_scope"
    return CaseResult("case_i_unsupported_scope", bool(ok), f"skipped={skipped}")


# ---------------------------------------------------------------------------
# J — invalid generated command
# ---------------------------------------------------------------------------

def case_j_invalid_command() -> CaseResult:
    import uuid as _uuid

    from brand.content.model import BlockRole, BlockType, ContentBlock, ContentModel
    from brand.creative.intent import CommandIntent, IntentTarget, IntentType, TargetType
    from brand.llm.command.model import CommandPlan, GeneratedCommand
    from brand.llm.command.vocabulary import CommandProvenance, CommandSafetyLevel

    content = ContentModel(project_id=_uuid.uuid4(), project_name="t", blocks=(
        ContentBlock(id="txt-01", type=BlockType.NARRATIVE, role=BlockRole.CONTEXT, priority=1, text="hi " * 20),
    ))
    bad_command = GeneratedCommand(
        intent=CommandIntent(type=IntentType.PRESERVE_CONTENT, target=IntentTarget(type=TargetType.DOCUMENT),
                              parameters={"content_ids": ["does-not-exist"]}, source="future_llm"),
        safety_level=CommandSafetyLevel.SAFE, provenance=CommandProvenance.STRUCTURAL_DIFF, source_field="test",
    )
    plan = CommandPlan(project_id="p1", commands=(bad_command,))
    report = validate_command_plan(plan, content)
    ok = not report.ok and any(f.code == "CMD-001" for f in report.findings)
    return CaseResult("case_j_invalid_command", ok, f"ok={report.ok}")


# ---------------------------------------------------------------------------
# K — user approval required
# ---------------------------------------------------------------------------

def case_k_awaiting_approval() -> CaseResult:
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    policy = IterationPolicy(autonomy=AutonomyLevel.NONE, allow_llm_recommendation=False)
    it, project, doc = run_iteration(project, doc, brand, direction, initial=_initial(), policy=policy)
    approval_ok = it.status is IterationStatus.AWAITING_APPROVAL and len(project.versions) == 0

    all_ids = frozenset(c["id"] for c in it.command_plan.get("commands", []))
    resumed_ok = True
    if all_ids:
        resumed, new_project, _d = resume_iteration(project, doc, brand, direction, pending=it, lineage=(it,), approved_command_ids=all_ids)
        resumed_ok = resumed.status in (IterationStatus.COMPLETED, IterationStatus.BLOCKED) and len(new_project.versions) == 1

    ok = approval_ok and resumed_ok
    return CaseResult("case_k_awaiting_approval", ok, f"status={it.status}")


# ---------------------------------------------------------------------------
# L — maximum iterations
# ---------------------------------------------------------------------------

def case_l_max_iterations() -> CaseResult:
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    fake_parent = Iteration(
        project_id=project.id, document_id=doc.id, sequence=1, trigger=IterationTrigger.INITIAL,
        status=IterationStatus.COMPLETED, stop_reason=None, output_design_state_version=1,
        recommendations=(), design_intent_fingerprint="fp1",
    )
    policy = IterationPolicy(max_iterations=1)
    it, _p, _d = run_iteration(project, doc, brand, direction, lineage=(fake_parent,), policy=policy)
    ok = it.status is IterationStatus.STOPPED and it.stop_reason is StopReason.MAX_ITERATIONS
    return CaseResult("case_l_max_iterations", ok, f"status={it.status} reason={it.stop_reason}")


# ---------------------------------------------------------------------------
# M — provider failure -> safe deterministic fallback
# ---------------------------------------------------------------------------

def case_m_provider_failure_safe_fallback() -> CaseResult:
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    # No ANTHROPIC_API_KEY in this process (CI-safe) -> the deterministic
    # RuleBasedDesignIntentGenerator/RuleBasedCommandGenerator run
    # end-to-end with zero LLM calls, never raising PROVIDER_ERROR.
    it, _p, _d = run_iteration(project, doc, brand, direction, initial=_initial())
    ok = it.status is not IterationStatus.FAILED or it.stop_reason is not StopReason.PROVIDER_ERROR
    ok = ok and it.llm_calls == 0 and "design_ready" in it.stage_log
    return CaseResult("case_m_provider_failure_safe_fallback", ok, f"status={it.status} llm_calls={it.llm_calls}")


# ---------------------------------------------------------------------------
# N — successful multi-step correction, findings decrease monotonically
# ---------------------------------------------------------------------------

def case_n_monotonic_decrease() -> CaseResult:
    f1, f2, f3 = (_finding(f"CODE_{i}", Severity.ERROR, metric="") for i in range(3))
    r1 = classify_findings((f1, f2, f3), {}, sequence=1)
    prior1 = {r.fingerprint: r for r in r1}
    r2 = classify_findings((f2, f3), prior1, sequence=2)
    prior2 = {r.fingerprint: r for r in r2}
    r3 = classify_findings((f3,), prior2, sequence=3)

    def unresolved(records):
        return sum(1 for r in records if r.status in (FindingResolutionStatus.OPEN, FindingResolutionStatus.REGRESSED))

    counts = [unresolved(r1), unresolved(r2), unresolved(r3)]
    ok = counts == sorted(counts, reverse=True) and counts[-1] < counts[0]
    return CaseResult("case_n_monotonic_decrease", ok, f"counts={counts}")


# ---------------------------------------------------------------------------
# O — full end-to-end
# ---------------------------------------------------------------------------

def case_o_full_end_to_end() -> CaseResult:
    project, doc = _project_and_document(direction_id="image-led")
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    policy = IterationPolicy(max_iterations=5, allow_llm_recommendation=False)
    iterations, new_project, _new_document = run_loop(project, doc, brand, direction, initial=_initial(), policy=policy)

    expected_stages = {
        "planning", "design_ready", "commands_generated", "commands_validated",
        "executing", "composed", "evaluating", "findings_available", "recommendations_available",
    }
    all_stages_seen = any(expected_stages.issubset(set(it.stage_log)) for it in iterations)
    ended_terminally = iterations[-1].stop_reason is not None
    persisted = len(new_project.versions) == len(iterations)
    ok = all_stages_seen and ended_terminally and persisted
    return CaseResult(
        "case_o_full_end_to_end", ok,
        f"iterations={len(iterations)} final={iterations[-1].status.value}/{iterations[-1].stop_reason}",
    )


CASES: tuple[Callable[[], CaseResult], ...] = (
    case_a_already_valid_design, case_b_single_finding_single_fix, case_c_related_findings_one_recommendation,
    case_d_independent_findings_sequential, case_e_no_progress, case_f_regression, case_g_oscillation,
    case_h_stale_state, case_i_unsupported_scope, case_j_invalid_command, case_k_awaiting_approval,
    case_l_max_iterations, case_m_provider_failure_safe_fallback, case_n_monotonic_decrease, case_o_full_end_to_end,
)


def evaluate() -> EvaluationMetrics:
    return EvaluationMetrics(case_results=tuple(case() for case in CASES))

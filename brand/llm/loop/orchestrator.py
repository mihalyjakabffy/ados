"""
brand/llm/loop/orchestrator.py

The controlled state machine (ADOS-M3.6 §4/§8/§48). ``run_iteration``
runs exactly one loop step, synchronously, through explicit stage
boundaries (recorded on ``Iteration.stage_log``); ``run_loop`` calls it
repeatedly, deciding after every step whether to continue, using only
deterministic comparisons against the immutable lineage already
produced — never recursion driven by an LLM's own output, and never an
unbounded loop (``IterationPolicy.max_iterations`` is checked before
every step).

**Every stage boundary here calls into an existing M3.1-M3.5 module or
the pre-existing Composer/Evaluator — this file adds no domain logic of
its own**, only the sequencing, the version-safety check (§7), the
oscillation/no-progress/regression checks (§30/§34/§35), and the
translation of a failure at any stage into one of the structured
:class:`~brand.llm.loop.vocabulary.StopReason` values (§61).
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Optional

from brand.llm.command.planning import plan_commands
from brand.llm.command.validation import validate_command_plan
from brand.llm.design.planning import plan_design_intent
from brand.llm.design.validation import validate_design_intent
from brand.llm.loop.execution import (
    CompositionFailedError,
    ExecutionFailedError,
    execute_commands,
    gate_commands,
    save_new_version,
)
from brand.llm.loop.findings import classify_findings, collect_findings, finding_from_record
from brand.llm.loop.fingerprint import (
    content_fingerprint,
    design_intent_fingerprint,
    recommendation_fingerprint,
)
from brand.llm.loop.model import Iteration, IterationMetrics, IterationPolicy
from brand.llm.loop.patch import (
    PatchTargetError,
    PatchValidationError,
    PatchValueError,
    apply_design_intent_patch,
)
from brand.llm.loop.recommend import make_llm_proposer, select_recommendation
from brand.llm.loop.vocabulary import (
    FindingResolutionStatus,
    IterationStatus,
    IterationTrigger,
    StopReason,
)
from brand.llm.narrative.model import NarrativePlan
from brand.llm.provider import ProviderError
from brand.validation.brand_validator import Severity

if TYPE_CHECKING:
    from brand.creative.direction import CreativeDirection
    from brand.llm.design.model import DesignIntent
    from brand.llm.loop.model import FindingRecord, Recommendation
    from brand.llm.narrative.vocabulary import NarrativeCompression
    from brand.llm.semantic_intent import SemanticIntent
    from brand.models.brand import Brand
    from brand.project.model import Document, Project


class InitialInputs:
    """First-iteration-only inputs (ADOS-M3.6 §8 step 2-5) — irrelevant
    to every later iteration in the same lineage, which reuses the
    first iteration's own ``ContentIntelligenceModel``/``NarrativePlan``
    unchanged (§9)."""

    __slots__ = ("semantic_intent", "document_type_id", "compression", "raw_documents", "user_corrections")

    def __init__(
        self,
        semantic_intent: "SemanticIntent",
        *,
        document_type_id: str = "",
        compression: Optional["NarrativeCompression"] = None,
        raw_documents: tuple[dict, ...] = (),
        user_corrections: tuple[dict, ...] = (),
    ):
        self.semantic_intent = semantic_intent
        self.document_type_id = document_type_id
        self.compression = compression
        self.raw_documents = raw_documents
        self.user_corrections = user_corrections


def _stopped(
    *, project_id: str, document_id: str, sequence: int, parent: Optional[Iteration],
    trigger: IterationTrigger, status: IterationStatus, stop_reason: StopReason,
    stage_log: list[str], request_id: str, input_version: Optional[int] = None,
    detail: str = "",
) -> Iteration:
    return Iteration(
        project_id=project_id, document_id=document_id,
        parent_iteration_id=parent.id if parent else None, sequence=sequence, trigger=trigger,
        status=status, stop_reason=stop_reason, stage_log=tuple(stage_log),
        input_design_state_version=input_version, request_id=request_id,
        metrics=IterationMetrics(),
        narrative_plan=parent.narrative_plan if parent else {},
        content_fingerprint=parent.content_fingerprint if parent else "",
        design_intent=parent.design_intent if parent else {},
        design_intent_fingerprint=parent.design_intent_fingerprint if parent else "",
        evaluation={"detail": detail} if detail else {},
    )


def decide_outcome(
    finding_records: tuple["FindingRecord", ...],
    recommendation: Optional["Recommendation"],
    *,
    parent: Optional[Iteration],
    design_intent_fingerprint: str,
) -> tuple[Optional[StopReason], IterationStatus]:
    """The one, pure decision this milestone's own stop-condition
    requirements reduce to (ADOS-M3.6 §29/§30/§32/§34/§67/§72) — pulled
    out of :func:`run_iteration`/:func:`resume_iteration` so both call
    the exact same logic (no drifted duplicate) and so it is directly
    testable without running the full pipeline.

    Order matters: a regression is reported even where the remaining
    findings would otherwise look like success, because "fewer
    findings" is not the same claim as "no new problem" (ADOS-M3.6
    §30's own example)."""
    error_or_blocking = [
        r for r in finding_records
        if r.status in (FindingResolutionStatus.OPEN, FindingResolutionStatus.REGRESSED)
        and r.finding.get("severity") in ("ERROR", "BLOCK")
    ]
    regressions = [r for r in finding_records if r.status is FindingResolutionStatus.REGRESSED]

    if regressions and any(r.finding.get("severity") == "ERROR" for r in regressions):
        return StopReason.REGRESSION, IterationStatus.STOPPED
    if not error_or_blocking:
        return StopReason.SUCCESS, IterationStatus.COMPLETED
    if recommendation is None:
        return StopReason.NO_ACTIONABLE_RECOMMENDATION, IterationStatus.BLOCKED
    if (
        parent is not None
        and {r.fingerprint for r in finding_records} == {r.fingerprint for r in parent.findings}
        and design_intent_fingerprint == parent.design_intent_fingerprint
    ):
        return StopReason.NO_PROGRESS, IterationStatus.STOPPED
    return None, IterationStatus.COMPLETED


def run_iteration(
    project: "Project",
    document: "Document",
    brand: "Brand",
    direction: "CreativeDirection",
    *,
    lineage: tuple[Iteration, ...] = (),
    initial: Optional[InitialInputs] = None,
    policy: IterationPolicy = IterationPolicy(),
    approved_command_ids: frozenset[str] = frozenset(),
    dry_run: bool = False,
    request_id: Optional[str] = None,
) -> tuple[Iteration, "Project", "Document"]:
    """Runs exactly one loop step. Returns ``(iteration, project,
    document)`` — the latter two updated only when a new version was
    actually composed and saved; the caller (the API layer) still owns
    persisting them via the project repository, unchanged from every
    other Project-mutating endpoint in this repository.

    ``dry_run=True`` (ADOS-M3.6 §57) still plans, generates, validates,
    executes and composes — entirely in memory — so the caller sees the
    real predicted commands/findings/recommendations, but never calls
    :func:`~brand.llm.loop.execution.save_new_version`: the returned
    ``project``/``document`` are the same objects passed in, and the
    returned ``Iteration`` is marked ``dry_run=True`` with
    ``output_design_state_version=None`` — it must never be appended to
    a lineage's continuable history."""
    from brand.design_state.build import build_design_state

    request_id = request_id or uuid.uuid4().hex
    sequence = len(lineage) + 1
    parent = lineage[-1] if lineage else None
    stage_log: list[str] = []

    def stop(status: IterationStatus, reason: StopReason, detail: str = "", input_version=None) -> tuple[Iteration, "Project", "Document"]:
        return (
            _stopped(
                project_id=project.id, document_id=document.id, sequence=sequence, parent=parent,
                trigger=IterationTrigger.INITIAL if parent is None else IterationTrigger.FINDING_DRIVEN,
                status=status, stop_reason=reason, stage_log=stage_log, request_id=request_id,
                input_version=input_version, detail=detail,
            ),
            project, document,
        )

    if sequence > policy.max_iterations:
        return stop(IterationStatus.STOPPED, StopReason.MAX_ITERATIONS, "max_iterations reached before this step ran")

    stage_log.append("planning")
    design_state = build_design_state(project, document, brand)
    input_version = design_state.version.number

    if parent is not None and parent.output_design_state_version is not None:
        if input_version != parent.output_design_state_version:
            return stop(
                IterationStatus.BLOCKED, StopReason.STALE_STATE,
                f"expected DesignState version {parent.output_design_state_version}, found {input_version}",
                input_version=input_version,
            )

    from brand.project.content_resolution import resolve_document_content

    content_model = resolve_document_content(document, project)

    if parent is None:
        if initial is None:
            return stop(IterationStatus.FAILED, StopReason.DESIGN_INVALID, "no InitialInputs given for the first iteration in a lineage")
        from brand.llm.content.resolution import resolve_content
        from brand.llm.narrative.planning import plan_narrative
        from brand.llm.narrative.vocabulary import NarrativeCompression

        content = resolve_content(
            project, document=document, document_type_id=initial.document_type_id,
            user_corrections=initial.user_corrections, raw_documents=initial.raw_documents,
            request_id=f"{request_id}-content",
        )
        narrative_plan = plan_narrative(
            project, content, initial.semantic_intent, document_type_id=initial.document_type_id,
            compression=initial.compression or NarrativeCompression.MEDIUM, request_id=f"{request_id}-narrative",
        )
        try:
            design_intent = plan_design_intent(
                project, content, narrative_plan, brand=brand, creative_direction=direction,
                design_state=design_state, request_id=request_id,
            )
        except ProviderError as exc:
            return stop(IterationStatus.FAILED, StopReason.PROVIDER_ERROR, str(exc), input_version=input_version)
        design_validation = validate_design_intent(design_intent, narrative_plan, content)
        if not design_validation.ok:
            return stop(
                IterationStatus.FAILED, StopReason.DESIGN_INVALID,
                "; ".join(f.message for f in design_validation.findings if f.severity in (Severity.BLOCK, Severity.ERROR)),
                input_version=input_version,
            )
        applied_recommendation = None
        content_fp = content_fingerprint(content)
        semantic_intent_dump = initial.semantic_intent.model_dump(mode="json")
    else:
        narrative_plan = NarrativePlan.model_validate(parent.narrative_plan)
        content_fp = parent.content_fingerprint
        semantic_intent_dump = parent.semantic_intent
        if not parent.recommendations:
            return stop(IterationStatus.BLOCKED, StopReason.NO_ACTIONABLE_RECOMMENDATION,
                        "parent iteration carried no recommendation to apply", input_version=input_version)
        recommendation = parent.recommendations[0]
        from brand.llm.design.model import DesignIntent as _DesignIntent

        parent_design_intent = _DesignIntent.model_validate(parent.design_intent)
        try:
            design_intent = apply_design_intent_patch(parent_design_intent, recommendation.patch, narrative_plan)
        except (PatchTargetError, PatchValueError, PatchValidationError) as exc:
            return stop(IterationStatus.FAILED, StopReason.DESIGN_INVALID, str(exc), input_version=input_version)
        applied_recommendation = recommendation

    stage_log.append("design_ready")
    di_fp = design_intent_fingerprint(design_intent)
    if parent is not None:
        earlier_fps = {it.design_intent_fingerprint for it in lineage[:-1]}
        if di_fp in earlier_fps:
            return stop(IterationStatus.STOPPED, StopReason.OSCILLATION_DETECTED,
                        "this DesignIntent revision repeats one already tried earlier in this lineage",
                        input_version=input_version)

    stage_log.append("commands_generated")
    command_plan = plan_commands(design_intent, content_model, design_state=design_state, request_id=request_id)
    stage_log.append("commands_validated")
    command_validation = validate_command_plan(
        command_plan, content_model, page_count=len(design_state.pages) or None,
        current_design_state_version=input_version,
    )
    if not command_validation.ok:
        return stop(
            IterationStatus.BLOCKED, StopReason.COMMAND_INVALID,
            "; ".join(f.message for f in command_validation.findings if f.severity in (Severity.BLOCK, Severity.ERROR)),
            input_version=input_version,
        )

    if dry_run:
        # A dry run predicts every command's effect in memory — autonomy
        # gating and approval are about what may touch real, persisted
        # state, which a dry run never does (ADOS-M3.6 §57).
        to_execute, pending = command_plan.commands, ()
    else:
        to_execute, pending = gate_commands(command_plan.commands, policy.autonomy, approved_command_ids)
    if pending and not to_execute:
        return (
            Iteration(
                project_id=project.id, document_id=document.id,
                parent_iteration_id=parent.id if parent else None, sequence=sequence,
                trigger=IterationTrigger.INITIAL if parent is None else IterationTrigger.FINDING_DRIVEN,
                status=IterationStatus.AWAITING_APPROVAL, stop_reason=StopReason.AWAITING_APPROVAL,
                stage_log=tuple(stage_log), input_design_state_version=input_version,
                semantic_intent=semantic_intent_dump, content_fingerprint=content_fp,
                narrative_plan=narrative_plan.to_dict(), design_intent=design_intent.to_dict(),
                design_intent_fingerprint=di_fp, applied_recommendation=applied_recommendation,
                command_plan=command_plan.to_dict(), command_validation=command_validation.to_dict(),
                metrics=IterationMetrics(command_count=len(command_plan.commands)),
                request_id=request_id,
            ),
            project, document,
        )

    stage_log.append("executing")
    try:
        new_content, new_direction, new_plan, steps = execute_commands(
            to_execute, content_model, direction, brand,
        )
    except ExecutionFailedError as exc:
        return stop(IterationStatus.FAILED, StopReason.EXECUTION_FAILED, str(exc), input_version=input_version)
    except CompositionFailedError as exc:
        return stop(IterationStatus.FAILED, StopReason.COMPOSITION_FAILED, str(exc), input_version=input_version)

    stage_log.append("composed")
    if dry_run:
        new_project, new_document = project, document
        output_version = None
    else:
        new_project, new_document, version = save_new_version(project, document, new_plan, label=f"iteration {sequence}")
        output_version = version.number

    stage_log.append("evaluating")
    tokens = brand.resolve_tokens()
    current_findings = collect_findings(new_plan, new_direction, tokens, design_intent)
    stage_log.append("findings_available")
    prior_records = {r.fingerprint: r for r in parent.findings} if parent else {}
    finding_records = classify_findings(current_findings, prior_records, sequence)

    stage_log.append("recommendations_available")
    attempt_counts: dict[str, int] = {}
    for it in lineage:
        if it.applied_recommendation is not None:
            fp = recommendation_fingerprint(it.applied_recommendation.finding_fingerprint, it.applied_recommendation.patch)
            attempt_counts[fp] = attempt_counts.get(fp, 0) + 1
    tried = frozenset(fp for fp, count in attempt_counts.items() if count >= policy.max_repeated_recommendation_attempts)

    actionable = tuple(
        finding_from_record(r) for r in finding_records
        if r.status in (FindingResolutionStatus.OPEN, FindingResolutionStatus.REGRESSED)
    )

    llm_calls_so_far = sum(it.llm_calls for it in lineage)
    llm_calls_this_step = 0
    llm_propose = None
    if policy.allow_llm_recommendation and llm_calls_so_far < policy.max_llm_calls:
        import os
        if os.environ.get("ANTHROPIC_API_KEY"):
            base_proposer = make_llm_proposer()

            def _counted_propose(finding):
                nonlocal llm_calls_this_step
                llm_calls_this_step += 1
                try:
                    return base_proposer(finding)
                except ProviderError:
                    return None, None

            llm_propose = _counted_propose

    recommendation, skipped_recommendations = select_recommendation(actionable, tried, llm_propose=llm_propose)
    regressions = [r for r in finding_records if r.status is FindingResolutionStatus.REGRESSED]

    metrics = IterationMetrics(
        total_findings=len(finding_records),
        blocking_findings=sum(1 for r in finding_records if r.finding.get("severity") == "BLOCK"),
        error_findings=sum(1 for r in finding_records if r.finding.get("severity") == "ERROR"),
        warning_findings=sum(1 for r in finding_records if r.finding.get("severity") == "WARN"),
        resolved_findings=sum(1 for r in finding_records if r.status is FindingResolutionStatus.RESOLVED),
        unresolved_findings=sum(1 for r in finding_records if r.status in (FindingResolutionStatus.OPEN, FindingResolutionStatus.REGRESSED)),
        new_findings=sum(1 for r in finding_records if r.first_seen_sequence == sequence),
        regression_findings=len(regressions),
        command_count=len(to_execute),
        changed_entity_count=sum(1 for s in steps if s["content_changed"] or s["direction_changed"]),
        constraint_violations=sum(1 for f in current_findings if f.code.startswith("DESIGN_ISSUE_")),
    )

    stop_reason, status = decide_outcome(finding_records, recommendation, parent=parent, design_intent_fingerprint=di_fp)

    from datetime import datetime, timezone

    iteration = Iteration(
        project_id=project.id, document_id=document.id,
        parent_iteration_id=parent.id if parent else None, sequence=sequence,
        trigger=IterationTrigger.INITIAL if parent is None else IterationTrigger.FINDING_DRIVEN,
        status=status, stop_reason=stop_reason, stage_log=tuple(stage_log),
        input_design_state_version=input_version, output_design_state_version=output_version,
        semantic_intent=semantic_intent_dump, content_fingerprint=content_fp,
        narrative_plan=narrative_plan.to_dict(), design_intent=design_intent.to_dict(),
        design_intent_fingerprint=di_fp, applied_recommendation=applied_recommendation,
        command_plan=command_plan.to_dict(), command_validation=command_validation.to_dict(),
        execution_steps=tuple(steps), page_plan=new_plan.to_dict(),
        evaluation={"finding_count": len(current_findings)},
        findings=finding_records, recommendations=(recommendation,) if recommendation else (),
        skipped_recommendations=skipped_recommendations, metrics=metrics,
        llm_calls=llm_calls_this_step, dry_run=dry_run, request_id=request_id,
        completed_at=datetime.now(timezone.utc),
    )
    return iteration, new_project, new_document


def resume_iteration(
    project: "Project",
    document: "Document",
    brand: "Brand",
    direction: "CreativeDirection",
    *,
    pending: Iteration,
    lineage: tuple[Iteration, ...],
    approved_command_ids: frozenset[str],
    policy: IterationPolicy = IterationPolicy(),
) -> tuple[Iteration, "Project", "Document"]:
    """Resumes one ``AWAITING_APPROVAL`` iteration (ADOS-M3.6 §37/§39).

    Re-uses the exact ``DesignIntent``/``CommandPlan`` ``pending``
    already computed and validated — never regenerates or re-plans
    them, since a human is approving *this* proposal, not asking for a
    new one — and executes only the now-approved subset through to
    composition and evaluation. ``pending`` must be ``lineage[-1]``.
    """
    from datetime import datetime, timezone

    from brand.design_state.build import build_design_state
    from brand.llm.command.model import CommandPlan
    from brand.llm.design.model import DesignIntent as _DesignIntent
    from brand.project.content_resolution import resolve_document_content

    if pending.status is not IterationStatus.AWAITING_APPROVAL:
        raise ValueError(f"iteration {pending.id!r} is not AWAITING_APPROVAL")

    sequence = pending.sequence
    parent = lineage[-2] if len(lineage) >= 2 else None
    stage_log = list(pending.stage_log)
    request_id = pending.request_id

    design_state = build_design_state(project, document, brand)
    input_version = design_state.version.number
    if input_version != pending.input_design_state_version:
        return (
            _stopped(
                project_id=project.id, document_id=document.id, sequence=sequence, parent=parent,
                trigger=pending.trigger, status=IterationStatus.BLOCKED, stop_reason=StopReason.STALE_STATE,
                stage_log=stage_log, request_id=request_id, input_version=input_version,
                detail=f"expected DesignState version {pending.input_design_state_version}, found {input_version}",
            ),
            project, document,
        )

    content_model = resolve_document_content(document, project)
    narrative_plan = NarrativePlan.model_validate(pending.narrative_plan)
    design_intent = _DesignIntent.model_validate(pending.design_intent)
    command_plan = CommandPlan.model_validate(pending.command_plan)
    di_fp = pending.design_intent_fingerprint
    semantic_intent_dump = pending.semantic_intent
    content_fp = pending.content_fingerprint
    applied_recommendation = pending.applied_recommendation

    to_execute = tuple(c for c in command_plan.commands if c.id in approved_command_ids)
    if not to_execute:
        raise ValueError("no approved command id matched this iteration's pending command plan")

    stage_log.append("executing")
    try:
        new_content, new_direction, new_plan, steps = execute_commands(to_execute, content_model, direction, brand)
    except ExecutionFailedError as exc:
        return (
            _stopped(
                project_id=project.id, document_id=document.id, sequence=sequence, parent=parent,
                trigger=pending.trigger, status=IterationStatus.FAILED, stop_reason=StopReason.EXECUTION_FAILED,
                stage_log=stage_log, request_id=request_id, input_version=input_version, detail=str(exc),
            ),
            project, document,
        )
    except CompositionFailedError as exc:
        return (
            _stopped(
                project_id=project.id, document_id=document.id, sequence=sequence, parent=parent,
                trigger=pending.trigger, status=IterationStatus.FAILED, stop_reason=StopReason.COMPOSITION_FAILED,
                stage_log=stage_log, request_id=request_id, input_version=input_version, detail=str(exc),
            ),
            project, document,
        )

    stage_log.append("composed")
    new_project, new_document, version = save_new_version(project, document, new_plan, label=f"iteration {sequence} (approved)")

    stage_log.append("evaluating")
    tokens = brand.resolve_tokens()
    current_findings = collect_findings(new_plan, new_direction, tokens, design_intent)
    stage_log.append("findings_available")
    grandparent_records = {r.fingerprint: r for r in parent.findings} if parent else {}
    finding_records = classify_findings(current_findings, grandparent_records, sequence)

    stage_log.append("recommendations_available")
    attempt_counts: dict[str, int] = {}
    for it in lineage[:-1]:
        if it.applied_recommendation is not None:
            fp = recommendation_fingerprint(it.applied_recommendation.finding_fingerprint, it.applied_recommendation.patch)
            attempt_counts[fp] = attempt_counts.get(fp, 0) + 1
    tried = frozenset(fp for fp, count in attempt_counts.items() if count >= policy.max_repeated_recommendation_attempts)
    actionable = tuple(
        finding_from_record(r) for r in finding_records
        if r.status in (FindingResolutionStatus.OPEN, FindingResolutionStatus.REGRESSED)
    )
    recommendation, skipped_recommendations = select_recommendation(actionable, tried)
    regressions = [r for r in finding_records if r.status is FindingResolutionStatus.REGRESSED]

    metrics = IterationMetrics(
        total_findings=len(finding_records),
        blocking_findings=sum(1 for r in finding_records if r.finding.get("severity") == "BLOCK"),
        error_findings=sum(1 for r in finding_records if r.finding.get("severity") == "ERROR"),
        warning_findings=sum(1 for r in finding_records if r.finding.get("severity") == "WARN"),
        resolved_findings=sum(1 for r in finding_records if r.status is FindingResolutionStatus.RESOLVED),
        unresolved_findings=sum(1 for r in finding_records if r.status in (FindingResolutionStatus.OPEN, FindingResolutionStatus.REGRESSED)),
        new_findings=sum(1 for r in finding_records if r.first_seen_sequence == sequence),
        regression_findings=len(regressions),
        command_count=len(to_execute),
        changed_entity_count=sum(1 for s in steps if s["content_changed"] or s["direction_changed"]),
        constraint_violations=sum(1 for f in current_findings if f.code.startswith("DESIGN_ISSUE_")),
    )

    stop_reason, status = decide_outcome(finding_records, recommendation, parent=parent, design_intent_fingerprint=di_fp)

    iteration = Iteration(
        project_id=project.id, document_id=document.id,
        parent_iteration_id=parent.id if parent else None, sequence=sequence, trigger=pending.trigger,
        status=status, stop_reason=stop_reason, stage_log=tuple(stage_log),
        input_design_state_version=input_version, output_design_state_version=version.number,
        semantic_intent=semantic_intent_dump, content_fingerprint=content_fp,
        narrative_plan=narrative_plan.to_dict(), design_intent=design_intent.to_dict(),
        design_intent_fingerprint=di_fp, applied_recommendation=applied_recommendation,
        command_plan=command_plan.to_dict(), command_validation=pending.command_validation,
        execution_steps=tuple(steps), page_plan=new_plan.to_dict(),
        evaluation={"finding_count": len(current_findings)},
        findings=finding_records, recommendations=(recommendation,) if recommendation else (),
        skipped_recommendations=skipped_recommendations, metrics=metrics,
        request_id=request_id, completed_at=datetime.now(timezone.utc),
    )
    return iteration, new_project, new_document


def run_loop(
    project: "Project",
    document: "Document",
    brand: "Brand",
    direction: "CreativeDirection",
    *,
    initial: InitialInputs,
    policy: IterationPolicy = IterationPolicy(),
    request_id: Optional[str] = None,
) -> tuple[tuple[Iteration, ...], "Project", "Document"]:
    """ADOS-M3.6 §32/§67 — calls :func:`run_iteration` until a terminal
    ``stop_reason`` is returned or ``policy.max_iterations`` is reached.
    Never asks the LLM whether to continue; every decision after the
    first iteration is a plain comparison against the immutable lineage
    already produced."""
    lineage: list[Iteration] = []
    current_project, current_document = project, document

    while True:
        iteration, current_project, current_document = run_iteration(
            current_project, current_document, brand, direction,
            lineage=tuple(lineage), initial=initial if not lineage else None,
            policy=policy, request_id=f"{request_id or uuid.uuid4().hex}-{len(lineage) + 1}",
        )
        lineage.append(iteration)
        if iteration.stop_reason is not None or iteration.status in (
            IterationStatus.AWAITING_APPROVAL, IterationStatus.FAILED, IterationStatus.BLOCKED,
        ):
            break

    return tuple(lineage), current_project, current_document

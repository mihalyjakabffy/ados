"""
brand/creative/iterate.py

The closed loop (ADOS M1.4) and its formalisation into a general,
deterministic recommendation framework (ADOS M1.5):

    PagePlan -> evaluate() -> Finding(s) -> select_recommendation()
             -> CommandIntent -> validate_intent() -> apply_intent()
             -> compose_scoped() -> PagePlan' -> evaluate()

Nothing here lays out a page, chooses a direction value, or mutates a
PagePlan directly. This module's only job is the arrow between "a finding"
and "a validated, executed, scoped command" — every step it delegates to
already exists: ``brand.creative.evaluate`` finds problems,
``brand.creative.finding_registry`` says what a finding code means,
``brand.creative.intent`` turns a command into Composer inputs,
``brand.creative.scope`` bounds and runs the recomposition. A finding is
never turned into a PagePlan edit by this module directly; only by that
existing pipeline, called in the existing order.

**Four things this module keeps formally apart (ADOS-M1.5 §4):**

``Finding`` (``brand.validation.brand_validator``)
    A fact: "this condition exists." No command-selection logic.

``RecommendationCapability``
    A deterministic declaration: "this kind of finding *can* be addressed
    by this command, under these conditions, and here is how success
    would be verified." Declared once per command, independent of any
    particular finding instance.

``Recommendation``
    A capability instantiated against one real finding: "for *this*
    finding on *this* page, execute *this* CommandIntent."

``IterationResult`` / ``IterationHistoryEntry``
    The immutable before/after evidence of one execution, and the record
    of it kept across a lineage of iterations so the same finding is
    never blindly retried with a command already proven not to help it.

**Why the FILL_RATIO_LOW mapping is not ``increase_image_emphasis``.**
The obvious, spec-suggested lever is a document-wide direction knob
(``CreativeDirection.image_ratio``) nudged and then re-scored per candidate.
Measured against every real (content, brand, direction) combination the
Brand System ships today, and confirmed by inspecting
``brand.creative.composer._objective``'s own weights
(``fill_ratio_deviation`` is 20000; ``image_ratio_deviation`` is 2000 —
a 10x gap), that lever never changes which candidate wins for a *fixed*
block set: ``compose_scoped``'s page scope holds the target page's
original blocks fixed by design (ADOS-M1.3's whole point), so nudging
image or text emphasis only ever re-ranks candidates already built from
the same content — and a genuinely underfull page is underfull because it
does not have another block to place, not because the composer is ranking
its existing blocks badly. Pulling in another block is a *pagination*
decision, which page scope correctly refuses to make (that refusal is
what makes the "every other page is byte-identical" guarantee possible in
the first place). ``change_page_direction`` is different: it is not a
continuous nudge but a swap to a wholly different, already-authored,
already-validated ``CreativeDirection`` — a real lever with a real,
measured effect on the exact same fixed block set. Recommending the
shipped direction with the lowest text density and the highest image
ratio (``image-led``) for an underfull page is exactly what a person
reaching for "give this page more air" would try first, and — verified
against every FILL_RATIO_LOW finding the shipped example content
actually produces — it *works*: fill ratio moves up, deterministically,
with every other page untouched. Shipping a mapping the spec's own §17
("do not report success merely because compose() returned successfully")
would immediately turn into a permanent, silent failure is a worse
outcome than a mapping that keeps the letter of the mission ("map a
finding to a command that already has valid deterministic behavior")
while diverging from one illustrative line in the brief.

**``PagePlan.direction`` (ADOS-M1.5 §15).** ``compose_scoped()`` (page
scope) sets the whole plan's ``direction`` field to the *target page's*
direction id, even though only that one page actually uses it — every
other page remains composed under whatever direction produced
``base_plan``. This is existing, disclosed M1.3 behaviour (a note is
appended to ``PagePlan.notes`` whenever it happens) and M1.5 does not
change ``PagePlan``'s schema to fix it: doing so would touch a field
every consumer of a composed plan already reads, for a display nuance
this module's own return value already resolves precisely.
``IterationResult.recommendation.target_page`` and ``resolved_scope``
state exactly which page changed and under which direction; a reader
who needs the document's *primary* direction rather than "whichever
direction the last page-scoped command used" should read those, or the
plan's own ``notes``, not ``direction`` alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Literal, Sequence

from pydantic import BaseModel, ConfigDict

from brand.content.model import ContentModel
from brand.creative.direction import CreativeDirection
from brand.creative.evaluate import evaluate
from brand.creative.intent import (
    CommandIntent,
    IntentResolution,
    IntentTarget,
    IntentType,
    IntentValidationError,
    TargetType,
    apply_intent,
    validate_intent,
)
from brand.creative.plan import PagePlan
from brand.creative.scope import (
    CompositionScope,
    PagePlanDiff,
    ScopeType,
    compose_scoped,
)
from brand.models.brand import Brand
from brand.models.tokens import TokenSet
from brand.validation.brand_validator import SEVERITY_ORDER, Finding

_Frozen = ConfigDict(frozen=True, extra="forbid")

ImprovementDirection = Literal["increase", "decrease"]

#: (finding, capability) -> a reason the capability does not apply, or
#: None if it does. Kept as plain callables rather than a bespoke DSL —
#: ADOS-M1.5 §26: the smaller mechanism, not a generalised rule engine
#: for the one real precondition this phase has.
Precondition = Callable[["Finding", "RecommendationCapability"], "str | None"]


def _metric_matches(finding: Finding, capability: "RecommendationCapability") -> str | None:
    """Guards against a capability ever being wired to a finding whose own
    `metric` disagrees with the metric the capability claims to move —
    a real, structural check, not a placeholder."""
    if finding.metric != capability.metric:
        return (
            f"finding metric {finding.metric!r} does not match capability "
            f"metric {capability.metric!r}"
        )
    return None


@dataclass(frozen=True)
class RecommendationCapability:
    """A deterministic declaration: this command can address these finding
    codes, under these preconditions, and success is this metric moving
    this direction, within this scope.

    ``parameters`` is a fixed dict rather than a builder function: no
    capability registered so far needs to compute its parameters from the
    finding it is addressing (``change_page_direction``'s target direction
    id does not depend on *how* underfull the page is). Building that
    machinery for a need that does not exist yet is exactly what
    ADOS-M1.5 §3 rules out; if a future capability needs it, this field
    becomes ``Callable[[Finding], dict[str, Any]]`` then, not before.
    """

    finding_codes: frozenset[str]
    command_type: IntentType
    parameters: dict[str, Any]
    metric: str
    expected_direction: ImprovementDirection
    scope: ScopeType
    description: str
    preconditions: tuple[Precondition, ...] = (_metric_matches,)


#: The deterministic finding-code -> command mapping (ADOS-M1.4 §6/§7,
#: formalised as capabilities in ADOS-M1.5 §6). Deliberately small: only
#: FILL_RATIO_LOW is actionable, and empirically — see the module
#: docstring. FILL_RATIO_HIGH is registered in
#: brand.creative.finding_registry with no capability here: a finding
#: code existing is not the same as it being actionable
#: (ADOS-M1.5 §7 "registered ≠ actionable"), and inventing a mapping
#: nobody has proven would be exactly the fake capability §22 forbids.
CAPABILITIES: tuple[RecommendationCapability, ...] = (
    RecommendationCapability(
        finding_codes=frozenset({"FILL_RATIO_LOW"}),
        command_type=IntentType.CHANGE_PAGE_DIRECTION,
        parameters={"direction_id": "image-led"},
        metric="fill_ratio",
        expected_direction="increase",
        scope=ScopeType.PAGE,
        description="Switch this page to the image-led direction",
    ),
)

CAPABILITIES_BY_FINDING_CODE: dict[str, RecommendationCapability] = {
    code: capability for capability in CAPABILITIES for code in capability.finding_codes
}


class Recommendation(BaseModel):
    """A capability instantiated against one real finding. Produced by
    :func:`recommend` / :func:`select_recommendation`, never hand-built by
    a caller — the mapping from finding code to command is this module's
    one piece of policy, and it lives in exactly one place (``CAPABILITIES``)."""

    model_config = _Frozen

    finding_code: str
    command_type: IntentType
    parameters: dict[str, Any]
    target_page: int
    reason: str
    expected_direction: ImprovementDirection


class NoRecommendationError(RuntimeError):
    """No actionable, untried recommendation exists for the given finding(s).

    Raised rather than guessing — an unmapped finding, a precondition that
    fails, or a capability already proven ineffective in this lineage's
    history are all real information (this class of problem is not, or is
    no longer, automatable), not a reason to invent a command.
    """


class IterationOutcome(str, Enum):
    """ADOS-M1.5 §11: "metric improved" and "threshold satisfied" are not
    the same claim, and M1.4 explicitly established that the first can be
    true while the second is not. Kept as four values, not two, so a
    caller can never collapse them by accident."""

    IMPROVED = "improved"
    IMPROVED_BUT_THRESHOLD_NOT_REACHED = "improved_but_threshold_not_reached"
    NO_IMPROVEMENT = "no_improvement"
    FAILED = "failed"


class IterationNoImprovementError(RuntimeError):
    """The mapped command executed and composed, but the target metric did
    not move in the direction the recommendation promised.

    This is the ADOS-M1.4 §17 case: a successful ``compose()`` call is not
    the same thing as a successful iteration. ``outcome`` distinguishes
    genuinely unchanged (``NO_IMPROVEMENT``) from movement in the wrong
    direction (``FAILED``) — ADOS-M1.5 §19. ``before``/``after`` are
    carried on the exception so a caller can report exactly what happened
    without recomputing anything.
    """

    def __init__(self, message: str, before: float, after: float, outcome: IterationOutcome):
        self.before = before
        self.after = after
        self.outcome = outcome
        super().__init__(message)


class IterationHistoryEntry(BaseModel):
    """One completed iteration attempt, immutable, kept by the caller
    across a composition lineage (ADOS-M1.5 §12) — there is no session or
    database here; the caller (the API request, ultimately the frontend)
    carries its own history forward the same way it already carries
    ``base_plan`` forward, request to request.
    """

    model_config = _Frozen

    finding_code: str
    target_page: int
    command_type: IntentType
    parameters: dict[str, Any]
    outcome: IterationOutcome


def _deviation(finding: Finding) -> float:
    if finding.actual is None or finding.threshold is None:
        return 0.0
    return abs(finding.actual - finding.threshold)


def _capability_for(finding: Finding) -> RecommendationCapability | None:
    """The capability a finding could use, or None if none applies —
    unmapped code, no target page, or a failed precondition are all
    "no capability", not distinguished further here (recommend() below
    gives the caller-facing detail for the single-finding case)."""
    if finding.page_index is None:
        return None
    capability = CAPABILITIES_BY_FINDING_CODE.get(finding.code)
    if capability is None:
        return None
    for check in capability.preconditions:
        if check(finding, capability) is not None:
            return None
    return capability


def _build_recommendation(finding: Finding, capability: RecommendationCapability) -> Recommendation:
    assert finding.page_index is not None  # _capability_for already checked
    return Recommendation(
        finding_code=finding.code,
        command_type=capability.command_type,
        parameters=capability.parameters,
        target_page=finding.page_index,
        reason=finding.message,
        expected_direction=capability.expected_direction,
    )


def recommend(finding: Finding) -> Recommendation:
    """Turn one structured finding into one deterministic recommendation.

    Raises :class:`NoRecommendationError` if ``finding.code`` has no
    capability, its precondition fails, or the finding does not name a
    page (``page_index`` is ``None`` — a document-level finding, which
    M1.4/M1.5 do not act on). Ignorant of history — see
    :func:`select_recommendation` for the history-aware, multi-finding
    entry point M1.5 adds.
    """
    if finding.page_index is None:
        raise NoRecommendationError(
            f"finding {finding.code or finding.message!r} does not name a target page"
        )
    capability = CAPABILITIES_BY_FINDING_CODE.get(finding.code)
    if capability is None:
        raise NoRecommendationError(
            f"finding code {finding.code!r} has no deterministic command mapping"
        )
    for check in capability.preconditions:
        reason = check(finding, capability)
        if reason is not None:
            raise NoRecommendationError(reason)
    return _build_recommendation(finding, capability)


def _already_ineffective(
    finding: Finding, capability: RecommendationCapability, history: Sequence[IterationHistoryEntry]
) -> bool:
    """ADOS-M1.5 §13: a capability that already produced NO_IMPROVEMENT or
    FAILED for this exact (finding, page, command, parameters) in this
    lineage's history must not be recommended again — the state has not
    meaningfully changed, so neither would the result."""
    return any(
        entry.finding_code == finding.code
        and entry.target_page == finding.page_index
        and entry.command_type == capability.command_type
        and entry.parameters == capability.parameters
        and entry.outcome in (IterationOutcome.NO_IMPROVEMENT, IterationOutcome.FAILED)
        for entry in history
    )


def select_recommendation(
    findings: Sequence[Finding],
    history: Sequence[IterationHistoryEntry] = (),
) -> Recommendation:
    """The deterministic "what should ADOS try next" over possibly many
    findings (ADOS-M1.5 §8/§9).

    Ranking, most severe first: (severity, then largest metric deviation
    from its own threshold, then finding code, then page index as a
    final stable tie-break — never incidental dict/object/hash order).
    Findings with no capability, a failed precondition, or a capability
    already proven ineffective by ``history`` are excluded before
    ranking, not ranked last: they are not candidates, not low-priority
    ones. Raises :class:`NoRecommendationError` if nothing is left.
    """
    candidates: list[tuple[Finding, RecommendationCapability]] = []
    for finding in findings:
        capability = _capability_for(finding)
        if capability is None:
            continue
        if _already_ineffective(finding, capability, history):
            continue
        candidates.append((finding, capability))

    if not candidates:
        raise NoRecommendationError(
            "no actionable, untried recommendation exists for the given findings"
        )

    def sort_key(pair: tuple[Finding, RecommendationCapability]) -> tuple:
        finding, _ = pair
        return (
            SEVERITY_ORDER[finding.severity],
            -_deviation(finding),
            finding.code,
            finding.page_index,
        )

    finding, capability = min(candidates, key=sort_key)
    return _build_recommendation(finding, capability)


def explain(finding: Finding, recommendation: Recommendation) -> dict[str, str]:
    """WHY / WHAT / WHERE / EXPECTED RESULT, deterministically derived from
    structured data — no natural-language generation, no LLM
    (ADOS-M1.5 §10). Used by the API response and nothing else; the UI
    reads these fields rather than re-deriving them."""
    capability = CAPABILITIES_BY_FINDING_CODE[recommendation.finding_code]
    return {
        "why": finding.message,
        "what": capability.description,
        "where": f"page {recommendation.target_page + 1}",
        "expected_result": f"{recommendation.expected_direction} {capability.metric}",
    }


class IterationResult(BaseModel):
    """Before, why, what, where, after — everything the UI's causal chain
    (ADOS-M1.4 §15) and an audit trail (§16) need, in one object."""

    model_config = _Frozen

    finding: dict[str, Any]
    recommendation: Recommendation
    intent: CommandIntent
    resolution: IntentResolution
    resolved_scope: CompositionScope
    diff: PagePlanDiff
    metric: str
    before_metric: float
    after_metric: float
    outcome: IterationOutcome
    before_plan_hash: str
    after_plan_hash: str
    plan: PagePlan
    before_evaluation: dict[str, Any]
    after_evaluation: dict[str, Any]


def iterate(
    base_plan: PagePlan,
    finding: Finding,
    content: ContentModel,
    direction: CreativeDirection,
    brand: Brand,
    *,
    tokens: TokenSet | None = None,
    page_format_name: str = "A4",
) -> IterationResult:
    """Run exactly one review-driven iteration end to end.

    ``finding`` must be one of ``evaluate(base_plan, direction, tokens)``'s
    own findings — this function does not itself review ``base_plan``, so
    the caller decides which finding an iteration responds to (ADOS-M1.4
    §13: one finding, one recommendation, one command, one compose, one
    review — never an automatic multi-finding loop within this call;
    :func:`select_recommendation` is the layer above that picks *which*
    finding, this one only ever executes what it is given).

    Raises :class:`NoRecommendationError`, :class:`~brand.creative.intent.IntentValidationError`,
    :class:`~brand.creative.scope.UnsupportedScopeError`,
    :class:`~brand.creative.scope.ScopeInfeasibleError`,
    :class:`~brand.creative.composer.CompositionError`, or
    :class:`IterationNoImprovementError`. On every one of these, nothing
    is returned and the caller's ``base_plan`` remains the current plan —
    the same discipline ``brand.creative.scope.compose_scoped`` already
    holds to, extended one step further to cover "composed, but did not
    actually help."
    """
    recommendation = recommend(finding)

    intent = CommandIntent(
        type=recommendation.command_type,
        target=IntentTarget(type=TargetType.PAGE, id=str(recommendation.target_page)),
        parameters=recommendation.parameters,
    )

    domain_errors = validate_intent(content, intent, page_count=len(base_plan.pages))
    if domain_errors:
        raise IntentValidationError(domain_errors)

    new_content, new_direction, resolution = apply_intent(content, direction, intent)

    scope = CompositionScope(type=ScopeType.PAGE, id=str(recommendation.target_page))
    new_plan, diff, resolved_scope = compose_scoped(
        base_plan, scope, new_content, new_direction, brand,
        tokens=tokens, page_format_name=page_format_name,
    )

    resolved_tokens = tokens or brand.resolve_tokens()
    before_evaluation = evaluate(base_plan, direction, resolved_tokens)
    after_evaluation = evaluate(new_plan, new_direction, resolved_tokens)

    before_metric = finding.actual
    after_metric = getattr(new_plan.pages[recommendation.target_page], finding.metric)
    if before_metric is None:
        raise NoRecommendationError(
            f"finding {finding.code!r} has no 'actual' value to compare against"
        )

    delta = after_metric - before_metric
    if recommendation.expected_direction == "increase":
        moved, wrong_way = delta > 0, delta < 0
    else:
        moved, wrong_way = delta < 0, delta > 0

    if not moved:
        outcome = IterationOutcome.FAILED if wrong_way else IterationOutcome.NO_IMPROVEMENT
        raise IterationNoImprovementError(
            f"{intent.type.value} on page {recommendation.target_page} did not move "
            f"{finding.metric} {recommendation.expected_direction} "
            f"(before={before_metric:.4f}, after={after_metric:.4f})",
            before_metric,
            after_metric,
            outcome,
        )

    if finding.threshold is None:
        outcome = IterationOutcome.IMPROVED
    else:
        reached = (
            after_metric >= finding.threshold
            if recommendation.expected_direction == "increase"
            else after_metric <= finding.threshold
        )
        outcome = IterationOutcome.IMPROVED if reached else IterationOutcome.IMPROVED_BUT_THRESHOLD_NOT_REACHED

    return IterationResult(
        finding=finding.to_dict(),
        recommendation=recommendation,
        intent=intent,
        resolution=resolution,
        resolved_scope=resolved_scope,
        diff=diff,
        metric=finding.metric,
        before_metric=before_metric,
        after_metric=after_metric,
        outcome=outcome,
        before_plan_hash=base_plan.plan_hash,
        after_plan_hash=new_plan.plan_hash,
        plan=new_plan,
        before_evaluation=before_evaluation.to_dict(),
        after_evaluation=after_evaluation.to_dict(),
    )

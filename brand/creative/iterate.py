"""
brand/creative/iterate.py

The closed loop (ADOS M1.4): Review -> deterministic recommendation ->
CommandIntent -> validate -> apply -> scoped compose -> Review again.

    PagePlan -> evaluate() -> Finding -> recommend() -> Recommendation
             -> CommandIntent -> validate_intent() -> apply_intent()
             -> compose_scoped() -> PagePlan' -> evaluate()

Nothing here lays out a page, chooses a direction value, or mutates a
PagePlan directly. This module's only job is the arrow between "a finding"
and "a validated, executed, scoped command" — every step it delegates to
already exists: ``brand.creative.evaluate`` finds problems,
``brand.creative.intent`` turns a command into Composer inputs,
``brand.creative.scope`` bounds and runs the recomposition. A finding is
never turned into a PagePlan edit by this module directly; only by that
existing pipeline, called in the existing order.

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
"""

from __future__ import annotations

from typing import Any, Literal

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
from brand.validation.brand_validator import Finding

_Frozen = ConfigDict(frozen=True, extra="forbid")

ImprovementDirection = Literal["increase", "decrease"]


class Recommendation(BaseModel):
    """A deterministic proposal: apply this command, at this target, because
    of this finding. Produced by :func:`recommend`, never hand-built by a
    caller — the mapping from finding code to command is this module's one
    piece of policy, and it lives in exactly one place (``_RECOMMENDATIONS``)."""

    model_config = _Frozen

    finding_code: str
    command_type: IntentType
    parameters: dict[str, Any]
    target_page: int
    reason: str
    expected_direction: ImprovementDirection


class NoRecommendationError(RuntimeError):
    """A finding has no deterministic command mapping.

    Raised rather than guessing — an unmapped finding is real information
    (this class of problem is not yet automatable), not a reason to invent
    a command the finding never asked for.
    """


class IterationNoImprovementError(RuntimeError):
    """The mapped command executed and composed, but the target metric did
    not move in the direction the recommendation promised.

    This is the ADOS-M1.4 §17 case: a successful ``compose()`` call is not
    the same thing as a successful iteration. ``before``/``after`` are
    carried on the exception so a caller can report exactly what happened
    without recomputing anything.
    """

    def __init__(self, message: str, before: float, after: float):
        self.before = before
        self.after = after
        super().__init__(message)


#: The deterministic finding-code -> command mapping (ADOS-M1.4 §6/§7).
#:
#: Deliberately small. Only ``FILL_RATIO_LOW`` is mapped, and to
#: ``change_page_direction`` rather than the spec's illustrative
#: ``increase_image_emphasis`` — see the module docstring for the measured
#: reason. ``FILL_RATIO_HIGH`` is a real finding code (wired in
#: ``brand.creative.evaluate``) with deliberately no entry here: the H13
#: ceiling it reports is already a hard Composer constraint that the
#: shipped example content never actually triggers, so there is nothing
#: to verify a command against yet. ``recommend()`` reports
#: :class:`NoRecommendationError` for it rather than inventing one.
_RECOMMENDATIONS: dict[str, tuple[IntentType, dict[str, Any], ImprovementDirection]] = {
    "FILL_RATIO_LOW": (
        IntentType.CHANGE_PAGE_DIRECTION,
        {"direction_id": "image-led"},
        "increase",
    ),
}


def recommend(finding: Finding) -> Recommendation:
    """Turn one structured finding into one deterministic recommendation.

    Raises :class:`NoRecommendationError` if ``finding.code`` has no
    mapping, or if the finding does not name a page (``page_index`` is
    ``None`` — a document-level finding, which M1.4 does not act on).
    """
    if finding.page_index is None:
        raise NoRecommendationError(
            f"finding {finding.code or finding.message!r} does not name a target page"
        )
    mapped = _RECOMMENDATIONS.get(finding.code)
    if mapped is None:
        raise NoRecommendationError(
            f"finding code {finding.code!r} has no deterministic command mapping"
        )
    command_type, parameters, expected_direction = mapped
    return Recommendation(
        finding_code=finding.code,
        command_type=command_type,
        parameters=parameters,
        target_page=finding.page_index,
        reason=finding.message,
        expected_direction=expected_direction,
    )


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
    review — never an automatic multi-finding loop).

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

    improved = (
        after_metric > before_metric
        if recommendation.expected_direction == "increase"
        else after_metric < before_metric
    )
    if not improved:
        raise IterationNoImprovementError(
            f"{intent.type.value} on page {recommendation.target_page} did not move "
            f"{finding.metric} {recommendation.expected_direction} "
            f"(before={before_metric:.4f}, after={after_metric:.4f})",
            before_metric,
            after_metric,
        )

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
        before_plan_hash=base_plan.plan_hash,
        after_plan_hash=new_plan.plan_hash,
        plan=new_plan,
        before_evaluation=before_evaluation.to_dict(),
        after_evaluation=after_evaluation.to_dict(),
    )

"""
brand/llm/loop/recommend.py

Finding -> Recommendation (ADOS-M3.6 §15/§16/§17). A small, deterministic
capability registry — mirroring ``brand.creative.iterate.CAPABILITIES``'s
own shape and its own honesty about being small (that registry has
exactly one entry; this one has three) — maps a finding's ``code`` to a
:class:`~brand.llm.loop.model.DesignIntentPatch`. A finding with no
registered capability is handed to a bounded LLM tie-breaker (only when
the caller supplies one and policy allows it); a finding neither path
can address is recorded as a
:class:`~brand.llm.loop.model.SkippedRecommendation`, never guessed at.

**Why these three, and not more.** ``FILL_RATIO_LOW``/``FILL_RATIO_HIGH``
are the only ``brand.creative.evaluate`` findings that already carry a
``code`` (see ``brand/creative/finding_registry.py``'s own registry) —
every other conformance/editorial finding ``evaluate()`` can raise is a
Composer-implementation defect (per that module's own docstring), not a
design decision a ``DesignIntentPatch`` could plausibly fix.
``DESIGN_ISSUE_BRAND_CONFLICT`` is the one M3.4 ``DesignIssue`` type
whose own root cause (an expressive ``typography_hierarchy`` on a
restrained-personality brand — see ``brand.llm.design.validation``'s
own DES-009) has a single, unambiguous corrective field. The other four
``DesignIssueType`` values (asset scarcity, contradictory density,
unsupported visual inference, missing content acknowledged) have no
safe automatic fix — asset scarcity needs more assets, not a strategy
change — and are always skipped with reason ``NO_SAFE_COMMAND_EXISTS``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from brand.llm.loop.fingerprint import finding_fingerprint, recommendation_fingerprint
from brand.llm.loop.model import DesignIntentPatch, Recommendation, SkippedRecommendation
from brand.llm.loop.vocabulary import RecommendationSource, SkippedRecommendationReason
from brand.llm.provider import ProviderMetadata
from brand.validation.brand_validator import Finding, Severity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecommendationCapability:
    finding_code: str
    target: str
    value: str
    expected_effect: str
    description: str


CAPABILITIES: tuple[RecommendationCapability, ...] = (
    RecommendationCapability(
        finding_code="FILL_RATIO_LOW", target="composition_strategy", value="image_led",
        expected_effect="fill_ratio increases",
        description="Switch to an image-led composition strategy — the same, empirically verified "
                    "lever brand.creative.iterate's own FILL_RATIO_LOW capability uses, expressed here "
                    "as a DesignIntent field rather than a direct CommandIntent.",
    ),
    RecommendationCapability(
        finding_code="FILL_RATIO_HIGH", target="density", value="low",
        expected_effect="fill_ratio decreases",
        description="Lower the target text density so the composed page has room to fit its content "
                    "without exceeding the fill-ratio ceiling.",
    ),
    RecommendationCapability(
        finding_code="DESIGN_ISSUE_BRAND_CONFLICT", target="typography_hierarchy", value="restrained",
        expected_effect="the flagged brand conflict no longer applies",
        description="An expressive typography hierarchy on a brand whose own personality is quiet/"
                    "precise/pragmatic is exactly what DES-009 flags — the direct fix is to restrain it.",
    ),
)

CAPABILITIES_BY_CODE: dict[str, RecommendationCapability] = {c.finding_code: c for c in CAPABILITIES}

#: Findings this loop never turns into a recommendation, regardless of
#: registry contents — INFO-severity findings are advisory by ADOS-M3.6
#: §13's own semantics ("normally does not trigger automatic iteration").
_NON_ACTIONABLE_SEVERITIES = frozenset({Severity.INFO})


def _priority(finding: Finding) -> tuple[int, str]:
    from brand.validation.brand_validator import SEVERITY_ORDER

    return (SEVERITY_ORDER[finding.severity], finding.code or finding.field)


def _capability_recommendation(finding: Finding, priority: int) -> Optional[Recommendation]:
    capability = CAPABILITIES_BY_CODE.get(finding.code)
    if capability is None:
        return None
    fp = finding_fingerprint(finding)
    patch = DesignIntentPatch(
        target=capability.target, value=capability.value,
        rationale=f"{finding.code}: {finding.message} -> {capability.description}",
    )
    return Recommendation(
        finding_fingerprint=fp, action=capability.target, rationale=capability.description,
        priority=priority, confidence=1.0, expected_effect=capability.expected_effect,
        executable=True, source=RecommendationSource.DETERMINISTIC, patch=patch,
    )


def select_recommendation(
    findings: tuple[Finding, ...],
    tried_recommendation_fingerprints: frozenset[str] = frozenset(),
    *,
    llm_propose: Optional[Any] = None,
) -> tuple[Optional[Recommendation], tuple[SkippedRecommendation, ...]]:
    """Deterministic-first selection over every actionable finding
    (ADOS-M3.6 §23/§16). Returns the single highest-priority
    recommendation not already exhausted by ``tried_recommendation_fingerprints``,
    plus every finding this call considered and could not/did not act
    on. ``llm_propose``, when given, is called with exactly one
    ``Finding`` (the highest-priority coded, uncapable one) and must
    return ``(Recommendation | None, ProviderMetadata | None)``.
    """
    candidates = [
        f for f in findings
        if f.severity not in _NON_ACTIONABLE_SEVERITIES
    ]
    candidates.sort(key=_priority)

    skipped: list[SkippedRecommendation] = []
    chosen: Optional[Recommendation] = None
    uncapable_top: Optional[Finding] = None

    for finding in candidates:
        fp = finding_fingerprint(finding)
        if not finding.code:
            # Composer-implementation defects (no code) are real
            # information but this package never guesses a DesignIntent
            # fix for one — see the module docstring.
            skipped.append(SkippedRecommendation(
                finding_fingerprint=fp, reason=SkippedRecommendationReason.UNSUPPORTED_SCOPE,
                detail=f"uncoded finding at {finding.field!r} has no DesignIntent-level correction",
            ))
            continue

        recommendation = _capability_recommendation(finding, priority=_priority(finding)[0])
        if recommendation is None:
            if uncapable_top is None:
                uncapable_top = finding
            skipped.append(SkippedRecommendation(
                finding_fingerprint=fp, reason=SkippedRecommendationReason.NO_SAFE_COMMAND_EXISTS,
                detail=f"{finding.code}: no deterministic recommendation capability is registered for it",
            ))
            continue

        rec_fp = recommendation_fingerprint(fp, recommendation.patch)
        if rec_fp in tried_recommendation_fingerprints:
            skipped.append(SkippedRecommendation(
                finding_fingerprint=fp, reason=SkippedRecommendationReason.ALREADY_ATTEMPTED,
                detail=f"{recommendation.patch.target}={recommendation.patch.value} was already "
                       f"attempted for this finding in this lineage and did not help",
            ))
            continue

        if chosen is None:
            chosen = recommendation
        else:
            skipped.append(SkippedRecommendation(
                finding_fingerprint=fp, reason=SkippedRecommendationReason.ALREADY_ATTEMPTED,
                detail="a higher-priority recommendation was selected this iteration instead",
            ))

    if chosen is None and uncapable_top is not None and llm_propose is not None:
        fp = finding_fingerprint(uncapable_top)
        proposal, _metadata = llm_propose(uncapable_top)
        if proposal is not None:
            rec_fp = recommendation_fingerprint(fp, proposal.patch)
            if rec_fp not in tried_recommendation_fingerprints:
                chosen = proposal
                skipped = [
                    s for s in skipped
                    if not (s.finding_fingerprint == fp and s.reason is SkippedRecommendationReason.NO_SAFE_COMMAND_EXISTS)
                ]

    return chosen, tuple(skipped)


# ---------------------------------------------------------------------------
# Bounded LLM tie-breaker (ADOS-M3.6 §17) — proposes one closed-vocabulary
# DesignIntentPatch, never a command, never arbitrary code.
# ---------------------------------------------------------------------------


def make_llm_proposer(model: Optional[str] = None, max_tokens: Optional[int] = None):
    """Returns a callable ``(finding) -> (Recommendation | None, ProviderMetadata | None)``
    suitable for ``select_recommendation``'s ``llm_propose`` — a thin
    closure so the orchestrator can count real LLM calls without this
    module needing to know about iteration budgets itself."""
    import os

    from pydantic import BaseModel, ConfigDict

    from brand.llm.loop.model import PATCHABLE_FIELDS

    class RawPatchChoice(BaseModel):
        model_config = ConfigDict(extra="forbid")

        target: Optional[str] = None
        value: Optional[str] = None
        rationale: str = ""

    def propose(finding: Finding) -> tuple[Optional[Recommendation], Optional[ProviderMetadata]]:
        from brand.llm.loop.patch import _FIELD_ENUM
        from brand.llm.loop.prompt import build_loop_system_prompt, build_loop_user_message
        from brand.llm.providers.claude_provider import call_structured, get_client

        chosen_model = model or os.environ.get("CLOSED_LOOP_MODEL", "claude-opus-5")
        chosen_max_tokens = max_tokens or int(os.environ.get("CLOSED_LOOP_MAX_TOKENS", 1024))

        client = get_client()
        raw, metadata = call_structured(
            client, model=chosen_model, max_tokens=chosen_max_tokens,
            system_prompt=build_loop_system_prompt(), user_message=build_loop_user_message(finding),
            output_format=RawPatchChoice, provider_name="claude",
        )

        if not raw.target or not raw.value or raw.target not in PATCHABLE_FIELDS:
            return None, metadata
        enum_cls = _FIELD_ENUM[raw.target]
        try:
            coerced = enum_cls(raw.value)
        except ValueError:
            logger.warning("closed loop: LLM proposed unknown value %r for %r, dropping", raw.value, raw.target)
            return None, metadata

        fp = finding_fingerprint(finding)
        patch = DesignIntentPatch(target=raw.target, value=coerced.value, rationale=raw.rationale)
        recommendation = Recommendation(
            finding_fingerprint=fp, action=raw.target,
            rationale=raw.rationale or f"LLM-proposed correction for {finding.code}",
            priority=0, confidence=0.6, expected_effect="unverified — LLM-proposed",
            executable=True, source=RecommendationSource.LLM, patch=patch,
        )
        return recommendation, metadata

    return propose

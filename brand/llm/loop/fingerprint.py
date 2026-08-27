"""
brand/llm/loop/fingerprint.py

Deterministic fingerprints (ADOS-M3.6 §42) — sha256 over a canonical
JSON projection of the *semantically relevant* fields, never a
timestamp or a random id. Used for no-progress detection (§34),
oscillation detection (§35), repeated-recommendation detection (§36),
and reproducibility (§83).
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from brand.llm.command.model import CommandPlan
    from brand.llm.design.model import DesignIntent
    from brand.llm.loop.model import DesignIntentPatch
    from brand.validation.brand_validator import Finding


def _hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def design_intent_fingerprint(design_intent: "DesignIntent") -> str:
    """The document-level decision surface this package can actually
    patch — composition/density/typography/whitespace/colour/grid/
    rhythm — plus every section's own composition-relevant fields. Two
    ``DesignIntent``s that differ only in ``id``/``created_at``/
    ``metadata`` fingerprint identically, which is the point: identity
    is a design decision, not an object's own bookkeeping.

    Deliberately keys each section by ``visual_role`` (a real,
    content-derived tag: ``intro``/``hero``/``process``/... — stable
    across independent planning runs given the same narrative), never
    by ``SectionDesign.section_id``: that field is a foreign key into
    ``NarrativePlan.sections[].id``, and ``plan_narrative()`` mints a
    fresh random id for every section on every call. A fingerprint keyed
    on it would call two structurally-identical DesignIntents "different"
    purely because they came from two independently-planned
    NarrativePlans — undermining the reproducibility this fingerprint
    exists for (ADOS-M3.6 §83; caught by this milestone's own production
    hardening pass, which ran the same real inputs through
    ``run_iteration`` ten times and diffed the result)."""
    payload = {
        "composition_strategy": design_intent.composition_strategy.value,
        "density": design_intent.density.value,
        "typography_hierarchy": design_intent.typography_hierarchy.value,
        "color_strategy": design_intent.color_strategy.value,
        "grid_strategy": design_intent.grid_strategy.value,
        "whitespace_strategy": design_intent.whitespace_strategy.value,
        "rhythm": design_intent.rhythm.value,
        "visual_language": sorted(v.value for v in design_intent.visual_language),
        "sections": sorted(
            (tuple(v.value for v in sd.visual_role), sd.composition_mode.value, sd.text_density.value,
             sd.image_density.value, sd.typography_hierarchy.value)
            for sd in design_intent.section_designs
        ),
    }
    return _hash(payload)


def command_plan_fingerprint(plan: "CommandPlan") -> str:
    payload = sorted(
        (c.intent.type.value, c.intent.target.type.value, c.intent.target.id,
         json.dumps(c.intent.parameters, sort_keys=True))
        for c in plan.commands
    )
    return _hash(payload)


def finding_fingerprint(finding: "Finding") -> str:
    """Stable cross-iteration identity for one finding (ADOS-M3.6 §69):
    ``code``/``metric`` only — never ``page_index`` (a document-scoped
    command can shift how many pages exist between iterations, so "the
    same problem, now on a different page" must still fingerprint the
    same) and never the free-text ``message`` alone (its wording can
    change without the underlying condition changing).

    A finding with no ``code`` (most of ``brand.creative.evaluate``'s
    own conformance checks) has no stable cross-iteration identity to
    track by design — those are Composer-implementation defects, not
    design decisions this loop patches (see ``findings.py``). But
    several of them do legitimately share the exact same ``field``
    text (e.g. ``evaluate.py``'s own document-level pacing and
    rejected-candidate checks both use ``field="plan"``) while being
    genuinely different findings — ``category`` plus a short hash of
    ``message`` disambiguates those within one evaluation without
    claiming any cross-iteration stability for them that does not
    actually exist (a real bug caught by this milestone's own live
    browser smoke test: two such findings collided to one fingerprint,
    producing a duplicate React list key)."""
    if finding.code:
        return _hash({"code": finding.code, "metric": finding.metric})
    return _hash({
        "code": f"uncoded:{finding.field}", "category": finding.category.value,
        "message_hash": _hash(finding.message),
    })


def state_fingerprint(direction_id: str, text_density: float | None, image_ratio: float | None) -> str:
    return _hash({"direction_id": direction_id, "text_density": text_density, "image_ratio": image_ratio})


def content_fingerprint(content: Any) -> str:
    """Works for either real content object this loop ever touches
    (``ContentIntelligenceModel`` or ``ContentModel``) via their shared
    ``to_dict()`` convention — never re-derives what "the same content"
    means from scratch."""
    return _hash(content.to_dict() if hasattr(content, "to_dict") else content)


def recommendation_fingerprint(finding_fp: str, patch: "DesignIntentPatch") -> str:
    """Identity for "this exact fix, for this exact problem" — ADOS-M3.6
    §36's repeated-failed-recommendation tracking keys on this, not on
    a random ``Recommendation.id``."""
    return _hash({"finding_fingerprint": finding_fp, "target": patch.target, "value": patch.value})

"""
brand/llm/loop/findings.py

The evaluation stage (ADOS-M3.6 §11/§12) — connects the real, existing
``brand.creative.evaluate.evaluate()`` to the loop, and the one honest
extension this milestone adds: a real ``DesignIntent.design_issues``
(M3.4's own flagged tensions — a brand conflict, asset scarcity — that
``brand.llm.command`` already refuses to silently auto-fix) is folded
into the *same* ``Finding`` vocabulary the loop reasons over, rather
than the loop having to understand two different "something is wrong"
representations. No second Finding/issue system is introduced — see
ADOS-M3.6 §12.

Also implements finding *identity* and *resolution tracking* (§68/§69/
§70): whether a finding is the "same" one across iterations is decided
by :func:`~brand.llm.loop.fingerprint.finding_fingerprint`, never by
whether a command happened to execute.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from brand.llm.loop.fingerprint import finding_fingerprint
from brand.llm.loop.model import FindingRecord
from brand.llm.loop.vocabulary import FindingResolutionStatus
from brand.validation.brand_validator import Category, Finding, Severity

if TYPE_CHECKING:
    from brand.creative.direction import CreativeDirection
    from brand.creative.plan import PagePlan
    from brand.llm.design.model import DesignIntent
    from brand.models.tokens import TokenSet


def _design_issues_as_findings(design_intent: "DesignIntent") -> list[Finding]:
    """A real M3.4 ``DesignIssue`` is real information the loop should
    act on the same way it acts on an ``evaluate()`` finding — coded, so
    ``recommend.py`` can map it to a capability, and WARN (never BLOCK):
    a flagged design tension does not, on its own, mean the composed
    document is unpublishable."""
    return [
        Finding(
            Severity.WARN, Category.CONSISTENCY, f"design_issue:{issue.type.value}",
            issue.description, code=f"DESIGN_ISSUE_{issue.type.value.upper()}",
        )
        for issue in design_intent.design_issues
    ]


def finding_from_record(record: FindingRecord) -> Finding:
    """The inverse of ``Finding.to_dict()`` — reconstructs the real,
    frozen dataclass from a stored ``FindingRecord`` so
    ``recommend.select_recommendation`` can reason over it the same way
    it reasons over a freshly-collected finding, without a second,
    dict-shaped "finding-like" type."""
    data = record.finding
    return Finding(
        severity=Severity(data["severity"]), category=Category(data["category"]),
        field=data["field"], message=data["message"], suggestion=data.get("suggestion", ""),
        rule=data.get("rule", ""), code=data.get("code", ""), metric=data.get("metric", ""),
        actual=data.get("actual"), threshold=data.get("threshold"), page_index=data.get("page_index"),
    )


def collect_findings(
    plan: "PagePlan", direction: "CreativeDirection", tokens: "TokenSet", design_intent: "DesignIntent",
) -> tuple[Finding, ...]:
    """The real ``evaluate()`` findings plus this DesignIntent's own
    flagged issues — the complete set of "something is wrong" signals
    the loop's recommendation stage may act on."""
    from brand.creative.evaluate import evaluate

    evaluation = evaluate(plan, direction, tokens)
    return tuple(evaluation.report.findings) + tuple(_design_issues_as_findings(design_intent))


def classify_findings(
    current: tuple[Finding, ...],
    prior_records: dict[str, FindingRecord],
    sequence: int,
) -> tuple[FindingRecord, ...]:
    """Compare this iteration's findings against the latest known record
    per fingerprint across the whole lineage so far (ADOS-M3.6 §70).

    A finding whose fingerprint was previously RESOLVED and has now
    reappeared is REGRESSED, not merely re-opened (§68's own "never
    resolved merely because a command executed" is the same discipline
    applied backwards: a finding is never quietly re-opened as if it
    were new, either).
    """
    seen_fingerprints: set[str] = set()
    records: list[FindingRecord] = []

    for finding in current:
        fp = finding_fingerprint(finding)
        seen_fingerprints.add(fp)
        prior = prior_records.get(fp)
        if prior is None:
            status = FindingResolutionStatus.OPEN
            first_seen = sequence
        elif prior.status is FindingResolutionStatus.RESOLVED:
            status = FindingResolutionStatus.REGRESSED
            first_seen = prior.first_seen_sequence
        else:
            status = prior.status
            first_seen = prior.first_seen_sequence
        records.append(FindingRecord(
            fingerprint=fp, finding=finding.to_dict(), status=status,
            first_seen_sequence=first_seen, last_seen_sequence=sequence,
        ))

    for fp, prior in prior_records.items():
        if fp in seen_fingerprints:
            continue
        if prior.status in (FindingResolutionStatus.OPEN, FindingResolutionStatus.IN_PROGRESS):
            records.append(FindingRecord(
                fingerprint=fp, finding=prior.finding, status=FindingResolutionStatus.RESOLVED,
                first_seen_sequence=prior.first_seen_sequence, last_seen_sequence=sequence,
            ))
        else:
            records.append(prior)

    return tuple(records)

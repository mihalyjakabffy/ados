"""ADOS-M3.6 — brand/llm/loop/findings.py."""

from __future__ import annotations

from brand.llm.design.model import DesignIntent, DesignIssue, DesignIssueType
from brand.llm.design.vocabulary import CompositionStrategy, TextDensity
from brand.llm.loop.findings import _design_issues_as_findings, classify_findings, finding_from_record
from brand.llm.loop.fingerprint import finding_fingerprint
from brand.llm.loop.vocabulary import FindingResolutionStatus
from brand.validation.brand_validator import Category, Finding, Severity


def _finding(code="FILL_RATIO_LOW", severity=Severity.ERROR) -> Finding:
    return Finding(severity, Category.STRUCTURAL, "page 1", "message", code=code, metric="fill_ratio")


def test_design_issues_become_coded_warn_findings():
    di = DesignIntent(
        project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM,
        design_issues=(DesignIssue(type=DesignIssueType.BRAND_CONFLICT, description="expressive on quiet brand"),),
    )
    findings = _design_issues_as_findings(di)
    assert len(findings) == 1
    assert findings[0].code == "DESIGN_ISSUE_BRAND_CONFLICT"
    assert findings[0].severity is Severity.WARN


def test_classify_findings_marks_new_findings_open():
    records = classify_findings((_finding(),), {}, sequence=1)
    assert len(records) == 1
    assert records[0].status is FindingResolutionStatus.OPEN
    assert records[0].first_seen_sequence == 1


def test_classify_findings_marks_disappeared_findings_resolved():
    f = _finding()
    records1 = classify_findings((f,), {}, sequence=1)
    prior = {r.fingerprint: r for r in records1}
    records2 = classify_findings((), prior, sequence=2)
    assert records2[0].status is FindingResolutionStatus.RESOLVED
    assert records2[0].first_seen_sequence == 1
    assert records2[0].last_seen_sequence == 2


def test_classify_findings_marks_reappeared_resolved_as_regressed():
    f = _finding()
    records1 = classify_findings((f,), {}, sequence=1)
    prior = {r.fingerprint: r for r in records1}
    records2 = classify_findings((), prior, sequence=2)
    prior2 = {r.fingerprint: r for r in records2}
    records3 = classify_findings((f,), prior2, sequence=3)
    assert records3[0].status is FindingResolutionStatus.REGRESSED
    assert records3[0].first_seen_sequence == 1


def test_classify_findings_keeps_still_open_findings_open_across_iterations():
    f = _finding()
    records1 = classify_findings((f,), {}, sequence=1)
    prior = {r.fingerprint: r for r in records1}
    records2 = classify_findings((f,), prior, sequence=2)
    assert records2[0].status is FindingResolutionStatus.OPEN
    assert records2[0].last_seen_sequence == 2


def test_finding_from_record_reconstructs_a_real_finding():
    f = _finding(code="FILL_RATIO_HIGH", severity=Severity.WARN)
    record = classify_findings((f,), {}, sequence=1)[0]
    restored = finding_from_record(record)
    assert restored.code == "FILL_RATIO_HIGH"
    assert restored.severity is Severity.WARN
    assert finding_fingerprint(restored) == finding_fingerprint(f)

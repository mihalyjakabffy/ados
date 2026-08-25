"""
brand/creative/evaluate.py

What a composed plan gets wrong, and what nobody checked.

Two things, kept apart, because they fail independently and because confusing
them is how a quality report stops being read:

**Conformance** is deterministic and blocking. The composer already refuses to
emit a page that breaks a hard constraint, so anything found here is a defect
in the composer rather than in the document — which is exactly why it is worth
re-checking the plan it produced instead of trusting it.

**Editorial quality** is advisory and says so. Underfilled pages, a measure
outside 45–75 characters, a pacing sequence that drifted from the direction's:
each is a judgement a person may reasonably overrule, so none of them blocks.

**There is no score.** A single number invites optimising against the number
and discards the only useful output — which field, what is wrong, and how to
fix it. What is reported instead is findings plus **coverage**: the fraction
of the checkable surface that was actually checked, and the named properties
that were not. "Fourteen of seventeen checkable properties verified; audience
fit and originality are not machine-checkable and were not assessed" is a more
honest sentence than "82 %", and a more useful one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from brand import ados
from brand.creative.composer import MEASURE_CHARS, TypeMetrics
from brand.creative.direction import CreativeDirection
from brand.creative.plan import PagePlan
from brand.models.tokens import TokenSet
from brand.validation.brand_validator import (
    Category,
    Finding,
    Severity,
    ValidationReport,
)

#: Properties of a document that no machine in this system can assess, named
#: so that coverage can report them rather than quietly omitting them. A gap
#: nobody has written down is a gap everybody assumes is covered.
NOT_MACHINE_CHECKABLE: tuple[str, ...] = (
    "audience fit",
    "originality",
    "whether the argument persuades",
)


@dataclass
class Evaluation:
    """Findings, plus an honest account of what was and was not checked."""

    plan_hash: str = ""
    report: ValidationReport = field(default_factory=ValidationReport)
    checked: tuple[str, ...] = ()
    not_checked: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.report.ok

    @property
    def coverage(self) -> str:
        total = len(self.checked) + len(self.not_checked)
        return (
            f"{len(self.checked)} of {total} checkable properties verified; "
            + ", ".join(self.not_checked)
            + " were not assessed."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_hash": self.plan_hash,
            "coverage": self.coverage,
            "checked": list(self.checked),
            "not_checked": list(self.not_checked),
            **self.report.to_dict(),
        }

    def summary(self) -> str:
        counts = self.report.to_dict()["counts"]
        return (
            f"{'ok' if self.ok else 'findings'} · "
            f"{counts['ERROR']} error, {counts['WARN']} warn, "
            f"{counts['INFO']} info · {self.coverage}"
        )


def evaluate(
    plan: PagePlan, direction: CreativeDirection, tokens: TokenSet
) -> Evaluation:
    """Check a composed plan. Never raises; a broken plan is a report."""
    ev = Evaluation(plan_hash=plan.plan_hash)
    ev.report.brand_label = f"{plan.project_name} · {plan.direction}"
    tm = TypeMetrics.from_tokens(tokens)
    low, high = ados.fill_ratio_bounds()

    checked: list[str] = []
    findings = ev.report.findings

    # -- conformance: blocking -------------------------------------------

    checked.append("H13 fill-ratio ceiling")
    for page in plan.pages:
        if page.fill_ratio > high:
            findings.append(Finding(
                Severity.ERROR, Category.STRUCTURAL, f"page {page.index + 1}",
                f"fill ratio {page.fill_ratio:.2f} above the {high:.2f} "
                f"ceiling — the page has no room left to read in",
                "Move a block to the next page.", "H13 / ADOS-3.7.010",
                code="FILL_RATIO_HIGH", metric="fill_ratio",
                actual=page.fill_ratio, threshold=high, page_index=page.index,
            ))

    checked.append("H12 local ink coverage")
    ceiling = ados.local_coverage_max()
    for page in plan.pages:
        if page.ink_coverage_max > ceiling + 1e-9:
            findings.append(Finding(
                Severity.ERROR, Category.STRUCTURAL, f"page {page.index + 1}",
                f"local ink coverage {page.ink_coverage_max:.2f} above "
                f"{ceiling:.2f}",
                "Open the leading, or set the block at a lower rank.",
                "H12 / ADOS-3.7.020",
            ))

    checked.append("H14 alignment edges")
    max_edges = ados.alignment_edges_max_per_axis()
    for page in plan.pages:
        if page.alignment_edges_x > max_edges:
            findings.append(Finding(
                Severity.ERROR, Category.STRUCTURAL, f"page {page.index + 1}",
                f"{page.alignment_edges_x} alignment edges on the x axis, "
                f"above {max_edges}",
                "Fewer column spans per page.", "H14 / ADOS-3.11.040",
            ))

    checked.append("H15 cap-height floor")
    checked.append("H6 sub-module lattice")
    lattice = ados.submodule_mm()
    floor = ados.absolute_cap_floor_mm()
    for page in plan.pages:
        for slot in page.slots:
            if slot.text and slot.cap_mm < floor - 1e-9:
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL,
                    f"page {page.index + 1} · {slot.component}",
                    f"{slot.cap_mm} mm cap is below the {floor} mm floor",
                    "Set it at a higher step.", "H15 / ADOS-3.4.010",
                ))
            if abs(slot.y_mm % lattice) > 1e-6:
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL,
                    f"page {page.index + 1} · {slot.component}",
                    f"origin y {slot.y_mm} is off the {lattice:g} mm lattice",
                    "Snap the row height to a whole sub-module.",
                    "H6 / ADOS-3.3.030",
                ))

    checked.append("every content block placed")
    placed = list(plan.placed_blocks)
    if len(placed) != len(set(placed)):
        duplicated = sorted({b for b in placed if placed.count(b) > 1})
        findings.append(Finding(
            Severity.ERROR, Category.STRUCTURAL, "plan",
            f"block(s) placed more than once: {', '.join(duplicated)}",
            "A composer that places a block twice has lost its queue.",
            "ADOS-2.2.010 one authoritative carrier",
        ))

    checked.append("brand version pinned")
    if not plan.brand_version:
        findings.append(Finding(
            Severity.ERROR, Category.STRUCTURAL, "plan",
            "the plan does not name the brand version it was composed against",
            "Without it the document cannot be reprinted.", "",
        ))

    # -- editorial quality: advisory --------------------------------------

    checked.append("fill-ratio floor")
    for page in plan.pages[:-1]:
        if page.fill_ratio < low:
            findings.append(Finding(
                Severity.WARN, Category.CONSISTENCY, f"page {page.index + 1}",
                f"fill ratio {page.fill_ratio:.2f} below the {low:.2f} "
                f"guideline — the page is mostly empty",
                "Not a failure: whitespace is a device, and the last page of "
                "any document is underfull by arithmetic. Worth a look if it "
                "is not the last page.",
                "ADOS-3.7.010 (advisory here)",
                code="FILL_RATIO_LOW", metric="fill_ratio",
                actual=page.fill_ratio, threshold=low, page_index=page.index,
            ))

    checked.append("density against the direction's target")
    drift = abs(plan.mean_fill_ratio - direction.text_density)
    if drift > 0.15:
        findings.append(Finding(
            Severity.WARN, Category.CONSISTENCY, "plan",
            f"mean fill ratio {plan.mean_fill_ratio:.2f} against the "
            f"direction's target of {direction.text_density:.2f}",
            "Either the content does not suit this direction or the "
            "direction's target does not suit this content. Both are "
            "editorial decisions, not defects.",
            "",
        ))

    checked.append("measure in characters")
    for page in plan.pages:
        for slot in page.slots:
            if slot.rank != "body" or not slot.text:
                continue
            chars = tm.chars_per_line(slot.cap_mm, slot.width_mm)
            if not (MEASURE_CHARS[0] <= chars <= MEASURE_CHARS[1]):
                findings.append(Finding(
                    Severity.WARN, Category.CONSISTENCY,
                    f"page {page.index + 1} · {slot.component}",
                    f"measure is about {chars:.0f} characters, outside "
                    f"{MEASURE_CHARS[0]}–{MEASURE_CHARS[1]}",
                    "Change the column span the archetype gives this slot.",
                    "ADOS-3.6.010",
                ))
                break                            # one per page is the point

    checked.append("words per page against the direction")
    for page in plan.pages:
        if page.words > direction.words_per_page_max:
            findings.append(Finding(
                Severity.WARN, Category.CONSISTENCY, f"page {page.index + 1}",
                f"{page.words} words against the direction's ceiling of "
                f"{direction.words_per_page_max}",
                "Split the page, or choose a denser direction.", "",
            ))

    checked.append("pacing against the direction")
    wanted = direction.pacing
    got = plan.archetype_sequence
    matched = sum(
        1 for i, name in enumerate(wanted) if i < len(got) and got[i] == name
    )
    if wanted and matched < len(wanted):
        findings.append(Finding(
            Severity.INFO, Category.CONSISTENCY, "plan",
            f"{matched} of {len(wanted)} pacing positions matched: asked for "
            f"[{' · '.join(wanted)}], composed [{' · '.join(got)}]",
            "Pacing is a preference the objective weighs, not a constraint. "
            "A mismatch usually means the content does not have the shape "
            "the direction assumes.",
            "",
        ))

    checked.append("candidates considered and rejected")
    if not plan.rejected:
        findings.append(Finding(
            Severity.INFO, Category.STRUCTURAL, "plan",
            "no rejected candidates were recorded",
            "A plan with an empty rejection list cannot be audited: there is "
            "no way to see the layout was chosen rather than defaulted.",
            "ADOS-7.5.010",
        ))

    ev.checked = tuple(checked)
    ev.not_checked = NOT_MACHINE_CHECKABLE
    return ev

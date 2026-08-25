"""
brand/creative/finding_registry.py

What a finding code *means* — one place, so ``brand.creative.evaluate``,
``brand.creative.iterate`` and the frontend all read the same definition
instead of three copies quietly drifting apart (ADOS-M1.5 §5).

A registered finding is not the same thing as an actionable one.
``FindingDefinition`` states facts about the *check*: which metric it
reports, what severity it is normally raised at, what scope a fix to it
would have to operate in. Whether a *command* actually exists that can
move that metric is a separate question — answered by
``brand.creative.iterate``'s capability registry, not stored here (see
:func:`is_actionable`). A finding code can be registered, meaningful, and
still have no capability; that is the honest, expected state for most of
them, not a gap to paper over.
"""

from __future__ import annotations

from dataclasses import dataclass

from brand.creative.scope import ScopeType
from brand.validation.brand_validator import Severity


@dataclass(frozen=True)
class FindingDefinition:
    """Metadata about a *kind* of finding, not one instance of it.

    ``threshold`` is the guideline value the metric is checked against —
    documentation of the rule, not the specific number a particular page's
    finding reported (that lives on the ``Finding`` itself, in ``actual``).
    """

    code: str
    metric: str
    severity: Severity
    threshold: float
    scope: ScopeType
    description: str


#: Every finding code brand.creative.evaluate can emit with a `code` set.
#: Adding a check that sets `code` without registering it here is a bug —
#: tests_brand/test_finding_registry.py enforces that both directions agree.
FINDING_REGISTRY: dict[str, FindingDefinition] = {
    "FILL_RATIO_LOW": FindingDefinition(
        code="FILL_RATIO_LOW",
        metric="fill_ratio",
        severity=Severity.WARN,
        threshold=0.40,
        scope=ScopeType.PAGE,
        description="Fill ratio below the guideline — the page is mostly empty.",
    ),
    "FILL_RATIO_HIGH": FindingDefinition(
        code="FILL_RATIO_HIGH",
        metric="fill_ratio",
        severity=Severity.ERROR,
        threshold=0.85,
        scope=ScopeType.PAGE,
        description="Fill ratio above the ceiling — the page has no room left to read in.",
    ),
}


class UnknownFindingCodeError(KeyError):
    """A finding code with no entry in FINDING_REGISTRY."""


def get_finding_definition(code: str) -> FindingDefinition:
    try:
        return FINDING_REGISTRY[code]
    except KeyError:
        raise UnknownFindingCodeError(code) from None


def is_actionable(code: str) -> bool:
    """Whether a *proven* recommendation capability exists for this code.

    Deferred import, deliberately: ``brand.creative.iterate`` imports this
    module (to validate its capabilities' finding codes against the
    registry), so importing it back here at module load time would be
    circular. By the time anything calls ``is_actionable``, both modules
    are already loaded — this is the same "ask the one place that knows"
    pattern the rest of ADOS uses instead of duplicating the answer.
    """
    from brand.creative.iterate import CAPABILITIES_BY_FINDING_CODE

    return code in FINDING_REGISTRY and code in CAPABILITIES_BY_FINDING_CODE


def describe(code: str) -> dict[str, object]:
    """The registry's answer to "what does this code mean, and can ADOS
    act on it" — one call, used by the API response and nowhere else
    reimplemented."""
    definition = get_finding_definition(code)
    return {
        "code": definition.code,
        "metric": definition.metric,
        "severity": definition.severity.value,
        "threshold": definition.threshold,
        "scope": definition.scope.value,
        "actionable": is_actionable(code),
        "description": definition.description,
    }

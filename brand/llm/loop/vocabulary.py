"""
brand/llm/loop/vocabulary.py

ADOS-M3.6's closed vocabularies. Reuses ``brand.validation.brand_validator
.Severity``/``Category`` directly wherever a finding is involved — this
package never declares a second severity or category scale.
"""

from __future__ import annotations

from enum import Enum


class IterationStatus(str, Enum):
    """One HTTP call to the orchestrator (``run_iteration``) runs
    synchronously from ``PLANNING`` through to one terminal status below
    — this package does not implement a resumable, externally-driven
    state machine (a deliberate scope decision; see the architecture
    doc). Intermediate values are still real and recorded, in order, on
    ``Iteration.stage_log`` — the sequence in ADOS-M3.6 §4 is preserved
    as an audit trail, not as separately-persisted, independently
    resumable states."""

    PLANNING = "planning"
    DESIGN_READY = "design_ready"
    COMMANDS_GENERATED = "commands_generated"
    COMMANDS_VALIDATED = "commands_validated"
    EXECUTING = "executing"
    COMPOSED = "composed"
    EVALUATING = "evaluating"
    FINDINGS_AVAILABLE = "findings_available"
    RECOMMENDATIONS_AVAILABLE = "recommendations_available"
    # -- terminal ----------------------------------------------------
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"


TERMINAL_STATUSES = frozenset({
    IterationStatus.COMPLETED, IterationStatus.STOPPED,
    IterationStatus.FAILED, IterationStatus.BLOCKED, IterationStatus.AWAITING_APPROVAL,
})


class StopReason(str, Enum):
    """ADOS-M3.6 §32's own enumerated list, verbatim as values."""

    SUCCESS = "success"
    MAX_ITERATIONS = "max_iterations"
    NO_PROGRESS = "no_progress"
    REGRESSION = "regression"
    OSCILLATION_DETECTED = "oscillation_detected"
    NO_ACTIONABLE_RECOMMENDATION = "no_actionable_recommendation"
    VALIDATION_FAILURE = "validation_failure"
    STALE_STATE = "stale_state"
    AWAITING_APPROVAL = "awaiting_approval"
    BUDGET_EXCEEDED = "budget_exceeded"
    PROVIDER_ERROR = "provider_error"
    DESIGN_INVALID = "design_invalid"
    COMMAND_INVALID = "command_invalid"
    EXECUTION_FAILED = "execution_failed"
    COMPOSITION_FAILED = "composition_failed"
    EVALUATION_FAILED = "evaluation_failed"
    UNSUPPORTED_SCOPE = "unsupported_scope"
    REPEATED_FAILED_RECOMMENDATION = "repeated_failed_recommendation"


class IterationTrigger(str, Enum):
    INITIAL = "initial"
    FINDING_DRIVEN = "finding_driven"
    USER_REQUESTED = "user_requested"


class AutonomyLevel(str, Enum):
    """ADOS-M3.6 §38. Deliberately reuses
    ``brand.llm.command.vocabulary.CommandSafetyLevel`` as the gate
    (SAFE / REVIEW_RECOMMENDED / DESTRUCTIVE) rather than inventing a
    second risk scale — autonomy asks "which of M3.5's own safety
    labels may execute without a human", not a new question."""

    #: Never execute — plan, validate, and stop at AWAITING_APPROVAL
    #: every time. Equivalent to always dry-running.
    NONE = "none"
    #: Generate recommendations and commands but require approval for
    #: every command, regardless of safety_level.
    RECOMMEND = "recommend"
    #: Auto-execute SAFE commands; REVIEW_RECOMMENDED/DESTRUCTIVE ones
    #: require approval. The default.
    SAFE = "safe"
    #: Auto-execute everything M3.5's own validator accepts. Still never
    #: bypasses validate_intent()/CMD-* validation — "full" is a policy
    #: choice about *approval*, not a relaxation of safety checking.
    FULL = "full"


class FindingResolutionStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REGRESSED = "regressed"
    WONT_FIX = "wont_fix"
    UNSUPPORTED = "unsupported"


class RecommendationSource(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class SkippedRecommendationReason(str, Enum):
    NO_SAFE_COMMAND_EXISTS = "no_safe_command_exists"
    UNSUPPORTED_SCOPE = "unsupported_scope"
    ALREADY_ATTEMPTED = "already_attempted"
    LLM_DECLINED = "llm_declined"
    PATCH_INVALID = "patch_invalid"


class PatchOperation(str, Enum):
    """A single operation kind today — ``SET`` on one root-level scalar
    ``DesignIntent`` field. ADOS-M3.6 §19 names ``operation`` as a field
    on the patch schema for a future append/remove use this package's
    own document-scope limitation (§55) gives no real driver for yet;
    adding a second value with no capability that produces it would be
    exactly the "field with no current use case" M3.4's own model.py
    docstring already warns against."""

    SET = "set"

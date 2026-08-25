// Mirrors brand/creative/iterate.py exactly — the closed loop (M1.4):
// a review finding -> a deterministic recommendation -> a CommandIntent ->
// validate -> apply -> scoped compose -> review again. The mapping from a
// finding's code to a command lives in exactly one place, iterate.py's
// _RECOMMENDATIONS — this file only describes the shapes that cross the
// HTTP boundary, never a second copy of that mapping.

import type { CommandIntent, CompositionScope, IntentResolution, PagePlanDiff } from "./intent-types"
import type { Evaluation, EvaluationFinding, PagePlan } from "./pageplan-types"

export interface Recommendation {
  finding_code: string
  command_type: string
  parameters: Record<string, unknown>
  target_page: number
  reason: string
  expected_direction: "increase" | "decrease"
}

// M1.5 — the four states an iteration can end in. "improved" and
// "improved_but_threshold_not_reached" both succeed (a plan is returned);
// "no_improvement"/"failed" only ever appear inside an error response's
// detail.outcome, since brand.creative.iterate raises rather than
// returning a result for those two.
export type IterationOutcome =
  | "improved"
  | "improved_but_threshold_not_reached"
  | "no_improvement"
  | "failed"

// Mirrors brand.creative.iterate.IterationHistoryEntry exactly — the
// caller (this frontend) carries its own lineage's prior attempts, the
// same way it already carries `base_plan` forward request to request.
// There is no server-side session to hold this instead.
export interface IterationHistoryEntry {
  finding_code: string
  target_page: number
  command_type: string
  parameters: Record<string, unknown>
  outcome: IterationOutcome
}

export interface Explanation {
  why: string
  what: string
  where: string
  expected_result: string
}

export interface IterateResponse {
  // Every finding the review produced, not only the one acted on
  // (ADOS-M1.5 §16) — the UI must show these, never hide them.
  findings: EvaluationFinding[]
  finding: EvaluationFinding
  recommendation: Recommendation
  explanation: Explanation
  intent: CommandIntent
  resolution: IntentResolution
  resolved_scope: CompositionScope
  diff: PagePlanDiff
  metric: string
  before_metric: number
  after_metric: number
  outcome: IterationOutcome
  plan: PagePlan
  before_evaluation: Record<string, unknown>
  after_evaluation: Evaluation
  meta: {
    requested_at: string
    brand_id: string
    brand_version: string
    previous_plan_hash: string
    composer: string
  }
}

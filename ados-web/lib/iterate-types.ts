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

export interface IterateResponse {
  finding: EvaluationFinding
  recommendation: Recommendation
  intent: CommandIntent
  resolution: IntentResolution
  resolved_scope: CompositionScope
  diff: PagePlanDiff
  metric: string
  before_metric: number
  after_metric: number
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

// Mirrors brand/creative/intent.py exactly — the structured layer between
// a Command button and the existing Composer. A CommandIntent never
// carries a coordinate, a colour, a font or a grid value; the backend
// enforces that independently (defence in depth), but the frontend only
// ever constructs the six shapes below, so there is nothing else to send.

export type IntentType =
  | "reduce_text_density"
  | "increase_text_density"
  | "increase_image_emphasis"
  | "decrease_image_emphasis"
  | "recompose_page"
  | "preserve_content"
  | "remove_content"
  | "change_page_direction"

export type TargetType = "document" | "page" | "region" | "contentBlock"

export interface IntentTarget {
  type: TargetType
  id?: string
}

export interface CommandIntent {
  type: IntentType
  target: IntentTarget
  parameters?: Record<string, unknown>
}

export interface IntentResolution {
  direction_changed: boolean
  content_changed: boolean
  notes: string[]
}

// Mirrors brand/creative/scope.py exactly. A CompositionScope is what the
// caller asked for (mostly `target`, restated); a resolved scope is what
// the backend actually bounded the recomposition to after
// brand.creative.scope.resolve_scope ran — a contentBlock scope always
// resolves to `{ type: "page", id }`, the page it was found on.
export type ScopeType = "document" | "page" | "region" | "contentBlock"

export interface CompositionScope {
  type: ScopeType
  id: string
}

// Mirrors brand/creative/scope.py's PagePlanDiff.to_dict() exactly — a
// structural comparison of the plan before and after one intent, not
// something the frontend computes itself (ADOS §21 again: a view, not a
// second source of truth).
export interface PagePlanDiff {
  changed_pages: number[]
  unchanged_pages: number[]
  changed_blocks: string[]
  unchanged_blocks: string[]
}

export interface IntentResponse {
  intent: CommandIntent
  resolution: IntentResolution
  resulting_direction: Record<string, unknown>
  plan: import("./pageplan-types").PagePlan
  scope: CompositionScope | null
  resolved_scope: CompositionScope | null
  diff: PagePlanDiff | null
  evaluation: import("./pageplan-types").Evaluation
  meta: {
    requested_at: string
    brand_id: string
    brand_version: string
    previous_plan_hash: string
    composer: string
  }
}

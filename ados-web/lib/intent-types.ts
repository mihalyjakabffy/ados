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

export interface IntentResponse {
  intent: CommandIntent
  resolution: IntentResolution
  resulting_direction: Record<string, unknown>
  plan: import("./pageplan-types").PagePlan
  evaluation: import("./pageplan-types").Evaluation
  meta: {
    requested_at: string
    brand_id: string
    brand_version: string
    previous_plan_hash: string
    composer: string
  }
}

// Mirrors brand/creative/plan.py's PagePlan.to_dict() and
// brand/creative/evaluate.py's Evaluation.to_dict() exactly — field for
// field, nothing added or renamed. This is a VIEW type: the frontend must
// not compute anything these fields don't already state (ADOS §21 — the
// Canvas is a view of the authoritative PagePlan, not a second layout
// engine).

export interface PageGrid {
  format: string
  page_width_mm: number
  page_height_mm: number
  columns: number
  gutter_mm: number
  margin_mm: number
  column_width_mm: number
  content_width_mm: number
  content_height_mm: number
}

export interface Slot {
  component: string
  block: string
  text: string
  label: string
  provenance: string
  path: string
  rank: string
  step: string
  cap_mm: number
  emphasis: boolean
  x_mm: number
  y_mm: number
  width_mm: number
  height_mm: number
  columns: number
  ink: number
}

export interface Page {
  index: number
  archetype: string
  grid: PageGrid
  slots: Slot[]
  fill_ratio: number
  ink_coverage_max: number
  alignment_edges_x: number
  words: number
  image_ratio: number
  objective: number
}

export type RejectionKind = "infeasible" | "outranked" | "no-match"

export interface Rejection {
  page: number
  archetype: string
  kind: RejectionKind
  reason: string
  rule: string
}

export interface PagePlan {
  document: string
  project_name: string
  brand_id: string
  brand_version: string
  direction: string
  content_hash: string
  ados_edition: string
  pages: Page[]
  rejected: Rejection[]
  notes: string[]
  plan_hash: string
}

export interface EvaluationFinding {
  status: string
  severity: "INFO" | "WARN" | "ERROR" | "BLOCK"
  category: string
  field: string
  message: string
  suggestion: string
  rule: string
}

export interface Evaluation {
  plan_hash: string
  coverage: string
  checked: string[]
  not_checked: string[]
  brand: string
  ok: boolean
  counts: { INFO: number; WARN: number; ERROR: number; BLOCK: number }
  findings: EvaluationFinding[]
}

export interface ComposeMeta {
  requested_at: string
  brand_id: string
  brand_version: string
  composer: string
}

export interface ComposeResult {
  plan: PagePlan
  evaluation: Evaluation
  meta: ComposeMeta
}

export interface ContentModel {
  project_id: string
  project_name: string
  source_state: string | null
  blocks: { id: string; type: string; role: string; [key: string]: unknown }[]
}

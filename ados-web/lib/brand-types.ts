// Shapes read from the real Brand System API (api/routers/brand.py, backed
// by brand/models/brand.py). Deliberately partial: the full Brand aggregate
// nests five large sub-models (identity, visual_identity, architectural
// language, communication, digital) — only the fields the UI actually reads
// are typed; the rest passes through as unknown so a schema addition on the
// backend never silently breaks the build.

export type BrandStatusValue = "draft" | "proposed" | "approved" | "published" | "superseded" | "withdrawn"

export interface BrandSummary {
  brand_id: string
  name: string
  latest_version: string
}

export interface BrandIdentity {
  name: string
  descriptor: string
  tagline: string
  positioning: string
  mission: string
  vision: string
  values: string[]
  personality: string[]
  keywords: string[]
  practice_scale: string
  founded: number
  locations: string[]
}

export interface BrandDetail {
  brand_id: string
  version: string
  status: BrandStatusValue
  parent_version: string | null
  content_hash: string
  created_at: string
  changelog: string
  ados_edition: string
  origin: string
  identity: BrandIdentity
  // visual_identity, architectural_language, communication, digital — read
  // via /tokens and /preview instead of walking this nested tree directly.
  [key: string]: unknown
}

export interface BrandVersionEntry {
  version: string
  status: BrandStatusValue
  content_hash: string
  changelog: string
}

export interface BrandVersions {
  brand_id: string
  versions: BrandVersionEntry[]
  latest_usable: string | null
}

export type TokenValue = string | number | boolean | string[]
export type FlatTokens = Record<string, TokenValue>

export interface TemplateInfo {
  template_id: string
  title: string
  family: string
  medium: string
  renders: boolean
  missing_tokens: string[]
}

export interface BrandTemplates {
  templates: TemplateInfo[]
}

export interface ValidationFinding {
  status: string
  severity: "INFO" | "WARN" | "ERROR" | "BLOCK"
  category: string
  field: string
  message: string
  suggestion: string
  rule: string
}

export interface ValidationReport {
  brand: string
  ok: boolean
  counts: { INFO: number; WARN: number; ERROR: number; BLOCK: number }
  findings: ValidationFinding[]
}

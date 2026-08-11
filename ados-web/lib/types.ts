// Subset of the ADOS-IR schema (docs/ados/machine/ados-sheet-schema.json)
// that the frontend reads. Field names are normative — see ADOS-2.1.010.

export interface QAResult {
  rule: string
  label: string
  status: "pass" | "fail"
  detail: string
}

export interface QASummary {
  pass: number
  fail: number
}

export interface ContainerSummary {
  container_id: string
  short_id: string | null
  title: string | null
  type: string
  status: string
  revision: string
  author: string | null
  checker: string | null
  approver: string | null
  latest_revision_date: string | null
  region_count: number
  reference_out_count: number
  reference_in_count: number
  qa_summary: QASummary
}

export interface Revision {
  code: string
  date: string
  description: string
  author: string
  checker: string
  affected_regions?: string[]
}

export interface Reference {
  ref_id: string
  kind: string
  source: { container_id: string; view_id?: string; anno_id?: string }
  target: { container_id?: string; view_id?: string; external_ref?: string }
  reciprocal_of?: string | null
}

// The full raw container record — a different shape from ContainerSummary
// (which is a flattened, list-friendly projection computed server-side).
export interface ContainerDetail {
  container_id: string
  short_id: string | null
  title: string | null
  type: string
  status: string
  revision: string
  sheet?: { size: string; orientation: string; zoning_template: string }
  parties: { author: string; checker: string; approver: string }
  revisions: Revision[]
  scope_statement: string
  read_with: string[]
  regions?: RegionDetail[]
  references_out: Reference[]
  references_in: Reference[]
  qa: QAResult[]
}

export interface RegionDetail {
  region_id: string
  views?: { view_id: string; view_type: string; level?: string; scale_denominator?: number }[]
  blocks?: { block_id: string; kind: string }[]
}

export interface EncodingRow {
  channel: string
  state: string
  meaning: string
  criticality: "life_safety" | "cost" | "efficiency"
  rule: string
}

export interface PackageData {
  package_id: string
  purpose: string | null
  status: string
  project: {
    code: string
    name: string
    jurisdiction: string
    units: string
    language: string
  }
  set: {
    originator_code: string
    nominated_issue_size: string
    conformance_class: string
    edition: string
    overlays?: string[]
  }
  issue: {
    date: string
    medium: string
    recipients: string[]
    supersedes?: string[]
  }
  encoding_table: EncodingRow[]
  containers: ContainerSummary[]
}

export interface Rule {
  id: string
  name: string
  volume: string
  chapter: string
  level: "shall" | "should" | "may"
  severity: string
  principles: string[]
  evidence: string
  validation: string
  classes: string[]
  source: string
}

export interface RuleRegistry {
  edition: string
  rule_count: number
  principles: Record<string, string>
  severities: Record<string, string>
  matched: number
  rules: Rule[]
}

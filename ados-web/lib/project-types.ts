// Mirrors brand/project/model.py's Project/Document/Asset/ContentItem/
// ProjectVersion/ProjectSummary exactly — field for field, nothing added
// or renamed. This is the product-facing domain the M2.1 UI is built on;
// it is deliberately not ContentModel/PagePlan (those stay the engine's
// own types in pageplan-types.ts).

export type ContentItemKind = "text" | "fact" | "metric" | "image"

export interface ContentItem {
  id: string
  kind: ContentItemKind
  label: string
  text: string
  value: number | string | null
  unit: string
  provenance: string
  asset_id: string | null
  caption: string
  aspect: string
}

export interface ProjectAsset {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  path: string
  uploaded_at: string
}

export interface Section {
  id: string
  kind: string
  name: string
  order: number
  content_item_ids: string[]
}

export interface ProjectDocument {
  id: string
  project_id: string
  name: string
  direction_id: string
  document_type_id: string
  sections: Section[]
  project_refs: string[]
  metadata: Record<string, unknown>
  content_items: ContentItem[]
  latest_plan: Record<string, unknown> | null
  latest_evaluation: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ProjectVersion {
  id: string
  number: number
  label: string
  document_id: string
  document_name: string
  direction_id: string
  document_type_id: string
  sections: Section[]
  content_items: ContentItem[]
  plan: Record<string, unknown> | null
  created_at: string
}

// Mirrors brand/project/document_types.py's DocumentType exactly. The
// wizard and Structure panel read this data rather than branching on a
// type's identity — see that module's docstring for why.
export interface DocumentType {
  id: string
  name: string
  description: string
  audience: string
  purpose: string
  typical_use: string
  expected_output: string
  default_structure: string[]
  required_sections: string[]
  optional_sections: string[]
  section_labels: Record<string, string>
  default_page_range: [number, number]
  max_pages: number | null
  asset_expectations: string[]
  metadata_requirements: string[]
  composition_profile: string
  supports_multi_project: boolean
}

// Mirrors brand.validation.brand_validator.Finding.to_dict() — the same
// shape brand.creative.evaluate's page findings already use in
// pageplan-types.ts's EvaluationFinding, reused here for document-level
// Requirement violations (brand/project/requirements.py).
export interface RequirementFinding {
  status: string
  severity: "INFO" | "WARN" | "ERROR" | "BLOCK"
  category: string
  field: string
  message: string
  suggestion: string
  rule: string
  code: string
  metric: string
  actual: number | null
  threshold: number | null
  page_index: number | null
}

export interface Requirement {
  id: string
  document_type_id: string
  severity: "INFO" | "WARN" | "ERROR" | "BLOCK"
  check: string
  message: string
  remediation: string
  params: Record<string, unknown>
}

export interface DocumentTypeDetail extends DocumentType {
  requirements: Requirement[]
}

export interface Project {
  id: string
  name: string
  description: string
  brand_id: string | null
  brand_version: string | null
  documents: ProjectDocument[]
  assets: ProjectAsset[]
  versions: ProjectVersion[]
  created_at: string
  updated_at: string
}

export interface ProjectSummary {
  id: string
  name: string
  description: string
  brand_name: string | null
  document_count: number
  asset_count: number
  current_version: number | null
  updated_at: string
}

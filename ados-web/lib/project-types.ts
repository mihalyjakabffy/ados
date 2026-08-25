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

export interface ProjectDocument {
  id: string
  project_id: string
  name: string
  direction_id: string
  document_type: string
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
  content_items: ContentItem[]
  plan: Record<string, unknown> | null
  created_at: string
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

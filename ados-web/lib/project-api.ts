import useSWR, { mutate } from "swr"
import type { ContentModel, Evaluation, PagePlan } from "./pageplan-types"
import type {
  ActionItem,
  ActionStatus,
  ContentItem,
  ContentItemKind,
  Decision,
  DocumentExport,
  DocumentType,
  DocumentTypeDetail,
  Meeting,
  OptionStatus,
  Participant,
  PresentationOption,
  Project,
  ProjectAsset,
  ProjectDocument,
  ProjectSummary,
  ProjectVersion,
  RequirementFinding,
  Section,
} from "./project-types"

// Same backend as brand-api.ts (api/main.py) — see that file's note on why
// ADOS talks to REVELATION_API_URL rather than ados-service.
const REVELATION_API_URL = process.env.NEXT_PUBLIC_REVELATION_API_URL ?? "http://localhost:8000"
const BASE = "/api/v2/ados-projects"

export class ProjectApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public detail: unknown,
  ) {
    super(`${status} ${code}`)
  }
}

async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${REVELATION_API_URL}${path}`)
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ProjectApiError(res.status, errorCode(data), data?.detail ?? data)
  return data as T
}

async function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${REVELATION_API_URL}${path}`, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ProjectApiError(res.status, errorCode(data), data?.detail ?? data)
  return data as T
}

function errorCode(data: unknown): string {
  const detail = (data as { detail?: unknown } | null)?.detail
  if (typeof detail === "object" && detail && "error" in detail) return String((detail as { error: unknown }).error)
  return "request_failed"
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export function useProjects() {
  return useSWR<{ projects: ProjectSummary[] }>(`${BASE}`, fetcher)
}

export function useProject(projectId: string | null) {
  return useSWR<Project & { brand_name: string | null }>(
    projectId ? `${BASE}/${encodeURIComponent(projectId)}` : null,
    fetcher,
  )
}

export async function createProject(body: { name: string; description?: string }): Promise<Project> {
  const project = await send<Project>("POST", BASE, body)
  await mutate(BASE)
  return project
}

export async function updateProject(
  projectId: string,
  body: { name?: string; description?: string },
): Promise<Project> {
  const project = await send<Project>("PATCH", `${BASE}/${encodeURIComponent(projectId)}`, body)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  await mutate(BASE)
  return project
}

export async function deleteProject(projectId: string): Promise<void> {
  await send<void>("DELETE", `${BASE}/${encodeURIComponent(projectId)}`)
  await mutate(BASE)
}

export async function attachBrand(
  projectId: string,
  brandId: string,
  brandVersion?: string,
): Promise<Project & { brand_name: string | null }> {
  const project = await send<Project & { brand_name: string | null }>(
    "PUT",
    `${BASE}/${encodeURIComponent(projectId)}/brand`,
    { brand_id: brandId, brand_version: brandVersion ?? null },
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return project
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export async function createDocument(
  projectId: string,
  body: { name: string; direction_id?: string; document_type_id?: string; metadata?: Record<string, unknown> },
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>("POST", `${BASE}/${encodeURIComponent(projectId)}/documents`, body)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  await mutate(BASE)
  return doc
}

export async function getDocument(projectId: string, documentId: string): Promise<ProjectDocument> {
  return fetcher<ProjectDocument>(
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}`,
  )
}

export async function updateDocument(
  projectId: string,
  documentId: string,
  body: { name?: string; direction_id?: string; metadata?: Record<string, unknown> },
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "PATCH",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}`,
    body,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function deleteDocument(projectId: string, documentId: string): Promise<void> {
  await send<void>(
    "DELETE",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}`,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  await mutate(BASE)
}

export async function duplicateDocument(projectId: string, documentId: string): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "POST",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/duplicate`,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  await mutate(BASE)
  return doc
}

// ---------------------------------------------------------------------------
// Content
// ---------------------------------------------------------------------------

export async function addContentItem(
  projectId: string,
  documentId: string,
  body: {
    kind: ContentItemKind
    label?: string
    text?: string
    value?: number | string | null
    unit?: string
    provenance?: string
    asset_id?: string | null
    caption?: string
    aspect?: string
  },
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "POST",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/content`,
    body,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function removeContentItem(
  projectId: string,
  documentId: string,
  itemId: string,
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "DELETE",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/content/${encodeURIComponent(itemId)}`,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

// ---------------------------------------------------------------------------
// Shared project-level content (ADOS-M2.5 §6) — a Project's own content_items
// pool, plus which of those a given Document currently includes. Reuses
// AddContentItem's exact body shape; nothing new client-side.
// ---------------------------------------------------------------------------

export async function addSharedContentItem(
  projectId: string,
  body: {
    kind: ContentItemKind
    label?: string
    text?: string
    value?: number | string | null
    unit?: string
    provenance?: string
    asset_id?: string | null
    caption?: string
    aspect?: string
  },
): Promise<Project> {
  const project = await send<Project>("POST", `${BASE}/${encodeURIComponent(projectId)}/content`, body)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return project
}

export async function removeSharedContentItem(projectId: string, itemId: string): Promise<Project> {
  const project = await send<Project>(
    "DELETE",
    `${BASE}/${encodeURIComponent(projectId)}/content/${encodeURIComponent(itemId)}`,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return project
}

export async function setContentSelection(
  projectId: string,
  documentId: string,
  contentItemIds: string[],
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "PUT",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/content-selection`,
    { content_item_ids: contentItemIds },
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

// ---------------------------------------------------------------------------
// Compose — the one call that reaches the real Composer directly
// ---------------------------------------------------------------------------

export interface DocumentComposeResult {
  document: ProjectDocument
  content_model: ContentModel
  plan: PagePlan
  evaluation: Evaluation
}

export async function composeDocument(projectId: string, documentId: string): Promise<DocumentComposeResult> {
  const result = await send<DocumentComposeResult>(
    "POST",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/compose`,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return result
}

// ---------------------------------------------------------------------------
// Assets
// ---------------------------------------------------------------------------

export function assetFileUrl(projectId: string, assetId: string): string {
  return `${REVELATION_API_URL}${BASE}/${encodeURIComponent(projectId)}/assets/${encodeURIComponent(assetId)}/file`
}

export async function uploadAsset(projectId: string, file: File): Promise<ProjectAsset> {
  const form = new FormData()
  form.append("file", file)
  const res = await fetch(`${REVELATION_API_URL}${BASE}/${encodeURIComponent(projectId)}/assets`, {
    method: "POST",
    body: form,
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ProjectApiError(res.status, errorCode(data), data?.detail ?? data)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return data as ProjectAsset
}

export async function deleteAsset(projectId: string, assetId: string): Promise<void> {
  await send<void>("DELETE", `${BASE}/${encodeURIComponent(projectId)}/assets/${encodeURIComponent(assetId)}`)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
}

// ---------------------------------------------------------------------------
// Versions
// ---------------------------------------------------------------------------

export async function saveVersion(
  projectId: string,
  body: { document_id: string; label?: string; plan?: PagePlan | null },
): Promise<ProjectVersion> {
  const version = await send<ProjectVersion>("POST", `${BASE}/${encodeURIComponent(projectId)}/versions`, body)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return version
}

export async function restoreVersion(projectId: string, versionNumber: number): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "POST",
    `${BASE}/${encodeURIComponent(projectId)}/versions/${versionNumber}/restore`,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

// ---------------------------------------------------------------------------
// Structured Client Presentation & Internal Documentation (ADOS-M2.2.1 P3/P4)
// ---------------------------------------------------------------------------

function _docPath(projectId: string, documentId: string): string {
  return `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}`
}

export async function addPresentationOption(
  projectId: string,
  documentId: string,
  body: { title: string; description?: string; status?: OptionStatus },
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>("POST", `${_docPath(projectId, documentId)}/options`, body)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function removePresentationOption(projectId: string, documentId: string, optionId: string): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>("DELETE", `${_docPath(projectId, documentId)}/options/${encodeURIComponent(optionId)}`)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function addDecision(
  projectId: string,
  documentId: string,
  body: { title: string; description?: string; selected_option_id?: string | null; date?: string | null },
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>("POST", `${_docPath(projectId, documentId)}/decisions`, body)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function removeDecision(projectId: string, documentId: string, decisionId: string): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>("DELETE", `${_docPath(projectId, documentId)}/decisions/${encodeURIComponent(decisionId)}`)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function addActionItem(
  projectId: string,
  documentId: string,
  body: { description: string; responsible?: string; deadline?: string | null; status?: ActionStatus },
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>("POST", `${_docPath(projectId, documentId)}/action-items`, body)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function removeActionItem(projectId: string, documentId: string, itemId: string): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>("DELETE", `${_docPath(projectId, documentId)}/action-items/${encodeURIComponent(itemId)}`)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function addMeeting(
  projectId: string,
  documentId: string,
  body: {
    title: string
    date?: string | null
    location?: string
    participants?: Participant[]
    agenda?: string[]
    decisions?: { title: string; description?: string; selected_option_id?: string | null; date?: string | null }[]
    action_items?: { description: string; responsible?: string; deadline?: string | null; status?: ActionStatus }[]
  },
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>("POST", `${_docPath(projectId, documentId)}/meetings`, body)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function removeMeeting(projectId: string, documentId: string, meetingId: string): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>("DELETE", `${_docPath(projectId, documentId)}/meetings/${encodeURIComponent(meetingId)}`)
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

// ---------------------------------------------------------------------------
// Export (ADOS-M2.2.1 P0) — the one call that reaches the real renderer/
// Chromium pipeline directly, exactly compose()'s posture above.
// ---------------------------------------------------------------------------

export interface ExportResult {
  export: DocumentExport
  findings: RequirementFinding[]
}

export async function exportDocument(
  projectId: string,
  documentId: string,
  versionNumber?: number,
  format?: "pdf" | "html",
): Promise<ExportResult> {
  const result = await send<ExportResult>(
    "POST",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/export`,
    { version_number: versionNumber ?? null, format: format ?? "pdf" },
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return result
}

export function exportFileUrl(projectId: string, exportId: string): string {
  return `${REVELATION_API_URL}${BASE}/${encodeURIComponent(projectId)}/exports/${encodeURIComponent(exportId)}/file`
}

export async function listDocumentExports(
  projectId: string,
  documentId: string,
): Promise<{ exports: DocumentExport[] }> {
  return fetcher(
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/exports`,
  )
}

// ---------------------------------------------------------------------------
// Document types (ADOS-M2.2)
// ---------------------------------------------------------------------------

export function useDocumentTypes() {
  return useSWR<{ document_types: DocumentType[] }>(`${BASE}/document-types`, fetcher)
}

export function useDocumentType(typeId: string | null) {
  return useSWR<DocumentTypeDetail>(
    typeId ? `${BASE}/document-types/${encodeURIComponent(typeId)}` : null,
    fetcher,
  )
}

// ---------------------------------------------------------------------------
// Sections
// ---------------------------------------------------------------------------

export async function createSection(
  projectId: string,
  documentId: string,
  body: { kind: string; name: string; order?: number },
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "POST",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/sections`,
    body,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function updateSection(
  projectId: string,
  documentId: string,
  sectionId: string,
  body: { name?: string; order?: number; content_item_ids?: string[] },
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "PATCH",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/sections/${encodeURIComponent(sectionId)}`,
    body,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function deleteSection(
  projectId: string,
  documentId: string,
  sectionId: string,
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "DELETE",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/sections/${encodeURIComponent(sectionId)}`,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

// ---------------------------------------------------------------------------
// Requirements (ADOS-M2.2 §19)
// ---------------------------------------------------------------------------

export async function getDocumentRequirements(
  projectId: string,
  documentId: string,
): Promise<{ findings: RequirementFinding[]; ok: boolean }> {
  return fetcher(
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/requirements`,
  )
}

// ---------------------------------------------------------------------------
// Project references (ADOS-M2.2 §10 — Portfolio)
// ---------------------------------------------------------------------------

export async function addProjectRef(
  projectId: string,
  documentId: string,
  refProjectId: string,
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "POST",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/project-refs`,
    { project_id: refProjectId },
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export async function removeProjectRef(
  projectId: string,
  documentId: string,
  refProjectId: string,
): Promise<ProjectDocument> {
  const doc = await send<ProjectDocument>(
    "DELETE",
    `${BASE}/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/project-refs/${encodeURIComponent(refProjectId)}`,
  )
  await mutate(`${BASE}/${encodeURIComponent(projectId)}`)
  return doc
}

export type {
  ActionItem,
  ActionStatus,
  ContentItem,
  ContentItemKind,
  Decision,
  DocumentExport,
  DocumentType,
  DocumentTypeDetail,
  Meeting,
  OptionStatus,
  Participant,
  PresentationOption,
  Project,
  ProjectAsset,
  ProjectDocument,
  ProjectSummary,
  ProjectVersion,
  RequirementFinding,
  Section,
}

"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useAdosState } from "@/lib/ados-state"
import {
  addActionItem,
  addContentItem,
  addDecision,
  addMeeting,
  addPresentationOption,
  addProjectRef,
  assetFileUrl,
  exportDocument,
  exportFileUrl,
  getDocumentRequirements,
  removeActionItem,
  removeContentItem,
  removeDecision,
  removeMeeting,
  removePresentationOption,
  removeProjectRef,
  saveVersion,
  updateSection,
  uploadAsset,
  useProjects,
} from "@/lib/project-api"
import type {
  ActionItem,
  ActionStatus,
  ContentItem,
  ContentItemKind,
  Decision,
  DocumentExport,
  Meeting,
  OptionStatus,
  Participant,
  PresentationOption,
  Project,
  ProjectDocument,
  RequirementFinding,
} from "@/lib/project-types"

// WHAT THIS PROJECT'S DOCUMENT CONTAINS — the M2.1 replacement for
// LibraryPanel in the Document Workspace: not "pick a fixture", but
// "this document's real content, assets and saved versions". Canvas and
// Command are reused completely unmodified (see app/projects/[id]/
// documents/[docId]/page.tsx); this panel is the only new surface.
export function DocumentContextPanel({
  project,
  document,
  onDocumentChanged,
  onRecompose,
  composeBusy,
  composeError,
}: {
  project: Project & { brand_name: string | null }
  document: ProjectDocument
  onDocumentChanged: () => void
  onRecompose: () => void
  composeBusy: boolean
  composeError: string | null
}) {
  return (
    <aside className="flex h-full flex-col overflow-y-auto bg-sidebar px-2.5 py-3">
      <div className="mb-3 px-2">
        <Link href={`/projects/${project.id}`} className="text-[10.5px] text-mute hover:text-ink">
          ← {project.name}
        </Link>
        <p className="mt-1 truncate text-[13.5px] font-semibold text-ink">{document.name}</p>
        <p className="text-[10.5px] text-mute">
          {project.brand_name ?? "No brand"} · {document.direction_id}
        </p>
      </div>

      <RecomposeButton onRecompose={onRecompose} busy={composeBusy} error={composeError} />

      <RequirementsSection project={project} document={document} />
      {document.document_type_id === "portfolio" ? (
        <ProjectReferencesSection project={project} document={document} onChanged={onDocumentChanged} />
      ) : null}
      {document.document_type_id === "client-presentation" ? (
        <ClientPresentationSection project={project} document={document} onChanged={onDocumentChanged} />
      ) : null}
      {document.document_type_id === "internal-documentation" ? (
        <InternalDocumentationSection project={project} document={document} onChanged={onDocumentChanged} />
      ) : null}
      <ContentSection project={project} document={document} onChanged={onDocumentChanged} />
      <AssetsSection project={project} />
      <VersionsSection project={project} document={document} onChanged={onDocumentChanged} />
      <ExportSection project={project} document={document} onChanged={onDocumentChanged} />

      <div className="flex-1" />
      <p className="px-2 pb-1 pt-3 text-[10.5px] text-mute">ADOS Project Workspace</p>
    </aside>
  )
}

function RecomposeButton({
  onRecompose,
  busy,
  error,
}: {
  onRecompose: () => void
  busy: boolean
  error: string | null
}) {
  return (
    <div className="mb-4 px-2">
      <button
        onClick={onRecompose}
        disabled={busy}
        className="w-full rounded-[7px] bg-accent px-3 py-[7px] text-[12px] font-medium text-white disabled:opacity-40"
      >
        {busy ? "Composing…" : "Compose"}
      </button>
      {error ? <p className="mt-1.5 text-[11px] text-crit">{error}</p> : null}
    </div>
  )
}

const KIND_LABEL: Record<ContentItemKind, string> = {
  text: "Text",
  fact: "Fact",
  metric: "Metric",
  image: "Image",
}

function ContentItemRow({
  item,
  project,
  document,
  onChanged,
}: {
  item: ContentItem
  project: Project
  document: ProjectDocument
  onChanged: () => void
}) {
  return (
    <div className="group flex items-start justify-between gap-1 rounded-[7px] px-2 py-[5px] hover:bg-black/[.03]">
      <div className="min-w-0">
        <span className="text-[10px] font-semibold uppercase tracking-[.04em] text-mute">
          {KIND_LABEL[item.kind]}
        </span>
        <p className="truncate text-[12px] text-ink-soft">
          {item.kind === "text" ? item.text : item.label || item.text || "(untitled)"}
          {item.kind === "metric" ? ` — ${item.value}${item.unit ? ` ${item.unit}` : ""}` : ""}
          {item.kind === "fact" ? ` — ${item.value}` : ""}
        </p>
      </div>
      <button
        onClick={async () => {
          await removeContentItem(project.id, document.id, item.id)
          onChanged()
        }}
        className="mt-0.5 flex-shrink-0 text-[10.5px] text-mute opacity-0 group-hover:opacity-100 hover:text-crit"
      >
        Remove
      </button>
    </div>
  )
}

function ContentSection({
  project,
  document,
  onChanged,
}: {
  project: Project
  document: ProjectDocument
  onChanged: () => void
}) {
  const [adding, setAdding] = useState(false)

  const byId = new Map(document.content_items.map((item) => [item.id, item]))
  const sectioned = new Set(document.sections.flatMap((s) => s.content_item_ids))
  const unsectioned = document.content_items.filter((item) => !sectioned.has(item.id))

  return (
    <div className="mb-5">
      <div className="mb-1 flex items-center justify-between px-2">
        <p className="text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">
          {document.sections.length > 0 ? "Structure" : "Content"}
        </p>
        <button
          onClick={() => setAdding((v) => !v)}
          className="text-[10.5px] font-medium text-accent hover:underline"
        >
          + Add
        </button>
      </div>

      {adding ? (
        <AddContentForm
          project={project}
          document={document}
          onDone={() => {
            setAdding(false)
            onChanged()
          }}
        />
      ) : null}

      {document.sections.length === 0 && document.content_items.length === 0 ? (
        <p className="px-2 py-1 text-[11.5px] text-mute">No content yet.</p>
      ) : document.sections.length === 0 ? (
        <div className="space-y-0.5">
          {document.content_items.map((item) => (
            <ContentItemRow key={item.id} item={item} project={project} document={document} onChanged={onChanged} />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {[...document.sections]
            .sort((a, b) => a.order - b.order)
            .map((section) => (
              <div key={section.id}>
                <p className="px-2 py-0.5 text-[10px] font-medium text-mute">
                  {section.name}
                  {section.content_item_ids.length === 0 ? " — empty" : ""}
                </p>
                {section.content_item_ids.map((itemId) => {
                  const item = byId.get(itemId)
                  return item ? (
                    <ContentItemRow key={item.id} item={item} project={project} document={document} onChanged={onChanged} />
                  ) : null
                })}
              </div>
            ))}
          {unsectioned.length > 0 ? (
            <div>
              <p className="px-2 py-0.5 text-[10px] font-medium text-mute">Unsectioned</p>
              {unsectioned.map((item) => (
                <ContentItemRow key={item.id} item={item} project={project} document={document} onChanged={onChanged} />
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}

function AddContentForm({
  project,
  document,
  onDone,
}: {
  project: Project
  document: ProjectDocument
  onDone: () => void
}) {
  const [kind, setKind] = useState<ContentItemKind>("text")
  const [sectionId, setSectionId] = useState("")
  const [text, setText] = useState("")
  const [label, setLabel] = useState("")
  const [value, setValue] = useState("")
  const [unit, setUnit] = useState("")
  const [provenance, setProvenance] = useState("")
  const [assetId, setAssetId] = useState("")
  const [caption, setCaption] = useState("")
  const [aspect, setAspect] = useState("")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function submit() {
    setBusy(true)
    setErr(null)
    try {
      const updated = await addContentItem(project.id, document.id, {
        kind,
        text: kind === "text" ? text : "",
        label: kind === "fact" || kind === "metric" ? label : "",
        value: kind === "fact" || kind === "metric" ? value : null,
        unit: kind === "metric" ? unit : "",
        provenance: kind === "metric" || kind === "image" ? provenance : "",
        asset_id: kind === "image" ? assetId || null : null,
        caption: kind === "image" ? caption : "",
        aspect: kind === "image" ? aspect : "",
      })
      if (sectionId) {
        const newItem = updated.content_items[updated.content_items.length - 1]
        const section = document.sections.find((s) => s.id === sectionId)
        if (section && newItem) {
          await updateSection(project.id, document.id, sectionId, {
            content_item_ids: [...section.content_item_ids, newItem.id],
          })
        }
      }
      onDone()
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not add this content — check the required fields.")
      setBusy(false)
    }
  }

  return (
    <div className="mb-2 flex flex-col gap-1.5 rounded-[8px] border border-line bg-paper-raised p-2">
      <select
        value={kind}
        onChange={(e) => setKind(e.target.value as ContentItemKind)}
        className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
      >
        <option value="text">Text</option>
        <option value="fact">Fact</option>
        <option value="metric">Metric</option>
        <option value="image">Image</option>
      </select>

      {document.sections.length > 0 ? (
        <select
          value={sectionId}
          onChange={(e) => setSectionId(e.target.value)}
          className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
        >
          <option value="">No section</option>
          {[...document.sections]
            .sort((a, b) => a.order - b.order)
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
        </select>
      ) : null}

      {kind === "text" ? (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Narrative text"
          rows={2}
          className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
        />
      ) : null}

      {kind === "fact" || kind === "metric" ? (
        <>
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Label"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Value"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
        </>
      ) : null}

      {kind === "metric" ? (
        <>
          <input
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            placeholder="Unit (e.g. m²)"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          <input
            value={provenance}
            onChange={(e) => setProvenance(e.target.value)}
            placeholder="Provenance — where this number is from (required)"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
        </>
      ) : null}

      {kind === "image" ? (
        <>
          <input
            value={assetId}
            onChange={(e) => setAssetId(e.target.value)}
            placeholder="Asset id (copy from Assets below)"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] font-mono text-[11px]"
          />
          <input
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Caption"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          <input
            value={aspect}
            onChange={(e) => setAspect(e.target.value)}
            placeholder="Aspect ratio (e.g. 4:3)"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          <input
            value={provenance}
            onChange={(e) => setProvenance(e.target.value)}
            placeholder="Credit — photographer, drawing author, or source"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
        </>
      ) : null}

      {err ? <p className="text-[10.5px] text-crit">{err}</p> : null}

      <div className="flex gap-1.5">
        <button
          onClick={submit}
          disabled={busy}
          className="rounded-[6px] bg-accent px-2 py-[4px] text-[11px] font-medium text-white disabled:opacity-40"
        >
          Add
        </button>
        <button onClick={onDone} className="rounded-[6px] px-2 py-[4px] text-[11px] text-mute hover:bg-black/[.04]">
          Cancel
        </button>
      </div>
    </div>
  )
}

function AssetsSection({ project }: { project: Project }) {
  const [busy, setBusy] = useState(false)
  const [uploaded, setUploaded] = useState(project.assets)

  return (
    <div className="mb-5">
      <div className="mb-1 flex items-center justify-between px-2">
        <p className="text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Assets</p>
        <label className="cursor-pointer text-[10.5px] font-medium text-accent hover:underline">
          {busy ? "Uploading…" : "+ Upload"}
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.webp,.pdf"
            className="hidden"
            disabled={busy}
            onChange={async (e) => {
              const file = e.target.files?.[0]
              if (!file) return
              setBusy(true)
              try {
                const asset = await uploadAsset(project.id, file)
                setUploaded((prev) => [...prev, asset])
              } finally {
                setBusy(false)
                e.target.value = ""
              }
            }}
          />
        </label>
      </div>
      {uploaded.length === 0 ? (
        <p className="px-2 py-1 text-[11.5px] text-mute">No assets yet.</p>
      ) : (
        <div className="space-y-0.5 px-2">
          {uploaded.map((a) => (
            <div key={a.id} className="flex items-center justify-between gap-1 text-[11px]">
              <span className="truncate text-ink-soft">{a.filename}</span>
              <span className="flex-shrink-0 font-mono text-[10px] text-mute">{a.id}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const SEVERITY_COLOR: Record<string, string> = {
  BLOCK: "text-crit", ERROR: "text-crit", WARN: "text-amber-600", INFO: "text-mute",
}

function RequirementsSection({
  project,
  document,
}: {
  project: Project
  document: ProjectDocument
}) {
  const [findings, setFindings] = useState<RequirementFinding[] | null>(null)

  useEffect(() => {
    if (!document.document_type_id) {
      setFindings([])
      return
    }
    let cancelled = false
    getDocumentRequirements(project.id, document.id).then((r) => {
      if (!cancelled) setFindings(r.findings)
    })
    return () => {
      cancelled = true
    }
    // Re-check whenever the document's own state changes (content added/
    // removed, composed, sections edited) — updated_at moves on all of those.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id, document.id, document.updated_at])

  if (!document.document_type_id || findings === null) return null
  if (findings.length === 0) {
    return (
      <div className="mb-5 px-2">
        <p className="text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Requirements</p>
        <p className="py-1 text-[11.5px] text-ok">All requirements satisfied.</p>
      </div>
    )
  }

  return (
    <div className="mb-5">
      <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">
        Requirements — {findings.length}
      </p>
      <div className="space-y-1 px-2">
        {findings.map((f, i) => (
          <div key={i} className="rounded-[7px] border border-line bg-paper-raised px-2 py-1.5">
            <p className={`text-[11px] font-medium ${SEVERITY_COLOR[f.severity] ?? "text-ink-soft"}`}>
              {f.code || f.severity}
            </p>
            <p className="text-[11px] text-ink-soft">{f.message}</p>
            {f.suggestion ? <p className="mt-0.5 text-[10.5px] text-mute">{f.suggestion}</p> : null}
          </div>
        ))}
      </div>
    </div>
  )
}

function ProjectReferencesSection({
  project,
  document,
  onChanged,
}: {
  project: Project
  document: ProjectDocument
  onChanged: () => void
}) {
  const { data } = useProjects()
  const [picking, setPicking] = useState("")
  const candidates = (data?.projects ?? []).filter(
    (p) => p.id !== project.id && !document.project_refs.includes(p.id),
  )
  const referenced = (data?.projects ?? []).filter((p) => document.project_refs.includes(p.id))

  return (
    <div className="mb-5">
      <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">
        Referenced Projects
      </p>
      {referenced.length === 0 ? (
        <p className="px-2 py-1 text-[11.5px] text-mute">No projects referenced yet.</p>
      ) : (
        <div className="space-y-0.5 px-2">
          {referenced.map((p) => (
            <div key={p.id} className="flex items-center justify-between gap-1 text-[11.5px]">
              <span className="truncate text-ink-soft">{p.name}</span>
              <button
                onClick={async () => {
                  await removeProjectRef(project.id, document.id, p.id)
                  onChanged()
                }}
                className="flex-shrink-0 text-[10.5px] text-mute hover:text-crit"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
      {candidates.length > 0 ? (
        <div className="mt-1.5 flex gap-1 px-2">
          <select
            value={picking}
            onChange={(e) => setPicking(e.target.value)}
            className="min-w-0 flex-1 rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11px]"
          >
            <option value="">Add a project…</option>
            {candidates.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            disabled={!picking}
            onClick={async () => {
              await addProjectRef(project.id, document.id, picking)
              setPicking("")
              onChanged()
            }}
            className="rounded-[6px] bg-accent px-2 py-[4px] text-[11px] font-medium text-white disabled:opacity-40"
          >
            Add
          </button>
        </div>
      ) : null}
    </div>
  )
}

// EXPORT — the production PDF (ADOS-M2.2.1 P0). Reuses the real renderer/
// Chromium pipeline behind POST .../export; this component only presents
// its outcome. A BLOCKED export never offers a download — there is nothing
// to download — and its blocking findings are shown inline rather than
// behind a second navigation, since they are exactly what the user must
// fix before trying again.
function ExportSection({
  project,
  document,
  onChanged,
}: {
  project: Project
  document: ProjectDocument
  onChanged: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [findings, setFindings] = useState<RequirementFinding[]>([])

  const history = project.exports
    .filter((e) => e.document_id === document.id)
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
  const latest = history[0] ?? null
  const blocking = findings.filter((f) => f.severity === "ERROR" || f.severity === "BLOCK")
  const warnings = findings.filter((f) => f.severity === "WARN")

  async function runExport() {
    setBusy(true)
    setErr(null)
    try {
      const result = await exportDocument(project.id, document.id)
      setFindings(result.findings)
      onChanged()
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Export failed unexpectedly — the server did not respond as expected.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mb-5">
      <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Export</p>
      <div className="mx-2 rounded-[8px] border border-line bg-paper-raised px-2.5 py-2">
        {latest ? (
          <p className="text-[11px] text-ink-soft">
            Last export: v{latest.version_number} · {latest.page_count} page{latest.page_count === 1 ? "" : "s"} ·{" "}
            {EXPORT_STATUS_LABEL[latest.status]}
          </p>
        ) : (
          <p className="text-[11px] text-mute">Not exported yet.</p>
        )}

        <button
          onClick={runExport}
          disabled={busy}
          className="mt-1.5 w-full rounded-[7px] bg-accent px-3 py-[7px] text-[12px] font-medium text-white disabled:opacity-40"
        >
          {busy ? "Exporting…" : "Export PDF"}
        </button>

        {err ? <p className="mt-1.5 text-[11px] text-crit">{err}</p> : null}

        {latest?.status === "blocked" ? (
          <div className="mt-2">
            <p className="text-[11px] font-medium text-crit">
              Export blocked{blocking.length > 0 ? ` — ${blocking.length} blocking issue${blocking.length === 1 ? "" : "s"}` : ""}
            </p>
            {blocking.length > 0 ? (
              <div className="mt-1 space-y-1">
                {blocking.map((f, i) => (
                  <p key={i} className="text-[10.5px] text-ink-soft">
                    {f.code ? `${f.code}: ` : ""}
                    {f.message}
                  </p>
                ))}
              </div>
            ) : (
              <p className="mt-1 text-[10.5px] text-mute">
                Re-run export to see which findings are blocking it.
              </p>
            )}
          </div>
        ) : null}

        {latest?.status === "failed" ? (
          <p className="mt-2 text-[11px] text-crit">{latest.error || "The PDF renderer failed unexpectedly."}</p>
        ) : null}

        {latest?.status === "completed" ? (
          <>
            {warnings.length > 0 ? (
              <p className="mt-2 text-[11px] text-amber-600">
                {warnings.length} warning{warnings.length === 1 ? "" : "s"} — exported anyway.
              </p>
            ) : null}
            <a
              href={exportFileUrl(project.id, latest.id)}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block text-[11px] font-medium text-accent hover:underline"
            >
              Open PDF — {latest.filename}
            </a>
          </>
        ) : null}
      </div>
    </div>
  )
}

const EXPORT_STATUS_LABEL: Record<DocumentExport["status"], string> = {
  ready: "ready",
  exporting: "exporting…",
  completed: "exported",
  failed: "failed",
  blocked: "blocked",
}

// CLIENT PRESENTATION (ADOS-M2.2.1 P3) — options, decisions, next steps.
// Deliberately three short lists with tiny inline add-forms, not a second
// content-editing surface: an option/decision/action item is a handful of
// fields, not a document.
const OPTION_STATUS_LABEL: Record<OptionStatus, string> = {
  proposed: "Proposed", recommended: "Recommended", rejected: "Rejected", selected: "Selected",
}
const OPTION_STATUS_COLOR: Record<OptionStatus, string> = {
  proposed: "text-mute", recommended: "text-ok", selected: "text-ok", rejected: "text-crit",
}

function ClientPresentationSection({
  project,
  document,
  onChanged,
}: {
  project: Project
  document: ProjectDocument
  onChanged: () => void
}) {
  return (
    <div className="mb-5">
      <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">
        Client Presentation
      </p>
      <OptionsList project={project} document={document} onChanged={onChanged} />
      <DecisionsList project={project} document={document} onChanged={onChanged} />
      <ActionItemsList
        items={document.action_items}
        onAdd={(body) => addActionItem(project.id, document.id, body).then(onChanged)}
        onRemove={(id) => removeActionItem(project.id, document.id, id).then(onChanged)}
        label="Next Steps"
      />
    </div>
  )
}

function OptionsList({
  project,
  document,
  onChanged,
}: {
  project: Project
  document: ProjectDocument
  onChanged: () => void
}) {
  const [adding, setAdding] = useState(false)
  const [title, setTitle] = useState("")
  const [status, setStatus] = useState<OptionStatus>("proposed")

  return (
    <div className="mb-2 px-2">
      <div className="mb-0.5 flex items-center justify-between">
        <p className="text-[10.5px] font-medium text-ink-soft">Options</p>
        <button onClick={() => setAdding((v) => !v)} className="text-[10.5px] font-medium text-accent hover:underline">
          + Add
        </button>
      </div>
      {document.presentation_options.length === 0 ? (
        <p className="text-[11px] text-mute">No options yet.</p>
      ) : (
        <div className="space-y-0.5">
          {document.presentation_options.map((o) => (
            <div key={o.id} className="group flex items-center justify-between gap-1 text-[11.5px]">
              <span className="truncate text-ink-soft">
                {o.title} <span className={`text-[10px] ${OPTION_STATUS_COLOR[o.status]}`}>· {OPTION_STATUS_LABEL[o.status]}</span>
              </span>
              <button
                onClick={() => removePresentationOption(project.id, document.id, o.id).then(onChanged)}
                className="flex-shrink-0 text-[10.5px] text-mute opacity-0 group-hover:opacity-100 hover:text-crit"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
      {adding ? (
        <div className="mt-1 flex flex-col gap-1.5 rounded-[8px] border border-line bg-paper-raised p-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Option title"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as OptionStatus)}
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          >
            <option value="proposed">Proposed</option>
            <option value="recommended">Recommended</option>
            <option value="rejected">Rejected</option>
            <option value="selected">Selected</option>
          </select>
          <div className="flex gap-1.5">
            <button
              onClick={async () => {
                if (!title.trim()) return
                await addPresentationOption(project.id, document.id, { title, status })
                setTitle("")
                setStatus("proposed")
                setAdding(false)
                onChanged()
              }}
              className="rounded-[6px] bg-accent px-2 py-[4px] text-[11px] font-medium text-white"
            >
              Add
            </button>
            <button onClick={() => setAdding(false)} className="rounded-[6px] px-2 py-[4px] text-[11px] text-mute hover:bg-black/[.04]">
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function DecisionsList({
  project,
  document,
  onChanged,
}: {
  project: Project
  document: ProjectDocument
  onChanged: () => void
}) {
  const [adding, setAdding] = useState(false)
  const [title, setTitle] = useState("")
  const [selectedOptionId, setSelectedOptionId] = useState("")
  const [date, setDate] = useState("")
  const optionById = new Map(document.presentation_options.map((o) => [o.id, o]))

  return (
    <div className="mb-2 px-2">
      <div className="mb-0.5 flex items-center justify-between">
        <p className="text-[10.5px] font-medium text-ink-soft">Decisions</p>
        <button onClick={() => setAdding((v) => !v)} className="text-[10.5px] font-medium text-accent hover:underline">
          + Add
        </button>
      </div>
      {document.decisions.length === 0 ? (
        <p className="text-[11px] text-mute">No decisions yet.</p>
      ) : (
        <div className="space-y-0.5">
          {document.decisions.map((d) => (
            <div key={d.id} className="group flex items-center justify-between gap-1 text-[11.5px]">
              <span className="truncate text-ink-soft">
                {d.title}
                {d.selected_option_id && optionById.get(d.selected_option_id) ? ` → ${optionById.get(d.selected_option_id)!.title}` : ""}
                {d.date ? ` · ${d.date}` : ""}
              </span>
              <button
                onClick={() => removeDecision(project.id, document.id, d.id).then(onChanged)}
                className="flex-shrink-0 text-[10.5px] text-mute opacity-0 group-hover:opacity-100 hover:text-crit"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
      {adding ? (
        <div className="mt-1 flex flex-col gap-1.5 rounded-[8px] border border-line bg-paper-raised p-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Decision"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          {document.presentation_options.length > 0 ? (
            <select
              value={selectedOptionId}
              onChange={(e) => setSelectedOptionId(e.target.value)}
              className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
            >
              <option value="">No option selected</option>
              {document.presentation_options.map((o) => (
                <option key={o.id} value={o.id}>{o.title}</option>
              ))}
            </select>
          ) : null}
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          <div className="flex gap-1.5">
            <button
              onClick={async () => {
                if (!title.trim()) return
                await addDecision(project.id, document.id, {
                  title, selected_option_id: selectedOptionId || null, date: date || null,
                })
                setTitle("")
                setSelectedOptionId("")
                setDate("")
                setAdding(false)
                onChanged()
              }}
              className="rounded-[6px] bg-accent px-2 py-[4px] text-[11px] font-medium text-white"
            >
              Add
            </button>
            <button onClick={() => setAdding(false)} className="rounded-[6px] px-2 py-[4px] text-[11px] text-mute hover:bg-black/[.04]">
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function ActionItemsList({
  items,
  onAdd,
  onRemove,
  label,
}: {
  items: ActionItem[]
  onAdd: (body: { description: string; responsible?: string; deadline?: string | null }) => Promise<void>
  onRemove: (id: string) => void
  label: string
}) {
  const [adding, setAdding] = useState(false)
  const [description, setDescription] = useState("")
  const [responsible, setResponsible] = useState("")
  const [deadline, setDeadline] = useState("")

  return (
    <div className="mb-2 px-2">
      <div className="mb-0.5 flex items-center justify-between">
        <p className="text-[10.5px] font-medium text-ink-soft">{label}</p>
        <button onClick={() => setAdding((v) => !v)} className="text-[10.5px] font-medium text-accent hover:underline">
          + Add
        </button>
      </div>
      {items.length === 0 ? (
        <p className="text-[11px] text-mute">No action items yet.</p>
      ) : (
        <div className="space-y-0.5">
          {items.map((a) => (
            <div key={a.id} className="group flex items-center justify-between gap-1 text-[11.5px]">
              <span className="truncate text-ink-soft">
                {a.description}
                {a.responsible ? ` — ${a.responsible}` : " — unassigned"}
                {a.deadline ? ` · due ${a.deadline}` : ""}
              </span>
              <button
                onClick={() => onRemove(a.id)}
                className="flex-shrink-0 text-[10.5px] text-mute opacity-0 group-hover:opacity-100 hover:text-crit"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
      {adding ? (
        <div className="mt-1 flex flex-col gap-1.5 rounded-[8px] border border-line bg-paper-raised p-2">
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Action"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          <input
            value={responsible}
            onChange={(e) => setResponsible(e.target.value)}
            placeholder="Responsible"
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          <input
            type="date"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
          />
          <div className="flex gap-1.5">
            <button
              onClick={async () => {
                if (!description.trim()) return
                await onAdd({ description, responsible, deadline: deadline || null })
                setDescription("")
                setResponsible("")
                setDeadline("")
                setAdding(false)
              }}
              className="rounded-[6px] bg-accent px-2 py-[4px] text-[11px] font-medium text-white"
            >
              Add
            </button>
            <button onClick={() => setAdding(false)} className="rounded-[6px] px-2 py-[4px] text-[11px] text-mute hover:bg-black/[.04]">
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

// INTERNAL DOCUMENTATION (ADOS-M2.2.1 P4) — meetings, recorded whole. A
// meeting's participants/agenda/decisions/action items are built up in
// local state before one POST — the backend has no sub-resource CRUD for
// a meeting's own contents (api/routers/ados_project.py's add_meeting),
// so neither does this form.
function InternalDocumentationSection({
  project,
  document,
  onChanged,
}: {
  project: Project
  document: ProjectDocument
  onChanged: () => void
}) {
  const [adding, setAdding] = useState(false)

  return (
    <div className="mb-5">
      <div className="mb-1 flex items-center justify-between px-2">
        <p className="text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Meetings</p>
        <button onClick={() => setAdding((v) => !v)} className="text-[10.5px] font-medium text-accent hover:underline">
          + Add
        </button>
      </div>

      {document.meetings.length === 0 ? (
        <p className="px-2 py-1 text-[11.5px] text-mute">No meetings recorded yet.</p>
      ) : (
        <div className="space-y-2 px-2">
          {document.meetings.map((m) => (
            <MeetingCard
              key={m.id}
              meeting={m}
              onRemove={() => removeMeeting(project.id, document.id, m.id).then(onChanged)}
            />
          ))}
        </div>
      )}

      {adding ? (
        <AddMeetingForm
          project={project}
          document={document}
          onDone={() => {
            setAdding(false)
            onChanged()
          }}
        />
      ) : null}
    </div>
  )
}

function MeetingCard({ meeting, onRemove }: { meeting: Meeting; onRemove: () => void }) {
  return (
    <div className="group rounded-[8px] border border-line bg-paper-raised px-2.5 py-2">
      <div className="flex items-center justify-between gap-1">
        <p className="truncate text-[11.5px] font-medium text-ink-soft">
          {meeting.title}{meeting.date ? ` — ${meeting.date}` : ""}
        </p>
        <button
          onClick={onRemove}
          className="flex-shrink-0 text-[10.5px] text-mute opacity-0 group-hover:opacity-100 hover:text-crit"
        >
          Remove
        </button>
      </div>
      {meeting.location ? <p className="text-[10.5px] text-mute">{meeting.location}</p> : null}
      {meeting.participants.length > 0 ? (
        <p className="mt-1 text-[10.5px] text-ink-soft">
          {meeting.participants.map((p) => (p.role ? `${p.name} (${p.role})` : p.name)).join(", ")}
        </p>
      ) : null}
      {meeting.decisions.length > 0 ? (
        <p className="mt-1 text-[10.5px] text-mute">{meeting.decisions.length} decision{meeting.decisions.length === 1 ? "" : "s"}</p>
      ) : null}
      {meeting.action_items.length > 0 ? (
        <div className="mt-1 space-y-0.5">
          {meeting.action_items.map((a) => (
            <p key={a.id} className="text-[10.5px] text-mute">
              • {a.description}{a.responsible ? ` — ${a.responsible}` : " — unassigned"}{a.deadline ? ` · due ${a.deadline}` : ""}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function AddMeetingForm({
  project,
  document,
  onDone,
}: {
  project: Project
  document: ProjectDocument
  onDone: () => void
}) {
  const [title, setTitle] = useState("")
  const [date, setDate] = useState("")
  const [location, setLocation] = useState("")
  const [participants, setParticipants] = useState<Participant[]>([])
  const [participantName, setParticipantName] = useState("")
  const [participantRole, setParticipantRole] = useState("")
  const [agendaText, setAgendaText] = useState("")
  const [decisionTitles, setDecisionTitles] = useState<string[]>([])
  const [decisionTitle, setDecisionTitle] = useState("")
  const [actionItems, setActionItems] = useState<{ description: string; responsible: string }[]>([])
  const [actionDescription, setActionDescription] = useState("")
  const [actionResponsible, setActionResponsible] = useState("")
  const [busy, setBusy] = useState(false)

  return (
    <div className="mt-1 flex flex-col gap-1.5 rounded-[8px] border border-line bg-paper-raised p-2">
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Meeting title"
        className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
      />
      <input
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value)}
        className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
      />
      <input
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        placeholder="Location"
        className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
      />

      <p className="text-[10px] font-medium text-mute">Participants</p>
      {participants.length > 0 ? (
        <p className="text-[10.5px] text-ink-soft">{participants.map((p) => p.name).join(", ")}</p>
      ) : null}
      <div className="flex gap-1">
        <input
          value={participantName}
          onChange={(e) => setParticipantName(e.target.value)}
          placeholder="Name"
          className="min-w-0 flex-1 rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11px]"
        />
        <input
          value={participantRole}
          onChange={(e) => setParticipantRole(e.target.value)}
          placeholder="Role"
          className="min-w-0 flex-1 rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11px]"
        />
        <button
          onClick={() => {
            if (!participantName.trim()) return
            setParticipants((prev) => [...prev, { name: participantName, role: participantRole }])
            setParticipantName("")
            setParticipantRole("")
          }}
          className="flex-shrink-0 rounded-[6px] px-2 py-[4px] text-[11px] text-accent hover:bg-accent-soft/40"
        >
          + Add
        </button>
      </div>

      <textarea
        value={agendaText}
        onChange={(e) => setAgendaText(e.target.value)}
        placeholder="Agenda — one item per line"
        rows={2}
        className="rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11.5px]"
      />

      <p className="text-[10px] font-medium text-mute">Decisions</p>
      {decisionTitles.length > 0 ? (
        <p className="text-[10.5px] text-ink-soft">{decisionTitles.join(" · ")}</p>
      ) : null}
      <div className="flex gap-1">
        <input
          value={decisionTitle}
          onChange={(e) => setDecisionTitle(e.target.value)}
          placeholder="Decision"
          className="min-w-0 flex-1 rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11px]"
        />
        <button
          onClick={() => {
            if (!decisionTitle.trim()) return
            setDecisionTitles((prev) => [...prev, decisionTitle])
            setDecisionTitle("")
          }}
          className="flex-shrink-0 rounded-[6px] px-2 py-[4px] text-[11px] text-accent hover:bg-accent-soft/40"
        >
          + Add
        </button>
      </div>

      <p className="text-[10px] font-medium text-mute">Action items</p>
      {actionItems.length > 0 ? (
        <p className="text-[10.5px] text-ink-soft">
          {actionItems.map((a) => `${a.description} (${a.responsible || "unassigned"})`).join(" · ")}
        </p>
      ) : null}
      <div className="flex gap-1">
        <input
          value={actionDescription}
          onChange={(e) => setActionDescription(e.target.value)}
          placeholder="Action"
          className="min-w-0 flex-1 rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11px]"
        />
        <input
          value={actionResponsible}
          onChange={(e) => setActionResponsible(e.target.value)}
          placeholder="Responsible"
          className="min-w-0 flex-1 rounded-[6px] border border-line-strong px-1.5 py-[4px] text-[11px]"
        />
        <button
          onClick={() => {
            if (!actionDescription.trim()) return
            setActionItems((prev) => [...prev, { description: actionDescription, responsible: actionResponsible }])
            setActionDescription("")
            setActionResponsible("")
          }}
          className="flex-shrink-0 rounded-[6px] px-2 py-[4px] text-[11px] text-accent hover:bg-accent-soft/40"
        >
          + Add
        </button>
      </div>

      <div className="mt-1 flex gap-1.5">
        <button
          disabled={busy || !title.trim()}
          onClick={async () => {
            setBusy(true)
            try {
              await addMeeting(project.id, document.id, {
                title,
                date: date || null,
                location,
                participants,
                agenda: agendaText.split("\n").map((s) => s.trim()).filter(Boolean),
                decisions: decisionTitles.map((t) => ({ title: t })),
                action_items: actionItems.map((a) => ({ description: a.description, responsible: a.responsible })),
              })
              onDone()
            } finally {
              setBusy(false)
            }
          }}
          className="rounded-[6px] bg-accent px-2 py-[4px] text-[11px] font-medium text-white disabled:opacity-40"
        >
          {busy ? "Saving…" : "Save meeting"}
        </button>
        <button onClick={onDone} className="rounded-[6px] px-2 py-[4px] text-[11px] text-mute hover:bg-black/[.04]">
          Cancel
        </button>
      </div>
    </div>
  )
}

function VersionsSection({
  project,
  document,
  onChanged,
}: {
  project: Project
  document: ProjectDocument
  onChanged: () => void
}) {
  const { plan } = useAdosState()
  const [busy, setBusy] = useState(false)
  const versions = project.versions
    .filter((v) => v.document_id === document.id)
    .sort((a, b) => b.number - a.number)

  return (
    <div className="mb-5">
      <div className="mb-1 flex items-center justify-between px-2">
        <p className="text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Versions</p>
        <button
          disabled={busy || !plan}
          onClick={async () => {
            setBusy(true)
            try {
              const label = window.prompt("Name this version (optional):", "") ?? ""
              await saveVersion(project.id, {
                document_id: document.id,
                label,
                plan: plan?.plan ?? null,
              })
              onChanged()
            } finally {
              setBusy(false)
            }
          }}
          className="text-[10.5px] font-medium text-accent hover:underline disabled:opacity-40"
        >
          + Save version
        </button>
      </div>
      {versions.length === 0 ? (
        <p className="px-2 py-1 text-[11.5px] text-mute">No saved versions yet.</p>
      ) : (
        <div className="space-y-0.5 px-2">
          {versions.map((v) => (
            <div key={v.id} className="flex items-center justify-between gap-1 text-[11px]">
              <span className="truncate text-ink-soft">
                v{v.number}
                {v.label ? ` — ${v.label}` : ""}
              </span>
              <span className="flex-shrink-0 text-mute">{new Date(v.created_at).toLocaleDateString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

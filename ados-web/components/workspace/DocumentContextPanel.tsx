"use client"

import { useState } from "react"
import Link from "next/link"
import { useAdosState } from "@/lib/ados-state"
import {
  addContentItem,
  assetFileUrl,
  removeContentItem,
  saveVersion,
  uploadAsset,
} from "@/lib/project-api"
import type { ContentItemKind, Project, ProjectDocument } from "@/lib/project-types"

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

      <ContentSection project={project} document={document} onChanged={onDocumentChanged} />
      <AssetsSection project={project} />
      <VersionsSection project={project} document={document} onChanged={onDocumentChanged} />

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

  return (
    <div className="mb-5">
      <div className="mb-1 flex items-center justify-between px-2">
        <p className="text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Content</p>
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

      {document.content_items.length === 0 ? (
        <p className="px-2 py-1 text-[11.5px] text-mute">No content yet.</p>
      ) : (
        <div className="space-y-0.5">
          {document.content_items.map((item) => (
            <div key={item.id} className="group flex items-start justify-between gap-1 rounded-[7px] px-2 py-[5px] hover:bg-black/[.03]">
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
          ))}
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
      await addContentItem(project.id, document.id, {
        kind,
        text: kind === "text" ? text : "",
        label: kind === "fact" || kind === "metric" ? label : "",
        value: kind === "fact" || kind === "metric" ? value : null,
        unit: kind === "metric" ? unit : "",
        provenance: kind === "metric" ? provenance : "",
        asset_id: kind === "image" ? assetId || null : null,
        caption: kind === "image" ? caption : "",
        aspect: kind === "image" ? aspect : "",
      })
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

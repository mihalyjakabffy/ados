"use client"

import { useState } from "react"
import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { TopBar } from "@/components/TopBar"
import { DocumentCreationWizard } from "@/components/DocumentCreationWizard"
import { useBrands } from "@/lib/brand-api"
import {
  attachBrand,
  deleteAsset,
  deleteDocument,
  deleteProject,
  duplicateDocument,
  restoreVersion,
  uploadAsset,
  useProject,
  assetFileUrl,
} from "@/lib/project-api"
import type { Project } from "@/lib/project-types"

export default function ProjectOverviewPage() {
  const params = useParams<{ id: string }>()
  const projectId = params.id
  const router = useRouter()
  const { data: project, isLoading, error, mutate } = useProject(projectId)

  if (isLoading) {
    return (
      <div className="flex h-screen flex-col">
        <TopBar />
        <p className="p-8 text-[12.5px] text-mute">Loading project…</p>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="flex h-screen flex-col">
        <TopBar />
        <div className="p-8">
          <p className="text-[13px] font-medium text-crit">Project not found</p>
          <Link href="/projects" className="mt-2 inline-block text-[12.5px] text-accent">
            Back to projects
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <div className="flex items-center gap-2 text-[12px] text-mute">
          <Link href="/projects" className="hover:text-ink">
            Projects
          </Link>
          <span>/</span>
          <span className="text-ink">{project.name}</span>
        </div>
        <button
          onClick={async () => {
            if (!confirm(`Delete "${project.name}"? This cannot be undone.`)) return
            await deleteProject(project.id)
            router.push("/projects")
          }}
          className="rounded-[7px] px-2.5 py-[5px] text-[11.5px] text-crit hover:bg-crit-bg"
        >
          Delete project
        </button>
      </div>

      <main className="flex-1 overflow-auto p-4">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          <header>
            <h1 className="text-[19px] font-semibold text-ink">{project.name}</h1>
            {project.description ? <p className="mt-1 text-[13px] text-mute">{project.description}</p> : null}
          </header>

          <BrandSection project={project} onChanged={mutate} />
          <DocumentsSection project={project} onChanged={mutate} />
          <AssetsSection project={project} onChanged={mutate} />
          <VersionsSection project={project} onChanged={mutate} />
        </div>
      </main>
    </div>
  )
}

type ProjectWithBrandName = Project & { brand_name: string | null }

function BrandSection({
  project,
  onChanged,
}: {
  project: ProjectWithBrandName
  onChanged: () => void
}) {
  const { data: brandsData } = useBrands()
  const [busy, setBusy] = useState(false)

  return (
    <section>
      <SectionHeading>Brand</SectionHeading>
      {project.brand_id ? (
        <p className="text-[13px] text-ink-soft">
          <span className="font-medium text-ink">{project.brand_name ?? project.brand_id}</span>
          {project.brand_version ? ` · v${project.brand_version}` : " · latest"}
        </p>
      ) : (
        <p className="text-[12.5px] text-mute">No brand attached yet. Every document composed here uses this brand.</p>
      )}
      <select
        disabled={busy}
        value=""
        onChange={async (e) => {
          const brandId = e.target.value
          if (!brandId) return
          setBusy(true)
          try {
            await attachBrand(project.id, brandId)
            onChanged()
          } finally {
            setBusy(false)
          }
        }}
        className="mt-2 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[6px] text-[12px]"
      >
        <option value="">{project.brand_id ? "Change brand…" : "Attach a brand…"}</option>
        {(brandsData?.brands ?? []).map((b) => (
          <option key={b.brand_id} value={b.brand_id}>
            {b.name} (v{b.latest_version})
          </option>
        ))}
      </select>
    </section>
  )
}

function DocumentsSection({
  project,
  onChanged,
}: {
  project: ProjectWithBrandName
  onChanged: () => void
}) {
  const router = useRouter()
  const [wizardOpen, setWizardOpen] = useState(false)

  return (
    <section>
      <div className="flex items-center justify-between">
        <SectionHeading>Documents</SectionHeading>
        <button
          onClick={() => setWizardOpen(true)}
          className="rounded-[7px] px-2 py-[4px] text-[11.5px] font-medium text-accent hover:bg-accent-soft"
        >
          + New document
        </button>
      </div>

      {wizardOpen ? (
        <DocumentCreationWizard
          projectId={project.id}
          onCancel={() => setWizardOpen(false)}
          onDone={(doc) => {
            setWizardOpen(false)
            onChanged()
            router.push(`/projects/${project.id}/documents/${doc.id}`)
          }}
        />
      ) : null}

      {project.documents.length === 0 ? (
        <p className="text-[12.5px] text-mute">No documents yet.</p>
      ) : (
        <div className="flex flex-col divide-y divide-line rounded-[8px] border border-line">
          {project.documents.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between px-3 py-2">
              <Link
                href={`/projects/${project.id}/documents/${doc.id}`}
                className="text-[12.5px] font-medium text-ink hover:text-accent"
              >
                {doc.name}
                <span className="ml-2 text-[11px] font-normal text-mute">
                  {doc.document_type_id ? `${doc.document_type_id.replace(/-/g, " ")} · ` : ""}
                  {doc.content_items.length} content item{doc.content_items.length === 1 ? "" : "s"}
                </span>
              </Link>
              <div className="flex gap-1">
                <button
                  onClick={async () => {
                    await duplicateDocument(project.id, doc.id)
                    onChanged()
                  }}
                  className="rounded-[6px] px-2 py-[3px] text-[11px] text-ink-soft hover:bg-black/[.04]"
                >
                  Duplicate
                </button>
                <button
                  onClick={async () => {
                    if (!confirm(`Delete "${doc.name}"?`)) return
                    await deleteDocument(project.id, doc.id)
                    onChanged()
                  }}
                  className="rounded-[6px] px-2 py-[3px] text-[11px] text-crit hover:bg-crit-bg"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function AssetsSection({
  project,
  onChanged,
}: {
  project: ProjectWithBrandName
  onChanged: () => void
}) {
  const [busy, setBusy] = useState(false)

  return (
    <section>
      <div className="flex items-center justify-between">
        <SectionHeading>Assets</SectionHeading>
        <label className="cursor-pointer rounded-[7px] px-2 py-[4px] text-[11.5px] font-medium text-accent hover:bg-accent-soft">
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
                await uploadAsset(project.id, file)
                onChanged()
              } finally {
                setBusy(false)
                e.target.value = ""
              }
            }}
          />
        </label>
      </div>

      {project.assets.length === 0 ? (
        <p className="text-[12.5px] text-mute">No assets uploaded yet.</p>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {project.assets.map((asset) => (
            <div key={asset.id} className="rounded-[8px] border border-line p-2">
              {asset.content_type.startsWith("image/") ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={assetFileUrl(project.id, asset.id)}
                  alt={asset.filename}
                  className="mb-1.5 h-20 w-full rounded-[5px] object-cover"
                />
              ) : (
                <div className="mb-1.5 flex h-20 w-full items-center justify-center rounded-[5px] bg-black/[.03] text-[10.5px] text-mute">
                  {asset.filename.split(".").pop()?.toUpperCase()}
                </div>
              )}
              <p className="truncate text-[10.5px] text-ink-soft" title={asset.filename}>
                {asset.filename}
              </p>
              <p className="mt-0.5 font-mono text-[9.5px] text-mute" title="Use this id in an image content item">
                {asset.id}
              </p>
              <button
                onClick={async () => {
                  await deleteAsset(project.id, asset.id)
                  onChanged()
                }}
                className="mt-1 text-[10.5px] text-crit hover:underline"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function VersionsSection({
  project,
  onChanged,
}: {
  project: ProjectWithBrandName
  onChanged: () => void
}) {
  if (project.versions.length === 0) {
    return (
      <section>
        <SectionHeading>Versions</SectionHeading>
        <p className="text-[12.5px] text-mute">
          No saved versions yet. Open a document and save one after you like what you see.
        </p>
      </section>
    )
  }

  const sorted = [...project.versions].sort((a, b) => b.number - a.number)

  return (
    <section>
      <SectionHeading>Versions</SectionHeading>
      <div className="flex flex-col divide-y divide-line rounded-[8px] border border-line">
        {sorted.map((v) => (
          <div key={v.id} className="flex items-center justify-between px-3 py-2">
            <div>
              <p className="text-[12.5px] font-medium text-ink">
                v{v.number}
                {v.label ? ` — ${v.label}` : ""}
              </p>
              <p className="text-[11px] text-mute">
                {v.document_name} · {new Date(v.created_at).toLocaleString()}
              </p>
            </div>
            <button
              onClick={async () => {
                if (!confirm(`Restore "${v.document_name}" to version ${v.number}? This replaces its current content.`)) return
                await restoreVersion(project.id, v.number)
                onChanged()
              }}
              className="rounded-[6px] px-2 py-[4px] text-[11px] font-medium text-accent hover:bg-accent-soft"
            >
              Restore
            </button>
          </div>
        ))}
      </div>
    </section>
  )
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-[.07em] text-mute">{children}</p>
  )
}

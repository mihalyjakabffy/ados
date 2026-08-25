"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { TopBar } from "@/components/TopBar"
import { createProject, useProjects } from "@/lib/project-api"

// The M2.1 product home: "I have a project", not "I have a brand id".
// Every row here is a real, persisted brand.project.model.Project — there
// is no fixture data on this page.
export default function ProjectsPage() {
  const { data, isLoading, error } = useProjects()
  const [creating, setCreating] = useState(false)

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <p className="text-[12px] text-mute">
          Projects{data ? ` — ${data.projects.length}` : ""}
        </p>
        <button
          onClick={() => setCreating(true)}
          className="rounded-[7px] bg-accent px-3 py-[6px] text-[12px] font-medium text-white"
        >
          New project
        </button>
      </div>

      {creating ? <CreateProjectForm onDone={() => setCreating(false)} /> : null}

      <main className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <p className="text-[12.5px] text-mute">Loading projects…</p>
        ) : error ? (
          <p className="text-[12.5px] text-crit">Could not load projects.</p>
        ) : data && data.projects.length === 0 ? (
          <EmptyState onCreate={() => setCreating(true)} />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data?.projects.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
      <p className="text-[13.5px] font-medium text-ink">No projects yet</p>
      <p className="max-w-sm text-[12.5px] text-mute">
        A project holds a brand, its documents and the assets and content that go into them.
      </p>
      <button
        onClick={onCreate}
        className="mt-2 rounded-[7px] bg-accent px-3 py-[6px] text-[12px] font-medium text-white"
      >
        Create your first project
      </button>
    </div>
  )
}

function ProjectCard({ project }: { project: import("@/lib/project-types").ProjectSummary }) {
  const router = useRouter()
  return (
    <button
      onClick={() => router.push(`/projects/${project.id}`)}
      className="flex flex-col items-start gap-1 rounded-[10px] border border-line bg-paper-raised p-3.5 text-left hover:border-line-strong"
    >
      <span className="text-[13.5px] font-semibold text-ink">{project.name}</span>
      {project.description ? (
        <span className="line-clamp-2 text-[11.5px] text-mute">{project.description}</span>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-mute">
        <span>{project.brand_name ?? "No brand"}</span>
        <span>·</span>
        <span>{project.document_count} document{project.document_count === 1 ? "" : "s"}</span>
        <span>·</span>
        <span>{project.asset_count} asset{project.asset_count === 1 ? "" : "s"}</span>
        {project.current_version ? (
          <>
            <span>·</span>
            <span>v{project.current_version}</span>
          </>
        ) : null}
      </div>
    </button>
  )
}

function CreateProjectForm({ onDone }: { onDone: () => void }) {
  const router = useRouter()
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function submit() {
    if (!name.trim()) return
    setBusy(true)
    setErr(null)
    try {
      const project = await createProject({ name: name.trim(), description: description.trim() })
      onDone()
      router.push(`/projects/${project.id}`)
    } catch {
      setErr("Could not create the project.")
      setBusy(false)
    }
  }

  return (
    <div className="border-b border-line bg-paper-raised px-4 py-3">
      <div className="flex max-w-lg flex-col gap-2">
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Project name"
          className="rounded-[7px] border border-line-strong px-2.5 py-[6px] text-[12.5px]"
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          rows={2}
          className="rounded-[7px] border border-line-strong px-2.5 py-[6px] text-[12.5px]"
        />
        {err ? <p className="text-[11.5px] text-crit">{err}</p> : null}
        <div className="flex gap-2">
          <button
            onClick={submit}
            disabled={busy || !name.trim()}
            className="rounded-[7px] bg-accent px-3 py-[6px] text-[12px] font-medium text-white disabled:opacity-40"
          >
            {busy ? "Creating…" : "Create"}
          </button>
          <button
            onClick={onDone}
            className="rounded-[7px] px-3 py-[6px] text-[12px] text-mute hover:bg-black/[.03]"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

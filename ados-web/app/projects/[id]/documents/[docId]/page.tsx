"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useParams } from "next/navigation"
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from "lucide-react"
import { TopBar } from "@/components/TopBar"
import { CanvasPanel } from "@/components/workspace/CanvasPanel"
import { CommandPanel } from "@/components/workspace/CommandPanel"
import { DocumentContextPanel } from "@/components/workspace/DocumentContextPanel"
import { DIRECTIONS, useAdosState, type DirectionId } from "@/lib/ados-state"
import { ProjectApiError, composeDocument, useProject } from "@/lib/project-api"
import type { ContentModel } from "@/lib/pageplan-types"

function isDirectionId(value: string): value is DirectionId {
  return (DIRECTIONS as readonly string[]).includes(value)
}

// The M2.1 Document Workspace: the exact same Canvas + Command panels
// /workspace already uses (nothing in either is touched), with the
// project-fixture LibraryPanel swapped for DocumentContextPanel — this
// document's real content, assets and versions instead of a picker over
// dev fixtures. Opening a document composes it through the real backend
// once to get its translated ContentModel (never re-derived here — that
// would duplicate brand/project/model.py's own translation), then feeds
// that model through the state machine's own unmodified runCompose, so
// every follow-on command and iteration keeps working exactly as before.
export default function DocumentWorkspacePage() {
  const params = useParams<{ id: string; docId: string }>()
  const projectId = params.id
  const documentId = params.docId

  const { data: project, isLoading, error, mutate } = useProject(projectId)
  const state = useAdosState()
  const { activeBrandId, selectProject, selectBrand, setActiveContent, setDirection, runCompose } = state

  const [libraryOpen, setLibraryOpen] = useState(true)
  const [commandOpen, setCommandOpen] = useState(true)
  const [composeBusy, setComposeBusy] = useState(false)
  const [composeError, setComposeError] = useState<string | null>(null)
  const initialisedFor = useRef<string | null>(null)
  // holds the real, translated ContentModel between "brand just selected"
  // and "runCompose actually sees the new activeBrandId" — see the effect
  // below for why this hand-off can't happen inside one synchronous call.
  const pendingCompose = useRef<ContentModel | null>(null)

  const document = project?.documents.find((d) => d.id === documentId) ?? null

  const runRecompose = useCallback(async () => {
    if (!project || !document) return
    setComposeBusy(true)
    setComposeError(null)
    try {
      const result = await composeDocument(project.id, document.id)
      selectProject(project.id, project.name)
      if (isDirectionId(document.direction_id)) setDirection(document.direction_id)
      setActiveContent(result.content_model)
      if (project.brand_id) {
        // selectBrand() schedules a state update; the runCompose closure
        // captured on THIS render still reads the old activeBrandId (React
        // state updates aren't visible until the next render), so calling
        // runCompose synchronously here would silently no-op. Stash the
        // content and let the effect below fire runCompose once
        // activeBrandId has actually caught up.
        pendingCompose.current = result.content_model
        selectBrand(project.brand_id)
      }
    } catch (e) {
      setComposeError(
        e instanceof ProjectApiError
          ? describeComposeError(e)
          : "Could not compose this document.",
      )
      setComposeBusy(false)
    }
  }, [project, document, selectProject, selectBrand, setDirection, setActiveContent])

  useEffect(() => {
    if (!pendingCompose.current) return
    if (!project?.brand_id || activeBrandId !== project.brand_id) return
    const content = pendingCompose.current
    pendingCompose.current = null
    void runCompose(content).finally(() => setComposeBusy(false))
  }, [activeBrandId, project?.brand_id, runCompose])

  // Compose automatically the first time this document is opened (and
  // again if the user navigates to a different document) — not on every
  // re-render, and never silently overwriting a plan the user is mid-
  // review on for the same document.
  useEffect(() => {
    if (!project || !document) return
    if (initialisedFor.current === document.id) return
    initialisedFor.current = document.id
    void runRecompose()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project?.id, document?.id])

  if (isLoading) {
    return (
      <div className="flex h-screen flex-col">
        <TopBar />
        <p className="p-8 text-[12.5px] text-mute">Loading document…</p>
      </div>
    )
  }

  if (error || !project || !document) {
    return (
      <div className="flex h-screen flex-col">
        <TopBar />
        <p className="p-8 text-[13px] font-medium text-crit">Document not found.</p>
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      <div className="flex min-h-0 flex-1">
        {libraryOpen ? (
          <div className="relative w-[300px] flex-shrink-0 border-r border-line">
            <DocumentContextPanel
              project={project}
              document={document}
              onDocumentChanged={() => mutate()}
              onRecompose={runRecompose}
              composeBusy={composeBusy}
              composeError={composeError}
            />
            <CollapseButton
              onClick={() => setLibraryOpen(false)}
              icon={<PanelLeftClose className="h-3.5 w-3.5" />}
              className="right-2"
            />
          </div>
        ) : (
          <CollapseRail side="left" onClick={() => setLibraryOpen(true)} icon={<PanelLeftOpen className="h-3.5 w-3.5" />} />
        )}

        <div className="min-w-0 flex-1">
          <CanvasPanel />
        </div>

        {commandOpen ? (
          <div className="relative w-[360px] flex-shrink-0 border-l border-line">
            <CollapseButton
              onClick={() => setCommandOpen(false)}
              icon={<PanelRightClose className="h-3.5 w-3.5" />}
              className="right-2"
            />
            <CommandPanel />
          </div>
        ) : (
          <CollapseRail side="right" onClick={() => setCommandOpen(true)} icon={<PanelRightOpen className="h-3.5 w-3.5" />} />
        )}
      </div>
    </div>
  )
}

function describeComposeError(e: ProjectApiError): string {
  if (e.code === "no_brand_attached") return "Attach a brand to this project before composing."
  if (e.code === "no_content") return "Add content to this document before composing."
  if (e.code === "composition_infeasible") return "This content could not be composed — try adjusting it."
  return `Could not compose: ${e.code}`
}

function CollapseButton({
  onClick,
  icon,
  className = "",
}: {
  onClick: () => void
  icon: React.ReactNode
  className?: string
}) {
  return (
    <button
      onClick={onClick}
      className={`absolute top-2 z-10 rounded-[6px] p-1 text-mute hover:bg-black/[.04] hover:text-ink ${className}`}
      aria-label="Collapse panel"
    >
      {icon}
    </button>
  )
}

function CollapseRail({
  side,
  onClick,
  icon,
}: {
  side: "left" | "right"
  onClick: () => void
  icon: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      aria-label={`Expand ${side} panel`}
      className={`flex w-[22px] flex-shrink-0 items-center justify-center text-mute hover:bg-black/[.03] hover:text-ink ${
        side === "left" ? "border-r border-line" : "border-l border-line"
      }`}
    >
      {icon}
    </button>
  )
}

"use client"

// The shared ADOS workspace state — the one thing Library, Canvas and
// Command all read and write. Plain React Context, matching the only
// precedent in the repo (archstate-web/lib/project-context.tsx): a small
// value object, no reducer library, no external state store. Nothing here
// is a second domain model — activeProjectId/activeBrandId/activeDirectionId
// are references into real backend entities, and `plan` is exactly the
// ComposeResult the API returned, unmodified.

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react"
import { ComposeApiError, composeDocument } from "./brand-api"
import type { ComposeResult, ContentModel } from "./pageplan-types"

export const DIRECTIONS = ["editorial-quiet", "technical-dense", "image-led"] as const
export type DirectionId = (typeof DIRECTIONS)[number]

export type Selection =
  | { kind: "none" }
  | { kind: "project"; id: string; label: string }
  | { kind: "brand"; id: string; label: string }
  | { kind: "page"; pageIndex: number }
  | { kind: "contentBlock"; blockId: string; pageIndex: number; slotComponent: string }

interface AdosStateValue {
  activeProjectId: string | null
  activeProjectLabel: string | null
  activeBrandId: string | null
  activeDirectionId: DirectionId

  plan: ComposeResult | null
  planStatus: "idle" | "loading" | "loaded" | "error"
  planError: string | null

  selection: Selection

  selectProject: (id: string, label: string) => void
  selectBrand: (id: string) => void
  setDirection: (id: DirectionId) => void
  select: (selection: Selection) => void
  clearSelection: () => void

  runCompose: (content: ContentModel) => Promise<void>
}

const Ctx = createContext<AdosStateValue | null>(null)

export function AdosStateProvider({ children }: { children: ReactNode }) {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [activeProjectLabel, setActiveProjectLabel] = useState<string | null>(null)
  const [activeBrandId, setActiveBrandId] = useState<string | null>(null)
  const [activeDirectionId, setActiveDirectionId] = useState<DirectionId>("editorial-quiet")

  const [plan, setPlan] = useState<ComposeResult | null>(null)
  const [planStatus, setPlanStatus] = useState<AdosStateValue["planStatus"]>("idle")
  const [planError, setPlanError] = useState<string | null>(null)

  const [selection, setSelection] = useState<Selection>({ kind: "none" })

  const selectProject = useCallback((id: string, label: string) => {
    setActiveProjectId(id)
    setActiveProjectLabel(label)
    setSelection({ kind: "project", id, label })
  }, [])

  const selectBrand = useCallback((id: string) => {
    setActiveBrandId(id)
    setSelection({ kind: "brand", id, label: id })
  }, [])

  const setDirection = useCallback((id: DirectionId) => setActiveDirectionId(id), [])

  const select = useCallback((s: Selection) => setSelection(s), [])
  const clearSelection = useCallback(() => setSelection({ kind: "none" }), [])

  const runCompose = useCallback(
    async (content: ContentModel) => {
      if (!activeBrandId) return
      setPlanStatus("loading")
      setPlanError(null)
      try {
        const result = await composeDocument(activeBrandId, {
          content_model: content,
          direction_id: activeDirectionId,
        })
        setPlan(result)
        setPlanStatus("loaded")
        setSelection({ kind: "page", pageIndex: 0 })
      } catch (err) {
        setPlan(null)
        setPlanStatus("error")
        setPlanError(
          err instanceof ComposeApiError
            ? `${err.code}: ${JSON.stringify(err.detail)}`
            : String(err),
        )
      }
    },
    [activeBrandId, activeDirectionId],
  )

  const value = useMemo<AdosStateValue>(
    () => ({
      activeProjectId,
      activeProjectLabel,
      activeBrandId,
      activeDirectionId,
      plan,
      planStatus,
      planError,
      selection,
      selectProject,
      selectBrand,
      setDirection,
      select,
      clearSelection,
      runCompose,
    }),
    [
      activeProjectId,
      activeProjectLabel,
      activeBrandId,
      activeDirectionId,
      plan,
      planStatus,
      planError,
      selection,
      selectProject,
      selectBrand,
      setDirection,
      select,
      clearSelection,
      runCompose,
    ],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAdosState(): AdosStateValue {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error("useAdosState must be used within AdosStateProvider")
  return ctx
}

"use client"

// The shared ADOS workspace state — the one thing Library, Canvas and
// Command all read and write. Plain React Context, matching the only
// precedent in the repo (archstate-web/lib/project-context.tsx): a small
// value object, no reducer library, no external state store. Nothing here
// is a second domain model — activeProjectId/activeBrandId/activeDirectionId
// are references into real backend entities, and `plan` is exactly the
// ComposeResult the API returned, unmodified.
//
// Hard rule for M1.2 (ADOS §17): a failed compose or a failed intent must
// never clear an existing valid `plan`. planStatus/planError only ever
// describe the *first* compose (there is nothing to preserve yet);
// intentStatus/intentError describe every follow-on command and are
// deliberately a separate pair of fields so a rejected intent cannot,
// even by accident, blank the Canvas.

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react"
import { ComposeApiError, composeDocument, executeIntent, executeIteration } from "./brand-api"
import type { ComposeResult, ContentModel, EvaluationFinding } from "./pageplan-types"
import type {
  CommandIntent,
  CompositionScope,
  IntentResolution,
  IntentTarget,
  IntentType,
  PagePlanDiff,
} from "./intent-types"
import type { Recommendation } from "./iterate-types"

export const DIRECTIONS = ["editorial-quiet", "technical-dense", "image-led"] as const
export type DirectionId = (typeof DIRECTIONS)[number]

export type Selection =
  | { kind: "none" }
  | { kind: "project"; id: string; label: string }
  | { kind: "brand"; id: string; label: string }
  | { kind: "page"; pageIndex: number }
  | { kind: "contentBlock"; blockId: string; pageIndex: number; slotComponent: string }

export interface LastIntentSummary {
  intent: CommandIntent
  resolution: IntentResolution
  previousPlanHash: string
  newPlanHash: string
  /** null when the request carried no base_plan (nothing to scope against
   *  yet) — never fabricated when the backend didn't return one. */
  resolvedScope: CompositionScope | null
  diff: PagePlanDiff | null
}

// M1.4 — one review-driven iteration's before/why/what/where/after, kept
// apart from LastIntentSummary rather than merged into it: an iteration is
// never something the user composed by hand (there is no free choice of
// parameters), it is the system's own recommendation, executed. Keeping
// them separate lets the Command panel show the right causal chain for
// whichever one actually just ran, instead of one shape trying to mean both.
export interface LastIterationSummary {
  finding: EvaluationFinding
  recommendation: Recommendation
  beforeMetric: number
  afterMetric: number
  previousPlanHash: string
  newPlanHash: string
  resolvedScope: CompositionScope
  diff: PagePlanDiff
}

interface AdosStateValue {
  activeProjectId: string | null
  activeProjectLabel: string | null
  activeBrandId: string | null
  activeDirectionId: DirectionId
  /** The last intent's resulting_direction, carried forward so the next
   *  intent chains onto it instead of restarting from the base direction. */
  activeDirection: Record<string, unknown> | null

  plan: ComposeResult | null
  previousPlan: ComposeResult | null
  planStatus: "idle" | "loading" | "loaded" | "error"
  planError: string | null

  intentStatus: "idle" | "running" | "error"
  intentError: string | null
  lastIntentSummary: LastIntentSummary | null

  iterationStatus: "idle" | "running" | "error"
  iterationError: string | null
  lastIterationSummary: LastIterationSummary | null

  selection: Selection

  selectProject: (id: string, label: string) => void
  selectBrand: (id: string) => void
  setDirection: (id: DirectionId) => void
  select: (selection: Selection) => void
  clearSelection: () => void

  runCompose: (content: ContentModel) => Promise<void>
  runIntent: (
    content: ContentModel,
    type: IntentType,
    target: IntentTarget,
    parameters?: Record<string, unknown>,
  ) => Promise<void>
  /** ADOS-M1.4: execute the deterministic recommendation for one review
   *  finding. The command itself is decided server-side
   *  (brand.creative.iterate); this only names which finding to act on. */
  runIteration: (content: ContentModel, finding: EvaluationFinding) => Promise<void>
}

const Ctx = createContext<AdosStateValue | null>(null)

export function AdosStateProvider({ children }: { children: ReactNode }) {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [activeProjectLabel, setActiveProjectLabel] = useState<string | null>(null)
  const [activeBrandId, setActiveBrandId] = useState<string | null>(null)
  const [activeDirectionId, setActiveDirectionId] = useState<DirectionId>("editorial-quiet")
  const [activeDirection, setActiveDirection] = useState<Record<string, unknown> | null>(null)

  const [plan, setPlan] = useState<ComposeResult | null>(null)
  const [previousPlan, setPreviousPlan] = useState<ComposeResult | null>(null)
  const [planStatus, setPlanStatus] = useState<AdosStateValue["planStatus"]>("idle")
  const [planError, setPlanError] = useState<string | null>(null)

  const [intentStatus, setIntentStatus] = useState<AdosStateValue["intentStatus"]>("idle")
  const [intentError, setIntentError] = useState<string | null>(null)
  const [lastIntentSummary, setLastIntentSummary] = useState<LastIntentSummary | null>(null)

  const [iterationStatus, setIterationStatus] = useState<AdosStateValue["iterationStatus"]>("idle")
  const [iterationError, setIterationError] = useState<string | null>(null)
  const [lastIterationSummary, setLastIterationSummary] = useState<LastIterationSummary | null>(null)

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

  const setDirection = useCallback((id: DirectionId) => {
    setActiveDirectionId(id)
    setActiveDirection(null) // a new base direction starts a fresh chain
  }, [])

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
        setPreviousPlan(null) // a fresh compose starts a new lineage, not a diff of the old one
        setPlan(result)
        setActiveDirection(null)
        setLastIntentSummary(null)
        setLastIterationSummary(null)
        setPlanStatus("loaded")
        setSelection({ kind: "page", pageIndex: 0 })
      } catch (err) {
        // Nothing valid existed yet on the very first compose — planStatus
        // "error" is the only state, there is no plan to protect.
        setPlanStatus("error")
        setPlanError(
          err instanceof ComposeApiError ? `${err.code}: ${JSON.stringify(err.detail)}` : String(err),
        )
      }
    },
    [activeBrandId, activeDirectionId],
  )

  const runIntent = useCallback(
    async (
      content: ContentModel,
      type: IntentType,
      target: IntentTarget,
      parameters: Record<string, unknown> = {},
    ) => {
      if (!activeBrandId || !plan) return
      setIntentStatus("running")
      setIntentError(null)
      const previousHash = plan.plan.plan_hash
      try {
        const result = await executeIntent(activeBrandId, {
          content_model: content,
          ...(activeDirection
            ? { base_direction: activeDirection }
            : { base_direction_id: activeDirectionId }),
          intent: { type, target, parameters },
          previous_plan_hash: previousHash,
          // The plan already on screen — its presence is what makes the
          // target genuinely scoped instead of document-wide (M1.3).
          base_plan: plan.plan,
        })
        // Success: replace the plan. Failure (catch below) never reaches
        // here, so a rejected intent cannot blank a valid Canvas.
        setPreviousPlan(plan)
        setPlan({ plan: result.plan, evaluation: result.evaluation, meta: result.meta })
        setActiveDirection(result.resulting_direction)
        setLastIntentSummary({
          intent: result.intent,
          resolution: result.resolution,
          previousPlanHash: previousHash,
          newPlanHash: result.plan.plan_hash,
          resolvedScope: result.resolved_scope,
          diff: result.diff,
        })
        setLastIterationSummary(null) // only one "what just happened" banner at a time
        setIntentStatus("idle")
        // Jump to the page the diff says actually changed, so a scoped
        // command is visibly proven rather than left for the reader to
        // find by re-scanning every page. Falls back to page 0, exactly
        // M1.2's behaviour, when there was nothing to diff against.
        setSelection((s) => {
          if (s.kind !== "page" && s.kind !== "contentBlock") return s
          const changed = result.diff?.changed_pages ?? []
          return { kind: "page", pageIndex: changed.length > 0 ? changed[0] : 0 }
        })
      } catch (err) {
        setIntentStatus("error")
        setIntentError(
          err instanceof ComposeApiError ? `${err.code}: ${JSON.stringify(err.detail)}` : String(err),
        )
      }
    },
    [activeBrandId, activeDirection, activeDirectionId, plan],
  )

  const runIteration = useCallback(
    async (content: ContentModel, finding: EvaluationFinding) => {
      if (!activeBrandId || !plan || finding.page_index === null) return
      setIterationStatus("running")
      setIterationError(null)
      const previousHash = plan.plan.plan_hash
      try {
        const result = await executeIteration(activeBrandId, {
          content_model: content,
          ...(activeDirection
            ? { base_direction: activeDirection }
            : { base_direction_id: activeDirectionId }),
          base_plan: plan.plan,
          finding_code: finding.code,
          target_page: finding.page_index,
          previous_plan_hash: previousHash,
        })
        setPreviousPlan(plan)
        setPlan({ plan: result.plan, evaluation: result.after_evaluation, meta: result.meta })
        // activeDirection is deliberately left untouched: the recommended
        // command is page-scoped (brand.creative.scope), so only that one
        // page now differs from the document's base direction — carrying
        // it forward as the chain's new base would wrongly spread a
        // single-page choice onto every future document-wide command.
        setLastIterationSummary({
          finding: result.finding,
          recommendation: result.recommendation,
          beforeMetric: result.before_metric,
          afterMetric: result.after_metric,
          previousPlanHash: previousHash,
          newPlanHash: result.plan.plan_hash,
          resolvedScope: result.resolved_scope,
          diff: result.diff,
        })
        setLastIntentSummary(null) // only one "what just happened" banner at a time
        setIterationStatus("idle")
        setSelection({ kind: "page", pageIndex: finding.page_index as number })
      } catch (err) {
        setIterationStatus("error")
        setIterationError(
          err instanceof ComposeApiError ? `${err.code}: ${JSON.stringify(err.detail)}` : String(err),
        )
      }
    },
    [activeBrandId, activeDirection, activeDirectionId, plan],
  )

  const value = useMemo<AdosStateValue>(
    () => ({
      activeProjectId,
      activeProjectLabel,
      activeBrandId,
      activeDirectionId,
      activeDirection,
      plan,
      previousPlan,
      planStatus,
      planError,
      intentStatus,
      intentError,
      lastIntentSummary,
      iterationStatus,
      iterationError,
      lastIterationSummary,
      selection,
      selectProject,
      selectBrand,
      setDirection,
      select,
      clearSelection,
      runCompose,
      runIntent,
      runIteration,
    }),
    [
      activeProjectId,
      activeProjectLabel,
      activeBrandId,
      activeDirectionId,
      activeDirection,
      plan,
      previousPlan,
      planStatus,
      planError,
      intentStatus,
      intentError,
      lastIntentSummary,
      iterationStatus,
      iterationError,
      lastIterationSummary,
      selection,
      selectProject,
      selectBrand,
      setDirection,
      select,
      clearSelection,
      runCompose,
      runIntent,
      runIteration,
    ],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAdosState(): AdosStateValue {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error("useAdosState must be used within AdosStateProvider")
  return ctx
}

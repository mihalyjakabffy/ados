"use client"

import { useState } from "react"
import { DIRECTIONS, useAdosState, type DirectionId } from "@/lib/ados-state"
import { useContentExample } from "@/lib/brand-api"
import type { ContentModel, EvaluationFinding, Page } from "@/lib/pageplan-types"
import type { IntentTarget, IntentType } from "@/lib/intent-types"

// WHAT I WANT TO CHANGE. Not a chat clone: no bubbles, no assistant
// avatar, no conversational filler. Every action below builds a typed
// CommandIntent and sends it to POST /brands/{id}/intent — the structured
// layer in brand/creative/intent.py, not a second Composer. The free-text
// field stays absent on purpose: natural-language parsing is the next
// phase's boundary (User -> LLM -> CommandIntent), not this one's, and
// pretending it exists here would blur exactly the line ADOS depends on.
export function CommandPanel() {
  const state = useAdosState()
  const { selection, plan } = state

  return (
    <aside className="flex h-full flex-col overflow-y-auto px-4 py-3">
      <p className="mb-3 text-[10.5px] font-semibold uppercase tracking-[.07em] text-mute">Command</p>

      <IntentFeedback state={state} />
      <IterationFeedback state={state} />

      {selection.kind === "page" ? (
        <PageContext state={state} />
      ) : selection.kind === "contentBlock" ? (
        <BlockContext state={state} />
      ) : !plan ? (
        <ComposeIntent state={state} />
      ) : (
        <p className="text-[12.5px] text-mute">Select a page or object in Canvas to inspect it.</p>
      )}

      {plan ? (
        <div className="mt-6 border-t border-line pt-3">
          <p className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[.07em] text-mute">Review</p>
          <ReviewSummary state={state} />
        </div>
      ) : null}
    </aside>
  )
}

// Before/after — ADOS §16. Shown once, after the intent that produced it,
// so recomposition reads as "the document changed", not "I edited it".
function IntentFeedback({ state }: { state: ReturnType<typeof useAdosState> }) {
  const { intentStatus, intentError, lastIntentSummary } = state

  if (intentStatus === "running") {
    return <p className="mb-4 text-[12px] text-ink-soft">Applying command…</p>
  }

  if (intentStatus === "error" && intentError) {
    return (
      <div className="mb-4 rounded-[8px] border border-crit/30 bg-crit-bg px-2.5 py-2 text-[11.5px] text-crit">
        <p className="font-medium">Composition rejected</p>
        <p className="mt-0.5">{intentError}</p>
        <p className="mt-1 text-[10.5px] opacity-80">The previous PagePlan is still shown.</p>
      </div>
    )
  }

  if (lastIntentSummary) {
    const { intent, resolution, previousPlanHash, newPlanHash, resolvedScope, diff } = lastIntentSummary
    const changed = previousPlanHash !== newPlanHash
    return (
      <div className="mb-4 rounded-[8px] border border-ok/30 bg-ok-bg px-2.5 py-2 text-[11.5px] text-ok">
        <p className="font-medium">Command executed: {LABELS[intent.type]}</p>
        <p className="mt-0.5 text-ink-soft">
          PagePlan {changed ? "regenerated" : "recomposed — no change"} · hash {newPlanHash.slice(0, 12)}…
        </p>
        <ScopeSummary resolvedScope={resolvedScope} diff={diff} />
        {resolution.notes.map((n, i) => (
          <p key={i} className="mt-1 text-[10.5px] text-ink-soft opacity-80">
            {n}
          </p>
        ))}
      </div>
    )
  }

  return null
}

// What brand.creative.scope actually bounded the change to — read straight
// off resolved_scope/diff, not re-derived, since the diff is the one thing
// this layer must never compute itself (ADOS §21).
function ScopeSummary({
  resolvedScope,
  diff,
}: {
  resolvedScope: import("@/lib/intent-types").CompositionScope | null
  diff: import("@/lib/intent-types").PagePlanDiff | null
}) {
  if (!resolvedScope || !diff) return null

  if (resolvedScope.type === "document") {
    return (
      <p className="mt-1 text-[10.5px] text-ink-soft opacity-80">
        Whole document recomposed — {diff.changed_pages.length} of {diff.changed_pages.length + diff.unchanged_pages.length} page(s) changed.
      </p>
    )
  }

  const pageLabel = (i: number) => i + 1
  return (
    <p className="mt-1 text-[10.5px] text-ink-soft opacity-80">
      Scoped to page {pageLabel(Number(resolvedScope.id))} — page{diff.changed_pages.length === 1 ? "" : "s"}{" "}
      {diff.changed_pages.map(pageLabel).join(", ") || "none"} changed
      {diff.unchanged_pages.length > 0
        ? `; page${diff.unchanged_pages.length === 1 ? "" : "s"} ${diff.unchanged_pages.map(pageLabel).join(", ")} untouched.`
        : "."}
    </p>
  )
}

// ADOS-M1.4: WHY / WHAT / WHERE / RESULT for the one iteration that just
// ran. resolvedScope/diff are read straight off the response, same
// discipline as ScopeSummary above — never recomputed here.
function IterationFeedback({ state }: { state: ReturnType<typeof useAdosState> }) {
  const { iterationStatus, iterationError, lastIterationSummary } = state

  if (iterationStatus === "running") {
    return <p className="mb-4 text-[12px] text-ink-soft">Applying recommended fix…</p>
  }

  if (iterationStatus === "error" && iterationError) {
    const noImprovement = iterationError.includes("no_improvement")
    return (
      <div className="mb-4 rounded-[8px] border border-crit/30 bg-crit-bg px-2.5 py-2 text-[11.5px] text-crit">
        <p className="font-medium">
          {noImprovement ? "Recommendation did not help — nothing applied" : "Iteration rejected"}
        </p>
        <p className="mt-0.5">{iterationError}</p>
        <p className="mt-1 text-[10.5px] opacity-80">The previous PagePlan is still shown.</p>
      </div>
    )
  }

  if (lastIterationSummary) {
    const { finding, recommendation, beforeMetric, afterMetric, resolvedScope, diff } = lastIterationSummary
    return (
      <div className="mb-4 rounded-[8px] border border-ok/30 bg-ok-bg px-2.5 py-2 text-[11.5px] text-ok">
        <p className="font-medium">Recommendation applied: {recommendationLabel(recommendation.command_type)}</p>
        <p className="mt-0.5 text-ink-soft">
          {finding.metric} {beforeMetric.toFixed(2)} → {afterMetric.toFixed(2)}
        </p>
        <ScopeSummary resolvedScope={resolvedScope} diff={diff} />
      </div>
    )
  }

  return null
}

// Descriptive only — execution always goes through POST /brands/{id}/iterate,
// which is the one place the finding->command mapping actually lives
// (brand.creative.iterate._RECOMMENDATIONS). A code with no friendly label
// here still works; it just shows its raw command name.
function recommendationLabel(commandType: string): string {
  return LABELS[commandType as IntentType] ?? commandType
}

const LABELS: Record<IntentType, string> = {
  reduce_text_density: "Reduce text density",
  increase_text_density: "Increase text density",
  increase_image_emphasis: "Increase image emphasis",
  decrease_image_emphasis: "Decrease image emphasis",
  recompose_page: "Recompose",
  preserve_content: "Preserve content",
  remove_content: "Remove content",
  change_page_direction: "Change direction",
}

function ComposeIntent({ state }: { state: ReturnType<typeof useAdosState> }) {
  const { activeProjectId, activeProjectLabel, activeBrandId, activeDirectionId, setDirection, runCompose, planStatus } =
    state
  const { data: content } = useContentExample(activeProjectId)

  if (!activeProjectId || !activeBrandId) {
    return (
      <p className="text-[12.5px] text-mute">
        Select a project and a Brand in Library to begin.
      </p>
    )
  }

  return (
    <div>
      <p className="text-[12.5px] text-ink-soft">
        <span className="font-medium text-ink">{activeProjectLabel}</span> · ready to compose
      </p>

      <label className="mt-3 flex flex-col gap-1 text-[12px]">
        <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Creative direction</span>
        <select
          value={activeDirectionId}
          onChange={(e) => setDirection(e.target.value as DirectionId)}
          className="rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[6px]"
        >
          {DIRECTIONS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </label>

      <button
        onClick={() => content && runCompose(content)}
        disabled={!content || planStatus === "loading"}
        className="mt-3 w-full rounded-[7px] bg-accent px-3 py-[8px] text-[12.5px] font-medium text-white disabled:opacity-40"
      >
        {planStatus === "loading" ? "Composing…" : "Compose"}
      </button>
      <p className="mt-2 text-[11px] text-mute">
        POST /brands/{"{id}"}/compose · ContentModel + CreativeDirection → PagePlan
      </p>
    </div>
  )
}

function PageContext({ state }: { state: ReturnType<typeof useAdosState> }) {
  const selection = state.selection
  const { data: content } = useContentExample(state.activeProjectId)
  const [strength, setStrength] = useState(0.5)

  if (selection.kind !== "page" || !state.plan) return null
  const page = state.plan.plan.pages[selection.pageIndex]
  if (!page) return null

  const target: IntentTarget = { type: "page", id: String(page.index) }
  const busy = state.intentStatus === "running"

  const run = (type: IntentType, parameters: Record<string, unknown> = {}) =>
    content && state.runIntent(content, type, target, parameters)

  return (
    <div>
      <p className="text-[13px] font-semibold text-ink">Page {page.index + 1}</p>
      <p className="text-[11.5px] text-mute">{state.plan.plan.document}</p>

      <div className="mt-3 space-y-1.5 text-[12px]">
        <Row k="Archetype" v={page.archetype} />
        <Row k="Fill ratio" v={page.fill_ratio.toFixed(2)} />
        <Row k="Image ratio" v={page.image_ratio.toFixed(2)} />
        <Row k="Words" v={String(page.words)} />
        <Row k="Alignment edges" v={String(page.alignment_edges_x)} />
        <Row k="Objective score" v={page.objective.toFixed(0)} />
      </div>

      <PageFindings state={state} page={page} content={content} />

      <div className="mt-4">
        <p className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
          Strength — {strength.toFixed(1)}
        </p>
        <input
          type="range"
          min={0.1}
          max={1}
          step={0.1}
          value={strength}
          onChange={(e) => setStrength(Number(e.target.value))}
          className="w-full"
        />
      </div>

      <div className="mt-2 space-y-1">
        <ActionButton disabled={busy || !content} onClick={() => run("reduce_text_density", { strength })}>
          Reduce text density
        </ActionButton>
        <ActionButton disabled={busy || !content} onClick={() => run("increase_text_density", { strength })}>
          Increase text density
        </ActionButton>
        <ActionButton disabled={busy || !content} onClick={() => run("increase_image_emphasis", { strength })}>
          Increase image emphasis
        </ActionButton>
        <ActionButton disabled={busy || !content} onClick={() => run("decrease_image_emphasis", { strength })}>
          Decrease image emphasis
        </ActionButton>
        <ActionButton disabled={busy || !content} onClick={() => run("recompose_page")}>
          Recompose
        </ActionButton>
      </div>

      <p className="mb-1.5 mt-4 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">Switch direction</p>
      <div className="space-y-1">
        {DIRECTIONS.filter((d) => d !== state.plan?.plan.direction).map((d) => (
          <ActionButton
            key={d}
            disabled={busy || !content}
            onClick={() => run("change_page_direction", { direction_id: d })}
          >
            {d}
          </ActionButton>
        ))}
      </div>

      <p className="mt-3 text-[10.5px] text-mute">
        Scoped to this page — every other page stays byte-identical. If the change no longer
        fits this page alone, the command is refused rather than left to spill onto neighbours;
        recompose the whole document instead.
      </p>
    </div>
  )
}

// ADOS-M1.4: WHY (the finding) / WHAT (the recommended command, described)
// / WHERE (this page) / ACTION (Execute), for every review finding on the
// selected page. Findings without a code are shown but not actionable —
// most of what a review checks (pacing, measure, rejected candidates) has
// no deterministic fix, and this section says so rather than hiding them.
function PageFindings({
  state,
  page,
  content,
}: {
  state: ReturnType<typeof useAdosState>
  page: Page
  content: ContentModel | undefined
}) {
  const findings = (state.plan?.evaluation.findings ?? []).filter(
    (f: EvaluationFinding) => f.page_index === page.index,
  )
  if (findings.length === 0) return null

  const busy = state.iterationStatus === "running"

  return (
    <div className="mt-4 rounded-[8px] border border-line-strong bg-paper-raised p-2.5">
      <p className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
        Review — this page
      </p>
      <div className="space-y-2.5">
        {findings.map((f: EvaluationFinding, i: number) => (
          <div key={i} className="text-[11.5px]">
            <p>
              <span className={f.severity === "ERROR" || f.severity === "BLOCK" ? "font-semibold text-crit" : "font-semibold text-warn"}>
                {f.severity}
              </span>{" "}
              <span className="text-ink-soft">{f.message}</span>
            </p>
            {f.code ? (
              <button
                onClick={() => content && state.runIteration(content, f)}
                disabled={busy || !content}
                className="mt-1 w-full rounded-[6px] border border-line-strong bg-paper px-2 py-[5px] text-left text-[11px] text-ink-soft hover:bg-black/[.03] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Try recommended fix: {recommendationLabel(FINDING_COMMAND_HINT[f.code] ?? "?")}
              </button>
            ) : (
              <p className="mt-0.5 text-[10.5px] text-mute">No deterministic fix for this finding yet.</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// Display-only hint of what POST /iterate will likely recommend, kept in
// sync by hand with brand.creative.iterate._RECOMMENDATIONS — the mapping
// itself is never duplicated here, only its label. If the backend ever
// disagrees (a new finding code, a changed mapping), the request still
// goes through the real endpoint and either succeeds or reports
// no_recommendation honestly; this hint only affects button text.
const FINDING_COMMAND_HINT: Record<string, IntentType> = {
  FILL_RATIO_LOW: "change_page_direction",
}

function BlockContext({ state }: { state: ReturnType<typeof useAdosState> }) {
  const selection = state.selection
  const { data: content } = useContentExample(state.activeProjectId)
  if (selection.kind !== "contentBlock" || !state.plan) return null

  const page = state.plan.plan.pages[selection.pageIndex]
  const found = page?.slots.find((s) => (s.block || s.component) === selection.blockId)
  if (!page || !found) return null

  const busy = state.intentStatus === "running"
  const blockId = found.block || found.component
  const target: IntentTarget = { type: "contentBlock", id: blockId }

  const run = (type: IntentType) =>
    content && found.block && state.runIntent(content, type, target, { content_ids: [found.block] })

  return (
    <div>
      <p className="text-[13px] font-semibold text-ink">{found.component}</p>
      {found.block ? <p className="font-mono text-[11px] text-mute">{found.block}</p> : null}

      <div className="mt-3 space-y-1.5 text-[12px]">
        {found.label ? <Row k="Label" v={found.label} /> : null}
        {found.text ? <Row k="Text" v={found.text.length > 80 ? found.text.slice(0, 80) + "…" : found.text} /> : null}
        {found.path ? <Row k="Asset" v={found.path} /> : null}
        {found.provenance ? <Row k="Provenance" v={found.provenance} /> : null}
        <Row k="Rank" v={found.rank} />
        <Row k="Size" v={`${found.width_mm.toFixed(0)} × ${found.height_mm.toFixed(0)} mm`} />
        <Row k="Emphasis" v={found.emphasis ? "yes" : "no"} />
      </div>

      {found.block ? (
        <div className="mt-4 space-y-1">
          <p className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">Actions</p>
          <ActionButton disabled={busy || !content} onClick={() => run("preserve_content")}>
            Preserve this content
          </ActionButton>
          <ActionButton disabled={busy || !content} onClick={() => run("remove_content")}>
            Remove this content
          </ActionButton>
        </div>
      ) : (
        <p className="mt-4 text-[11.5px] text-mute">
          This slot is fixed (title, credit) rather than a ContentModel block — nothing to preserve or remove.
        </p>
      )}
    </div>
  )
}

function ReviewSummary({ state }: { state: ReturnType<typeof useAdosState> }) {
  if (!state.plan) return null
  const { evaluation } = state.plan
  return (
    <div>
      <p className="text-[12px] text-ink-soft">{evaluation.coverage}</p>
      {evaluation.findings.length === 0 ? (
        <p className="mt-1 text-[11.5px] text-ok">No findings.</p>
      ) : (
        <div className="mt-1.5 space-y-1.5">
          {evaluation.findings.map((f, i) => (
            <div key={i} className="text-[11.5px]">
              <span
                className={
                  f.severity === "ERROR" || f.severity === "BLOCK" ? "font-semibold text-crit" : "font-semibold text-warn"
                }
              >
                {f.severity}
              </span>{" "}
              <span className="text-ink-soft">{f.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ActionButton({
  children,
  disabled,
  onClick,
}: {
  children: React.ReactNode
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex w-full items-center justify-between rounded-[7px] border border-line-strong bg-paper-raised px-2.5 py-[6px] text-left text-[12px] text-ink-soft hover:bg-black/[.03] disabled:cursor-not-allowed disabled:opacity-40"
    >
      {children}
    </button>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-mute">{k}</span>
      <span className="text-right font-medium text-ink">{v}</span>
    </div>
  )
}

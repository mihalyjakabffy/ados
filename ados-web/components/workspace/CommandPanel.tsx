"use client"

import { DIRECTIONS, useAdosState, type DirectionId } from "@/lib/ados-state"
import { useContentExample } from "@/lib/brand-api"

// WHAT I WANT TO CHANGE. Not a chat clone: no bubbles, no assistant
// avatar, no conversational filler. In M1.1 there is exactly one real
// command — "compose this project, under this direction, for this
// brand" — plus a set of suggested follow-on actions that are honestly
// marked unavailable, because their backend operations (M2.9's
// Command -> Composer mutation pipeline) do not exist yet. Nothing here
// fakes a successful mutation.
export function CommandPanel() {
  const state = useAdosState()
  const { selection, plan } = state

  return (
    <aside className="flex h-full flex-col overflow-y-auto px-4 py-3">
      <p className="mb-3 text-[10.5px] font-semibold uppercase tracking-[.07em] text-mute">Command</p>

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
  if (selection.kind !== "page" || !state.plan) return null
  const page = state.plan.plan.pages[selection.pageIndex]
  if (!page) return null

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

      <SuggestedActions
        actions={["Recompose this page", "Reduce text density", "Increase image emphasis", "Make this page image-led"]}
      />
    </div>
  )
}

function BlockContext({ state }: { state: ReturnType<typeof useAdosState> }) {
  const selection = state.selection
  if (selection.kind !== "contentBlock" || !state.plan) return null

  const page = state.plan.plan.pages[selection.pageIndex]
  const found = page?.slots.find((s) => (s.block || s.component) === selection.blockId)
  if (!page || !found) return null

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

      <SuggestedActions actions={["Promote to hero", "Swap image", "Trim text"]} />
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

function SuggestedActions({ actions }: { actions: string[] }) {
  return (
    <div className="mt-4">
      <p className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">Suggested</p>
      <div className="space-y-1">
        {actions.map((a) => (
          <button
            key={a}
            disabled
            title="Not yet available — the Command → Composer mutation pipeline is a later phase"
            className="flex w-full items-center justify-between rounded-[7px] border border-line px-2.5 py-[6px] text-left text-[12px] text-mute opacity-60"
          >
            {a}
            <span className="text-[10px] uppercase tracking-[.04em]">upcoming</span>
          </button>
        ))}
      </div>
    </div>
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

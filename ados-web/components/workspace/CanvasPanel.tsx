"use client"

import { useAdosState } from "@/lib/ados-state"
import type { Page } from "@/lib/pageplan-types"

// WHAT IT LOOKS LIKE. A view over the authoritative PagePlan returned by
// POST /brands/{id}/compose — never a second layout engine. Every
// rectangle drawn here comes directly from a Slot's own x_mm/y_mm/
// width_mm/height_mm, scaled uniformly against the page's own
// page_width_mm/page_height_mm. Nothing is computed that the backend
// did not already state.
export function CanvasPanel() {
  const { plan, planStatus, planError, selection, select, lastIntentSummary } = useAdosState()

  if (planStatus === "idle" && !plan) {
    return (
      <Centered>
        <p className="text-[13px] text-mute">
          Select a project and a Brand in Library, then compose from Command.
        </p>
      </Centered>
    )
  }

  if (planStatus === "loading") {
    return (
      <Centered>
        <p className="text-[13px] text-ink-soft">Composing…</p>
        <p className="mt-1 text-[11.5px] text-mute">POST /brands/{"{id}"}/compose</p>
      </Centered>
    )
  }

  if (planStatus === "error") {
    return (
      <Centered>
        <p className="text-[13px] font-medium text-crit">Composition failed</p>
        <p className="mt-1 max-w-md text-center text-[11.5px] text-mute">{planError}</p>
      </Centered>
    )
  }

  if (!plan) {
    return (
      <Centered>
        <p className="text-[13px] text-mute">No PagePlan loaded.</p>
      </Centered>
    )
  }

  const { plan: pagePlan, evaluation } = plan
  const selectedIndex = selection.kind === "page" || selection.kind === "contentBlock" ? selection.pageIndex : 0
  const page = pagePlan.pages[selectedIndex] ?? pagePlan.pages[0]

  // Which pages the last command actually touched — read straight off the
  // diff brand.creative.scope returned, not re-derived by comparing plans
  // here. Only applies to the diff that produced the plan on screen; a
  // fresh compose (or a plan from before scoping existed) shows none.
  const changedPages =
    lastIntentSummary?.diff && lastIntentSummary.newPlanHash === pagePlan.plan_hash
      ? new Set(lastIntentSummary.diff.changed_pages)
      : null

  return (
    <div className="flex h-full flex-col bg-paper">
      {/* Plan status header — ADOS §20 */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-b border-line px-4 py-2 text-[11.5px]">
        <span className="font-semibold text-ink">{pagePlan.project_name}</span>
        <Stat label="Pages" value={String(pagePlan.pages.length)} />
        <Stat label="Direction" value={pagePlan.direction} />
        <Stat label="Brand" value={`v${pagePlan.brand_version}`} />
        <span
          className={`rounded-full px-2 py-[2px] text-[10.5px] font-semibold ${
            evaluation.ok ? "bg-ok-bg text-ok" : "bg-warn-bg text-warn"
          }`}
        >
          {evaluation.ok ? "Evaluation: PASS" : `Evaluation: ${evaluation.counts.ERROR + evaluation.counts.WARN} finding(s)`}
        </span>
        <span className="font-mono text-mute">{pagePlan.plan_hash.slice(0, 16)}…</span>
        {pagePlan.rejected.length > 0 ? (
          <span className="text-mute">{pagePlan.rejected.length} candidate(s) rejected</span>
        ) : null}
      </div>

      {/* Page thumbnail rail */}
      <div className="flex gap-2 overflow-x-auto border-b border-line px-4 py-3">
        {pagePlan.pages.map((p) => (
          <Thumbnail
            key={p.index}
            page={p}
            active={p.index === selectedIndex}
            changed={changedPages?.has(p.index) ?? false}
            onClick={() => select({ kind: "page", pageIndex: p.index })}
          />
        ))}
      </div>

      {/* Selected page, full geometry */}
      <div className="flex flex-1 items-center justify-center overflow-auto p-6">
        <PageView
          page={page}
          scale={1}
          onSelectSlot={(slot) =>
            select({
              kind: "contentBlock",
              blockId: slot.block || slot.component,
              pageIndex: page.index,
              slotComponent: slot.component,
            })
          }
          selectedBlockId={selection.kind === "contentBlock" ? selection.blockId : null}
        />
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <span className="text-mute">
      {label} <span className="font-medium text-ink-soft">{value}</span>
    </span>
  )
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex h-full flex-col items-center justify-center bg-paper p-8">{children}</div>
}

const THUMB_WIDTH = 72

function Thumbnail({
  page,
  active,
  changed,
  onClick,
}: {
  page: Page
  active: boolean
  changed: boolean
  onClick: () => void
}) {
  const aspect = page.grid.page_height_mm / page.grid.page_width_mm
  return (
    <button
      onClick={onClick}
      className={`relative flex-shrink-0 overflow-hidden rounded-[4px] border text-left ${
        active ? "border-accent ring-1 ring-accent" : "border-line-strong hover:border-mute"
      }`}
      style={{ width: THUMB_WIDTH }}
    >
      {changed ? (
        <span
          title="Changed by the last command"
          className="absolute right-1 top-1 z-10 h-[6px] w-[6px] rounded-full bg-accent"
        />
      ) : null}
      <div
        className="relative bg-paper-raised"
        style={{ width: THUMB_WIDTH, height: THUMB_WIDTH * aspect }}
      >
        {page.slots.map((s, i) => (
          <div
            key={i}
            className="absolute bg-accent-soft"
            style={{
              left: `${(s.x_mm / page.grid.page_width_mm) * 100}%`,
              top: `${(s.y_mm / page.grid.page_height_mm) * 100}%`,
              width: `${(s.width_mm / page.grid.page_width_mm) * 100}%`,
              height: `${(s.height_mm / page.grid.page_height_mm) * 100}%`,
            }}
          />
        ))}
      </div>
      <div className="px-1 py-0.5">
        <p className="truncate text-[9px] font-medium text-ink-soft">{page.index + 1}. {page.archetype}</p>
      </div>
    </button>
  )
}

function PageView({
  page,
  onSelectSlot,
  selectedBlockId,
}: {
  page: Page
  scale: number
  onSelectSlot: (slot: Page["slots"][number]) => void
  selectedBlockId: string | null
}) {
  const MAX_WIDTH = 480
  const width = MAX_WIDTH
  const height = MAX_WIDTH * (page.grid.page_height_mm / page.grid.page_width_mm)

  return (
    <div
      className="relative flex-shrink-0 border border-line-strong bg-paper-raised shadow-panel"
      style={{ width, height }}
    >
      {page.slots.map((s, i) => {
        const id = s.block || s.component
        const active = id === selectedBlockId
        return (
          <button
            key={i}
            onClick={() => onSelectSlot(s)}
            className={`absolute overflow-hidden border text-left ${
              active ? "border-accent bg-accent-soft" : "border-line-strong bg-sidebar hover:bg-black/[.03]"
            }`}
            style={{
              left: `${(s.x_mm / page.grid.page_width_mm) * 100}%`,
              top: `${(s.y_mm / page.grid.page_height_mm) * 100}%`,
              width: `${(s.width_mm / page.grid.page_width_mm) * 100}%`,
              height: `${(s.height_mm / page.grid.page_height_mm) * 100}%`,
            }}
          >
            <p className={`px-1 pt-0.5 text-[8.5px] font-semibold uppercase tracking-[.03em] ${active ? "text-accent" : "text-mute"}`}>
              {s.component}
            </p>
            <p className="truncate px-1 text-[9px] text-ink-soft">{s.label || s.text}</p>
          </button>
        )
      })}
    </div>
  )
}

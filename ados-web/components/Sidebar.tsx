"use client"

import type { PackageData } from "@/lib/types"

// The Library rail: Set -> Package, per ADOS-2.1.2's containment graph
// (Project -> Set -> Package -> Container). This pane only ever shows
// Library structure — Rules/Encoding/QA live under System in the TopBar,
// not stacked into this sidebar.
export function Sidebar({ pkg }: { pkg?: PackageData }) {
  const byType = new Map<string, number>()
  for (const c of pkg?.containers ?? []) {
    byType.set(c.type, (byType.get(c.type) ?? 0) + 1)
  }

  return (
    <aside className="flex w-[200px] flex-shrink-0 flex-col overflow-y-auto border-r border-line bg-sidebar px-2.5 py-3">
      <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Sets</p>

      {pkg ? (
        <div className="mb-5">
          <div className="rounded-[7px] px-2 py-[6px] text-[12.5px] font-semibold text-ink-soft">
            {pkg.set.originator_code}
          </div>
          <div className="ml-2 border-l border-line-strong pl-2.5">
            <div className="rounded-[7px] bg-accent-soft px-2 py-[6px] text-[12.5px] font-semibold text-accent">
              {pkg.package_id}
              <div className="mt-0.5 truncate text-[10.5px] font-normal text-accent/80">{pkg.purpose}</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="px-2 py-[6px] text-[12px] text-mute">Betöltés…</div>
      )}

      {byType.size > 0 ? (
        <div>
          <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Típus szerint</p>
          <div className="space-y-0.5">
            {[...byType.entries()].map(([type, count]) => (
              <div key={type} className="flex items-center gap-2 rounded-[7px] px-2 py-[6px] text-[12.5px] text-ink-soft">
                <span className="flex-1 truncate">{type}</span>
                <span className="text-[10.5px] text-mute">{count}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="flex-1" />
      <div className="px-2 pb-1 pt-3 text-[10.5px] text-mute">
        ADOS 1.0 · {pkg?.set.conformance_class ? `Class ${pkg.set.conformance_class}` : "reference build"}
      </div>
    </aside>
  )
}

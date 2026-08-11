"use client"

import type { ContainerSummary } from "@/lib/types"
import { relativeDate } from "@/lib/format"
import { StatusPill } from "./StatusPill"
import { TypeIcon } from "./TypeIcon"

const COLUMNS = "1fr 84px 128px 76px 96px 120px"

export function ContainerList({
  containers,
  selectedId,
  onSelect,
}: {
  containers: ContainerSummary[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  if (containers.length === 0) {
    return <div className="p-8 text-center text-[12.5px] text-mute">Nincs a szűrésnek megfelelő elem.</div>
  }

  return (
    <div className="flex-1 overflow-auto">
      <div
        className="sticky top-0 grid gap-2.5 border-b border-line-strong bg-paper px-4 py-2 text-[10.5px] font-semibold uppercase tracking-[.04em] text-mute"
        style={{ gridTemplateColumns: COLUMNS }}
      >
        <span>Név</span>
        <span>Típus</span>
        <span>Státusz</span>
        <span>Rev.</span>
        <span>Módosítva</span>
        <span>Szerző</span>
      </div>

      {containers.map((c) => {
        const selected = c.container_id === selectedId
        return (
          <button
            key={c.container_id}
            onClick={() => onSelect(c.container_id)}
            className={`grid w-full items-center gap-2.5 border-b border-line px-4 py-2 text-left text-[12.5px] ${
              selected ? "bg-accent-soft" : "hover:bg-black/[.025]"
            }`}
            style={{ gridTemplateColumns: COLUMNS }}
          >
            <span className="flex min-w-0 items-center gap-2.5">
              <TypeIcon type={c.type} />
              <span className="min-w-0">
                <span className="block truncate font-medium text-ink">{c.title ?? c.short_id ?? c.container_id}</span>
                <span className="block truncate font-mono text-[11px] text-mute">{c.container_id}</span>
              </span>
            </span>
            <span className="truncate text-mute">{c.type}</span>
            <span>
              <StatusPill status={c.status} />
            </span>
            <span className="font-mono text-mute">{c.revision}</span>
            <span className="text-mute">{relativeDate(c.latest_revision_date)}</span>
            <span className="truncate text-mute">{c.author ?? "—"}</span>
          </button>
        )
      })}
    </div>
  )
}

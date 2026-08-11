"use client"

import type { ContainerSummary, PackageData } from "@/lib/types"
import { useContainer } from "@/lib/api"
import { TypeIcon } from "./TypeIcon"

// Miller-column drill-down proving the ADOS containment graph
// (ADOS-2.1.2): Set -> Package -> Container -> Region. Three columns is a
// deliberate floor, not a limitation — ADOS-0.3.040 caps navigation at
// four levels, and Region is the last of them.
export function ColumnView({
  pkg,
  containers,
  selectedId,
  onSelect,
}: {
  pkg?: PackageData
  containers: ContainerSummary[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const { data: detail } = useContainer(selectedId)

  return (
    <div className="flex flex-1 overflow-hidden">
      <MillerColumn title="Package">
        {pkg ? (
          <MillerItem active label={pkg.package_id} sub={pkg.purpose ?? undefined} hasChildren />
        ) : (
          <div className="px-3 py-2 text-[12px] text-mute">Betöltés…</div>
        )}
      </MillerColumn>

      <MillerColumn title="Container">
        {containers.map((c) => (
          <MillerItem
            key={c.container_id}
            active={c.container_id === selectedId}
            label={c.title ?? c.short_id ?? c.container_id}
            sub={c.container_id}
            icon={<TypeIcon type={c.type} />}
            hasChildren
            onClick={() => onSelect(c.container_id)}
          />
        ))}
      </MillerColumn>

      <MillerColumn title="Region">
        {!selectedId ? (
          <div className="px-3 py-2 text-[12px] text-mute">Válassz egy Containert.</div>
        ) : !detail ? (
          <div className="px-3 py-2 text-[12px] text-mute">Betöltés…</div>
        ) : (detail.regions ?? []).length === 0 ? (
          <div className="px-3 py-2 text-[12px] text-mute">Nincs régió.</div>
        ) : (
          (detail.regions ?? []).map((r) => (
            <div key={r.region_id} className="border-b border-line px-3 py-2 text-[12px]">
              <div className="font-mono font-semibold text-ink">{r.region_id}</div>
              {(r.views ?? []).map((v) => (
                <div key={v.view_id} className="mt-0.5 text-[11px] text-mute">
                  {v.view_type}
                  {v.level ? ` · ${v.level}` : ""}
                  {v.scale_denominator ? ` · 1∶${v.scale_denominator}` : ""}
                </div>
              ))}
              {(r.blocks ?? []).map((b) => (
                <div key={b.block_id} className="mt-0.5 text-[11px] text-mute">
                  block · {b.kind}
                </div>
              ))}
            </div>
          ))
        )}
      </MillerColumn>
    </div>
  )
}

function MillerColumn({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex w-1/3 flex-shrink-0 flex-col overflow-y-auto border-r border-line last:border-r-0">
      <p className="border-b border-line-strong px-3 py-1.5 text-[10.5px] font-semibold uppercase tracking-[.06em] text-mute">
        {title}
      </p>
      <div className="flex-1">{children}</div>
    </div>
  )
}

function MillerItem({
  label,
  sub,
  active,
  hasChildren,
  icon,
  onClick,
}: {
  label: string
  sub?: string
  active?: boolean
  hasChildren?: boolean
  icon?: React.ReactNode
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-2 border-b border-line px-3 py-2 text-left text-[12px] ${
        active ? "bg-accent text-white" : "text-ink-soft hover:bg-black/[.03]"
      }`}
    >
      {icon}
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{label}</span>
        {sub ? (
          <span className={`block truncate font-mono text-[10.5px] ${active ? "text-white/75" : "text-mute"}`}>
            {sub}
          </span>
        ) : null}
      </span>
      {hasChildren ? <span className={active ? "text-white/70" : "text-line-strong"}>›</span> : null}
    </button>
  )
}

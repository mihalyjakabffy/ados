"use client"

import { useContainer } from "@/lib/api"
import { relativeDate, statusLabel } from "@/lib/format"
import { StatusPill } from "./StatusPill"

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 border-t border-line py-[7px] text-[12px] first:border-t-0">
      <span className="text-mute">{k}</span>
      <span className="text-right font-medium text-ink">{v}</span>
    </div>
  )
}

export function Inspector({ containerId }: { containerId: string | null }) {
  const { data: c, isLoading } = useContainer(containerId)

  if (!containerId) {
    return (
      <aside className="flex w-[280px] flex-shrink-0 items-center justify-center border-l border-line p-6 text-center text-[12.5px] text-mute">
        Válassz egy elemet a listából a részletek megtekintéséhez.
      </aside>
    )
  }

  if (isLoading || !c) {
    return <aside className="w-[280px] flex-shrink-0 border-l border-line p-4 text-[12.5px] text-mute">Betöltés…</aside>
  }

  const view = c.regions?.flatMap((r) => r.views ?? [])[0]

  return (
    <aside className="w-[280px] flex-shrink-0 overflow-y-auto border-l border-line p-4">
      <div
        className="mb-3 h-[100px] rounded-[10px] border border-line-strong bg-paper-raised"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, var(--accent-soft) 0, var(--accent-soft) 1px, transparent 1px, transparent 9px), repeating-linear-gradient(90deg, var(--accent-soft) 0, var(--accent-soft) 1px, transparent 1px, transparent 9px)",
        }}
      />

      <h2 className="text-[14px] font-semibold leading-snug text-ink">{c.title ?? c.short_id}</h2>
      <p className="mb-3 font-mono text-[11px] text-mute">
        {c.container_id} · Rev {c.revision}
      </p>

      <Row k="Státusz" v={<StatusPill status={c.status} />} />
      {view?.level ? <Row k="Szint" v={view.level} /> : null}
      {view?.scale_denominator ? <Row k="Lépték" v={`1∶${view.scale_denominator}`} /> : null}
      <Row k="Szerző / Ellenőr" v={`${c.parties.author} / ${c.parties.checker}`} />
      <Row k="Jóváhagyó" v={c.parties.approver} />
      {c.read_with.length > 0 ? <Row k="Együtt olvasandó" v={`${c.read_with.length} dokumentum`} /> : null}
      <Row k="Hivatkozik rá" v={`${c.references_in.length} helyről`} />
      <Row k="Kifelé hivatkozik" v={`${c.references_out.length} célra`} />

      {c.scope_statement ? (
        <div className="mt-3 rounded-[8px] bg-sidebar p-2.5 text-[11.5px] leading-relaxed text-ink-soft">
          <span className="font-semibold text-ink">Scope. </span>
          {c.scope_statement}
        </div>
      ) : null}

      {c.revisions.length > 0 ? (
        <div className="mt-4">
          <p className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[.06em] text-mute">Revíziók</p>
          <div className="space-y-2">
            {c.revisions.map((rev) => (
              <div key={rev.code} className="border-t border-line pt-2 text-[11.5px] first:border-t-0 first:pt-0">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-semibold text-ink">{rev.code}</span>
                  <span className="text-mute">{relativeDate(rev.date)}</span>
                </div>
                <p className="mt-0.5 text-ink-soft">{rev.description}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {c.references_out.length > 0 ? (
        <div className="mt-4">
          <p className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[.06em] text-mute">Hivatkozások</p>
          <div className="space-y-1.5">
            {c.references_out.map((ref) => (
              <div key={ref.ref_id} className="text-[11.5px]">
                <span className="text-mute">{ref.kind.replace(/_/g, " ")} → </span>
                <span className="font-mono text-ink-soft">{ref.target.container_id ?? ref.target.external_ref}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <p className="mt-4 text-[10.5px] text-mute">{statusLabel(c.status)}</p>
    </aside>
  )
}

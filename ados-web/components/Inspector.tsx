"use client"

import { useContainer } from "@/lib/api"
import { relativeDate, statusLabel } from "@/lib/format"
import { StatusPill } from "./StatusPill"

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-line py-3 first:border-t-0 first:pt-0">
      <p className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[.07em] text-mute">{title}</p>
      {children}
    </div>
  )
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-[3px] text-[12px]">
      <span className="text-mute">{k}</span>
      <span className="text-right font-medium text-ink">{v}</span>
    </div>
  )
}

export function Inspector({ containerId }: { containerId: string | null }) {
  const { data: c, isLoading } = useContainer(containerId)

  if (!containerId) {
    return (
      <aside className="flex w-[300px] flex-shrink-0 items-center justify-center border-l border-line p-6 text-center text-[12.5px] text-mute">
        Válassz egy elemet a részletek megtekintéséhez.
      </aside>
    )
  }

  if (isLoading || !c) {
    return <aside className="w-[300px] flex-shrink-0 border-l border-line p-4 text-[12.5px] text-mute">Betöltés…</aside>
  }

  const view = c.regions?.flatMap((r) => r.views ?? [])[0]
  const passCount = c.qa.filter((r) => r.status === "pass").length

  return (
    <aside className="w-[300px] flex-shrink-0 overflow-y-auto border-l border-line px-4 py-3">
      <p className="font-mono text-[11px] text-mute">{c.short_id ?? c.container_id}</p>
      <h2 className="text-[15px] font-semibold leading-snug text-ink">{c.title ?? c.container_id}</h2>

      <Section title="Identity">
        <Row k="ID" v={<span className="font-mono">{c.container_id}</span>} />
        <Row k="Típus" v={c.type} />
        <Row k="Státusz" v={<StatusPill status={c.status} />} />
        <Row k="Revízió" v={<span className="font-mono">{c.revision}</span>} />
      </Section>

      <Section title="Document">
        {view?.level ? <Row k="Szint" v={view.level} /> : null}
        {view?.scale_denominator ? <Row k="Lépték" v={`1∶${view.scale_denominator}`} /> : null}
        <Row k="Szerző" v={c.parties.author} />
        <Row k="Ellenőr" v={c.parties.checker} />
        <Row k="Jóváhagyó" v={c.parties.approver} />
      </Section>

      <Section title="Relationships">
        <Row k="Együtt olvasandó" v={c.read_with.length > 0 ? `${c.read_with.length} dokumentum` : "—"} />
        <Row k="Hivatkozik rá" v={`${c.references_in.length} helyről`} />
        <Row k="Kifelé hivatkozik" v={`${c.references_out.length} célra`} />
        {c.references_out.length > 0 ? (
          <div className="mt-1.5 space-y-1">
            {c.references_out.map((ref) => (
              <div key={ref.ref_id} className="text-[11px]">
                <span className="text-mute">{ref.kind.replace(/_/g, " ")} → </span>
                <span className="font-mono text-ink-soft">{ref.target.container_id ?? ref.target.external_ref}</span>
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      <Section title={`QA — ${passCount}/${c.qa.length}`}>
        <div className="space-y-1.5">
          {c.qa.map((r) => (
            <div key={r.rule} className="flex items-start gap-2 text-[11.5px]">
              <span className={r.status === "pass" ? "text-ok" : "text-warn"}>{r.status === "pass" ? "✓" : "⚠"}</span>
              <span className="min-w-0 flex-1">
                <span className="block text-ink-soft">{r.label}</span>
                {r.status === "fail" ? <span className="block text-mute">{r.detail}</span> : null}
                <span className="font-mono text-[10px] text-mute">{r.rule}</span>
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Scope">
        <p className="text-[11.5px] leading-relaxed text-ink-soft">{c.scope_statement}</p>
      </Section>

      {c.revisions.length > 0 ? (
        <Section title="Revíziók">
          <div className="space-y-2">
            {c.revisions.map((rev) => (
              <div key={rev.code} className="text-[11.5px]">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-semibold text-ink">{rev.code}</span>
                  <span className="text-mute">{relativeDate(rev.date)}</span>
                </div>
                <p className="mt-0.5 text-ink-soft">{rev.description}</p>
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      <p className="mt-3 text-[10.5px] text-mute">{statusLabel(c.status)}</p>
    </aside>
  )
}

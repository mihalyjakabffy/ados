"use client"

import { useState } from "react"
import { usePackage, useRules } from "@/lib/api"
import { Sidebar } from "@/components/Sidebar"
import { Toolbar } from "@/components/Toolbar"
import { RuleLevelPill } from "@/components/RuleLevelPill"

const COLUMNS = "150px 1fr 220px 70px 60px"

export default function RulesPage() {
  const { data: pkg } = usePackage()
  const [search, setSearch] = useState("")
  const { data, error, isLoading } = useRules({ q: search || undefined })

  return (
    <div className="flex h-screen">
      <Sidebar pkg={pkg} />

      <main className="flex min-w-0 flex-1 flex-col">
        <Toolbar
          crumbs={["ADOS 1.0", "Szabálytár", data ? `${data.matched} / ${data.rule_count}` : "…"]}
          search={search}
          onSearchChange={setSearch}
          placeholder="Keresés azonosító vagy név szerint…"
        />

        {isLoading ? (
          <div className="flex-1 p-8 text-[12.5px] text-mute">Betöltés…</div>
        ) : error ? (
          <div className="flex-1 p-8 text-[12.5px] text-crit">Nem sikerült betölteni a szabálytárat.</div>
        ) : (
          <div className="flex-1 overflow-auto">
            <div
              className="sticky top-0 grid gap-2.5 border-b border-line-strong bg-paper px-4 py-2 text-[10.5px] font-semibold uppercase tracking-[.04em] text-mute"
              style={{ gridTemplateColumns: COLUMNS }}
            >
              <span>Azonosító</span>
              <span>Név</span>
              <span>Kötet</span>
              <span>Szint</span>
              <span>Súly.</span>
            </div>

            {data?.rules.map((rule) => (
              <div
                key={rule.id}
                className="grid items-center gap-2.5 border-b border-line px-4 py-2 text-[12.5px]"
                style={{ gridTemplateColumns: COLUMNS }}
              >
                <span className="font-mono text-ink-soft">{rule.id}</span>
                <span className="truncate text-ink">{rule.name}</span>
                <span className="truncate text-mute">{rule.volume}</span>
                <span>
                  <RuleLevelPill level={rule.level} />
                </span>
                <span className="text-mute">{rule.severity}</span>
              </div>
            ))}

            {data && data.rules.length === 0 ? (
              <div className="p-8 text-center text-[12.5px] text-mute">Nincs a keresésnek megfelelő szabály.</div>
            ) : null}
          </div>
        )}
      </main>
    </div>
  )
}

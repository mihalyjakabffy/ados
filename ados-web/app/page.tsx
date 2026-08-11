"use client"

import { useMemo, useState } from "react"
import { usePackage } from "@/lib/api"
import { TopBar } from "@/components/TopBar"
import { Sidebar } from "@/components/Sidebar"
import { ContainerList } from "@/components/ContainerList"
import { ColumnView } from "@/components/ColumnView"
import { Inspector } from "@/components/Inspector"
import { ViewSwitch, type ViewMode } from "@/components/ViewSwitch"

export default function LibraryPage() {
  const { data: pkg, error, isLoading } = usePackage()
  const [search, setSearch] = useState("")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode, setMode] = useState<ViewMode>("list")

  const containers = useMemo(() => {
    const all = pkg?.containers ?? []
    if (!search.trim()) return all
    const needle = search.toLowerCase()
    return all.filter(
      (c) =>
        c.title?.toLowerCase().includes(needle) ||
        c.container_id.toLowerCase().includes(needle) ||
        c.short_id?.toLowerCase().includes(needle),
    )
  }, [pkg, search])

  const activeId = selectedId ?? containers[0]?.container_id ?? null

  return (
    <div className="flex h-screen flex-col">
      <TopBar pkg={pkg} search={search} onSearchChange={setSearch} searchPlaceholder="Keresés a Library-ban…" />

      <div className="flex min-h-0 flex-1">
        <Sidebar pkg={pkg} />

        <main className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center justify-between border-b border-line px-4 py-2">
            <p className="text-[12px] text-mute">
              {pkg ? `${pkg.purpose} · ${containers.length} elem` : "Betöltés…"}
            </p>
            <ViewSwitch mode={mode} onChange={setMode} />
          </div>

          {isLoading ? (
            <div className="flex-1 p-8 text-[12.5px] text-mute">Betöltés…</div>
          ) : error ? (
            <div className="flex-1 p-8 text-[12.5px] text-crit">
              Nem sikerült elérni az ados-service-t ({process.env.NEXT_PUBLIC_ADOS_API_URL ?? "http://localhost:8010"}
              ). Ellenőrizd, hogy fut-e a backend.
            </div>
          ) : mode === "list" ? (
            <ContainerList containers={containers} selectedId={activeId} onSelect={setSelectedId} />
          ) : (
            <ColumnView pkg={pkg} containers={containers} selectedId={activeId} onSelect={setSelectedId} />
          )}
        </main>

        <Inspector containerId={activeId} />
      </div>
    </div>
  )
}

"use client"

import { useMemo, useState } from "react"
import { usePackage } from "@/lib/api"
import { Sidebar } from "@/components/Sidebar"
import { Toolbar } from "@/components/Toolbar"
import { ContainerList } from "@/components/ContainerList"
import { Inspector } from "@/components/Inspector"

export default function BrowserPage() {
  const { data: pkg, error, isLoading } = usePackage()
  const [search, setSearch] = useState("")
  const [selectedId, setSelectedId] = useState<string | null>(null)

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
    <div className="flex h-screen">
      <Sidebar pkg={pkg} />

      <main className="flex min-w-0 flex-1 flex-col">
        <Toolbar
          crumbs={
            pkg
              ? [pkg.project.name, pkg.set.originator_code, pkg.purpose ?? pkg.package_id]
              : ["ADOS"]
          }
          search={search}
          onSearchChange={setSearch}
          placeholder="Keresés a csomagban…"
        />

        {isLoading ? (
          <div className="flex-1 p-8 text-[12.5px] text-mute">Betöltés…</div>
        ) : error ? (
          <div className="flex-1 p-8 text-[12.5px] text-crit">
            Nem sikerült elérni az ados-service-t ({process.env.NEXT_PUBLIC_ADOS_API_URL ?? "http://localhost:8010"}).
            Ellenőrizd, hogy fut-e a backend.
          </div>
        ) : (
          <ContainerList containers={containers} selectedId={activeId} onSelect={setSelectedId} />
        )}
      </main>

      <Inspector containerId={activeId} />
    </div>
  )
}

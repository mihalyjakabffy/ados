"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { TopBar } from "@/components/TopBar"
import { useBrands } from "@/lib/brand-api"

export default function BrandListPage() {
  const [search, setSearch] = useState("")
  const { data, error, isLoading } = useBrands()

  const brands = useMemo(() => {
    const all = data?.brands ?? []
    if (!search.trim()) return all
    const needle = search.toLowerCase()
    return all.filter((b) => b.name.toLowerCase().includes(needle))
  }, [data, search])

  return (
    <div className="flex h-screen flex-col">
      <TopBar search={search} onSearchChange={setSearch} searchPlaceholder="Keresés a Brand-ek között…" />

      <div className="border-b border-line px-4 py-2">
        <p className="text-[12px] text-mute">Brand · {data ? `${brands.length} identitás` : "…"}</p>
      </div>

      <main className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <p className="text-[12.5px] text-mute">Betöltés…</p>
        ) : error ? (
          <p className="text-[12.5px] text-crit">
            Nem sikerült elérni a Brand API-t (
            {process.env.NEXT_PUBLIC_REVELATION_API_URL ?? "http://localhost:8000"}
            ). Ellenőrizd, hogy fut-e az api.main backend.
          </p>
        ) : brands.length === 0 ? (
          <p className="text-[12.5px] text-mute">Nincs a keresésnek megfelelő brand.</p>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-3">
            {brands.map((b) => (
              <Link
                key={b.brand_id}
                href={`/brand/${b.brand_id}`}
                className="rounded-[10px] border border-line-strong bg-paper-raised p-4 shadow-panel transition-shadow hover:shadow-[0_2px_8px_rgba(0,0,0,.08)]"
              >
                <div
                  className="mb-3 h-16 rounded-[8px] border border-line"
                  style={{
                    backgroundImage:
                      "repeating-linear-gradient(45deg, var(--accent-soft) 0, var(--accent-soft) 1px, transparent 1px, transparent 8px)",
                  }}
                />
                <p className="text-[13px] font-semibold text-ink">{b.name}</p>
                <p className="mt-0.5 font-mono text-[11px] text-mute">v{b.latest_version}</p>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

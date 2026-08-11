"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Search } from "lucide-react"
import type { PackageData } from "@/lib/types"

const SECTIONS = [
  { href: "/", label: "Library" },
  { href: "/brand", label: "Brand" },
  { href: "/rules", label: "System" },
]

export function TopBar({
  pkg,
  search,
  onSearchChange,
  searchPlaceholder = "Keresés",
}: {
  pkg?: PackageData
  search?: string
  onSearchChange?: (value: string) => void
  searchPlaceholder?: string
}) {
  const pathname = usePathname()

  return (
    <header className="flex h-12 flex-shrink-0 items-center gap-4 border-b border-line bg-paper-raised px-4">
      <span className="text-[13px] font-bold tracking-wide text-ink">ADOS</span>

      <nav className="flex items-center gap-1">
        {SECTIONS.map((s) => {
          const active = s.href === "/" ? pathname === "/" : pathname.startsWith(s.href)
          return (
            <Link
              key={s.href}
              href={s.href}
              className={`rounded-[6px] px-2.5 py-[5px] text-[12px] font-medium ${
                active ? "bg-accent-soft text-accent" : "text-mute hover:text-ink"
              }`}
            >
              {s.label}
            </Link>
          )
        })}
      </nav>

      <div className="mx-1 h-4 w-px bg-line-strong" />

      <button className="flex items-center gap-1.5 rounded-[6px] px-2 py-[5px] text-[12px] text-ink-soft hover:bg-black/[.03]">
        {pkg?.project.name ?? "Project"}
        <span className="text-mute">▾</span>
      </button>

      <div className="flex-1" />

      {onSearchChange ? (
        <label className="flex w-64 items-center gap-1.5 rounded-[7px] border border-line-strong px-2.5 py-[5px] text-[12px] text-mute">
          <Search className="h-3.5 w-3.5 flex-shrink-0" strokeWidth={2} />
          <input
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-full bg-transparent text-ink outline-none placeholder:text-mute"
          />
        </label>
      ) : null}
    </header>
  )
}

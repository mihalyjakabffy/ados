"use client"

import { Search } from "lucide-react"

export function Toolbar({
  crumbs,
  search,
  onSearchChange,
  placeholder = "Keresés",
}: {
  crumbs: string[]
  search: string
  onSearchChange: (value: string) => void
  placeholder?: string
}) {
  return (
    <div className="flex items-center gap-3 border-b border-line px-4 py-2.5">
      <div className="flex min-w-0 flex-1 items-center gap-1.5 text-[12.5px] text-mute">
        {crumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-1.5 truncate">
            {i > 0 ? <span className="text-line-strong">›</span> : null}
            <span className={i === crumbs.length - 1 ? "font-semibold text-ink" : "truncate"}>{crumb}</span>
          </span>
        ))}
      </div>
      <label className="flex items-center gap-1.5 rounded-[7px] border border-line-strong px-2.5 py-[5px] text-[12px] text-mute">
        <Search className="h-3.5 w-3.5" strokeWidth={2} />
        <input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={placeholder}
          className="w-40 bg-transparent text-ink outline-none placeholder:text-mute"
        />
      </label>
    </div>
  )
}

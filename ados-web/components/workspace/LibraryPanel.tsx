"use client"

import Link from "next/link"
import { useBrands, useContentExample } from "@/lib/brand-api"
import { useAdosState } from "@/lib/ados-state"

// WHAT EXISTS. A Finder-style semantic browser over real backend data —
// not a second filesystem. "Projects" here is intentionally one real
// entry (the Malthouse content fixture used by the Compose API's dev
// path): a fabricated multi-project list would be mock domain data, and
// the M1.1 objective is a real project -> real Composer -> real PagePlan
// flow, not project-management breadth.
export function LibraryPanel() {
  const { data: brandsData } = useBrands()
  const { data: malthouse } = useContentExample("malthouse")
  const { activeProjectId, activeBrandId, selectProject, selectBrand, setActiveContent } = useAdosState()

  return (
    <aside className="flex h-full flex-col overflow-y-auto bg-sidebar px-2.5 py-3">
      <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Projects</p>
      <div className="mb-5 space-y-0.5">
        {malthouse ? (
          <Row
            active={activeProjectId === "malthouse"}
            label={malthouse.project_name}
            sub={`${malthouse.blocks.length} content blocks`}
            onClick={() => {
              selectProject("malthouse", malthouse.project_name)
              setActiveContent(malthouse)
            }}
          />
        ) : (
          <p className="px-2 py-[6px] text-[12px] text-mute">Betöltés…</p>
        )}
      </div>

      <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">Brands</p>
      <div className="mb-5 space-y-0.5">
        {(brandsData?.brands ?? []).map((b) => (
          <Row
            key={b.brand_id}
            active={activeBrandId === b.brand_id}
            label={b.name}
            sub={`v${b.latest_version}`}
            onClick={() => selectBrand(b.brand_id)}
          />
        ))}
      </div>

      <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">System</p>
      <div className="space-y-0.5">
        <Link
          href="/rules"
          className="block rounded-[7px] px-2 py-[6px] text-[12.5px] text-ink-soft hover:bg-black/[.03]"
        >
          Rule Registry
        </Link>
        <Link
          href="/"
          className="block rounded-[7px] px-2 py-[6px] text-[12.5px] text-ink-soft hover:bg-black/[.03]"
        >
          Document Library
        </Link>
      </div>

      <div className="flex-1" />
      <p className="px-2 pb-1 pt-3 text-[10.5px] text-mute">ADOS Workspace · M1.1</p>
    </aside>
  )
}

function Row({
  active,
  label,
  sub,
  onClick,
}: {
  active: boolean
  label: string
  sub: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full flex-col items-start gap-0 rounded-[7px] px-2 py-[6px] text-left ${
        active ? "bg-accent-soft" : "hover:bg-black/[.03]"
      }`}
    >
      <span className={`truncate text-[12.5px] font-medium ${active ? "text-accent" : "text-ink-soft"}`}>
        {label}
      </span>
      <span className={`truncate text-[10.5px] ${active ? "text-accent/80" : "text-mute"}`}>{sub}</span>
    </button>
  )
}

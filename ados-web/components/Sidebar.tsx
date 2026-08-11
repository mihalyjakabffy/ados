"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import type { PackageData } from "@/lib/types"

function Item({
  href,
  active,
  children,
  count,
}: {
  href: string
  active: boolean
  children: React.ReactNode
  count?: number
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2 rounded-[7px] px-2 py-[6px] text-[12.5px] transition-colors ${
        active ? "bg-accent-soft font-semibold text-accent" : "text-ink-soft hover:bg-black/[.03]"
      }`}
    >
      <span className="flex-1 truncate">{children}</span>
      {count !== undefined ? (
        <span className={`text-[10.5px] ${active ? "text-accent" : "text-mute"}`}>{count}</span>
      ) : null}
    </Link>
  )
}

export function Sidebar({ pkg }: { pkg?: PackageData }) {
  const pathname = usePathname()

  const byType = new Map<string, number>()
  for (const c of pkg?.containers ?? []) {
    byType.set(c.type, (byType.get(c.type) ?? 0) + 1)
  }

  return (
    <aside className="flex h-screen w-[210px] flex-shrink-0 flex-col border-r border-line bg-sidebar">
      <div className="border-b border-line px-4 py-4">
        <div className="text-[13px] font-bold tracking-wide text-ink">ADOS</div>
        <div className="text-[10px] tracking-wide text-mute">Documentation OS</div>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-2.5 py-3">
        <div>
          <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">
            Gyors elérés
          </p>
          <div className="space-y-0.5">
            <Item href="/" active={pathname === "/"}>
              Csomag böngésző
            </Item>
            <Item href="/rules" active={pathname.startsWith("/rules")}>
              Szabálytár
            </Item>
          </div>
        </div>

        {pkg ? (
          <div>
            <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">
              Set — {pkg.set.originator_code}
            </p>
            <div className="space-y-0.5">
              <Item href="/" active={pathname === "/"}>
                {pkg.package_id}
              </Item>
            </div>
          </div>
        ) : null}

        {byType.size > 0 ? (
          <div>
            <p className="mb-1 px-2 text-[9.5px] font-semibold uppercase tracking-[.1em] text-mute">
              Típus szerint
            </p>
            <div className="space-y-0.5">
              {[...byType.entries()].map(([type, count]) => (
                <div
                  key={type}
                  className="flex items-center gap-2 rounded-[7px] px-2 py-[6px] text-[12.5px] text-ink-soft"
                >
                  <span className="flex-1 truncate">{type}</span>
                  <span className="text-[10.5px] text-mute">{count}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </nav>

      <div className="border-t border-line px-3 py-3 text-[10.5px] text-mute">
        ADOS 1.0 · {pkg?.set.conformance_class ? `Class ${pkg.set.conformance_class}` : "reference build"}
      </div>
    </aside>
  )
}

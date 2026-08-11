import type { BrandStatusValue } from "@/lib/brand-types"

const TIER: Record<BrandStatusValue, "ok" | "warn" | "crit"> = {
  published: "ok",
  approved: "ok",
  proposed: "warn",
  draft: "warn",
  superseded: "crit",
  withdrawn: "crit",
}

const CLASSES = {
  ok: "bg-ok-bg text-ok",
  warn: "bg-warn-bg text-warn",
  crit: "bg-crit-bg text-crit",
} as const

export function BrandStatusPill({ status }: { status: BrandStatusValue }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-[3px] text-[11px] font-semibold ${CLASSES[TIER[status]]}`}>
      {status}
    </span>
  )
}

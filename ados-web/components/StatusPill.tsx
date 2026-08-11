import { statusLabel, statusTier } from "@/lib/format"

const TIER_CLASSES = {
  ok: "bg-ok-bg text-ok",
  warn: "bg-warn-bg text-warn",
  crit: "bg-crit-bg text-crit",
} as const

export function StatusPill({ status, revision }: { status: string; revision?: string }) {
  const tier = statusTier(status)
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-[3px] text-[11px] font-semibold whitespace-nowrap ${TIER_CLASSES[tier]}`}
      title={statusLabel(status)}
    >
      {status}
      {revision ? <span className="opacity-70 font-mono">· {revision}</span> : null}
    </span>
  )
}

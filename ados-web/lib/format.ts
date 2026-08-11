export function relativeDate(iso: string | null | undefined): string {
  if (!iso) return "—"
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return iso
  const days = Math.round((Date.now() - then) / 86_400_000)
  if (days === 0) return "today"
  if (days === 1) return "yesterday"
  if (days < 30) return `${days}d ago`
  const months = Math.round(days / 30)
  if (months < 12) return `${months}mo ago`
  return `${Math.round(months / 12)}y ago`
}

// ADOS-2.6.010 status prefixes: S0-S7 (internal→archived), A#/B# (in
// progress), WD (withdrawn). Mapped to a 3-way semantic tier, never colour
// alone — the caller always pairs this with the status text (ADOS-0.3.030).
export function statusTier(status: string): "ok" | "warn" | "crit" {
  if (status.startsWith("S3") || status.startsWith("S4") || status.startsWith("S6") || status.startsWith("S7")) {
    return "ok"
  }
  if (status === "WD") return "crit"
  return "warn"
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    S0: "Work in progress",
    S1: "Shared, not for use",
    S2: "Internal review",
    S3: "Shared for coordination",
    S4: "Shared, approved",
    S6: "Construction issue",
    S7: "As-built / archived",
    WD: "Withdrawn",
  }
  return labels[status] ?? status
}

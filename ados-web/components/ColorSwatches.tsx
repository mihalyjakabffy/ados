import type { FlatTokens } from "@/lib/brand-types"

// Flat colour tokens ("color.brand.primary" -> "#111111") rendered as
// actual swatches — the point of a token is that it resolves to a real
// value, so show the value, not just its name.
export function ColorSwatches({ tokens }: { tokens: FlatTokens }) {
  const colors = Object.entries(tokens).filter(
    ([k, v]) => k.startsWith("color.") && typeof v === "string" && v.startsWith("#"),
  ) as [string, string][]

  if (colors.length === 0) return null

  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(96px,1fr))] gap-2.5">
      {colors.map(([key, hex]) => (
        <div key={key} className="overflow-hidden rounded-[8px] border border-line-strong">
          <div className="h-12" style={{ backgroundColor: hex }} />
          <div className="bg-paper-raised px-2 py-1.5">
            <p className="truncate text-[10.5px] font-medium text-ink-soft">{key.replace("color.", "")}</p>
            <p className="font-mono text-[10px] text-mute">{hex}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

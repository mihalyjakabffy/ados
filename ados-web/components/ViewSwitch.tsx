"use client"

export type ViewMode = "list" | "columns"

export function ViewSwitch({ mode, onChange }: { mode: ViewMode; onChange: (mode: ViewMode) => void }) {
  return (
    <div className="flex overflow-hidden rounded-[7px] border border-line-strong text-[11.5px]">
      {(["list", "columns"] as const).map((m) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          className={`px-2.5 py-1 ${
            mode === m ? "bg-accent-soft font-semibold text-accent" : "text-mute hover:bg-black/[.03]"
          }`}
        >
          {m === "list" ? "Lista" : "Oszlopok"}
        </button>
      ))}
    </div>
  )
}

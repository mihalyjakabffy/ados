const CLASSES: Record<string, string> = {
  shall: "bg-crit-bg text-crit",
  should: "bg-warn-bg text-warn",
  may: "bg-ok-bg text-ok",
}

export function RuleLevelPill({ level }: { level: string }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-[3px] text-[11px] font-semibold ${CLASSES[level] ?? "bg-accent-soft text-accent"}`}>
      {level}
    </span>
  )
}

// ADOS-5.0.010 closed container type registry, grouped for the icon colour —
// grouping follows what the type *is for*, matching a Finder file-kind badge,
// not an arbitrary palette. Colour is always paired with the 2-letter code
// (text), never the sole carrier (ADOS-0.3.030 / ADOS-0.4.070).
const GROUPS: Record<string, { label: string; className: string }> = {
  // location drawings
  "GA-P": g("#5C7DA8"), SO: g("#5C7DA8"), EX: g("#5C7DA8"), DM: g("#5C7DA8"),
  PH: g("#5C7DA8"), SL: g("#5C7DA8"), SP: g("#5C7DA8"), FS: g("#5C7DA8"),
  AS: g("#5C7DA8"), RP: g("#5C7DA8"), RCP: g("#5C7DA8"), EL: g("#5C7DA8"),
  SE: g("#5C7DA8"), EN: g("#5C7DA8"), IE: g("#5C7DA8"),
  // assemblies / details
  WT: g("#8A7550"), DT: g("#8A7550"),
  // schedules
  TS: g("#6E7A5B"), RS: g("#6E7A5B"), DS: g("#6E7A5B"), WS: g("#6E7A5B"), AR: g("#6E7A5B"),
  // documents / records
  "SP-SPEC": g("#7B6C9B"), TP: g("#7B6C9B"), RFI: g("#7B6C9B"), CO: g("#7B6C9B"),
  DD: g("#7B6C9B"), PR: g("#7B6C9B"), MM: g("#7B6C9B"), DR: g("#7B6C9B"),
  SR: g("#7B6C9B"), CI: g("#7B6C9B"), AB: g("#7B6C9B"), OM: g("#7B6C9B"),
  // front matter
  CS: g("#87837A"), IX: g("#87837A"), GN: g("#87837A"),
}

function g(hex: string) {
  return { label: hex, className: "" }
}

export function TypeIcon({ type }: { type: string }) {
  const hex = GROUPS[type]?.label ?? "#87837A"
  return (
    <span
      className="flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center rounded-[7px] text-[9.5px] font-bold text-white"
      style={{ backgroundColor: hex }}
    >
      {type.replace("-SPEC", "").slice(0, 2)}
    </span>
  )
}

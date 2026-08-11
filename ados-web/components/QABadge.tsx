import type { QASummary } from "@/lib/types"

// The QA state as a glance-able badge — meant to appear wherever a
// Container is listed (List row, Column entry, Inspector), not only on a
// separate dashboard. A single fail token still shows both colour and
// text, never colour alone (ADOS-0.3.030 / ADOS-0.4.070).
export function QABadge({ qa }: { qa: QASummary }) {
  const allPass = qa.fail === 0
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-1.5 py-[2px] text-[10.5px] font-semibold ${
        allPass ? "bg-ok-bg text-ok" : "bg-warn-bg text-warn"
      }`}
      title={allPass ? `QA: ${qa.pass}/${qa.pass} passed` : `QA: ${qa.fail} check(s) failed`}
    >
      {allPass ? "✓" : "⚠"} {qa.pass}/{qa.pass + qa.fail}
    </span>
  )
}

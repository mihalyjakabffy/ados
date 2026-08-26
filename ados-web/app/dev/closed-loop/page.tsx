"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/TopBar"

const REVELATION_API_URL = process.env.NEXT_PUBLIC_REVELATION_API_URL ?? "http://localhost:8000"

const PIPELINE_STAGES = [
  "planning", "design_ready", "commands_generated", "commands_validated",
  "executing", "composed", "evaluating", "findings_available", "recommendations_available",
]

interface FindingRecord {
  fingerprint: string
  finding: { severity: string; code: string; field: string; message: string }
  status: string
}

interface Recommendation {
  id: string
  action: string
  rationale: string
  confidence: number
  source: string
  patch: { target: string; value: string; rationale: string }
}

interface SkippedRecommendation {
  reason: string
  detail: string
}

interface GeneratedCommand {
  id: string
  intent: { type: string; parameters: Record<string, unknown> }
  safety_level: string
  rationale: string
}

interface IterationMetrics {
  total_findings: number
  error_findings: number
  warning_findings: number
  resolved_findings: number
  unresolved_findings: number
  new_findings: number
  regression_findings: number
  command_count: number
}

interface Iteration {
  id: string
  sequence: number
  trigger: string
  status: string
  stop_reason: string | null
  stage_log: string[]
  input_design_state_version: number | null
  output_design_state_version: number | null
  design_intent_fingerprint: string
  command_plan: { commands: GeneratedCommand[] }
  findings: FindingRecord[]
  recommendations: Recommendation[]
  skipped_recommendations: SkippedRecommendation[]
  metrics: IterationMetrics
  llm_calls: number
  dry_run: boolean
}

const STATUS_COLOR: Record<string, string> = {
  completed: "text-mute",
  awaiting_approval: "text-warn",
  blocked: "text-warn",
  failed: "text-crit",
  stopped: "text-mute",
}

// ADOS-M3.6 — the developer-facing view of the closed loop:
//   DesignIntent -> Commands -> Execute -> Compose -> Evaluate -> Finding
//   -> Recommendation -> DesignIntent patch -> repeat
// The LLM never controls this loop; every transition below is a plain,
// deterministic decision made by brand.llm.loop.orchestrator.
export default function DevClosedLoopPage() {
  const [projectId, setProjectId] = useState("")
  const [documentId, setDocumentId] = useState("")
  const [documentTypeId, setDocumentTypeId] = useState("portfolio")
  const [rawText, setRawText] = useState(
    "Residential development in Budapest. 84 apartments. GFA of 13,100 m². The project creates a strong connection to the landscape."
  )
  const [autonomy, setAutonomy] = useState("safe")
  const [maxIterations, setMaxIterations] = useState(5)

  const [iterations, setIterations] = useState<Iteration[]>([])
  const [selected, setSelected] = useState<Iteration | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const base = `${REVELATION_API_URL}/api/v2/ados-projects/${encodeURIComponent(projectId)}/documents/${encodeURIComponent(documentId)}/loop`

  function policyBody() {
    return { policy: { autonomy, max_iterations: maxIterations } }
  }

  function startBody() {
    return {
      ...policyBody(),
      semantic_intent: { explicit: { audience: "prospective_client" } },
      document_type_id: documentTypeId,
      raw_documents: rawText.trim() ? [{ source_id: "dev-source", text: rawText }] : [],
    }
  }

  async function refreshHistory() {
    try {
      const res = await fetch(`${base}`)
      if (res.ok) {
        const data = await res.json()
        setIterations(data.iterations)
        if (data.iterations.length) setSelected(data.iterations[data.iterations.length - 1])
      }
    } catch {
      // dev-only convenience
    }
  }

  async function call(path: string, body: unknown) {
    if (!projectId.trim() || !documentId.trim()) {
      setError("A project id and document id are required.")
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await fetch(`${base}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(`${res.status} ${JSON.stringify(data.detail)}`)
        return
      }
      await refreshHistory()
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (projectId && documentId) refreshHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const last = iterations[iterations.length - 1]
  const canApprove = last && last.status === "awaiting_approval"
  const canContinue = last && last.stop_reason === null

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      <div className="border-b border-line bg-warn-bg px-4 py-2 text-[12px] font-medium text-warn">
        DEV — ADOS-M3.6 Closed Loop. The LLM never controls this loop — every
        transition is a deterministic decision in brand.llm.loop.orchestrator.
      </div>

      <main className="flex-1 overflow-auto p-4">
        <div className="mb-4 flex flex-col gap-3 text-[12.5px]">
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Project id</span>
              <input
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="required"
                className="w-64 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Document id</span>
              <input
                value={documentId}
                onChange={(e) => setDocumentId(e.target.value)}
                placeholder="required"
                className="w-64 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Autonomy</span>
              <select
                value={autonomy}
                onChange={(e) => setAutonomy(e.target.value)}
                className="w-36 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              >
                <option value="none">none</option>
                <option value="recommend">recommend</option>
                <option value="safe">safe</option>
                <option value="full">full</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Max iterations</span>
              <input
                type="number"
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value) || 5)}
                className="w-20 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
          </div>

          <label className="flex flex-col gap-1">
            <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">
              Simulated source text (first iteration only)
            </span>
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={2}
              className="rounded-[7px] border border-line-strong bg-paper-raised px-2.5 py-[6px] font-mono text-[12px]"
            />
          </label>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => call("/start", startBody())}
              disabled={busy || iterations.length > 0}
              className="w-fit rounded-[7px] bg-accent px-3 py-[6px] font-medium text-white disabled:opacity-40"
            >
              Start
            </button>
            <button
              onClick={() => call("/continue", policyBody())}
              disabled={busy || !canContinue}
              className="w-fit rounded-[7px] border border-line-strong bg-paper-raised px-3 py-[6px] font-medium disabled:opacity-40"
            >
              Continue
            </button>
            <button
              onClick={() => call("/run", startBody())}
              disabled={busy || iterations.length > 0}
              className="w-fit rounded-[7px] border border-line-strong bg-paper-raised px-3 py-[6px] font-medium disabled:opacity-40"
            >
              Run full loop
            </button>
            <button
              onClick={() => call("/approve", {})}
              disabled={busy || !canApprove}
              className="w-fit rounded-[7px] border border-line-strong bg-paper-raised px-3 py-[6px] font-medium disabled:opacity-40"
            >
              Approve pending commands
            </button>
            <button
              onClick={() => call("/stop", {})}
              disabled={busy || iterations.length === 0}
              className="w-fit rounded-[7px] border border-line-strong bg-paper-raised px-3 py-[6px] font-medium disabled:opacity-40"
            >
              Stop
            </button>
          </div>
        </div>

        {error ? <p className="mb-3 text-[12.5px] text-crit">{error}</p> : null}

        {iterations.length > 0 ? (
          <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
            <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
              Iteration timeline
            </p>
            <div className="flex flex-wrap gap-2">
              {iterations.map((it) => (
                <button
                  key={it.id}
                  onClick={() => setSelected(it)}
                  className={`rounded-[7px] border px-2.5 py-1 text-[11.5px] ${
                    selected?.id === it.id ? "border-accent" : "border-line-strong"
                  }`}
                >
                  #{it.sequence} <span className={STATUS_COLOR[it.status] ?? ""}>{it.status}</span>
                  {it.stop_reason ? ` · ${it.stop_reason}` : ""}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <p className="mb-4 text-[12.5px] text-mute">
            Enter a project id (with a brand attached) and a document id, then Start or Run full loop.
          </p>
        )}

        {selected ? (
          <>
            <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
              <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                Iteration #{selected.sequence} pipeline
              </p>
              <div className="flex flex-wrap items-center gap-1 text-[11px]">
                {PIPELINE_STAGES.map((stage, i) => (
                  <span key={stage} className="flex items-center gap-1">
                    <span
                      className={
                        selected.stage_log.includes(stage)
                          ? "rounded-full bg-accent px-2 py-0.5 text-white"
                          : "rounded-full border border-line-strong px-2 py-0.5 text-mute"
                      }
                    >
                      {stage}
                    </span>
                    {i < PIPELINE_STAGES.length - 1 ? <span className="text-mute">→</span> : null}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-[11px] text-mute">
                version {selected.input_design_state_version ?? "—"} → {selected.output_design_state_version ?? "—"}
                {selected.dry_run ? " · DRY RUN (not persisted)" : ""} · llm_calls={selected.llm_calls}
              </p>
            </div>

            <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
              <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                  Commands ({selected.command_plan.commands?.length ?? 0})
                </p>
                {(selected.command_plan.commands ?? []).map((c) => (
                  <div key={c.id} className="mb-1 border-b border-line pb-1 last:border-0">
                    <p className="text-[12px] text-ink-soft">
                      <span className="font-mono font-medium">{c.intent.type}</span>{" "}
                      <span className="text-mute">[{c.safety_level}]</span>
                    </p>
                    <p className="text-[11px] text-mute">{c.rationale}</p>
                  </div>
                ))}
                {(selected.command_plan.commands ?? []).length === 0 && (
                  <p className="text-[12px] text-mute">No commands — nothing needed to change.</p>
                )}
              </div>

              <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                  Metrics
                </p>
                <p className="text-[12px] text-ink-soft">
                  total={selected.metrics.total_findings} · error={selected.metrics.error_findings} · warn=
                  {selected.metrics.warning_findings}
                </p>
                <p className="text-[12px] text-ink-soft">
                  resolved={selected.metrics.resolved_findings} · unresolved={selected.metrics.unresolved_findings} ·
                  new={selected.metrics.new_findings} · regressed={selected.metrics.regression_findings}
                </p>
              </div>
            </div>

            <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
              <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                Findings ({selected.findings.length})
              </p>
              {selected.findings.map((r) => (
                <p key={r.fingerprint} className="text-[12px] text-ink-soft">
                  <span className="font-mono text-[10.5px] text-mute">{r.finding.code || "(uncoded)"}</span>{" "}
                  <span className="font-medium">{r.finding.severity}</span> · {r.status}: {r.finding.message}
                </p>
              ))}
              {selected.findings.length === 0 && <p className="text-[12px] text-mute">None.</p>}
            </div>

            <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
              <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                  Recommendation
                </p>
                {selected.recommendations.length === 0 ? (
                  <p className="text-[12px] text-mute">None selected this iteration.</p>
                ) : (
                  selected.recommendations.map((r) => (
                    <p key={r.id} className="text-[12px] text-ink-soft">
                      {r.patch.target} = <span className="font-mono">{r.patch.value}</span> ({r.source}, confidence{" "}
                      {r.confidence}) — {r.rationale}
                    </p>
                  ))
                )}
              </div>
              <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                  Skipped recommendations
                </p>
                {selected.skipped_recommendations.length === 0 ? (
                  <p className="text-[12px] text-mute">None.</p>
                ) : (
                  selected.skipped_recommendations.map((s, i) => (
                    <p key={i} className="text-[12px] text-mute">
                      {s.reason}: {s.detail}
                    </p>
                  ))
                )}
              </div>
            </div>

            <pre className="mb-4 overflow-auto rounded-[10px] border border-line-strong bg-paper-raised p-3 text-[11px] leading-relaxed text-ink-soft">
              {JSON.stringify(selected, null, 2)}
            </pre>
          </>
        ) : null}
      </main>
    </div>
  )
}

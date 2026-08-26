"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/TopBar"

const REVELATION_API_URL = process.env.NEXT_PUBLIC_REVELATION_API_URL ?? "http://localhost:8000"

const DEFAULT_CONTENT_MODEL = `{
  "project_id": "00000000-0000-4000-8000-000000000000",
  "project_name": "Riverside",
  "blocks": [
    { "id": "txt-01", "type": "narrative", "role": "context", "priority": 1,
      "text": "A residential development of 84 apartments on the riverside, with a strong connection to the landscape." }
  ]
}`

interface CommandIntent {
  type: string
  target: { type: string; id: string }
  parameters: Record<string, unknown>
  source: string
}

interface GeneratedCommand {
  id: string
  intent: CommandIntent
  safety_level: string
  provenance: string
  source_field: string
  rationale: string
  idempotent: boolean
}

interface SkippedLever {
  source_field: string
  reason: string
  detail: string
}

interface CommandPlan {
  id: string
  project_id: string
  design_state_version: number | null
  commands: GeneratedCommand[]
  skipped: SkippedLever[]
  metadata: Record<string, unknown>
}

interface ValidationFinding {
  code: string
  severity: string
  field: string
  message: string
}

interface Validation {
  ok: boolean
  findings: ValidationFinding[]
}

interface GenerateResult {
  command_plan: CommandPlan
  command_validation: Validation
  request_id: string
}

interface ApplyResult {
  steps: { command_id: string; direction_changed: boolean; content_changed: boolean; notes: string[] }[]
  final_plan: { pages: unknown[] } | null
  final_direction_id: string
}

interface Trace {
  request_id: string
  project_id: string
  generator: string
  command_count: number
  skipped_count: number
  latency_ms: number
}

const SAFETY_COLOR: Record<string, string> = {
  safe: "text-mute",
  review_recommended: "text-warn",
  destructive: "text-crit",
}

// ADOS-M3.5 — the developer-facing way to inspect
//   DesignIntent -> brand.llm.command.planning.plan_commands -> CommandPlan
//   -> brand.llm.command.validation.validate_command_plan
// Generation never composes. "Apply" below is the one action on this page
// that calls the real, existing apply_intent()/compose() — a second,
// separate step, exactly like the API router's own generate/apply split.
export default function DevCommandGenerationPage() {
  const [projectId, setProjectId] = useState("")
  const [documentId, setDocumentId] = useState("")
  const [documentTypeId, setDocumentTypeId] = useState("portfolio")
  const [rawText, setRawText] = useState(
    "Residential development in Budapest. 84 apartments. GFA of 13,100 m². The project creates a strong connection to the landscape."
  )
  const [contentModelText, setContentModelText] = useState(DEFAULT_CONTENT_MODEL)
  const [baseDirectionId, setBaseDirectionId] = useState("editorial-quiet")

  const [result, setResult] = useState<GenerateResult | null>(null)
  const [applyResult, setApplyResult] = useState<ApplyResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [traces, setTraces] = useState<Trace[]>([])

  async function loadTraces() {
    try {
      const res = await fetch(`${REVELATION_API_URL}/api/v2/ados-projects/commands/traces?limit=20`)
      if (res.ok) setTraces((await res.json()).traces)
    } catch {
      // dev-only convenience
    }
  }

  useEffect(() => {
    loadTraces()
  }, [])

  function parsedContentModel(): unknown {
    return JSON.parse(contentModelText)
  }

  async function generate() {
    if (!projectId.trim()) {
      setError("A project id is required — create one in /projects first.")
      return
    }
    setBusy(true)
    setError(null)
    setResult(null)
    setApplyResult(null)
    try {
      let contentModel: unknown
      try {
        contentModel = parsedContentModel()
      } catch (e) {
        setError(`content_model is not valid JSON: ${String(e)}`)
        return
      }
      const res = await fetch(
        `${REVELATION_API_URL}/api/v2/ados-projects/${encodeURIComponent(projectId)}/commands/generate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            semantic_intent: { explicit: { audience: "prospective_client" } },
            document_id: documentId || undefined,
            document_type_id: documentTypeId || undefined,
            content_model: contentModel,
            raw_documents: rawText.trim() ? [{ source_id: "dev-source", text: rawText }] : [],
          }),
        }
      )
      const data = await res.json()
      if (!res.ok) {
        setError(`${res.status} ${JSON.stringify(data.detail)}`)
        return
      }
      setResult(data)
      await loadTraces()
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  async function apply() {
    if (!result) return
    setBusy(true)
    setError(null)
    setApplyResult(null)
    try {
      const res = await fetch(
        `${REVELATION_API_URL}/api/v2/ados-projects/${encodeURIComponent(projectId)}/commands/apply`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            command_plan: result.command_plan,
            content_model: parsedContentModel(),
            base_direction_id: baseDirectionId,
          }),
        }
      )
      const data = await res.json()
      if (!res.ok) {
        setError(`${res.status} ${JSON.stringify(data.detail)}`)
        return
      }
      setApplyResult(data)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      <div className="border-b border-line bg-warn-bg px-4 py-2 text-[12px] font-medium text-warn">
        DEV — ADOS-M3.5 Command Generation. A compiler, not an agent: every command below is one of the
        eight existing, already-validated CommandIntent types — nothing new, nothing geometric.
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
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Document id (optional)</span>
              <input
                value={documentId}
                onChange={(e) => setDocumentId(e.target.value)}
                className="w-56 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Document type</span>
              <input
                value={documentTypeId}
                onChange={(e) => setDocumentTypeId(e.target.value)}
                className="w-40 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">
                Base direction id (for Apply)
              </span>
              <input
                value={baseDirectionId}
                onChange={(e) => setBaseDirectionId(e.target.value)}
                className="w-44 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
          </div>

          <label className="flex flex-col gap-1">
            <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">
              Simulated source text (feeds M3.2 → M3.3 → M3.4)
            </span>
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={2}
              className="rounded-[7px] border border-line-strong bg-paper-raised px-2.5 py-[6px] font-mono text-[12px]"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">
              content_model (brand.content.model.ContentModel — no store exists yet, so this is supplied inline)
            </span>
            <textarea
              value={contentModelText}
              onChange={(e) => setContentModelText(e.target.value)}
              rows={6}
              className="rounded-[7px] border border-line-strong bg-paper-raised px-2.5 py-[6px] font-mono text-[11.5px]"
            />
          </label>

          <div className="flex gap-2">
            <button
              onClick={generate}
              disabled={busy}
              className="w-fit rounded-[7px] bg-accent px-3 py-[6px] font-medium text-white disabled:opacity-40"
            >
              {busy ? "Compiling…" : "POST /commands/generate"}
            </button>
            <button
              onClick={apply}
              disabled={busy || !result || result.command_plan.commands.length === 0}
              className="w-fit rounded-[7px] border border-line-strong bg-paper-raised px-3 py-[6px] font-medium disabled:opacity-40"
            >
              POST /commands/apply
            </button>
          </div>
        </div>

        {error ? <p className="mb-3 text-[12.5px] text-crit">{error}</p> : null}

        {result ? (
          <>
            <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
              <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                Command plan — {result.command_plan.commands.length} command(s),{" "}
                {result.command_plan.skipped.length} lever(s) considered and not acted on
              </p>
              <p className="mb-2 text-[11px] text-mute">
                generator: {String(result.command_plan.metadata.generator)} · design_state_version:{" "}
                {result.command_plan.design_state_version ?? "(none)"}
              </p>
              {result.command_plan.commands.length === 0 ? (
                <p className="text-[12px] text-mute">No commands — the current state already reflects this DesignIntent.</p>
              ) : (
                result.command_plan.commands.map((c) => (
                  <div key={c.id} className="mb-2 border-b border-line pb-2 last:border-0">
                    <p className="text-[12px] text-ink-soft">
                      <span className="font-mono font-medium">{c.intent.type}</span>{" "}
                      <span className={`font-medium ${SAFETY_COLOR[c.safety_level] ?? "text-mute"}`}>
                        [{c.safety_level}]
                      </span>{" "}
                      target={c.intent.target.type}
                      {c.intent.target.id ? `:${c.intent.target.id}` : ""} · params=
                      {JSON.stringify(c.intent.parameters)}
                    </p>
                    <p className="text-[11.5px] text-mute">
                      from {c.source_field} · provenance={c.provenance} · idempotent={String(c.idempotent)}
                    </p>
                    <p className="text-[11.5px] italic text-ink-soft">{c.rationale}</p>
                  </div>
                ))
              )}
            </div>

            <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
              <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                Skipped levers
              </p>
              {result.command_plan.skipped.length === 0 ? (
                <p className="text-[12px] text-mute">None — every lever this DesignIntent named was acted on.</p>
              ) : (
                result.command_plan.skipped.map((s, i) => (
                  <p key={i} className="text-[12px] text-ink-soft">
                    <span className="font-mono text-[10.5px] text-mute">{s.source_field}</span>{" "}
                    <span className="font-medium">{s.reason}</span>
                    {s.detail ? ` — ${s.detail}` : ""}
                  </p>
                ))
              )}
            </div>

            <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
              <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                Validation — {result.command_validation.ok ? "ok" : "has findings"}
              </p>
              {result.command_validation.findings.length === 0 ? (
                <p className="text-[12px] text-mute">No findings.</p>
              ) : (
                result.command_validation.findings.map((f, i) => (
                  <p key={i} className="text-[12px] text-ink-soft">
                    <span className="font-mono text-[10.5px] text-mute">{f.code}</span>{" "}
                    <span className="font-medium">{f.severity}</span> {f.field}: {f.message}
                  </p>
                ))
              )}
            </div>

            {applyResult ? (
              <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                  Apply result — {applyResult.steps.length} step(s) executed
                </p>
                {applyResult.steps.map((s, i) => (
                  <p key={i} className="text-[12px] text-ink-soft">
                    step {i + 1}: direction_changed={String(s.direction_changed)}, content_changed=
                    {String(s.content_changed)}
                    {s.notes.length ? ` — ${s.notes.join("; ")}` : ""}
                  </p>
                ))}
                <p className="mt-1 text-[12px] text-mute">
                  final direction: <span className="font-mono">{applyResult.final_direction_id}</span> · final
                  page count: {applyResult.final_plan ? applyResult.final_plan.pages.length : "—"}
                </p>
              </div>
            ) : null}

            <pre className="mb-4 overflow-auto rounded-[10px] border border-line-strong bg-paper-raised p-3 text-[11px] leading-relaxed text-ink-soft">
              {JSON.stringify(result, null, 2)}
            </pre>
          </>
        ) : (
          <p className="mb-4 text-[12.5px] text-mute">
            Enter a project id and POST /commands/generate. This resolves content → narrative → design intent
            exactly as /dev/design-intent does, then compiles the result into a CommandPlan — a small,
            provenanced set of the same eight CommandIntent types the M1.2 command panel already executes.
          </p>
        )}

        <div>
          <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
            Recent compilations (this process, in memory)
          </p>
          {traces.length === 0 ? (
            <p className="text-[12px] text-mute">None yet.</p>
          ) : (
            <div className="space-y-0.5">
              {traces.map((t) => (
                <div key={t.request_id} className="flex items-center gap-2 text-[11.5px]">
                  <span className="text-ink-soft">{t.command_count} cmd</span>
                  <span className="text-mute">{t.skipped_count} skipped</span>
                  <span className="truncate text-ink-soft">{t.project_id}</span>
                  <span className="text-mute">{t.generator}</span>
                  <span className="ml-auto flex-shrink-0 text-mute">{t.latency_ms.toFixed(0)}ms</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

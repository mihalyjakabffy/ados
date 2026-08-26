"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/TopBar"

const REVELATION_API_URL = process.env.NEXT_PUBLIC_REVELATION_API_URL ?? "http://localhost:8000"

interface SemanticIntentResult {
  intent: {
    explicit: Record<string, unknown>
    inferred: Record<string, unknown>
    ambiguous: string[]
    ambiguity_notes: Record<string, string>
    confidence: number
  }
  validation: {
    ok: boolean
    counts: Record<string, number>
    findings: { code: string; severity: string; field: string; message: string; suggestion: string }[]
  }
  request_id: string
  provider: string
  model: string
}

interface Trace {
  request_id: string
  provider: string
  model: string
  request_preview: string
  latency_ms: number
  created_at: string
  validation: { ok: boolean }
}

// ADOS-M3.1 §20 — the developer-facing way to inspect
//   User request -> SemanticIntent -> Validation
// before M3.2 exists to do anything with it. Raw JSON is the point here
// too (see /dev/compose's own docstring) — this is not a conversational
// UI, and it never executes anything: POST /intent/semantic never
// reaches CommandIntent or the Composer.
export default function DevSemanticIntentPage() {
  const [request, setRequest] = useState(
    "Create a portfolio about the Riverside project. Make it feel like our existing studio materials but more premium."
  )
  const [projectId, setProjectId] = useState("")
  const [documentId, setDocumentId] = useState("")
  const [result, setResult] = useState<SemanticIntentResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [traces, setTraces] = useState<Trace[]>([])

  async function loadTraces() {
    try {
      const res = await fetch(`${REVELATION_API_URL}/api/v2/intent/semantic/traces?limit=20`)
      if (res.ok) setTraces((await res.json()).traces)
    } catch {
      // dev-only convenience — a failed refresh isn't worth surfacing
    }
  }

  useEffect(() => {
    loadTraces()
  }, [])

  async function submit() {
    if (!request.trim()) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(`${REVELATION_API_URL}/api/v2/intent/semantic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request,
          project_id: projectId || undefined,
          document_id: documentId || undefined,
        }),
      })
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

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      <div className="border-b border-line bg-warn-bg px-4 py-2 text-[12px] font-medium text-warn">
        DEV — ADOS-M3.1 Semantic Intent inspection. Nothing here executes a command.
      </div>

      <main className="flex-1 overflow-auto p-4">
        <div className="mb-4 flex flex-col gap-3 text-[12.5px]">
          <label className="flex flex-col gap-1">
            <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">User request</span>
            <textarea
              value={request}
              onChange={(e) => setRequest(e.target.value)}
              rows={3}
              className="rounded-[7px] border border-line-strong bg-paper-raised px-2.5 py-[6px] font-mono text-[12px]"
            />
          </label>

          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Project id (optional)</span>
              <input
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="real context, or leave blank"
                className="w-64 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Document id (optional)</span>
              <input
                value={documentId}
                onChange={(e) => setDocumentId(e.target.value)}
                placeholder="needs project id too"
                className="w-64 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
            <button
              onClick={submit}
              disabled={!request.trim() || busy}
              className="rounded-[7px] bg-accent px-3 py-[6px] font-medium text-white disabled:opacity-40"
            >
              {busy ? "Interpreting…" : "POST /intent/semantic"}
            </button>
          </div>
        </div>

        {error ? <p className="mb-3 text-[12.5px] text-crit">{error}</p> : null}

        {result ? (
          <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
            <FieldBucket title="Explicit" fields={result.intent.explicit} />
            <FieldBucket title="Inferred" fields={result.intent.inferred} />
          </div>
        ) : null}

        {result && result.intent.ambiguous.length > 0 ? (
          <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
            <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">Ambiguous</p>
            {result.intent.ambiguous.map((field) => (
              <p key={field} className="text-[12px] text-ink-soft">
                <span className="font-mono font-medium">{field}</span>
                {result.intent.ambiguity_notes[field] ? ` — ${result.intent.ambiguity_notes[field]}` : ""}
              </p>
            ))}
          </div>
        ) : null}

        {result ? (
          <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
            <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
              Validation — {result.validation.ok ? "ok" : "has findings"} · confidence{" "}
              {result.intent.confidence.toFixed(2)} · {result.provider}/{result.model}
            </p>
            {result.validation.findings.length === 0 ? (
              <p className="text-[12px] text-mute">No findings.</p>
            ) : (
              result.validation.findings.map((f, i) => (
                <p key={i} className="text-[12px] text-ink-soft">
                  <span className="font-mono text-[10.5px] text-mute">{f.code}</span>{" "}
                  <span className="font-medium">{f.severity}</span> {f.field}: {f.message}
                </p>
              ))
            )}
          </div>
        ) : null}

        {result ? (
          <pre className="mb-4 overflow-auto rounded-[10px] border border-line-strong bg-paper-raised p-3 text-[11px] leading-relaxed text-ink-soft">
            {JSON.stringify(result, null, 2)}
          </pre>
        ) : (
          <p className="mb-4 text-[12.5px] text-mute">
            Enter a request and POST /intent/semantic. Add a project id (and document id, for an
            open document's design state) to see how the same request resolves differently with
            real context available.
          </p>
        )}

        <div>
          <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
            Recent traces (this process, in memory)
          </p>
          {traces.length === 0 ? (
            <p className="text-[12px] text-mute">None yet.</p>
          ) : (
            <div className="space-y-0.5">
              {traces.map((t) => (
                <div key={t.request_id} className="flex items-center gap-2 text-[11.5px]">
                  <span className={t.validation.ok ? "text-mute" : "text-crit"}>
                    {t.validation.ok ? "ok" : "findings"}
                  </span>
                  <span className="font-mono text-[10.5px] text-mute">{t.provider}</span>
                  <span className="truncate text-ink-soft">{t.request_preview}</span>
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

function FieldBucket({ title, fields }: { title: string; fields: Record<string, unknown> }) {
  const set = Object.entries(fields).filter(([, v]) => v !== null && v !== "" && !(Array.isArray(v) && v.length === 0))
  return (
    <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
      <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">{title}</p>
      {set.length === 0 ? (
        <p className="text-[12px] text-mute">Nothing in this bucket.</p>
      ) : (
        set.map(([key, value]) => (
          <p key={key} className="text-[12px] text-ink-soft">
            <span className="font-mono font-medium">{key}</span>:{" "}
            {Array.isArray(value) ? value.join("; ") : String(value)}
          </p>
        ))
      )}
    </div>
  )
}

"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/TopBar"

const REVELATION_API_URL = process.env.NEXT_PUBLIC_REVELATION_API_URL ?? "http://localhost:8000"

interface SourceRef {
  source_id: string
  source_type: string
  page: number | null
  section: string
  extraction_method: string
}

interface Fact {
  id: string
  key: string
  value: unknown
  unit: string
  status: string
  confidence: number
  source_refs: SourceRef[]
  conflicting_values: { value: unknown; unit: string; source_refs: SourceRef[] }[]
  superseded_by: string | null
}

interface Claim {
  id: string
  text: string
  status: string
  confidence: number
  source_refs: SourceRef[]
  related_entity_ids: string[]
}

interface Entity {
  id: string
  type: string
  name: string
  aliases: string[]
  status: string
  source_refs: SourceRef[]
}

interface Relationship {
  id: string
  subject_entity_id: string
  predicate: string
  object_entity_id: string
  status: string
  source_refs: SourceRef[]
}

interface AssetContentItem {
  asset_id: string
  type: string
  caption: string
  description: string
  source_refs: SourceRef[]
}

interface MissingInfo {
  key: string
  required_for: string
  reason: string
}

interface ContentIntelligenceModel {
  project_id: string
  entities: Entity[]
  facts: Fact[]
  claims: Claim[]
  relationships: Relationship[]
  assets: AssetContentItem[]
  missing_information: MissingInfo[]
  sources: SourceRef[]
}

interface ResolveResult {
  content: ContentIntelligenceModel
  validation: {
    ok: boolean
    findings: { code: string; severity: string; field: string; message: string }[]
  }
  request_id: string
}

interface Trace {
  request_id: string
  project_id: string
  source_extractors: Record<string, string>
  status_counts: Record<string, number>
  validation_ok: boolean
  latency_ms: number
}

// ADOS-M3.2 §26 — the developer-facing way to inspect
//   Sources -> Entities/Facts/Claims/Metrics/Assets/Relationships/Missing/Conflicts -> Provenance
// before M3.3 exists to decide what to say with any of it. Raw JSON is
// included for the same reason /dev/semantic-intent's is: it is the API
// contract, not a polished product surface.
export default function DevContentIntelligencePage() {
  const [projectId, setProjectId] = useState("")
  const [documentId, setDocumentId] = useState("")
  const [documentTypeId, setDocumentTypeId] = useState("")
  const [rawText, setRawText] = useState(
    "Residential development in Budapest. 84 apartments. GFA of 13,100 m². The project creates a strong connection to the landscape."
  )
  const [result, setResult] = useState<ResolveResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [traces, setTraces] = useState<Trace[]>([])

  async function loadTraces() {
    try {
      const res = await fetch(`${REVELATION_API_URL}/api/v2/ados-projects/content/traces?limit=20`)
      if (res.ok) setTraces((await res.json()).traces)
    } catch {
      // dev-only convenience
    }
  }

  useEffect(() => {
    loadTraces()
  }, [])

  async function submit() {
    if (!projectId.trim()) {
      setError("A project id is required — create one in /projects first.")
      return
    }
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(
        `${REVELATION_API_URL}/api/v2/ados-projects/${encodeURIComponent(projectId)}/content/resolve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            document_id: documentId || undefined,
            document_type_id: documentTypeId || undefined,
            raw_documents: rawText.trim()
              ? [{ source_id: "dev-source", text: rawText }]
              : [],
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

  const metrics = result?.content.facts.filter((f) => typeof f.value === "number") ?? []
  const conflicts = result?.content.facts.filter((f) => f.status === "conflicting") ?? []

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      <div className="border-b border-line bg-warn-bg px-4 py-2 text-[12px] font-medium text-warn">
        DEV — ADOS-M3.2 Content Intelligence inspection. Nothing here executes a command or produces a narrative.
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
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Document type (for missing-info)</span>
              <input
                value={documentTypeId}
                onChange={(e) => setDocumentTypeId(e.target.value)}
                placeholder="e.g. client-presentation"
                className="w-56 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
          </div>

          <label className="flex flex-col gap-1">
            <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">
              Simulated source text (no PDF pipeline exists yet — see docs)
            </span>
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={3}
              className="rounded-[7px] border border-line-strong bg-paper-raised px-2.5 py-[6px] font-mono text-[12px]"
            />
          </label>

          <button
            onClick={submit}
            disabled={busy}
            className="w-fit rounded-[7px] bg-accent px-3 py-[6px] font-medium text-white disabled:opacity-40"
          >
            {busy ? "Resolving…" : "POST /content/resolve"}
          </button>
        </div>

        {error ? <p className="mb-3 text-[12.5px] text-crit">{error}</p> : null}

        {result ? (
          <>
            <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
              <Section title="Entities">
                {result.content.entities.map((e) => (
                  <Row key={e.id} label={`${e.type}: ${e.name}`} refs={e.source_refs} sub={e.status} />
                ))}
                {result.content.entities.length === 0 && <Empty />}
              </Section>

              <Section title="Facts">
                {result.content.facts.map((f) => (
                  <Row
                    key={f.id}
                    label={`${f.key} = ${f.status === "conflicting" ? "?" : `${f.value}${f.unit ? ` ${f.unit}` : ""}`}`}
                    refs={f.source_refs}
                    sub={`${f.status}${f.superseded_by ? " (superseded)" : ""} · confidence ${f.confidence.toFixed(2)}`}
                  />
                ))}
                {result.content.facts.length === 0 && <Empty />}
              </Section>

              <Section title="Claims">
                {result.content.claims.map((c) => (
                  <Row key={c.id} label={c.text} refs={c.source_refs} sub={c.status} />
                ))}
                {result.content.claims.length === 0 && <Empty />}
              </Section>

              <Section title="Metrics">
                {metrics.map((f) => (
                  <Row key={f.id} label={`${f.key} = ${f.value}${f.unit ? ` ${f.unit}` : ""}`} refs={f.source_refs} sub={f.status} />
                ))}
                {metrics.length === 0 && <Empty />}
              </Section>

              <Section title="Relationships">
                {result.content.relationships.map((r) => (
                  <Row key={r.id} label={`${r.subject_entity_id} --${r.predicate}--> ${r.object_entity_id}`} refs={r.source_refs} sub={r.status} />
                ))}
                {result.content.relationships.length === 0 && <Empty />}
              </Section>

              <Section title="Assets">
                {result.content.assets.map((a) => (
                  <Row key={a.asset_id} label={`${a.type}: ${a.caption || a.asset_id}`} refs={a.source_refs} />
                ))}
                {result.content.assets.length === 0 && <Empty />}
              </Section>

              <Section title="Missing information">
                {result.content.missing_information.map((m) => (
                  <p key={m.key} className="text-[12px] text-ink-soft">
                    <span className="font-mono font-medium">{m.key}</span>
                    {m.required_for ? ` — required for ${m.required_for}` : ""}
                    {m.reason ? ` (${m.reason})` : ""}
                  </p>
                ))}
                {result.content.missing_information.length === 0 && <Empty />}
              </Section>

              <Section title="Conflicts">
                {conflicts.map((f) => (
                  <div key={f.id} className="mb-1.5">
                    <p className="text-[12px] font-medium text-crit">{f.key}</p>
                    {f.conflicting_values.map((cv, i) => (
                      <Row key={i} label={`${cv.value}${cv.unit ? ` ${cv.unit}` : ""}`} refs={cv.source_refs} />
                    ))}
                  </div>
                ))}
                {conflicts.length === 0 && <Empty />}
              </Section>
            </div>

            <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
              <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                Validation — {result.validation.ok ? "ok" : "has findings"}
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

            <pre className="mb-4 overflow-auto rounded-[10px] border border-line-strong bg-paper-raised p-3 text-[11px] leading-relaxed text-ink-soft">
              {JSON.stringify(result, null, 2)}
            </pre>
          </>
        ) : (
          <p className="mb-4 text-[12.5px] text-mute">
            Enter a project id and POST /content/resolve. Real project metadata and content items are
            always included automatically; the text box above simulates an uploaded document, since this
            repository has no PDF-text-extraction pipeline yet.
          </p>
        )}

        <div>
          <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
            Recent resolutions (this process, in memory)
          </p>
          {traces.length === 0 ? (
            <p className="text-[12px] text-mute">None yet.</p>
          ) : (
            <div className="space-y-0.5">
              {traces.map((t) => (
                <div key={t.request_id} className="flex items-center gap-2 text-[11.5px]">
                  <span className={t.validation_ok ? "text-mute" : "text-crit"}>
                    {t.validation_ok ? "ok" : "findings"}
                  </span>
                  <span className="truncate text-ink-soft">{t.project_id}</span>
                  <span className="text-mute">{Object.keys(t.source_extractors).length} source(s)</span>
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
      <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">{title}</p>
      {children}
    </div>
  )
}

function Empty() {
  return <p className="text-[12px] text-mute">Nothing here.</p>
}

function Row({ label, refs, sub }: { label: string; refs: SourceRef[]; sub?: string }) {
  return (
    <div className="mb-1.5">
      <p className="text-[12px] text-ink-soft">
        {label}
        {sub ? <span className="text-mute"> — {sub}</span> : null}
      </p>
      {refs.length > 0 ? (
        <p className="text-[10.5px] text-mute">
          from {refs.map((r) => `${r.source_type}:${r.source_id}`).join(", ")}
        </p>
      ) : null}
    </div>
  )
}

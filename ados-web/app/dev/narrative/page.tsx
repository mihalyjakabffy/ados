"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/TopBar"

const REVELATION_API_URL = process.env.NEXT_PUBLIC_REVELATION_API_URL ?? "http://localhost:8000"

interface SourceRef {
  source_id: string
  source_type: string
  extraction_method: string
}

interface ContentRefs {
  fact_ids: string[]
  claim_ids: string[]
  asset_ids: string[]
  entity_ids: string[]
}

interface Fact {
  id: string
  key: string
  value: unknown
  status: string
  source_refs: SourceRef[]
}

interface Claim {
  id: string
  text: string
  status: string
  source_refs: SourceRef[]
}

interface NarrativeSection {
  id: string
  role: string
  purpose: string
  title: string
  summary: string
  sequence: number
  priority: string
  requirement: string
  audience_relevance: string
  content_refs: ContentRefs
  emphasis: string[]
  subsections: NarrativeSection[]
  draft: string | null
}

interface GeneratedClaim {
  id: string
  text: string
  status: string
  supporting_refs: ContentRefs
  related_section_id: string | null
}

interface NarrativeIssue {
  type: string
  description: string
  content_refs: ContentRefs
  impact: string
}

interface NarrativeExclusion {
  reason: string
  description: string
  excluded_refs: ContentRefs
}

interface MissingInfoImpact {
  key: string
  required_for: string
  impact: string
  affected_section_id: string | null
}

interface NarrativeThesis {
  statement: string
  supporting_refs: ContentRefs
}

interface NarrativePlan {
  id: string
  project_id: string
  content_model_version: number | null
  objective: string
  audience: string
  audience_label: string
  tone: string | null
  voice: string
  thesis: NarrativeThesis | null
  narrative_strategy: string[]
  compression: string
  sections: NarrativeSection[]
  generated_claims: GeneratedClaim[]
  missing_information: MissingInfoImpact[]
  narrative_issues: NarrativeIssue[]
  exclusions: NarrativeExclusion[]
}

interface ContentIntelligenceModel {
  facts: Fact[]
  claims: Claim[]
}

interface PlanResult {
  narrative_plan: NarrativePlan
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
  model: string
  validation_ok: boolean
  latency_ms: number
}

// ADOS-M3.3 — the developer-facing way to inspect
//   SemanticIntent -> Resolved Content -> Objective/Thesis/Strategy
//   -> Sections -> Content refs -> Missing/Conflicting -> Validation -> Trace
// before M3.4 exists to turn any of it into a visual design.
export default function DevNarrativePage() {
  const [projectId, setProjectId] = useState("")
  const [documentTypeId, setDocumentTypeId] = useState("portfolio")
  const [audience, setAudience] = useState("prospective_client")
  const [purpose, setPurpose] = useState("introduce_project")
  const [action, setAction] = useState("create")
  const [compression, setCompression] = useState("medium")
  const [rawText, setRawText] = useState(
    "Residential development in Budapest. 84 apartments. GFA of 13,100 m². The project creates a strong connection to the landscape."
  )
  const [result, setResult] = useState<PlanResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [traces, setTraces] = useState<Trace[]>([])

  async function loadTraces() {
    try {
      const res = await fetch(`${REVELATION_API_URL}/api/v2/ados-projects/narrative/traces?limit=20`)
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
        `${REVELATION_API_URL}/api/v2/ados-projects/${encodeURIComponent(projectId)}/narrative/plan`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            semantic_intent: {
              explicit: {
                action: action || undefined,
                audience: audience || undefined,
                purpose: purpose || undefined,
                document_type: documentTypeId || undefined,
              },
            },
            document_type_id: documentTypeId || undefined,
            compression,
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

  function factLabel(id: string): string {
    const fact = result?.content.facts.find((f) => f.id === id)
    return fact ? `${fact.key} = ${fact.value}` : id
  }
  function claimLabel(id: string): string {
    const claim = result?.content.claims.find((c) => c.id === id)
    return claim ? claim.text : id
  }

  function Refs({ refs }: { refs: ContentRefs }) {
    const items = [
      ...refs.fact_ids.map((id) => `fact: ${factLabel(id)}`),
      ...refs.claim_ids.map((id) => `claim: ${claimLabel(id)}`),
      ...refs.asset_ids.map((id) => `asset: ${id}`),
      ...refs.entity_ids.map((id) => `entity: ${id}`),
    ]
    if (items.length === 0) return <p className="text-[10.5px] text-mute">no content references</p>
    return (
      <ul className="ml-3 list-disc text-[11px] text-ink-soft">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    )
  }

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      <div className="border-b border-line bg-warn-bg px-4 py-2 text-[12px] font-medium text-warn">
        DEV — ADOS-M3.3 Narrative Generation inspection. Answers "what should we say", never "how
        should it look" — no layout, no PagePlan, no CommandIntent here.
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
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Document type</span>
              <input
                value={documentTypeId}
                onChange={(e) => setDocumentTypeId(e.target.value)}
                className="w-40 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Audience (free text)</span>
              <input
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                className="w-44 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Purpose (free text)</span>
              <input
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                className="w-44 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Compression</span>
              <select
                value={compression}
                onChange={(e) => setCompression(e.target.value)}
                className="w-32 rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px] font-mono text-[11.5px]"
              >
                <option value="short">short</option>
                <option value="medium">medium</option>
                <option value="long">long</option>
              </select>
            </label>
          </div>

          <label className="flex flex-col gap-1">
            <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">
              Simulated source text (feeds M3.2 content resolution)
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
            {busy ? "Planning…" : "POST /narrative/plan"}
          </button>
        </div>

        {error ? <p className="mb-3 text-[12.5px] text-crit">{error}</p> : null}

        {result ? (
          <>
            <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
              <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                Objective / Audience / Strategy
              </p>
              <p className="text-[12px] text-ink-soft">
                objective = <span className="font-mono">{result.narrative_plan.objective}</span> · audience ={" "}
                <span className="font-mono">{result.narrative_plan.audience}</span>
                {result.narrative_plan.audience_label ? ` (${result.narrative_plan.audience_label})` : ""} ·
                compression = <span className="font-mono">{result.narrative_plan.compression}</span> · voice ={" "}
                <span className="font-mono">{result.narrative_plan.voice}</span>
                {result.narrative_plan.tone ? ` · tone = ${result.narrative_plan.tone}` : ""}
              </p>
              <p className="mt-1 text-[12px] text-ink-soft">
                strategy: {result.narrative_plan.narrative_strategy.join(" → ") || "(none)"}
              </p>
              {result.narrative_plan.thesis ? (
                <div className="mt-1 text-[12px] text-ink-soft">
                  <span className="font-medium">Thesis:</span> {result.narrative_plan.thesis.statement}
                  <Refs refs={result.narrative_plan.thesis.supporting_refs} />
                </div>
              ) : (
                <p className="mt-1 text-[12px] text-mute">No thesis — content did not support one.</p>
              )}
            </div>

            <div className="mb-4 rounded-[10px] border border-line-strong bg-paper-raised p-3">
              <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">Sections</p>
              {result.narrative_plan.sections.map((s) => (
                <div key={s.id} className="mb-2 border-b border-line pb-2 last:border-0">
                  <p className="text-[12px] text-ink-soft">
                    <span className="font-mono">{s.sequence}.</span>{" "}
                    <span className="font-medium">{s.role}</span>
                    {s.title ? ` — ${s.title}` : ""} <span className="text-mute">({s.priority}, {s.requirement}, relevance={s.audience_relevance})</span>
                  </p>
                  <p className="text-[11.5px] text-mute">why: {s.purpose}</p>
                  {s.draft ? <p className="text-[11.5px] italic text-ink-soft">draft: {s.draft}</p> : null}
                  <Refs refs={s.content_refs} />
                </div>
              ))}
              {result.narrative_plan.sections.length === 0 && <p className="text-[12px] text-mute">No sections.</p>}
            </div>

            <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
              <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">Generated claims</p>
                {result.narrative_plan.generated_claims.map((c) => (
                  <div key={c.id} className="mb-1.5">
                    <p className="text-[12px] text-ink-soft">{c.text} <span className="text-mute">({c.status})</span></p>
                    <Refs refs={c.supporting_refs} />
                  </div>
                ))}
                {result.narrative_plan.generated_claims.length === 0 && <p className="text-[12px] text-mute">None.</p>}
              </div>

              <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">Missing information</p>
                {result.narrative_plan.missing_information.map((m) => (
                  <p key={m.key} className="text-[12px] text-ink-soft">
                    <span className="font-mono">{m.key}</span> — impact: {m.impact}
                    {m.required_for ? ` (required for ${m.required_for})` : ""}
                  </p>
                ))}
                {result.narrative_plan.missing_information.length === 0 && <p className="text-[12px] text-mute">None.</p>}
              </div>

              <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">Narrative issues</p>
                {result.narrative_plan.narrative_issues.map((issue, i) => (
                  <div key={i} className="mb-1.5">
                    <p className="text-[12px] text-crit">{issue.type} — {issue.impact}</p>
                    <p className="text-[11.5px] text-ink-soft">{issue.description}</p>
                    <Refs refs={issue.content_refs} />
                  </div>
                ))}
                {result.narrative_plan.narrative_issues.length === 0 && <p className="text-[12px] text-mute">None.</p>}
              </div>

              <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">Exclusions</p>
                {result.narrative_plan.exclusions.map((ex, i) => (
                  <div key={i} className="mb-1.5">
                    <p className="text-[12px] text-ink-soft">{ex.reason} — {ex.description}</p>
                    <Refs refs={ex.excluded_refs} />
                  </div>
                ))}
                {result.narrative_plan.exclusions.length === 0 && <p className="text-[12px] text-mute">None.</p>}
              </div>
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
            Enter a project id and POST /narrative/plan. Content is resolved through the same M3.2
            pipeline /dev/content-intelligence uses; this page adds SemanticIntent + narrative
            reasoning on top of it.
          </p>
        )}

        <div>
          <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
            Recent plans (this process, in memory)
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
                  <span className="text-mute">{t.model}</span>
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

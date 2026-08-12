"use client"

import { useState } from "react"
import { TopBar } from "@/components/TopBar"
import { useBrands } from "@/lib/brand-api"

const REVELATION_API_URL = process.env.NEXT_PUBLIC_REVELATION_API_URL ?? "http://localhost:8000"

const DIRECTIONS = ["editorial-quiet", "technical-dense", "image-led"] as const

// This page proves one thing and nothing else: a real ContentModel, posted
// to the real /compose endpoint, comes back as a real PagePlan. It is not
// the M1 Canvas — no layout, no selection model, no editing. Raw JSON is the
// point: it shows exactly what the API contract is before anything is built
// on top of it.
export default function DevComposePage() {
  const { data: brandsData } = useBrands()
  const [brandId, setBrandId] = useState("")
  const [directionId, setDirectionId] = useState<(typeof DIRECTIONS)[number]>("editorial-quiet")
  const [contentModel, setContentModel] = useState<Record<string, unknown> | null>(null)
  const [contentLabel, setContentLabel] = useState("")
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const activeBrandId = brandId || brandsData?.brands[0]?.brand_id || ""

  async function loadExample() {
    setError(null)
    const res = await fetch(`${REVELATION_API_URL}/api/v2/dev/content-examples/malthouse`)
    if (!res.ok) {
      setError(`${res.status} loading example content`)
      return
    }
    const data = await res.json()
    setContentModel(data)
    setContentLabel(`${data.project_name} — ${data.blocks.length} blocks`)
  }

  async function runCompose() {
    if (!contentModel || !activeBrandId) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(`${REVELATION_API_URL}/api/v2/brands/${activeBrandId}/compose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content_model: contentModel, direction_id: directionId }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(`${res.status} ${JSON.stringify(data.detail)}`)
        return
      }
      setResult(data)
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
        DEV — API contract verification only. Not the M1 Canvas.
      </div>

      <main className="flex-1 overflow-auto p-4">
        <div className="mb-4 flex flex-wrap items-end gap-3 text-[12.5px]">
          <label className="flex flex-col gap-1">
            <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Brand</span>
            <select
              value={activeBrandId}
              onChange={(e) => setBrandId(e.target.value)}
              className="rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px]"
            >
              {(brandsData?.brands ?? []).map((b) => (
                <option key={b.brand_id} value={b.brand_id}>
                  {b.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-[10.5px] uppercase tracking-[.05em] text-mute">Direction</span>
            <select
              value={directionId}
              onChange={(e) => setDirectionId(e.target.value as (typeof DIRECTIONS)[number])}
              className="rounded-[7px] border border-line-strong bg-paper-raised px-2 py-[5px]"
            >
              {DIRECTIONS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>

          <button
            onClick={loadExample}
            className="rounded-[7px] border border-line-strong bg-paper-raised px-3 py-[6px] font-medium text-ink-soft hover:bg-black/[.03]"
          >
            Load example content (Malthouse)
          </button>

          <button
            onClick={runCompose}
            disabled={!contentModel || !activeBrandId || busy}
            className="rounded-[7px] bg-accent px-3 py-[6px] font-medium text-white disabled:opacity-40"
          >
            {busy ? "Composing…" : "POST /compose"}
          </button>

          {contentLabel ? <span className="text-mute">{contentLabel}</span> : null}
        </div>

        {error ? <p className="mb-3 text-[12.5px] text-crit">{error}</p> : null}

        {result ? (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-3 mb-4">
            <Stat label="Pages" value={String((result.plan as any)?.pages?.length ?? 0)} />
            <Stat label="Plan hash" value={String((result.plan as any)?.plan_hash ?? "").slice(0, 16) + "…"} mono />
            <Stat label="Rejected candidates" value={String((result.plan as any)?.rejected?.length ?? 0)} />
            <Stat
              label="Evaluation"
              value={(result.evaluation as any)?.ok ? "ok" : "findings"}
            />
          </div>
        ) : null}

        {result ? (
          <pre className="overflow-auto rounded-[10px] border border-line-strong bg-paper-raised p-3 text-[11px] leading-relaxed text-ink-soft">
            {JSON.stringify(result, null, 2)}
          </pre>
        ) : (
          <p className="text-[12.5px] text-mute">
            Load example content, pick a brand and direction, then POST /compose.
          </p>
        )}
      </main>
    </div>
  )
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-[10px] border border-line-strong bg-paper-raised p-3">
      <p className="text-[10.5px] uppercase tracking-[.05em] text-mute">{label}</p>
      <p className={`mt-0.5 text-[14px] font-semibold text-ink ${mono ? "font-mono" : ""}`}>{value}</p>
    </div>
  )
}

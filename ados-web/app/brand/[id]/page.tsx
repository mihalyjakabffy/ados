"use client"

import { useParams } from "next/navigation"
import { TopBar } from "@/components/TopBar"
import { BrandStatusPill } from "@/components/BrandStatusPill"
import { Chips } from "@/components/Chips"
import { ColorSwatches } from "@/components/ColorSwatches"
import {
  useBrand,
  useBrandTemplates,
  useBrandTokens,
  useBrandValidation,
  useBrandVersions,
  brandPreviewUrl,
} from "@/lib/brand-api"
import { relativeDate } from "@/lib/format"
import type { TemplateInfo } from "@/lib/brand-types"

const SEVERITY_CLASS: Record<string, string> = {
  INFO: "text-accent",
  WARN: "text-warn",
  ERROR: "text-crit",
  BLOCK: "text-crit",
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-line py-3 first:border-t-0 first:pt-0">
      <p className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[.07em] text-mute">{title}</p>
      {children}
    </div>
  )
}

export default function BrandDetailPage() {
  const { id } = useParams<{ id: string }>()
  const brandId = decodeURIComponent(id)

  const { data: brand, isLoading } = useBrand(brandId)
  const { data: tokens } = useBrandTokens(brandId)
  const { data: templates } = useBrandTemplates(brandId)
  const { data: versions } = useBrandVersions(brandId)
  const { data: validation } = useBrandValidation(brandId)

  const templatesByFamily = new Map<string, TemplateInfo[]>()
  for (const t of templates?.templates ?? []) {
    const list = templatesByFamily.get(t.family) ?? []
    list.push(t)
    templatesByFamily.set(t.family, list)
  }

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      {isLoading || !brand ? (
        <div className="flex-1 p-8 text-[12.5px] text-mute">Betöltés…</div>
      ) : (
        <>
          <div className="flex items-start justify-between gap-4 border-b border-line px-4 py-3">
            <div>
              <p className="text-[16px] font-semibold text-ink">{brand.identity.name}</p>
              <p className="text-[12.5px] text-ink-soft">{brand.identity.descriptor}</p>
              <p className="mt-0.5 text-[11.5px] italic text-mute">&ldquo;{brand.identity.tagline}&rdquo;</p>
            </div>
            <div className="flex flex-col items-end gap-1.5">
              <BrandStatusPill status={brand.status} />
              <span className="font-mono text-[11px] text-mute">v{brand.version}</span>
            </div>
          </div>

          <div className="flex min-h-0 flex-1">
            <aside className="w-[320px] flex-shrink-0 overflow-y-auto border-r border-line px-4 py-3">
              <Section title="Identity">
                <p className="text-[11.5px] leading-relaxed text-ink-soft">{brand.identity.positioning}</p>
              </Section>

              <Section title="Values">
                <Chips items={brand.identity.values} />
              </Section>

              <Section title="Personality">
                <Chips items={brand.identity.personality} />
              </Section>

              <Section title="Keywords">
                <Chips items={brand.identity.keywords} />
              </Section>

              {validation ? (
                <Section title={`Validation — ${validation.ok ? "OK" : "issues"}`}>
                  <div className="mb-2 flex gap-3 text-[11px] text-mute">
                    <span>INFO {validation.counts.INFO}</span>
                    <span>WARN {validation.counts.WARN}</span>
                    <span>ERROR {validation.counts.ERROR}</span>
                    <span>BLOCK {validation.counts.BLOCK}</span>
                  </div>
                  <div className="space-y-2">
                    {validation.findings.map((f, i) => (
                      <div key={i} className="text-[11.5px]">
                        <span className={`font-semibold ${SEVERITY_CLASS[f.severity] ?? "text-ink-soft"}`}>
                          {f.severity}
                        </span>{" "}
                        <span className="text-ink-soft">{f.message}</span>
                        <p className="mt-0.5 font-mono text-[10px] text-mute">{f.field}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              ) : null}

              {versions ? (
                <Section title="Versions">
                  <div className="space-y-2">
                    {versions.versions.map((v) => (
                      <div key={v.version} className="text-[11.5px]">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-semibold text-ink">{v.version}</span>
                          <BrandStatusPill status={v.status} />
                        </div>
                        <p className="mt-0.5 text-ink-soft">{v.changelog || "—"}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              ) : null}
            </aside>

            <main className="flex-1 overflow-y-auto p-4">
              <Section title="Live preview">
                <div className="overflow-hidden rounded-[10px] border border-line-strong shadow-panel">
                  <iframe
                    src={brandPreviewUrl(brandId)}
                    title="Brand preview"
                    className="h-[520px] w-full bg-paper-raised"
                  />
                </div>
              </Section>

              {tokens ? (
                <Section title={`Colour tokens — ${Object.keys(tokens).length} total`}>
                  <ColorSwatches tokens={tokens} />
                </Section>
              ) : null}

              {templates ? (
                <Section title={`Documents this brand can render — ${templates.templates.length}`}>
                  <div className="space-y-3">
                    {[...templatesByFamily.entries()].map(([family, list]) => (
                      <div key={family}>
                        <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.05em] text-mute">
                          {family}
                        </p>
                        <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-2">
                          {list.map((t) => (
                            <div
                              key={t.template_id}
                              className="flex items-center justify-between gap-2 rounded-[8px] border border-line px-2.5 py-2 text-[11.5px]"
                            >
                              <span className="min-w-0 truncate text-ink-soft">{t.title}</span>
                              <span
                                className={`flex-shrink-0 rounded-full px-1.5 py-[2px] text-[10px] font-semibold ${
                                  t.renders ? "bg-ok-bg text-ok" : "bg-warn-bg text-warn"
                                }`}
                              >
                                {t.renders ? "✓" : `${t.missing_tokens.length} hiányzik`}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </Section>
              ) : null}

              <p className="pt-2 text-[10.5px] text-mute">
                {relativeDate(brand.created_at)} · {brand.changelog}
              </p>
            </main>
          </div>
        </>
      )}
    </div>
  )
}

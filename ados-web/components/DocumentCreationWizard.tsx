"use client"

import { useState } from "react"
import { createDocument, useDocumentTypes } from "@/lib/project-api"
import type { DocumentType, ProjectDocument } from "@/lib/project-types"

// ADOS-M2.2 §26 — the guided creation flow: "What are you creating?" then
// "Document Brief". Every card and field below comes from the
// DocumentType registry (brand/project/document_types.py) — nothing here
// hard-codes a type's identity, so a tenth document type added as data
// appears here with zero frontend changes.
export function DocumentCreationWizard({
  projectId,
  onDone,
  onCancel,
}: {
  projectId: string
  onDone: (doc: ProjectDocument) => void
  onCancel: () => void
}) {
  const { data } = useDocumentTypes()
  const [step, setStep] = useState<1 | 2>(1)
  const [selected, setSelected] = useState<DocumentType | null>(null)
  const [name, setName] = useState("")
  const [metadata, setMetadata] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  function chooseType(type: DocumentType | null) {
    setSelected(type)
    if (type) setName((n) => n || type.name)
    setStep(2)
  }

  async function submit() {
    if (!name.trim()) return
    setBusy(true)
    setErr(null)
    try {
      const cleaned = Object.fromEntries(
        Object.entries(metadata).filter(([, v]) => v.trim() !== ""),
      )
      const doc = await createDocument(projectId, {
        name: name.trim(),
        document_type_id: selected?.id ?? "",
        metadata: cleaned,
      })
      onDone(doc)
    } catch {
      setErr("Could not create the document.")
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-[12px] bg-paper-raised shadow-xl">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <p className="text-[13px] font-semibold text-ink">
            New document {step === 2 ? `— ${selected?.name ?? "Free-form"}` : ""}
          </p>
          <button onClick={onCancel} className="text-[12px] text-mute hover:text-ink">
            Cancel
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {step === 1 ? (
            <>
              <p className="mb-3 text-[12.5px] text-mute">What are you creating?</p>
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                {(data?.document_types ?? []).map((t) => (
                  <button
                    key={t.id}
                    onClick={() => chooseType(t)}
                    className="flex flex-col items-start gap-1 rounded-[9px] border border-line p-3 text-left hover:border-accent hover:bg-accent-soft/40"
                  >
                    <span className="text-[13px] font-semibold text-ink">{t.name}</span>
                    <span className="text-[11.5px] text-ink-soft">{t.description}</span>
                    <span className="mt-1 text-[10.5px] text-mute">
                      For {t.audience.toLowerCase()} · {t.typical_use}
                    </span>
                  </button>
                ))}
                <button
                  onClick={() => chooseType(null)}
                  className="flex flex-col items-start gap-1 rounded-[9px] border border-dashed border-line p-3 text-left hover:border-accent hover:bg-accent-soft/40"
                >
                  <span className="text-[13px] font-semibold text-ink">Free-form document</span>
                  <span className="text-[11.5px] text-ink-soft">
                    No fixed structure — build it up however you like.
                  </span>
                </button>
              </div>
            </>
          ) : (
            <div className="flex flex-col gap-3">
              {selected ? (
                <p className="text-[12px] text-mute">
                  {selected.purpose} Expected output: {selected.expected_output}
                </p>
              ) : null}

              <label className="flex flex-col gap-1 text-[12px]">
                <span className="font-medium text-ink-soft">Title</span>
                <input
                  autoFocus
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="rounded-[7px] border border-line-strong px-2.5 py-[6px] text-[13px]"
                />
              </label>

              {selected ? (
                <>
                  <p className="mt-1 text-[10.5px] font-semibold uppercase tracking-[.06em] text-mute">
                    Document brief
                  </p>
                  {selected.metadata_requirements.map((key) => (
                    <label key={key} className="flex flex-col gap-1 text-[12px]">
                      <span className="text-ink-soft">{labelFor(key)}</span>
                      <input
                        value={metadata[key] ?? ""}
                        onChange={(e) => setMetadata((m) => ({ ...m, [key]: e.target.value }))}
                        className="rounded-[7px] border border-line-strong px-2.5 py-[6px] text-[12.5px]"
                      />
                    </label>
                  ))}
                  {["subtitle", "author", "purpose"]
                    .filter((k) => !selected.metadata_requirements.includes(k))
                    .map((key) => (
                      <label key={key} className="flex flex-col gap-1 text-[12px]">
                        <span className="text-ink-soft">{labelFor(key)} (optional)</span>
                        <input
                          value={metadata[key] ?? ""}
                          onChange={(e) => setMetadata((m) => ({ ...m, [key]: e.target.value }))}
                          className="rounded-[7px] border border-line-strong px-2.5 py-[6px] text-[12.5px]"
                        />
                      </label>
                    ))}
                  <p className="text-[11px] text-mute">
                    Starting structure: {selected.default_structure.map((k) => selected.section_labels[k] ?? k).join(" · ")}
                  </p>
                </>
              ) : null}

              {err ? <p className="text-[11.5px] text-crit">{err}</p> : null}

              <div className="mt-2 flex gap-2">
                <button
                  onClick={() => setStep(1)}
                  className="rounded-[7px] px-3 py-[7px] text-[12px] text-mute hover:bg-black/[.03]"
                >
                  Back
                </button>
                <button
                  onClick={submit}
                  disabled={busy || !name.trim()}
                  className="rounded-[7px] bg-accent px-3 py-[7px] text-[12.5px] font-medium text-white disabled:opacity-40"
                >
                  {busy ? "Creating…" : "Create document"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function labelFor(key: string): string {
  return key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ")
}

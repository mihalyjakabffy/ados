import useSWR from "swr"
import type { ContainerDetail, PackageData, RuleRegistry } from "./types"

const API_URL = process.env.NEXT_PUBLIC_ADOS_API_URL ?? "http://localhost:8010"

async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`)
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} — ${path}`)
  }
  return res.json() as Promise<T>
}

export function usePackage() {
  return useSWR<PackageData>("/api/package", fetcher)
}

export function useContainer(containerId: string | null) {
  return useSWR<ContainerDetail>(
    containerId ? `/api/containers/${encodeURIComponent(containerId)}` : null,
    fetcher,
  )
}

export function useRules(params: { q?: string; volume?: string; level?: string } = {}) {
  const search = new URLSearchParams()
  if (params.q) search.set("q", params.q)
  if (params.volume) search.set("volume", params.volume)
  if (params.level) search.set("level", params.level)
  const qs = search.toString()
  return useSWR<RuleRegistry>(`/api/rules${qs ? `?${qs}` : ""}`, fetcher)
}

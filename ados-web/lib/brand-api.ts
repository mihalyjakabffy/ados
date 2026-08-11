import useSWR from "swr"
import type {
  BrandDetail,
  BrandTemplates,
  BrandVersions,
  FlatTokens,
  ValidationReport,
} from "./brand-types"

// The Brand System lives on the real REVELATION API (api/main.py), not on
// ados-service — a different backend from the Library/System pages, on
// purpose: ADOS is the document/brand product, REVELATION is the platform
// it borrows a couple of architectural patterns from, not the same app.
const REVELATION_API_URL = process.env.NEXT_PUBLIC_REVELATION_API_URL ?? "http://localhost:8000"

async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${REVELATION_API_URL}${path}`)
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} — ${path}`)
  }
  return res.json() as Promise<T>
}

export function useBrands() {
  return useSWR<{ brands: { brand_id: string; name: string; latest_version: string }[] }>(
    "/api/v2/brands",
    fetcher,
  )
}

export function useBrand(brandId: string | null) {
  return useSWR<BrandDetail>(brandId ? `/api/v2/brands/${encodeURIComponent(brandId)}` : null, fetcher)
}

export function useBrandTokens(brandId: string | null) {
  return useSWR<FlatTokens>(
    brandId ? `/api/v2/brands/${encodeURIComponent(brandId)}/tokens?flat=true` : null,
    fetcher,
  )
}

export function useBrandTemplates(brandId: string | null) {
  return useSWR<BrandTemplates>(
    brandId ? `/api/v2/brands/${encodeURIComponent(brandId)}/templates` : null,
    fetcher,
  )
}

export function useBrandVersions(brandId: string | null) {
  return useSWR<BrandVersions>(
    brandId ? `/api/v2/brands/${encodeURIComponent(brandId)}/versions` : null,
    fetcher,
  )
}

export function useBrandValidation(brandId: string | null) {
  return useSWR<ValidationReport>(
    brandId ? `/api/v2/brands/${encodeURIComponent(brandId)}/validate` : null,
    fetcher,
  )
}

export function brandPreviewUrl(brandId: string): string {
  return `${REVELATION_API_URL}/api/v2/brands/${encodeURIComponent(brandId)}/preview`
}

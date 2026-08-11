# ados-web

Finder-style browser for the ADOS 1.0 documentation model (Package →
Container → Region → View). Standalone Next.js app with its own,
deliberately light and monochrome-first visual system — see the design
rationale in the approved plan (ADOS Frontend — terv).

Talks to [`ados-service`](../ados-service) for data; ships no backend of
its own.

## Run

```bash
cd ados-web
npm install
cp .env.example .env.local   # points at ados-service, defaults to :8010

npm run dev                  # http://localhost:3100
```

Requires `ados-service` running on port 8010 (see its README).

## Structure

| Path | Role |
|---|---|
| `app/page.tsx` | Package browser — sidebar, breadcrumb toolbar, container list, inspector |
| `app/rules/page.tsx` | Rule registry — searchable list of the 476 ADOS rules |
| `components/` | `Sidebar`, `Toolbar`, `ContainerList`, `Inspector`, `StatusPill`, `TypeIcon`, `RuleLevelPill` |
| `lib/types.ts` | TypeScript types mirroring `docs/ados/machine/ados-sheet-schema.json` |
| `lib/api.ts` | SWR data hooks against `ados-service` |

## Status

M0 of the phased plan: read-only browser (List view + Inspector) and the
Rule Registry, both on real data from the specification's own reference
package. Icon/Gallery/Column views, the QA dashboard and the Deviation
Register are follow-up phases.

import { AdosStateProvider } from "@/lib/ados-state"

// Same scoping precedent as app/workspace/layout.tsx: the shared compose/
// intent/iterate state lives only where the Canvas+Command panels do.
export default function DocumentWorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <AdosStateProvider>{children}</AdosStateProvider>
}

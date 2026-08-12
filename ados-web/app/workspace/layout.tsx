import { AdosStateProvider } from "@/lib/ados-state"

// Scoped to /workspace only — Library ("/"), Brand and System keep working
// exactly as they did, with zero new code in their path.
export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <AdosStateProvider>{children}</AdosStateProvider>
}

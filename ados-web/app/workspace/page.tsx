"use client"

import { useState } from "react"
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from "lucide-react"
import { TopBar } from "@/components/TopBar"
import { LibraryPanel } from "@/components/workspace/LibraryPanel"
import { CanvasPanel } from "@/components/workspace/CanvasPanel"
import { CommandPanel } from "@/components/workspace/CommandPanel"

// The primary ADOS workspace: three views of one shared state
// (lib/ados-state.tsx), not three independent pages. Library = what
// exists, Canvas = what it looks like, Command = what I want to change.
export default function WorkspacePage() {
  const [libraryOpen, setLibraryOpen] = useState(true)
  const [commandOpen, setCommandOpen] = useState(true)

  return (
    <div className="flex h-screen flex-col">
      <TopBar />

      <div className="flex min-h-0 flex-1">
        {libraryOpen ? (
          <div className="relative w-[260px] flex-shrink-0 border-r border-line">
            <LibraryPanel />
            <CollapseButton
              onClick={() => setLibraryOpen(false)}
              icon={<PanelLeftClose className="h-3.5 w-3.5" />}
              className="right-2"
            />
          </div>
        ) : (
          <CollapseRail side="left" onClick={() => setLibraryOpen(true)} icon={<PanelLeftOpen className="h-3.5 w-3.5" />} />
        )}

        <div className="min-w-0 flex-1">
          <CanvasPanel />
        </div>

        {commandOpen ? (
          <div className="relative w-[360px] flex-shrink-0 border-l border-line">
            <CollapseButton
              onClick={() => setCommandOpen(false)}
              icon={<PanelRightClose className="h-3.5 w-3.5" />}
              className="right-2"
            />
            <CommandPanel />
          </div>
        ) : (
          <CollapseRail side="right" onClick={() => setCommandOpen(true)} icon={<PanelRightOpen className="h-3.5 w-3.5" />} />
        )}
      </div>
    </div>
  )
}

function CollapseButton({
  onClick,
  icon,
  className = "",
}: {
  onClick: () => void
  icon: React.ReactNode
  className?: string
}) {
  return (
    <button
      onClick={onClick}
      className={`absolute top-2 z-10 rounded-[6px] p-1 text-mute hover:bg-black/[.04] hover:text-ink ${className}`}
      aria-label="Collapse panel"
    >
      {icon}
    </button>
  )
}

function CollapseRail({
  side,
  onClick,
  icon,
}: {
  side: "left" | "right"
  onClick: () => void
  icon: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      aria-label={`Expand ${side} panel`}
      className={`flex w-[22px] flex-shrink-0 items-center justify-center text-mute hover:bg-black/[.03] hover:text-ink ${
        side === "left" ? "border-r border-line" : "border-l border-line"
      }`}
    >
      {icon}
    </button>
  )
}

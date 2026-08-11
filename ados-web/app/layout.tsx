import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "ADOS Documentation OS",
  description: "Finder-style browser for ADOS packages, containers and the rule registry.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans text-[13px] antialiased">{children}</body>
    </html>
  )
}

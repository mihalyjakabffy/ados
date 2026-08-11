import type { Config } from "tailwindcss"

// Design tokens carried over from the approved plan (ADOS Frontend — terv):
// warm-neutral paper ground, a single restrained "drafting blue" accent,
// and semantic status colours kept on a separate channel from the accent —
// mirrors ADOS-0.3.030 (colour is never the sole carrier of a distinction).
const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "var(--paper)",
        "paper-raised": "var(--paper-raised)",
        ink: "var(--ink)",
        "ink-soft": "var(--ink-soft)",
        mute: "var(--mute)",
        line: "var(--line)",
        "line-strong": "var(--line-strong)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        "accent-line": "var(--accent-line)",
        ok: "var(--ok)",
        "ok-bg": "var(--ok-bg)",
        warn: "var(--warn)",
        "warn-bg": "var(--warn-bg)",
        crit: "var(--crit)",
        "crit-bg": "var(--crit-bg)",
        sidebar: "var(--sidebar)",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Text"',
          '"Segoe UI"',
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          '"SF Mono"',
          "Menlo",
          '"Cascadia Mono"',
          "monospace",
        ],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(20,18,14,.04), 0 8px 24px rgba(20,18,14,.06)",
      },
    },
  },
  plugins: [],
}

export default config

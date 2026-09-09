# ADOS — Architectural Document Operating System

ADOS turns a practice's brand, a project's facts, and a document type into a
composed, validated, exportable document — a project report, a design report,
an investor report, a portfolio case study, a sales brochure — without any of
those document types hard-coding how the others work.

It was built as one part of a larger monorepo and split out here once it
proved to be a genuinely standalone system: nothing in `brand/` or
`tests_brand/` reaches into anything outside this repository.

## What's here

- **`brand/`** — the domain: brand identity, content modelling and
  extraction, narrative and design-intent generation, command compilation,
  document composition and export, and the closed-loop iteration engine
  that observes a composed document, finds problems, recommends a fix, and
  re-applies it.
- **`tests_brand/`** — ~1,100 tests covering that domain: unit, API,
  determinism, AST-boundary (LLM modules must not import each other's
  internals), and evaluation-dataset tests for every generation stage.
- **`api/`** — the FastAPI surface: `api/main.py` mounts the eight ADOS
  routers (brand, projects, semantic intent, content intelligence,
  narrative, design intent, command generation, closed loop).
- **`ados-web/`** — the Next.js frontend: a Finder-style browser for ADOS
  projects, brands, documents and the rule registry, plus developer
  inspection pages for each generation stage.
- **`ados-service/`** — a small, separate read-only API over
  `docs/ados/machine/` (the ADOS 1.0 specification's own reference package
  and 476-rule registry). Deliberately independent of `api/main.py`: it
  serves ados-web's Package browser and Rule Registry pages, a different
  domain with no shared foreign keys to the Brand System.
- **`docs/ados/`**, **`docs/architecture/`**, **`docs/templates/`** — the
  ADOS visual-language specification, the architecture notes for each
  milestone, and the PDF/Word document builders + fonts the export pipeline
  renders through.

## Running it

Main backend:

```bash
pip install -r requirements.txt
python -m playwright install chromium   # only needed for HTML→PDF export
uvicorn api.main:app --reload --port 8000
```

Documentation-model service (powers ados-web's home page and rule registry):

```bash
cd ados-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8010
```

Frontend:

```bash
cd ados-web
npm install
cp .env.example .env.local
npm run dev   # http://localhost:3100
```

`ados-web` talks to `api/main.py` at `http://localhost:8000` (Brand, Projects,
dev pages) and to `ados-service` at `http://localhost:8010` (home page,
`/rules`) — both defaults are already set in `.env.example`. Both APIs'
CORS defaults already allow `http://localhost:3100`.

## Testing

```bash
python -m pytest tests_brand -q
```

The suite needs no database, no storage service and no API key — every
LLM-backed generator has a deterministic rule-based fallback, and that's the
path CI exercises. `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` are optional; set
one to exercise the real LLM path locally.

## History

This repository's git history was carried over from the original monorepo
via `git filter-repo`, keeping the real commit history for every file that
belongs to ADOS. Two small dependencies that lived outside ADOS's own
directories in that monorepo — a shared `BaseAgent` LLM-call wrapper and a
subset of a "Design State v2" schema needed by one worked example — were
vendored into `brand/agents/_vendor/` and `brand/examples/_vendor/` rather
than dropped, since real, passing tests depended on both.

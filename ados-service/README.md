# ados-service

Minimal read-only API over the ADOS 1.0 specification's own machine
artefacts (`docs/ados/machine/`). Serves the reference package instance
(`ados-ir-example.json`) and the 476-rule registry (`ados-rules.yaml`) to
the `ados-web` frontend.

Deliberately separate from the REVELATION API (`api/main.py`): ADOS
documents issued drawing/document packages, a different domain with no
shared foreign keys — same boundary pattern the repo already uses between
REVELATION and CONSTRUMIND.

## Run

```bash
cd ados-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8010
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/package` | Package metadata + container summary list |
| `GET` | `/api/containers/{container_id}` | Full container record (regions, revisions, references) |
| `GET` | `/api/rules?q=&volume=&level=` | Rule registry, optionally filtered |
| `GET` | `/health` | Liveness check |

## Environment

| Variable | Default | Description |
|---|---|---|
| `ADOS_DOCS_ROOT` | repo root | Where `docs/ados/machine/` is resolved from |
| `ADOS_ALLOWED_ORIGINS` | `http://localhost:3100` | CORS allow-list, comma-separated |

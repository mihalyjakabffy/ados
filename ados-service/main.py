"""
ados-service/main.py

Minimal read-only API for the ADOS (Architectural Documentation Operating
System) specification and its reference package instance.

Scope (deliberately narrow): this is not part of the REVELATION DesignState
API (api/main.py) — ADOS documents a completely different domain (issued
drawing/document packages, not renderable design states) and has no shared
foreign keys with it, mirroring the REVELATION/CONSTRUMIND domain-boundary
pattern already used in this repository.

Data source: the specification's own normative machine artefacts —
docs/ados/machine/ados-ir-example.json (one schema-valid reference package)
and docs/ados/machine/ados-rules.yaml (the 476-rule registry). Nothing here
is fabricated; every field returned is read straight from those files.

Run:
    uvicorn ados-service.main:app --reload --port 8010
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(os.environ.get("ADOS_DOCS_ROOT", Path(__file__).resolve().parent.parent))
_MACHINE_DIR = _REPO_ROOT / "docs" / "ados" / "machine"
_IR_EXAMPLE_PATH = _MACHINE_DIR / "ados-ir-example.json"
_RULES_PATH = _MACHINE_DIR / "ados-rules.yaml"


@lru_cache(maxsize=1)
def _load_ir() -> dict[str, Any]:
    if not _IR_EXAMPLE_PATH.is_file():
        raise FileNotFoundError(f"ADOS IR example not found at {_IR_EXAMPLE_PATH}")
    return json.loads(_IR_EXAMPLE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_rules() -> dict[str, Any]:
    if not _RULES_PATH.is_file():
        raise FileNotFoundError(f"ADOS rule registry not found at {_RULES_PATH}")
    return yaml.safe_load(_RULES_PATH.read_text(encoding="utf-8"))


def _container_summary(container: dict[str, Any], encoding_table: list[dict[str, Any]]) -> dict[str, Any]:
    revisions = container.get("revisions", [])
    latest = revisions[0] if revisions else None
    qa = _run_qa(container, encoding_table)
    return {
        "container_id": container["container_id"],
        "short_id": container.get("short_id"),
        "title": container.get("title"),
        "type": container.get("type"),
        "status": container.get("status"),
        "revision": container.get("revision"),
        "author": container.get("parties", {}).get("author"),
        "checker": container.get("parties", {}).get("checker"),
        "approver": container.get("parties", {}).get("approver"),
        "latest_revision_date": latest["date"] if latest else None,
        "region_count": len(container.get("regions", [])),
        "reference_out_count": len(container.get("references_out", [])),
        "reference_in_count": len(container.get("references_in", [])),
        "qa_summary": {
            "pass": sum(1 for r in qa if r["status"] == "pass"),
            "fail": sum(1 for r in qa if r["status"] == "fail"),
        },
    }


# ---------------------------------------------------------------------------
# QA — a small number of genuinely deterministic checks, computed from the
# container's own data. No invented scores: every result here is either a
# direct field check or a cross-reference against the package's own
# encoding table. See docs/ados/ADOS-V8-Quality-Assurance.md for the full
# (currently unimplemented) metric set this is a narrow, honest slice of.
# ---------------------------------------------------------------------------

def _run_qa(container: dict[str, Any], encoding_table: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    # ADOS-0.3.090 — Absence shall be explicit: every sheet carries a
    # non-empty scope statement.
    scope = (container.get("scope_statement") or "").strip()
    results.append({
        "rule": "ADOS-0.3.090",
        "label": "Scope statement present",
        "status": "pass" if scope else "fail",
        "detail": "Scope statement is present." if scope else "No scope statement — exclusions are not explicit.",
    })

    # ADOS-2.6.020-adjacent — the declared current revision shall match the
    # most recent entry in the revision history.
    revisions = container.get("revisions", [])
    declared = container.get("revision")
    latest_code = revisions[0]["code"] if revisions else None
    rev_ok = bool(revisions) and declared == latest_code
    results.append({
        "rule": "ADOS-2.6.020",
        "label": "Declared revision matches history",
        "status": "pass" if rev_ok else "fail",
        "detail": (
            f"Container revision '{declared}' matches the latest history entry."
            if rev_ok
            else f"Container declares revision '{declared}', but the latest history entry is '{latest_code}'."
        ),
    })

    # ADOS-0.3.010 — every graphic variable used shall appear in the
    # encoding table. We check the three channels the IR carries directly:
    # line_weight (Stroke.tier), line_type (Stroke.line_type), tone
    # (Stroke.tone / Fill.tone).
    encoded = {(row["channel"], row["state"]) for row in encoding_table}
    used: set[tuple[str, str]] = set()
    for region in container.get("regions", []):
        for view in region.get("views", []):
            for geom in view.get("geometry", []):
                if geom.get("kind") == "stroke":
                    used.add(("line_weight", geom.get("tier")))
                    used.add(("line_type", geom.get("line_type")))
                    used.add(("tone", geom.get("tone")))
                elif geom.get("kind") == "fill":
                    used.add(("tone", geom.get("tone")))

    missing = sorted(f"{ch}/{st}" for ch, st in used if st and (ch, st) not in encoded)
    results.append({
        "rule": "ADOS-0.3.010",
        "label": "Encoding table covers used channels",
        "status": "pass" if not missing else "fail",
        "detail": (
            "Every line weight, line type and tone used on this sheet is declared in the encoding table."
            if not missing
            else f"Used but undeclared in the encoding table: {', '.join(missing)}."
        ),
    })

    return results


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ADOS Documentation OS — API",
    description="Read-only API over the ADOS 1.0 reference package and rule registry.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip()
        for o in os.environ.get(
            "ADOS_ALLOWED_ORIGINS", "http://localhost:3100,http://127.0.0.1:3100"
        ).split(",")
        if o.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", tags=["infrastructure"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/package", tags=["package"])
async def get_package() -> dict[str, Any]:
    """Package metadata (project, set, issue, encoding table) plus a container summary list."""
    try:
        pkg = _load_ir()["package"]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "package_id": pkg["package_id"],
        "purpose": pkg.get("purpose"),
        "status": pkg.get("status"),
        "project": pkg["project"],
        "set": pkg["set"],
        "issue": pkg["issue"],
        "encoding_table": pkg.get("encoding_table", []),
        "containers": [_container_summary(c, pkg.get("encoding_table", [])) for c in pkg.get("containers", [])],
    }


@app.get("/api/containers/{container_id}", tags=["package"])
async def get_container(container_id: str) -> dict[str, Any]:
    """Full container record — the sole detail the Inspector panel reads from."""
    try:
        pkg = _load_ir()["package"]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    for container in pkg.get("containers", []):
        if container["container_id"] == container_id:
            return {**container, "qa": _run_qa(container, pkg.get("encoding_table", []))}

    raise HTTPException(status_code=404, detail=f"Container '{container_id}' not found in package.")


@app.get("/api/rules", tags=["rules"])
async def list_rules(q: str | None = None, volume: str | None = None, level: str | None = None) -> dict[str, Any]:
    """
    The rule registry, optionally filtered.

    q       — case-insensitive substring match against id or name.
    volume  — exact match against the rule's volume label (e.g. "0 — Manifesto").
    level   — exact match against shall | should | may.
    """
    try:
        registry = _load_rules()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    rules: list[dict[str, Any]] = registry.get("rules", [])

    if q:
        needle = q.lower()
        rules = [r for r in rules if needle in r["id"].lower() or needle in r.get("name", "").lower()]
    if volume:
        rules = [r for r in rules if r.get("volume") == volume]
    if level:
        rules = [r for r in rules if r.get("level") == level]

    return {
        "edition": registry.get("edition"),
        "rule_count": registry.get("rule_count"),
        "principles": registry.get("principles", {}),
        "severities": registry.get("severities", {}),
        "matched": len(rules),
        "rules": rules,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)

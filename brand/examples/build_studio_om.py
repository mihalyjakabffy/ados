#!/usr/bin/env python3
"""
brand/examples/build_studio_om.py

Builds the complete STUDIO OM brand package, through the pipeline.

    python -m brand.examples.build_studio_om [outdir]

This is the acceptance test for the whole Brand System, run as a program:

    brief ──► BrandAgent ──► proposal ──► validation ──► approval
                                                            │
                                                       design tokens
                                                            │
        ┌──────────┬──────────┬──────────┬──────────┬───────┴────────┐
        ▼          ▼          ▼          ▼          ▼                ▼
      logo      documents  presentation portfolio  website      guidelines
        │          │          │          │          │                │
        └──────────┴──────────┴──────────┴──────────┴────────────────┘
                                    │
                        asset inventory + consistency audit

The brand the package is built from is ``studio_om.STUDIO_OM``, which is the
approved definition. The agent step runs first against the same brief and its
proposal is *compared* to the approved brand rather than replacing it — that
is the honest version of "AI proposes, the user approves": the proposal is
evidence, the approved definition is the source of truth.

Nothing in this file decides what anything looks like. Every value comes from
the resolved tokens.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from brand.assets.logo import LogoSystem, Variant
from brand.examples.studio_om import STUDIO_OM
from brand.export import (
    AssetInventory,
    browser_available,
    html_to_pdf,
    rasterise_svg,
    to_colour_table,
    to_css_variables,
    to_json,
    to_yaml,
)
from brand.guidelines import render_guidelines
from brand.models.brand import Brand
from brand.preview.brand_preview import render_preview
from brand.templates.document_templates import TEMPLATES, Medium, get_template
from brand.templates.renderers import render_sheet_pdf, render_word_dotx
from brand.validation.consistency import audit_package

BRIEF = (
    "STUDIO OM is a contemporary architecture studio working across "
    "architecture, interior architecture, adaptive reuse, residential and "
    "small-scale public projects, and conceptual research. The identity "
    "should feel precise, quiet, material and rigorous — intellectual rather "
    "than corporate, contextual rather than signature, and contemporary "
    "without being trendy."
)

#: Which raster widths each logo variant needs, and why.
_RASTER_WIDTHS = {
    "primary": 2000,      # print and presentation
    "symbol": 512,        # avatar
    "compact": 512,       # favicon source
    "reversed": 2000,
}


def build(out_dir: Path, brand: Brand = STUDIO_OM) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tokens = brand.resolve_tokens()
    inv = AssetInventory(brand, out_dir)
    log = _Log()

    # -- 1. the agent step, for the record ------------------------------
    proposal = _propose(brand, log)
    (out_dir / "brand").mkdir(exist_ok=True)
    inv.add(
        _write(out_dir / "brand/agent-proposal.json",
               json.dumps(proposal, indent=2)),
        type="provenance",
        note="What the agent proposed from the brief. Evidence, not the brand.",
    )

    # -- 2. validation ---------------------------------------------------
    report = brand.check()
    inv.add(
        _write(out_dir / "brand/validation.json",
               json.dumps(report.to_dict(), indent=2)),
        type="provenance",
    )
    log.step("Validation", report.summary())
    if not report.ok:
        raise SystemExit(
            "STUDIO OM does not validate; the package is not built from a "
            "brand the system considers sound.\n" + report.summary()
        )

    # -- 3. the brand itself, in every serialisation ---------------------
    inv.add(_write(out_dir / "brand/studio-om.json", brand.to_json()),
            type="brand-definition")
    inv.add(_write(out_dir / "brand/studio-om.yaml", to_yaml(brand)),
            type="brand-definition")
    inv.add(_write(out_dir / "brand/tokens.json", to_json(tokens)),
            type="tokens", token_count=len(tokens))
    inv.add(_write(out_dir / "brand/tokens.flat.json", to_json(tokens, flat=True)),
            type="tokens")
    inv.add(_write(out_dir / "brand/tokens.css", to_css_variables(tokens)),
            type="tokens")
    inv.add(
        _write(out_dir / "brand/colours.json",
               json.dumps(to_colour_table(tokens), indent=2)),
        type="tokens",
        note="HEX, RGB, uncalibrated CMYK, L* and the monochrome equivalent.",
    )
    log.step("Brand + tokens", f"{len(tokens)} tokens, five serialisations")

    # -- 4. the logo system ----------------------------------------------
    logos = LogoSystem(brand, tokens)
    logo_dir = out_dir / "logo"
    rastered = 0
    for logo in logos.build_all():
        path = logo.write(logo_dir)
        meta = logo.metadata(brand.identity.name)
        meta["path"] = str(path.relative_to(out_dir)).replace("\\", "/")
        inv.extend([meta], type="logo")
        width = _RASTER_WIDTHS.get(logo.variant.value)
        if width:
            png = rasterise_svg(path, logo_dir / f"{logo.slug}.png",
                                width_px=width)
            if png.ok and png.path:
                rastered += 1
                inv.add(png.path, type="logo", name=f"{logo.slug}-png",
                        variant=logo.variant.value, background=logo.background,
                        derived_from=path.name, width_px=width)
            else:
                log.note(f"PNG: {png.reason}")
    log.step(
        "Logo system",
        f"{len(logos.build_all())} SVG variants, {rastered} PNG rasters · "
        f"clear space {logos.clear_space_mm():g} mm · "
        f"minimum {logos.min_width_mm():g} mm",
    )

    # -- 5. every template ------------------------------------------------
    doc_dir = out_dir / "documents"
    counts = {"html": 0, "pdf": 0, "dotx": 0}
    for tid, template in sorted(TEMPLATES.items()):
        if template.medium is Medium.PDF:
            doc = render_sheet_pdf(
                template, tokens, brand=brand,
                project="Malthouse", client="Ash Trust",
                container_id="2317-SOM-ZZ-XX-DR-A-0001",
            )
        elif template.medium is Medium.DOCX:
            doc = render_word_dotx(template, tokens, brand=brand)
        else:
            doc = template.render(tokens, **_context_for(tid))
        counts[doc.medium.value] += 1
        target = (out_dir / "word" if template.medium is Medium.DOCX else doc_dir)
        path = doc.write(target / f"{tid}.{doc.medium.value}")
        inv.add(path, type=_asset_type(template), template=tid,
                title=template.title, page=template.page,
                family=template.family.value, medium=template.medium.value,
                tokens_used=len(doc.tokens_used))
    log.step("Templates", f"{counts['html']} HTML, {counts['pdf']} PDF, "
                          f"{counts['dotx']} Word, {len(TEMPLATES)} total")

    # -- 6. guidelines, preview -------------------------------------------
    guide_html = out_dir / "brand-guidelines/studio-om-brand-guidelines.html"
    inv.add(_write(guide_html, render_guidelines(brand, tokens=tokens)),
            type="guidelines")
    pdf = html_to_pdf(guide_html,
                      guide_html.with_suffix(".pdf"), page_format="A4")
    if pdf.ok and pdf.path:
        inv.add(pdf.path, type="guidelines", derived_from=guide_html.name)
    else:
        log.note(f"guidelines PDF: {pdf.reason}")

    inv.add(_write(out_dir / "brand/preview.html", render_preview(brand, tokens=tokens)),
            type="preview")
    log.step("Guidelines", f"18 sections{' + PDF' if pdf.ok else ' (HTML only)'}")

    # -- 7. inventory and audit -------------------------------------------
    # The inventory does not list itself, the audit report or the README:
    # those are reports *about* the package. Listing them would need the
    # manifest written after files that are themselves written after the
    # manifest, and the first fresh build would fail the audit.
    inventory_path = inv.write()
    audit = audit_package(out_dir, brand, tokens)
    _write(out_dir / "consistency-audit.json", json.dumps(audit.to_dict(), indent=2))
    log.step("Consistency audit", audit.summary())

    _write(out_dir / "README.md", _package_readme(brand, tokens, inv, audit, log))

    return {
        "out_dir": out_dir,
        "tokens": len(tokens),
        "assets": len(inv.records),
        "audit": audit,
        "inventory": inventory_path,
        "log": log,
    }


# ---------------------------------------------------------------------------


def _propose(brand: Brand, log: "_Log") -> dict[str, Any]:
    """Run the agent on the brief and compare it with the approved brand."""
    from brand.agents.brand_agent import BrandAgent

    proposal = BrandAgent().generate_proposal(BRIEF, name="STUDIO OM")
    proposed = proposal.brand
    approved = brand
    diff = {
        "personality": {
            "proposed": [a.value for a in proposed.identity.personality],
            "approved": [a.value for a in approved.identity.personality],
        },
        "typeface": {
            "proposed": proposed.visual_identity.typography.primary_font.family,
            "approved": approved.visual_identity.typography.primary_font.family,
        },
        "accent": {
            "proposed": proposed.visual_identity.colour.accent,
            "approved": approved.visual_identity.colour.accent,
        },
        "cut_mm": {
            "proposed": proposed.architectural_language.drawing.lineweights.cut_mm,
            "approved": approved.architectural_language.drawing.lineweights.cut_mm,
        },
    }
    log.step(
        f"Agent proposal ({proposal.source})",
        f"personality {', '.join(diff['personality']['proposed'])} · "
        f"confidence {proposal.confidence:.2f} · "
        f"{proposal.validation.summary() if proposal.validation else ''}",
    )
    log.note(
        "The proposal is recorded, not adopted: the approved definition keeps "
        "a 1.00 mm cut and the oxidised accent, both human decisions the agent "
        "did not make."
    )
    return {
        "brief": BRIEF,
        "source": proposal.source,
        "confidence": proposal.confidence,
        "rationale": proposal.rationale,
        "assumptions": proposal.assumptions,
        "open_questions": proposal.open_questions,
        "validation": proposal.validation.to_dict() if proposal.validation else None,
        "difference_from_approved": diff,
        "proposed_brand": proposal.brand.model_dump(mode="json"),
    }


def _context_for(template_id: str) -> dict[str, Any]:
    """Realistic placeholder content, so a template is judged as a layout."""
    common = {
        "project": "Malthouse",
        "code": "2317",
        "date": "2026-03-04",
        "person": "Anna Kovács",
        "role": "Architect",
        "email": "anna@studio-om.example",
        "phone": "+36 1 000 0000",
        "address": "Bródy Sándor utca 1 · 1088 Budapest",
    }
    extra: dict[str, dict[str, Any]] = {
        "BT01-a4-report": {"title": "Malthouse — feasibility study"},
        "BT08-proposal": {"title": "Fee proposal"},
        "BI05-portfolio-spread": {
            "location": "Budapest", "year": "2025", "area": "1 240 m²",
            "status": "Completed",
            "text": "A 1904 malthouse with a sound brick shell and a failed "
                    "roof. We kept the shell, replaced the roof in timber, and "
                    "cut one new opening.",
        },
        "BI06-competition-board": {
            "title": "Malthouse", "code": "ENTRY 0417",
            "text": "Keep the shell. Replace the roof. Cut one opening.",
        },
        "BI04-presentation-deck": {
            "subtitle": "Stage 3 design review", "section": "The existing shell",
            "heading": "One opening",
        },
        "BI07-social-post": {"kind": "construction progress"},
    }
    return {**common, **extra.get(template_id, {})}


def _asset_type(template) -> str:
    if template.medium.value == "dotx":
        return "word-template"
    return {
        "document": "document", "sheet": "drawing",
        "presentation": "presentation", "board": "portfolio",
        "correspondence": "stationery",
    }[template.family.value]


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class _Log:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []
        self.notes: list[str] = []

    def step(self, title: str, detail: str) -> None:
        self.entries.append((title, detail))
        print(f"  · {title:<22} {detail}")

    def note(self, text: str) -> None:
        self.notes.append(text)
        print(f"    ↳ {text}")


def _package_readme(brand, tokens, inv, audit, log) -> str:
    by_type = "\n".join(
        f"| {t} | {len(records)} |"
        for t, records in sorted(inv.by_type().items())
    )
    steps = "\n".join(f"{i}. **{t}** — {d}" for i, (t, d) in enumerate(log.entries, 1))
    return f"""# {brand.identity.name} — brand package

Generated by the ADOS Brand System from brand `{brand.version}`
(`{brand.content_hash[:12]}`), against ADOS {brand.ados_edition}.

**Nothing in this folder was authored by hand.** Every file is derived from
`brand/examples/studio_om.py` through the resolver. To change any of it,
change the brand and rebuild:

```
python -m brand.examples.build_studio_om
```

## Pipeline

{steps}

## Contents

| Type | Files |
|---|---|
{by_type}

`asset-inventory.json` records every file with its brand version.
`consistency-audit.json` is the result of auditing this folder against the
brand: {audit.summary()}

## Reading order

1. `brand/preview.html` — the identity on one page
2. `brand-guidelines/` — the eighteen sections
3. `logo/` — the mark, SVG masters and PNG rasters
4. `documents/` — every template, rendered
"""


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    out = Path(argv[0]) if argv else Path(__file__).resolve().parent / "studio-om"
    print(f"\n  Building the STUDIO OM brand package into {out}\n")
    if not browser_available():
        print("    ↳ no Chromium: PNG and PDF exports are skipped, HTML is complete\n")
    result = build(out)
    audit = result["audit"]
    print(
        f"\n  {result['assets']} assets · {result['tokens']} tokens · "
        f"audit {'clean' if audit.ok else 'has findings'}\n"
    )
    for finding in audit.report.sorted()[:12]:
        print(f"    [{finding.severity.value:5}] {finding.field}: {finding.message}")
    return 0 if audit.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

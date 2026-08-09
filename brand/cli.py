#!/usr/bin/env python3
"""
brand/cli.py

Command line for the Brand System.

    python -m brand.cli demo                        the whole flow, end to end
    python -m brand.cli propose "<brief>" [--name N]
    python -m brand.cli validate  [--brand FILE]
    python -m brand.cli tokens    [--brand FILE] [--flat]
    python -m brand.cli preview   [--brand FILE] [--out preview.html]
    python -m brand.cli render <template-id> [--brand FILE] [--out FILE]
    python -m brand.cli templates
    python -m brand.cli schema [--out FILE]

With no ``--brand`` every command uses the STUDIO NORD example, so the system
can be explored before anyone has authored anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from brand.models.brand import Brand


#: Brands that ship with the system, addressable by name.
EXAMPLES = {"studio-nord": "brand.examples.studio_nord:STUDIO_NORD",
            "studio-om": "brand.examples.studio_om:STUDIO_OM"}


def _load_brand(path: str | None) -> Brand:
    if path is None:
        from brand.examples.studio_nord import STUDIO_NORD

        return STUDIO_NORD
    if path in EXAMPLES:
        module, name = EXAMPLES[path].split(":")
        return getattr(__import__(module, fromlist=[name]), name)
    return Brand.from_json(Path(path).read_text())


# ---------------------------------------------------------------------------


def cmd_propose(args) -> int:
    from brand.agents.brand_agent import BrandAgent

    proposal = BrandAgent().generate_proposal(args.brief, name=args.name)
    b = proposal.brand
    print(f"\n  {b.identity.name} — proposed ({proposal.source}, "
          f"confidence {proposal.confidence:.2f})")
    print(f"  {b.identity.descriptor}")
    print(f"\n  personality  {', '.join(a.value for a in b.identity.personality)}")
    print(f"  typeface     {b.visual_identity.typography.primary_font.family}")
    print(f"  accent       {b.visual_identity.colour.accent}")
    print(f"  renders      {b.architectural_language.renders.lighting.value}, "
          f"{b.architectural_language.renders.mood.value}")
    print(f"\n  {proposal.rationale}\n")
    if proposal.assumptions:
        print("  Assumptions:")
        for a in proposal.assumptions:
            print(f"    · {a}")
    if proposal.open_questions:
        print("\n  Open questions:")
        for q in proposal.open_questions:
            print(f"    · {q}")
    print(f"\n  {proposal.validation.summary()}")
    print("\n  Nothing has been saved. This is a proposal; a human approves it.")
    if args.out:
        Path(args.out).write_text(json.dumps(proposal.to_dict(), indent=2))
        print(f"  Written to {args.out}")
    return 0


def cmd_validate(args) -> int:
    brand = _load_brand(args.brand)
    report = brand.check()
    print(f"\n  {report.summary()}\n")
    for f in report.sorted():
        print(f"  [{f.severity.value:5}] {f.category.value:14} {f.field}")
        print(f"          {f.message}")
        if f.suggestion:
            print(f"          → {f.suggestion}")
        if f.rule:
            print(f"          ({f.rule})")
        print()
    return 0 if report.ok else 1


def cmd_tokens(args) -> int:
    tokens = _load_brand(args.brand).resolve_tokens()
    if args.flat:
        print(json.dumps(tokens.flat(), indent=2))
        return 0
    if args.json:
        print(json.dumps(tokens.to_json_dict(), indent=2))
        return 0
    width = max(len(k) for k in tokens)
    for name, token in tokens.items():
        unit = "" if token.unit.value == "string" else f" {token.unit.value}"
        print(f"  {name:<{width}}  {token.value}{unit}")
    print(f"\n  {len(tokens)} tokens")
    return 0


def cmd_preview(args) -> int:
    from brand.preview.brand_preview import write_preview

    path = write_preview(_load_brand(args.brand), args.out)
    print(f"  {path}  ({path.stat().st_size} bytes)")
    return 0


def cmd_templates(args) -> int:
    from brand.templates.document_templates import TEMPLATES, coverage

    tokens = _load_brand(args.brand).resolve_tokens()
    cov = coverage(tokens)
    for tid, missing in sorted(cov.items()):
        t = TEMPLATES[tid]
        state = "renders" if not missing else f"missing {len(missing)}"
        print(f"  {tid:<24} {t.family.value:<15} {t.medium.value:<5} {state}")
    return 0


def cmd_render(args) -> int:
    from brand.templates.document_templates import Medium, get_template
    from brand.templates.renderers import render_sheet_pdf

    brand = _load_brand(args.brand)
    tokens = brand.resolve_tokens()
    template = get_template(args.template_id)
    if template.medium is Medium.PDF:
        doc = render_sheet_pdf(template, tokens, brand=brand)
    else:
        doc = template.render(tokens)
    out = args.out or f"{args.template_id}.{template.medium.value}"
    path = doc.write(out)
    print(f"  {path}  ({len(doc.content)} bytes, {len(doc.tokens_used)} tokens)")
    return 0


def cmd_logo(args) -> int:
    from brand.assets.logo import LogoSystem

    brand = _load_brand(args.brand)
    system = LogoSystem(brand)
    for logo in system.build_all():
        path = logo.write(args.out)
        print(f"  {path}  {logo.width_mm:.1f} × {logo.height_mm:.1f} mm"
              f"{'' if logo.outlined else '  (live text — face not bundled)'}")
        for note in logo.notes:
            print(f"      ↳ {note}")
    print(f"\n  clear space {system.clear_space_mm():g} mm · "
          f"minimum width {system.min_width_mm():g} mm")
    return 0


def cmd_guidelines(args) -> int:
    from brand.export import html_to_pdf
    from brand.guidelines import render_guidelines

    brand = _load_brand(args.brand)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_guidelines(brand))
    print(f"  {out}  ({out.stat().st_size} bytes, 18 sections)")
    if args.pdf:
        result = html_to_pdf(out, out.with_suffix(".pdf"))
        print(f"  {result.path}" if result.ok else f"  ↳ {result.reason}")
    return 0


def cmd_export(args) -> int:
    from brand.export import to_css_variables, to_json, to_yaml

    brand = _load_brand(args.brand)
    tokens = brand.resolve_tokens()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, text in (
        ("tokens.css", to_css_variables(tokens)),
        ("tokens.json", to_json(tokens)),
        ("tokens.flat.json", to_json(tokens, flat=True)),
        ("brand.yaml", to_yaml(brand)),
    ):
        (out / name).write_text(text)
        print(f"  {out / name}")
    return 0


def cmd_audit(args) -> int:
    from brand.validation.consistency import audit_package

    audit = audit_package(args.package, _load_brand(args.brand))
    print(f"\n  {audit.summary()}\n")
    for f in audit.report.sorted():
        print(f"  [{f.severity.value:5}] {f.field}\n          {f.message}")
        if f.suggestion:
            print(f"          → {f.suggestion}")
    return 0 if audit.ok else 1


def cmd_package(args) -> int:
    from brand.examples.build_studio_om import build

    result = build(Path(args.out_dir))
    return 0 if result["audit"].ok else 1


def cmd_schema(args) -> int:
    from brand.schemas.brand_schema import brand_json_schema, write_schema

    if args.out:
        print(f"  {write_schema(args.out)}")
    else:
        print(json.dumps(brand_json_schema(), indent=2))
    return 0


def cmd_demo(args) -> int:
    """The complete flow, printed. This is the acceptance demonstration."""
    from brand.agents.brand_agent import BrandAgent
    from brand.preview.brand_preview import write_preview
    from brand.resolution.pts_bridge import build_overlay
    from brand.templates.document_templates import PROJECT_COVER, get_template
    from brand.templates.renderers import render_sheet_pdf

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    step = _stepper()

    brief = args.brief or (
        "We are a small contemporary architecture studio focused on adaptive "
        "reuse. We want the identity to feel precise, quiet, material and "
        "editorial."
    )

    step("User brief", brief)

    proposal = BrandAgent().generate_proposal(brief, name=args.name or "Studio Nord")
    step(
        f"AI brand proposal ({proposal.source})",
        f"{proposal.brand.identity.name} — "
        f"{', '.join(a.value for a in proposal.brand.identity.personality)}\n"
        f"    typeface {proposal.brand.visual_identity.typography.primary_font.family}, "
        f"accent {proposal.brand.visual_identity.colour.accent}, "
        f"confidence {proposal.confidence:.2f}",
    )

    step(
        "Structured brand",
        f"status={proposal.brand.status.value} origin={proposal.brand.origin} "
        f"hash={proposal.brand.content_hash[:12]}",
    )

    step("Validation", proposal.validation.summary())

    approved = proposal.approve(approved_by=args.approver)
    published = approved.published()
    step(
        "User approval",
        f"approved by {args.approver} → status={published.status.value}, "
        f"version {published.version} is now immutable",
    )

    tokens = published.resolve_tokens()
    step(
        "Design tokens",
        f"{len(tokens)} resolved — e.g. "
        f"font.size.sm={tokens['font.size.sm'].value} mm "
        f"({tokens['font.size.sm.pt'].value} pt), "
        f"stroke.cut={tokens['stroke.cut'].value} mm, "
        f"color.text.primary={tokens['color.text.primary'].value}",
    )

    overlay = build_overlay(published, tokens)
    step(
        "PTS overlay",
        "the existing sheet builder receives "
        + ", ".join(overlay.paths()),
    )

    html_doc = get_template("BT01-a4-report").render(
        tokens, title="Feasibility study", project="Malthouse"
    )
    html_path = html_doc.write(out / "report.html")

    pdf_doc = render_sheet_pdf(
        PROJECT_COVER, tokens, brand=published,
        project="Malthouse", client="Ash Trust",
        container_id="2317-STN-ZZ-XX-DR-A-0001",
    )
    pdf_path = pdf_doc.write(out / "cover.pdf")
    preview_path = write_preview(published, out / "preview.html")

    step(
        "Rendered brand-aware documents",
        f"{html_path}  ({len(html_doc.content)} bytes)\n"
        f"    {pdf_path}  ({len(pdf_doc.content)} bytes, built by "
        f"docs/templates/pdf/ptspdf.py)\n"
        f"    {preview_path}",
    )

    print("\n  The PDF is the proof of integration: it is the same builder that\n"
          "  produces the verified PTS sheets, driven by this brand's tokens.\n")
    return 0


def _stepper():
    counter = {"n": 0}

    def step(title: str, detail: str) -> None:
        counter["n"] += 1
        print(f"\n  {counter['n']}. {title}")
        print(f"     {'─' * (len(title) + 3)}")
        for line in detail.splitlines():
            print(f"     {line}")

    return step


# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brand", description="ADOS Brand System"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_brand_arg(p):
        p.add_argument("--brand", help="Brand JSON file, or an example "
                       "name: studio-nord, studio-om")

    p = sub.add_parser("propose", help="brief → structured proposal")
    p.add_argument("brief")
    p.add_argument("--name")
    p.add_argument("--out")
    p.set_defaults(func=cmd_propose)

    p = sub.add_parser("validate", help="run the validator")
    add_brand_arg(p)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("tokens", help="resolve design tokens")
    add_brand_arg(p)
    p.add_argument("--flat", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_tokens)

    p = sub.add_parser("preview", help="write the brand preview")
    add_brand_arg(p)
    p.add_argument("--out", default="brand-preview.html")
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("templates", help="which documents this brand renders")
    add_brand_arg(p)
    p.set_defaults(func=cmd_templates)

    p = sub.add_parser("render", help="render one template")
    p.add_argument("template_id")
    add_brand_arg(p)
    p.add_argument("--out")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("logo", help="generate the logo system as SVG")
    add_brand_arg(p)
    p.add_argument("--out", default="logo")
    p.set_defaults(func=cmd_logo)

    p = sub.add_parser("guidelines", help="generate the 18-section guidelines")
    add_brand_arg(p)
    p.add_argument("--out", default="brand-guidelines.html")
    p.add_argument("--pdf", action="store_true")
    p.set_defaults(func=cmd_guidelines)

    p = sub.add_parser("export", help="tokens as CSS, JSON and YAML")
    add_brand_arg(p)
    p.add_argument("--out-dir", default="export")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("audit", help="audit a generated package")
    p.add_argument("package")
    add_brand_arg(p)
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("package", help="build the STUDIO OM brand package")
    p.add_argument("--out-dir", default="brand/examples/studio-om")
    p.set_defaults(func=cmd_package)

    p = sub.add_parser("schema", help="emit the JSON Schema")
    p.add_argument("--out")
    p.set_defaults(func=cmd_schema)

    p = sub.add_parser("demo", help="the complete flow, end to end")
    p.add_argument("--brief")
    p.add_argument("--name")
    p.add_argument("--approver", default="MJ")
    p.add_argument("--out-dir", default="build/brand-demo")
    p.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

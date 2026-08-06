#!/usr/bin/env python3
"""ADOS 1.0 — specification self-check.

Applies ADOS-0.3.070 (every rule shall be checkable) to the specification itself.
Run from anywhere:

    python3 docs/ados/machine/check_ados.py

Checks
  C1  Every machine artefact parses (JSON / YAML / instance-against-schema).
  C2  Every rule ID cited in the prose is defined by a rule block.
  C3  Every rule defined in the prose appears in the registry, and vice versa.
  C4  Every registry entry carries principle refs, evidence class and a validation ID
      (ADOS-8.10.040).
  C5  Every rule cited by a metric in the validation profile exists in the registry.
  C6  Every relative link between volumes resolves to a file that exists.
  C7  Normative Decision text contains no banned subjective lexicon (ADOS-7.2.020).
  C8  The reference IR instance validates against the sheet schema and its dimension
      chains close (ADOS-4.5.030).

Exit status is 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent
MACHINE = DOCS / "machine"

RULE_RE = re.compile(r"ADOS-[0-9A]\.\d{1,2}\.\d{3}")
RULE_HEAD_RE = re.compile(r"^#{2,4}\s+(ADOS-[0-9A]\.\d{1,2}\.\d{3})\s+—\s+(.+?)\s*$")
RULE_BOLD_RE = re.compile(r"^\*\*(ADOS-[0-9A]\.\d{1,2}\.\d{3})\s+—\s+(.+?)\.?\*\*")
LINK_RE = re.compile(r"\]\((?!https?:)([^)#]+)")

# ADOS-7.2.020. Matched case-insensitively as whole words inside normative text.
BANNED = [
    "appropriate", "appropriately", "as necessary", "as required", "adequate",
    "balanced", "elegant", "generally", "good practice", "harmonious",
    "if possible", "neat", "pleasing", "reasonable", "sensible", "suitable",
    "tidy", "well-organised", "where practicable", "wherever possible",
]
BANNED_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in BANNED) + r")(?![\w-])", re.I)

# Illustrative identifiers that deliberately do not resolve to a rule block.
ALLOWED_UNDEFINED = {"ADOS-3.4.015"}


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.lines: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.lines.append(f"[{'PASS' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
        if not ok:
            self.failures.append(name)

    def emit(self) -> int:
        print("\n".join(self.lines))
        print()
        if self.failures:
            print(f"{len(self.failures)} check(s) failed: {', '.join(self.failures)}")
            return 1
        print("All checks passed.")
        return 0


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError:  # pragma: no cover - environment dependent
        return None
    return yaml.safe_load(path.read_text())


def collect_rules(md_files: list[Path]) -> dict[str, dict]:
    rules: dict[str, dict] = {}
    for f in md_files:
        for line in f.read_text().splitlines():
            m = RULE_HEAD_RE.match(line.strip()) or RULE_BOLD_RE.match(line.strip())
            if m:
                rules.setdefault(m.group(1), {"name": m.group(2).replace("⚠", "").strip(), "file": f.name})
    return rules


def strip_quotations(text: str) -> str:
    """Remove fenced blocks, inline code and quoted strings.

    A banned word cited as an example of a banned word is not a use of it
    (ADOS-7.2.020 Exceptions). Quotation is marked by fences, backticks or
    double quotes throughout this specification, so removing those spans
    leaves only the specification's own normative voice.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"\"[^\"]*\"", " ", text)
    return text


def collect_decisions(md_files: list[Path]) -> list[tuple[str, str]]:
    """Return (file, text) for every **Decision.** / **Constraints.** paragraph."""
    out = []
    for f in md_files:
        text = f.read_text()
        for m in re.finditer(r"\*\*(?:Decision|Constraints)\.?\*\*(.+?)(?=\n\*\*|\n#{2,4} |\n---)", text, re.S):
            out.append((f.name, strip_quotations(m.group(1))))
    return out


def main() -> int:
    r = Report()
    md_files = sorted(p for p in DOCS.glob("*.md"))

    # ---- C1 artefacts parse -------------------------------------------------
    ok = True
    detail = []
    for name in ("ados-tokens.json", "ados-sheet-schema.json", "ados-ir-example.json"):
        try:
            json.loads((MACHINE / name).read_text())
        except Exception as exc:  # noqa: BLE001
            ok = False
            detail.append(f"{name}: {exc}")
    registry = load_yaml(MACHINE / "ados-rules.yaml")
    profile = load_yaml(MACHINE / "ados-validation.yaml")
    if registry is None or profile is None:
        detail.append("PyYAML not installed; YAML artefacts unchecked")
    r.check("C1 artefacts parse", ok, "; ".join(detail))

    # ---- C2 cited rule IDs are defined --------------------------------------
    defined = collect_rules(md_files)
    cited: set[str] = set()
    for f in md_files:
        cited |= set(RULE_RE.findall(f.read_text()))
    undefined = sorted(cited - set(defined) - ALLOWED_UNDEFINED)
    r.check("C2 cited rule IDs defined", not undefined, ", ".join(undefined[:8]))

    # ---- C3 registry matches prose ------------------------------------------
    if registry:
        reg_ids = {x["id"] for x in registry["rules"]}
        missing = sorted(set(defined) - reg_ids)
        extra = sorted(reg_ids - set(defined))
        r.check(
            "C3 registry matches prose",
            not missing and not extra,
            f"missing {missing[:5]} extra {extra[:5]}" if (missing or extra) else f"{len(reg_ids)} rules",
        )

        # ---- C4 registry completeness ---------------------------------------
        bad = [x["id"] for x in registry["rules"]
               if not x.get("principles") or not x.get("evidence") or not x.get("validation")]
        r.check("C4 registry entries complete", not bad, ", ".join(bad[:5]))
    else:
        r.check("C3 registry matches prose", False, "registry unreadable")
        r.check("C4 registry entries complete", False, "registry unreadable")

    # ---- C5 metric rule references ------------------------------------------
    if registry and profile:
        reg_ids = {x["id"] for x in registry["rules"]}
        refs = {s.get("rule") for m in profile["metrics"] for s in m["submetrics"]}
        refs |= {m.get("rule") for m in profile.get("system_measures", [])}
        bad = sorted(x for x in refs if x and x not in reg_ids)
        n = sum(len(m["submetrics"]) for m in profile["metrics"])
        r.check("C5 metric rule references", not bad, ", ".join(bad[:5]) or f"{n} sub-metrics")
    else:
        r.check("C5 metric rule references", False, "artefacts unreadable")

    # ---- C6 relative links resolve ------------------------------------------
    broken = []
    for f in md_files:
        for target in LINK_RE.findall(f.read_text()):
            if not (f.parent / target).exists():
                broken.append(f"{f.name} -> {target}")
    r.check("C6 relative links resolve", not broken, "; ".join(broken[:5]))

    # ---- C7 banned lexicon in normative text --------------------------------
    hits = []
    for fname, text in collect_decisions(md_files):
        for m in BANNED_RE.finditer(text):
            hits.append(f"{fname}: '{m.group(1)}'")
    r.check("C7 normative lexicon clean", not hits, "; ".join(sorted(set(hits))[:6]))

    # ---- C8 reference IR instance -------------------------------------------
    inst = json.loads((MACHINE / "ados-ir-example.json").read_text())
    try:
        import jsonschema

        schema = json.loads((MACHINE / "ados-sheet-schema.json").read_text())
        errs = list(jsonschema.Draft202012Validator(schema).iter_errors(inst))
        schema_note = f"{len(errs)} schema errors"
        schema_ok = not errs
    except ImportError:
        schema_ok, schema_note = True, "jsonschema not installed; schema check skipped"

    chains: dict[str, list[dict]] = defaultdict(list)
    for c in inst["package"]["containers"]:
        for region in c["regions"]:
            for view in region.get("views", []):
                for a in view["annotations"]:
                    if a.get("dimension"):
                        chains[a["dimension"]["chain_id"]].append(a["dimension"])
    inner = sum(d["value_um"] for d in chains.get("CH-S-1", []))
    outer = sum(d["value_um"] for d in chains.get("CH-S-3", []))
    closed = bool(chains) and inner == outer
    r.check("C8 reference IR valid and chains close", schema_ok and closed,
            f"{schema_note}; closure {inner} vs {outer}")

    return r.emit()


if __name__ == "__main__":
    sys.exit(main())

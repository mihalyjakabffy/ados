"""
brand/schemas/brand_schema.py

The JSON Schema for a brand, and validation of untrusted payloads against it.

The schema is *generated* from the pydantic models rather than written beside
them, because a hand-maintained schema is a second definition of the brand
that drifts from the first. ``docs/ados/machine/`` follows the same principle:
the rule registry is generated from the prose, not typed twice.

Two consumers:

* ``BrandAgent`` — an LLM response is JSON of unknown shape, and the schema is
  what turns it into either a brand or a clear rejection.
* The API — a POST body from a client is equally untrusted.

Pydantic already validates on construction; the schema exists because a caller
needs to know the shape *before* sending, and because a jsonschema error names
every fault at once, where pydantic stops at the first for nested unions.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from brand.models.brand import Brand

#: Bumped when the schema changes shape in a way a stored payload would notice.
SCHEMA_VERSION = "1.0.0"

SCHEMA_ID = (
    "https://ados.dev/schemas/brand/"
    f"{SCHEMA_VERSION}/brand.schema.json"
)


@lru_cache(maxsize=1)
def brand_json_schema() -> dict[str, Any]:
    """The JSON Schema for a complete :class:`Brand`."""
    schema = Brand.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = SCHEMA_ID
    schema["title"] = "ADOS Brand"
    schema["description"] = (
        "A practice's identity in machine-readable form. Generated from the "
        "pydantic models in brand/models — do not edit by hand."
    )
    return schema


@lru_cache(maxsize=1)
def proposal_json_schema() -> dict[str, Any]:
    """The looser schema a ``BrandAgent`` payload must satisfy.

    Deliberately not the full brand schema: an agent answers what the brief
    supports and the deterministic baseline fills the rest, so requiring a
    complete brand would reject useful partial answers. What it does enforce is
    that the fields present are the right *shape* — a hallucinated
    ``"colour": "warm greys"`` fails here rather than three layers down.
    """
    hex_pattern = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_ID.replace("brand.schema", "proposal.schema"),
        "title": "ADOS Brand Proposal",
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "identity": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 1, "maxLength": 120},
                    "descriptor": {"type": "string", "maxLength": 200},
                    "tagline": {"type": "string", "maxLength": 200},
                    "positioning": {"type": "string", "maxLength": 600},
                    "mission": {"type": "string", "maxLength": 600},
                    "vision": {"type": "string", "maxLength": 600},
                    "values": {"type": "array", "items": {"type": "string"}},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "personality": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 6,
                    },
                },
            },
            "typography": {
                "type": "object",
                "properties": {
                    "primary_font": {"type": ["object", "string"]},
                    "secondary_font": {"type": ["object", "string", "null"]},
                },
            },
            "colour": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    key: {"type": "string", "pattern": hex_pattern}
                    for key in (
                        "primary", "secondary", "accent", "background",
                        "surface", "text_primary", "text_secondary", "border",
                    )
                },
            },
            "architectural_language": {
                "type": "object",
                "properties": {
                    "drawing": {
                        "type": "object",
                        "properties": {
                            "lineweights": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "number", "exclusiveMinimum": 0,
                                },
                            }
                        },
                    },
                    "diagrams": {"type": "object"},
                    "renders": {"type": "object"},
                },
            },
            "communication": {"type": "object"},
            "rationale": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
    }


class SchemaValidationError(ValueError):
    """A payload does not satisfy the schema. Carries every fault, not the first."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(
            f"{len(errors)} schema violation(s): " + "; ".join(errors[:6])
            + (f" (+{len(errors) - 6} more)" if len(errors) > 6 else "")
        )


def validate_payload(payload: Any, *, schema: dict[str, Any] | None = None) -> None:
    """Raise :class:`SchemaValidationError` if ``payload`` does not conform.

    Degrades to a no-op when ``jsonschema`` is not installed, matching the way
    ``services/shacl_service.py`` treats ``pyshacl``: an optional validator that
    is absent must not take the pipeline down with it. Pydantic still catches
    everything structural at construction; what is lost is the multi-error
    report, and the caller is told so.
    """
    schema = schema or brand_json_schema()
    try:
        import jsonschema
    except ImportError:                                    # pragma: no cover
        import logging

        logging.getLogger(__name__).info(
            "jsonschema not installed — payload shape is checked at model "
            "construction only. pip install jsonschema for full reports."
        )
        return

    validator = jsonschema.Draft202012Validator(schema)
    errors = [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in validator.iter_errors(payload)
    ]
    if errors:
        raise SchemaValidationError(errors)


def write_schema(path: str | Path) -> Path:
    """Emit the schema next to the other ADOS machine artefacts."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(brand_json_schema(), indent=2) + "\n")
    return p

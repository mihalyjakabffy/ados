"""
brand/content/extract.py

One extractor: a ``DesignState`` (plus any precedents) becomes a
:class:`~brand.content.model.ContentModel`.

Everything this produces is a **fact the platform already holds** — an area
target, a code check, a budget delta, a material, a storey count — carried
across with its provenance intact. What it deliberately does *not* do is
invent prose. ``DesignState`` has no narrative field, and deriving one from
``semantic.style`` and ``semantic.mood`` would mean a client report containing
sentences nobody wrote. So the prose arrives as an argument, authored, and the
extractor's job is to place it against the facts rather than to compose it.

The same applies to images. As the architecture proposal records (§C.3), the
brand describes photography but no image is catalogued anywhere, so there is
nothing for an extractor to read. Until an image inventory exists, figures are
declared by the caller. That gap is real and naming it is more useful than
papering over it with a directory scan.

**Determinism.** Two runs over the same state must produce the same model,
including the same block ids, or nothing downstream can be reproducible. Every
mapping is iterated in sorted order and ids are assigned by
:func:`~brand.content.model.renumber` from the emission order alone.
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable, Sequence

from brand.content.model import (
    BlockRole,
    BlockType,
    ContentBlock,
    ContentModel,
    renumber,
)

#: An authored figure: everything the composer needs to place it and nothing
#: about how it should look.
Figure = dict[str, Any]

#: An authored paragraph: ``(role, text)``.
Passage = tuple[BlockRole, str]


def extract_content(
    state: Any,
    *,
    project_name: str,
    narrative: Sequence[Passage] = (),
    figures: Sequence[Figure] = (),
    precedents: Iterable[Any] = (),
    author: str = "",
) -> ContentModel:
    """Build a :class:`ContentModel` from a design state.

    ``state`` is a ``schemas.v2_models.DesignState`` — duck-typed rather than
    imported, so the Brand System keeps its one-way dependency on the platform
    and the extractor stays testable without SQLAlchemy.

    ``narrative`` and ``figures`` are the authored parts. ``precedents`` are
    ``PrecedentORM`` rows or anything with the same attributes.
    """
    origin = _origin(state)
    blocks: list[ContentBlock] = []

    blocks.extend(_narrative(narrative, author or _created_by(state)))
    blocks.extend(_semantic_facts(state, origin))
    blocks.extend(_geometry_facts(state, origin))
    blocks.extend(_constraint_metrics(state, origin))
    blocks.extend(_precedent_metrics(precedents))
    blocks.extend(_figures(figures))
    blocks.extend(_credits(state, author))

    return ContentModel(
        project_id=_uuid(getattr(state, "project_id", None)),
        project_name=project_name,
        source_state=_uuid(getattr(state, "design_state_id", None)),
        blocks=renumber(blocks),
    )


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def _origin(state: Any) -> str:
    """The provenance string every derived number carries.

    Prefers the content hash over the row id: the hash identifies *the content*
    a number came from, so the same figure extracted from a re-saved state
    reads as the same figure, which is the question a reader actually asks.
    """
    digest = getattr(state, "content_hash", None)
    if digest:
        return f"design_state {str(digest)[:8]}"
    ident = getattr(state, "design_state_id", None)
    return f"design_state {str(ident)[:8]}" if ident else "design_state"


def _created_by(state: Any) -> str:
    return str(getattr(state, "created_by", "") or "")


def _uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


# ---------------------------------------------------------------------------
# The authored parts
# ---------------------------------------------------------------------------


def _narrative(passages: Sequence[Passage], author: str) -> list[ContentBlock]:
    """Prose, in the order the author wrote it.

    Priority follows position within a role: the first paragraph of a role
    leads it, later ones support it. That is a convention, not an inference —
    an author who wants a different ranking authors a different order.
    """
    seen: dict[BlockRole, int] = {}
    out: list[ContentBlock] = []
    for role, text in passages:
        seen[role] = seen.get(role, 0) + 1
        out.append(
            ContentBlock(
                id="nar-01",                       # replaced by renumber()
                type=BlockType.NARRATIVE,
                role=role,
                priority=min(seen[role], 5),
                text=text.strip(),
                provenance=f"authored{f' · {author}' if author else ''}",
            )
        )
    return out


def _figures(figures: Sequence[Figure]) -> list[ContentBlock]:
    out: list[ContentBlock] = []
    for spec in figures:
        kind = BlockType(str(spec.get("type", "image")))
        out.append(
            ContentBlock(
                id="img-01",                       # replaced by renumber()
                type=kind,
                role=BlockRole(str(spec.get("role", "context"))),
                priority=int(spec.get("priority", 2)),
                path=str(spec["path"]),
                aspect=str(spec.get("aspect", "3:2")),
                caption=str(spec.get("caption", "")),
                sequence_position=str(spec.get("sequence_position", "")),
                provenance=str(spec.get("provenance", "authored")),
            )
        )
    return out


# ---------------------------------------------------------------------------
# The derived parts
# ---------------------------------------------------------------------------


def _semantic_facts(state: Any, origin: str) -> list[ContentBlock]:
    semantic = getattr(state, "semantic", None)
    if semantic is None:
        return []
    out: list[ContentBlock] = []
    for label, attr in (("Character", "style"), ("Atmosphere", "mood")):
        value = getattr(semantic, attr, None)
        if value:
            out.append(
                ContentBlock(
                    id="fct-01",
                    type=BlockType.FACT,
                    role=BlockRole.INTERVENTION,
                    priority=3,
                    label=label,
                    value=str(value),
                    provenance=f"{origin} · semantic.{attr}",
                )
            )
    materials = dict(getattr(semantic, "materials", {}) or {})
    for surface in sorted(materials):
        material = materials[surface]
        if not material:
            continue
        out.append(
            ContentBlock(
                id="fct-01",
                type=BlockType.FACT,
                role=BlockRole.DETAIL,
                priority=4,
                label=surface.replace("_", " ").capitalize(),
                value=str(material),
                provenance=f"{origin} · semantic.materials",
            )
        )
    return out


def _geometry_facts(state: Any, origin: str) -> list[ContentBlock]:
    geometry = getattr(state, "geometry", None)
    if geometry is None:
        return []
    out: list[ContentBlock] = []
    for label, attr in (("Storeys", "storey_count"), ("Spaces", "space_count")):
        value = getattr(geometry, attr, None)
        if value:
            out.append(
                ContentBlock(
                    id="fct-01",
                    type=BlockType.FACT,
                    role=BlockRole.CONTEXT,
                    priority=4,
                    label=label,
                    value=str(value),
                    provenance=f"{origin} · geometry.{attr}",
                )
            )
    return out


def _constraint_metrics(state: Any, origin: str) -> list[ContentBlock]:
    """Budget, area targets and code checks, as metrics with provenance.

    A constraint item carries a target and, once built or modelled, an
    achieved value. The *achieved* number is the one that belongs in a
    document — a target is an intention, and reporting an intention as an
    outcome is the oldest way to mislead with a true number. Where nothing has
    been achieved yet the target is reported and labelled as one.
    """
    constraints = getattr(state, "constraints", None)
    if constraints is None:
        return []
    out: list[ContentBlock] = []

    target = getattr(constraints, "budget_target", None)
    achieved = getattr(constraints, "budget_achieved", None)
    currency = str(getattr(constraints, "budget_currency", "") or "")
    if achieved is not None or target is not None:
        reported = achieved if achieved is not None else target
        out.append(
            ContentBlock(
                id="met-01",
                type=BlockType.METRIC,
                role=BlockRole.EVIDENCE,
                priority=2,
                label="Construction cost" if achieved is not None
                else "Construction cost (target)",
                value=float(reported),
                unit=currency,
                provenance=f"{origin} · constraints.budget",
            )
        )

    for group, role in (("area_targets", BlockRole.EVIDENCE),
                        ("code_checks", BlockRole.EVIDENCE)):
        items = list(getattr(constraints, group, []) or [])
        for item in sorted(items, key=lambda i: str(getattr(i, "name", ""))):
            item_achieved = getattr(item, "achieved", None)
            reported = item_achieved if item_achieved is not None else getattr(
                item, "target", None
            )
            if reported is None:
                continue
            name = str(getattr(item, "name", "")).replace("_", " ")
            out.append(
                ContentBlock(
                    id="met-01",
                    type=BlockType.METRIC,
                    role=role,
                    priority=3,
                    label=name[:1].upper() + name[1:] if name else "Constraint",
                    value=float(reported),
                    unit=str(getattr(item, "unit", "") or ""),
                    provenance=f"{origin} · constraints.{group}",
                )
            )
    return out


def _precedent_metrics(precedents: Iterable[Any]) -> list[ContentBlock]:
    """Closed-out deltas from comparable projects.

    Only the *deltas* travel. A precedent's absolute cost belongs to somebody
    else's project and putting it in this project's document invites a reader
    to compare two numbers that were never comparable; the planned-versus-
    actual delta is the transferable fact, which is why the precedent table
    stores it.
    """
    out: list[ContentBlock] = []
    rows = sorted(
        precedents,
        key=lambda p: (str(getattr(p, "solution_type", "")), str(getattr(p, "id", ""))),
    )
    for row in rows:
        label_base = str(getattr(row, "solution_type", "precedent")).replace("_", " ")
        origin = f"precedent {str(getattr(row, 'id', ''))[:8]}"
        for attr, label, unit in (
            ("cost_delta_pct", "cost against plan", "%"),
            ("carbon_delta_pct", "carbon against plan", "%"),
        ):
            value = getattr(row, attr, None)
            if value is None:
                continue
            out.append(
                ContentBlock(
                    id="met-01",
                    type=BlockType.METRIC,
                    role=BlockRole.EVIDENCE,
                    priority=3,
                    label=f"{label_base}: {label}",
                    value=float(value),
                    unit=unit,
                    provenance=origin,
                )
            )
    return out


def _credits(state: Any, author: str) -> list[ContentBlock]:
    who = author or _created_by(state)
    if not who:
        return []
    return [
        ContentBlock(
            id="crd-01",
            type=BlockType.CREDIT,
            role=BlockRole.PROVENANCE,
            priority=5,
            label="Prepared by",
            value=who,
            provenance=_origin(state),
        )
    ]

"""
brand/agents/brand_agent.py

BrandAgent — turns a natural-language brief into a structured brand proposal.

Subclasses ``services.agents.base_agent.BaseAgent``, so it inherits the
repository's LLM contract for free: lazy client, prompt-injection
sanitisation, tolerant JSON extraction, and a deterministic rule-based
fallback whenever the key is absent or the call fails. The pipeline degrades,
it does not break — which for a brand agent matters more than usual, because
the fallback path is the one CI runs.

**The agent never returns a Brand.** It returns a :class:`BrandProposal`: a
brand-shaped object plus the reasoning, the confidence, and the list of things
it guessed. Turning one into a brand is :meth:`BrandProposal.approve`, and only
a caller with a human behind it should call it. The flow is::

    brief ──► BrandAgent.generate_proposal()
                    │
                    ▼
              BrandProposal  (status = proposed, origin = agent)
                    │  schema validation + BrandValidator
                    ▼
              human reads the diff
                    │
                    ▼
            proposal.approve(approved_by=...)  ──► Brand (status = approved)

This is not ceremony. A brand is the source of truth for every document a
practice issues; a model that can silently rewrite it can silently rewrite the
letterhead on a contract.
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# The agent base lives in the repository root package `services`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.agents.base_agent import AgentError, BaseAgent  # noqa: E402

from brand.models.architectural_language import (  # noqa: E402
    ArchitecturalLanguage,
    DiagramLanguage,
    DiagramProjection,
    DiagramStyle,
    DrawingLanguage,
    LightingScenario,
    Lineweights,
    RenderLanguage,
    RenderMood,
)
from brand.models.brand import Brand, BrandStatus  # noqa: E402
from brand.models.communication import Communication, Person, Tone  # noqa: E402
from brand.models.identity import (  # noqa: E402
    Identity,
    PersonalityAxis,
    PracticeScale,
)
from brand.models.visual_identity import (  # noqa: E402
    ColourSystem,
    ColourTreatment,
    FontClass,
    FontFace,
    Grid,
    Imagery,
    RoleClass,
    Spacing,
    Typography,
    TypeRole,
    VisualIdentity,
)
from brand.validation.brand_validator import ValidationReport  # noqa: E402

logger = logging.getLogger(__name__)


class BrandProposalError(RuntimeError):
    """The agent produced something that is not a brand."""


@dataclass
class BrandProposal:
    """A brand the agent suggests, and everything a human needs to judge it."""

    brand: Brand
    brief: str
    rationale: str = ""
    confidence: float = 0.0
    assumptions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    source: str = "rules"                  # "llm" | "rules"
    validation: Optional[ValidationReport] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def approve(self, *, approved_by: str, changelog: str = "") -> Brand:
        """Accept the proposal. The one step a human must take.

        Refuses a proposal that does not validate: approving a brand the
        system already knows is broken produces documents that are broken in
        the same way, on every sheet, until someone notices.
        """
        if not approved_by.strip():
            raise BrandProposalError(
                "approve() needs the name of the person approving. A brand "
                "approved by nobody is a brand nobody owns."
            )
        report = self.validation or self.brand.check()
        if not report.ok:
            blocking = "; ".join(
                f"{f.field}: {f.message}"
                for f in report.findings
                if f.severity.value in ("BLOCK", "ERROR")
            )
            raise BrandProposalError(
                f"proposal does not validate and cannot be approved — {blocking}"
            )
        return self.brand.model_copy(
            update={
                "status": BrandStatus.APPROVED,
                "origin": "agent",
                "changelog": changelog
                or f"Proposed from brief; approved by {approved_by}.",
            }
        ).with_content_hash()

    def reject(self, *, reason: str) -> "BrandProposal":
        """Record a rejection. Kept so the next proposal can see it."""
        return BrandProposal(
            brand=self.brand,
            brief=self.brief,
            rationale=self.rationale,
            confidence=0.0,
            assumptions=self.assumptions,
            open_questions=[*self.open_questions, f"rejected: {reason}"],
            source=self.source,
            validation=self.validation,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief": self.brief,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "assumptions": self.assumptions,
            "open_questions": self.open_questions,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "brand": self.brand.model_dump(mode="json"),
            "validation": self.validation.to_dict() if self.validation else None,
        }


# ---------------------------------------------------------------------------
# Keyword → structured parameter tables for the deterministic path
#
# These are the agent's actual domain knowledge, and they are a table rather
# than a prompt so that the fallback is as opinionated as the LLM path and CI
# exercises real behaviour instead of a stub.
# ---------------------------------------------------------------------------

_PERSONALITY_CUES: dict[PersonalityAxis, tuple[str, ...]] = {
    PersonalityAxis.PRECISE: ("precise", "rigorous", "exact", "technical", "measured"),
    PersonalityAxis.QUIET: ("quiet", "calm", "restrained", "understated", "subtle"),
    PersonalityAxis.MATERIAL: ("material", "tactile", "texture", "timber", "concrete",
                               "brick", "stone"),
    PersonalityAxis.EDITORIAL: ("editorial", "publication", "essay", "narrative",
                                "written"),
    PersonalityAxis.WARM: ("warm", "human", "welcoming", "domestic"),
    PersonalityAxis.RIGOROUS: ("rigorous", "systematic", "disciplined"),
    PersonalityAxis.EXPERIMENTAL: ("experimental", "radical", "speculative",
                                   "research"),
    PersonalityAxis.CIVIC: ("civic", "public", "community", "municipal"),
    PersonalityAxis.CRAFT: ("craft", "handmade", "joinery", "artisan"),
    PersonalityAxis.PRAGMATIC: ("pragmatic", "practical", "buildable", "deliverable"),
    PersonalityAxis.MONUMENTAL: ("monumental", "civic scale", "imposing"),
    PersonalityAxis.PLAYFUL: ("playful", "joyful", "colourful", "bold"),
}

#: Personality axis → typographic direction. A neo-grotesk for precision, a
#: humanist for warmth, an editorial serif as the secondary wherever the
#: practice describes itself as writing.
_TYPE_DIRECTION: dict[PersonalityAxis, tuple[str, FontClass]] = {
    PersonalityAxis.PRECISE: ("Inter", FontClass.NEO_GROTESK),
    PersonalityAxis.RIGOROUS: ("Inter", FontClass.NEO_GROTESK),
    PersonalityAxis.QUIET: ("Inter", FontClass.NEO_GROTESK),
    PersonalityAxis.WARM: ("Source Sans 3", FontClass.HUMANIST),
    PersonalityAxis.CRAFT: ("Source Sans 3", FontClass.HUMANIST),
    PersonalityAxis.EXPERIMENTAL: ("Space Grotesk", FontClass.GROTESK),
    PersonalityAxis.PLAYFUL: ("Space Grotesk", FontClass.GROTESK),
    PersonalityAxis.CIVIC: ("Inter", FontClass.NEO_GROTESK),
    PersonalityAxis.MONUMENTAL: ("Inter", FontClass.NEO_GROTESK),
}

#: Personality axis → (accent, background). Deliberately low-chroma: an accent
#: is what the eye lands on once, and a saturated one on a technical sheet
#: competes with the drawing.
_PALETTE_DIRECTION: dict[PersonalityAxis, tuple[str, str]] = {
    PersonalityAxis.MATERIAL: ("#b8a88a", "#f4f2ed"),
    PersonalityAxis.QUIET: ("#8d9a94", "#f5f5f3"),
    PersonalityAxis.WARM: ("#c08552", "#faf6f0"),
    PersonalityAxis.CIVIC: ("#5b7a99", "#f4f5f6"),
    PersonalityAxis.CRAFT: ("#a3714a", "#f7f3ec"),
    PersonalityAxis.EXPERIMENTAL: ("#4a5bd4", "#f7f7f9"),
    PersonalityAxis.PLAYFUL: ("#d4623a", "#fbf8f4"),
    PersonalityAxis.PRECISE: ("#6b6f76", "#f6f6f5"),
}

_RENDER_DIRECTION: dict[PersonalityAxis, tuple[LightingScenario, RenderMood, float]] = {
    PersonalityAxis.MATERIAL: (LightingScenario.SOFT_DAYLIGHT,
                               RenderMood.MATERIAL_FOCUSED, 0.70),
    PersonalityAxis.QUIET: (LightingScenario.OVERCAST, RenderMood.MINIMAL, 0.55),
    PersonalityAxis.EDITORIAL: (LightingScenario.SOFT_DAYLIGHT,
                                RenderMood.EDITORIAL, 0.65),
    PersonalityAxis.WARM: (LightingScenario.GOLDEN_HOUR, RenderMood.ATMOSPHERIC, 0.90),
    PersonalityAxis.EXPERIMENTAL: (LightingScenario.STUDIO, RenderMood.MINIMAL, 0.50),
    PersonalityAxis.MONUMENTAL: (LightingScenario.DUSK, RenderMood.DRAMATIC, 0.60),
    PersonalityAxis.PRECISE: (LightingScenario.OVERCAST,
                              RenderMood.DOCUMENTARY, 0.65),
}

_SCALE_CUES: dict[PracticeScale, tuple[str, ...]] = {
    PracticeScale.SOLO: ("sole practitioner", "solo", "one-person"),
    PracticeScale.SMALL: ("small", "boutique", "studio of"),
    PracticeScale.MEDIUM: ("medium", "mid-size", "growing"),
    PracticeScale.LARGE: ("large", "international", "multi-office"),
}

#: Words a practice describing itself as precise or quiet should not use.
#: Shipped as a default so a brand arrives with a house style rather than an
#: empty list nobody fills in.
_DEFAULT_FORBIDDEN = (
    "bespoke", "iconic", "cutting-edge", "solution", "leverage", "synergy",
    "state-of-the-art", "unique",
)


class BrandAgent(BaseAgent):
    """Interprets briefs, proposes brands, and audits existing ones."""

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def _build_user_message(self, state: Any) -> str:
        brief = self._sanitize_intent(str(state.get("brief", "")))
        name = state.get("name") or "the practice"
        return (
            f"Practice name: {name}\n"
            f"Brief:\n{brief}\n\n"
            "Return one JSON object matching the schema in your instructions. "
            "No prose outside the JSON."
        )

    def _parse_llm_response(self, response_text: str, state: Any) -> "BrandProposal":
        payload = self._extract_json(response_text)
        return self._proposal_from_payload(
            payload, brief=state.get("brief", ""),
            name=state.get("name"), source="llm",
        )

    def _run_rules(self, state: Any) -> "BrandProposal":
        return self._propose_from_keywords(
            brief=state.get("brief", ""), name=state.get("name")
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_proposal(
        self, brief: str, *, name: str | None = None
    ) -> BrandProposal:
        """Propose a brand from a natural-language brief.

        Uses the LLM when one is configured and falls back to the keyword
        tables otherwise, exactly like every other agent in the repository.
        The result is validated before it is returned, so a caller always sees
        the findings alongside the proposal rather than discovering them at
        approval time.
        """
        if not brief or not brief.strip():
            raise BrandProposalError("a brand brief cannot be empty")
        proposal: BrandProposal = self.run({"brief": brief, "name": name})
        proposal.validation = proposal.brand.check()
        return proposal

    def audit(self, brand: Brand) -> ValidationReport:
        """Check an existing brand. Never modifies it.

        Deliberately just the validator: an agent that both judges and edits
        the source of truth is an agent that can talk itself into a change.
        """
        return brand.check()

    def suggest_improvements(self, brand: Brand) -> list[str]:
        """Human-readable next steps, derived from the validation report."""
        report = self.audit(brand)
        out = [
            f"{f.field}: {f.suggestion or f.message}"
            for f in report.sorted()
            if f.suggestion
        ]
        if brand.visual_identity.typography.secondary_font is None:
            out.append(
                "visual_identity.typography.secondary_font: a single family "
                "cannot separate a caption from body copy at the same size; a "
                "second face gives the caption a voice without a size change."
            )
        if not brand.architectural_language.materials.palette:
            out.append(
                "architectural_language.materials.palette: no materials "
                "declared, so drawings and renders share no vocabulary. This "
                "is the field that makes two projects look like one practice."
            )
        return out

    # ------------------------------------------------------------------
    # Structured-output path (LLM)
    # ------------------------------------------------------------------

    def _proposal_from_payload(
        self, payload: dict[str, Any], *, brief: str,
        name: str | None, source: str,
    ) -> BrandProposal:
        """Turn a raw JSON object into a validated proposal.

        Everything the model returns is coerced through the pydantic models,
        so a hallucinated field is rejected (``extra='forbid'``) and a
        hallucinated enum value fails rather than propagating. Where a value
        is missing, the deterministic path supplies it: a half-answer plus
        defaults is more useful than an exception, provided the gaps are
        listed in ``assumptions``.
        """
        if not isinstance(payload, dict):                  # pragma: no cover
            raise BrandProposalError("agent returned a non-object payload")

        assumptions: list[str] = list(payload.get("assumptions") or [])
        baseline = self._propose_from_keywords(brief=brief, name=name)

        try:
            brand = self._merge_payload(payload, baseline.brand, assumptions)
        except Exception as exc:                           # noqa: BLE001
            raise BrandProposalError(
                f"agent payload did not satisfy the brand schema: {exc}"
            ) from exc

        return BrandProposal(
            brand=brand,
            brief=brief,
            rationale=str(payload.get("rationale", ""))[:2000],
            confidence=_clamp(payload.get("confidence", 0.5)),
            assumptions=assumptions,
            open_questions=list(payload.get("open_questions") or []),
            source=source,
        )

    def _merge_payload(
        self, payload: dict[str, Any], baseline: Brand, assumptions: list[str]
    ) -> Brand:
        """Overlay the model's answers onto the deterministic baseline."""
        updates: dict[str, Any] = {}

        if ident := payload.get("identity"):
            merged = baseline.identity.model_dump()
            merged.update(_pick(ident, Identity.model_fields))
            merged["name"] = merged.get("name") or baseline.identity.name
            updates["identity"] = Identity.model_validate(merged)
        else:
            assumptions.append("identity taken from the brief's keywords")

        if colour := payload.get("colour"):
            merged = baseline.visual_identity.colour.model_dump()
            merged.update(_pick(colour, ColourSystem.model_fields))
            updates["visual_identity"] = baseline.visual_identity.model_copy(
                update={"colour": ColourSystem.model_validate(merged)}
            )

        if typo := payload.get("typography"):
            vi = updates.get("visual_identity", baseline.visual_identity)
            primary = typo.get("primary_font")
            face = (
                FontFace.model_validate(primary)
                if isinstance(primary, dict)
                else vi.typography.primary_font
                if not isinstance(primary, str)
                else FontFace(family=primary)
            )
            secondary = typo.get("secondary_font")
            sec_face = (
                FontFace.model_validate(secondary)
                if isinstance(secondary, dict)
                else FontFace(family=secondary,
                              classification=FontClass.EDITORIAL_SERIF)
                if isinstance(secondary, str)
                else vi.typography.secondary_font
            )
            updates["visual_identity"] = vi.model_copy(
                update={
                    "typography": vi.typography.model_copy(
                        update={"primary_font": face, "secondary_font": sec_face}
                    )
                }
            )
            if isinstance(primary, str):
                assumptions.append(
                    f"cap-height ratio for {face.family} defaulted; measure it "
                    f"from the font binary before publishing"
                )

        if arch := payload.get("architectural_language"):
            updates["architectural_language"] = self._merge_architectural(
                arch, baseline.architectural_language
            )

        if comms := payload.get("communication"):
            merged = baseline.communication.model_dump()
            merged.update(_pick(comms, Communication.model_fields))
            updates["communication"] = Communication.model_validate(merged)

        return baseline.model_copy(
            update={**updates, "origin": "agent", "status": BrandStatus.PROPOSED}
        ).with_content_hash()

    @staticmethod
    def _merge_architectural(
        payload: dict[str, Any], baseline: ArchitecturalLanguage
    ) -> ArchitecturalLanguage:
        updates: dict[str, Any] = {}
        if draw := payload.get("drawing"):
            lw = baseline.drawing.lineweights.model_dump()
            lw.update(_pick(draw.get("lineweights", {}), Lineweights.model_fields))
            updates["drawing"] = baseline.drawing.model_copy(
                update={
                    "lineweights": Lineweights.model_validate(lw),
                    **_pick(draw, DrawingLanguage.model_fields, exclude={"lineweights"}),
                }
            )
        if diag := payload.get("diagrams"):
            updates["diagrams"] = baseline.diagrams.model_copy(
                update=_pick(diag, DiagramLanguage.model_fields)
            )
        if rend := payload.get("renders"):
            updates["renders"] = baseline.renders.model_copy(
                update=_pick(rend, RenderLanguage.model_fields, exclude={"camera"})
            )
        return baseline.model_copy(update=updates)

    # ------------------------------------------------------------------
    # Deterministic path
    # ------------------------------------------------------------------

    def _propose_from_keywords(
        self, *, brief: str, name: str | None
    ) -> BrandProposal:
        text = (brief or "").lower()
        assumptions: list[str] = []

        axes = self._detect_personality(text)
        if not axes:
            axes = (PersonalityAxis.PRECISE, PersonalityAxis.QUIET)
            assumptions.append(
                "no personality cues found in the brief; defaulted to "
                "precise + quiet, which is the least-committal pair"
            )

        practice_name = name or self._detect_name(brief) or "Unnamed Practice"
        if practice_name == "Unnamed Practice":
            assumptions.append("no practice name in the brief")

        scale = self._detect_scale(text)
        family, classification = self._first_match(
            axes, _TYPE_DIRECTION, ("Inter", FontClass.NEO_GROTESK)
        )
        accent, background = self._first_match(
            axes, _PALETTE_DIRECTION, ("#6b6f76", "#f6f6f5")
        )
        lighting, mood, saturation = self._first_match(
            axes, _RENDER_DIRECTION,
            (LightingScenario.SOFT_DAYLIGHT, RenderMood.MATERIAL_FOCUSED, 0.7),
        )
        editorial = PersonalityAxis.EDITORIAL in axes

        primary = FontFace(family=family, classification=classification,
                           cap_height_ratio=0.7275, fallback="Arial",
                           weights=(400, 500, 600))
        secondary = (
            FontFace(family="Source Serif 4",
                     classification=FontClass.EDITORIAL_SERIF,
                     cap_height_ratio=0.670, fallback="Georgia",
                     weights=(400, 600))
            if editorial else None
        )
        mono = FontFace(family="IBM Plex Mono", classification=FontClass.MONO,
                        cap_height_ratio=0.698, fallback="Consolas",
                        weights=(400,))

        typography = Typography(
            primary_font=primary,
            secondary_font=secondary,
            mono_font=mono,
            heading_styles={
                "h1": TypeRole(step="t7", weight=500, uppercase=True,
                               tracking_percent=2.0),
                "h2": TypeRole(step="t5", weight=500, uppercase=True,
                               tracking_percent=2.0),
                "h3": TypeRole(step="t4", weight=500),
                "h4": TypeRole(step="t3", weight=500, uppercase=True,
                               tracking_percent=2.0),
            },
            body_styles={
                "body": TypeRole(step="t2"),
                "lead": TypeRole(step="t3", face="secondary" if editorial else "primary"),
                "caption": TypeRole(step="t1", role_class=RoleClass.TERTIARY,
                                    face="secondary" if editorial else "primary"),
                "legal": TypeRole(step="t1", role_class=RoleClass.TERTIARY),
            },
            numeric_styles={
                "identifier": TypeRole(step="t2", face="mono"),
                "dimension": TypeRole(step="t2"),
            },
            baseline_mm=5.0,
        )

        text_secondary = self._readable_secondary(background)
        colour = ColourSystem(
            primary="#111111",
            secondary=text_secondary,
            accent=accent,
            background=background,
            surface="#ffffff",
            text_primary="#111111",
            text_secondary=text_secondary,
            border="#d5d1c8",
        )

        visual = VisualIdentity(
            typography=typography,
            colour=colour,
            spacing=Spacing(base_unit_mm=5.0, scale=(1, 2, 4, 8), margin_mm=10.0),
            grid=Grid(columns=6, gutter_mm=10.0, margin_mm=20.0,
                      baseline_mm=5.0, module_mm=10.0),
            imagery=Imagery(
                colour_treatment=(
                    ColourTreatment.DESATURATED if saturation < 0.8
                    else ColourTreatment.NATURAL
                ),
                saturation=saturation,
                bleed=False,
            ),
        )

        architectural = ArchitecturalLanguage(
            drawing=DrawingLanguage(
                lineweights=Lineweights(),      # the ADOS tiers
                show_figures=PersonalityAxis.CIVIC in axes,
            ),
            diagrams=DiagramLanguage(
                style=DiagramStyle.EDITORIAL if editorial else DiagramStyle.MINIMAL,
                projection=DiagramProjection.AXONOMETRIC,
                palette=("#111111", accent),
                fill_tones=("T0", "T1", "T3"),
            ),
            renders=RenderLanguage(
                lighting=lighting, mood=mood,
                contrast=0.45 if PersonalityAxis.QUIET in axes else 0.6,
                saturation=saturation,
                material_expression=(
                    ("grain", "patina", "weathering")
                    if PersonalityAxis.MATERIAL in axes else ()
                ),
            ),
        )

        communication = Communication(
            tone=Tone.EDITORIAL if editorial else Tone.PRECISE,
            person=Person.FIRST_PLURAL,
            sentence_length_max=28,
            forbidden_words=_DEFAULT_FORBIDDEN,
        )

        brand = Brand(
            identity=Identity(
                name=practice_name,
                descriptor=self._descriptor(text),
                positioning=brief.strip()[:600],
                personality=axes,
                keywords=tuple(self._keywords(text)),
                practice_scale=scale,
            ),
            visual_identity=visual,
            architectural_language=architectural,
            communication=communication,
            status=BrandStatus.PROPOSED,
            origin="agent",
        ).with_content_hash()

        assumptions.append(
            "line weights defaulted to the ADOS tiers (0.70 / 0.35 / 0.18); a "
            "practice with a heavier hand should raise the cut weight"
        )
        return BrandProposal(
            brand=brand,
            brief=brief,
            rationale=self._rationale(axes, family, accent, mood),
            confidence=0.45 + 0.1 * min(len(axes), 4),
            assumptions=assumptions,
            open_questions=[
                "Is a typeface already licensed? Every point size is derived "
                "from its measured cap height.",
                "Is there an existing mark to carry forward, or is this a new "
                "identity?",
            ],
            source="rules",
        )

    # -- keyword helpers -------------------------------------------------

    @staticmethod
    def _detect_personality(text: str) -> tuple[PersonalityAxis, ...]:
        hits: list[tuple[int, PersonalityAxis]] = []
        for axis, cues in _PERSONALITY_CUES.items():
            score = sum(1 for cue in cues if cue in text)
            if score:
                hits.append((score, axis))
        hits.sort(key=lambda pair: (-pair[0], pair[1].value))
        return tuple(axis for _, axis in hits[:4])

    @staticmethod
    def _detect_scale(text: str) -> PracticeScale:
        for scale, cues in _SCALE_CUES.items():
            if any(cue in text for cue in cues):
                return scale
        return PracticeScale.SMALL

    @staticmethod
    def _detect_name(brief: str) -> Optional[str]:
        """Pull a practice name out of the brief if it is stated plainly."""
        for pattern in (
            r"(?:we are|this is|called|named)\s+([A-Z][\w&'’-]*(?:\s+[A-Z][\w&'’-]*){0,3})",
            r"^([A-Z][\w&'’-]*(?:\s+[A-Z][\w&'’-]*){0,3})\s+is\s+an?\s",
        ):
            m = re.search(pattern, brief)
            if m:
                candidate = m.group(1).strip()
                if candidate.lower() not in ("we", "a", "an", "the"):
                    return candidate
        return None

    @staticmethod
    def _descriptor(text: str) -> str:
        for cue, descriptor in (
            ("adaptive reuse", "Architecture and adaptive reuse"),
            ("retrofit", "Architecture and retrofit"),
            ("housing", "Housing architecture"),
            ("interior", "Architecture and interiors"),
            ("landscape", "Architecture and landscape"),
            ("heritage", "Architecture and heritage"),
            ("masterplan", "Architecture and masterplanning"),
        ):
            if cue in text:
                return descriptor
        return "Architecture"

    @staticmethod
    def _keywords(text: str) -> list[str]:
        vocabulary = (
            "adaptive reuse", "retrofit", "heritage", "housing", "timber",
            "concrete", "low carbon", "embodied carbon", "passive", "interiors",
            "masterplanning", "landscape", "public", "existing fabric",
        )
        return [w for w in vocabulary if w in text]

    @staticmethod
    def _first_match(axes, table: dict, default):
        for axis in axes:
            if axis in table:
                return table[axis]
        return default

    @staticmethod
    def _readable_secondary(background: str) -> str:
        """The darkest of a small ramp that clears the ADOS contrast floor.

        Picking the *darkest passing* value rather than the first one that
        passes keeps a margin: a secondary that scrapes the floor fails as
        soon as a practice lightens its paper.
        """
        from brand import ados
        from brand import colour as _c

        want = ados.text_contrast_ratio_min()
        for candidate in ("#5c5952", "#565349", "#4f4c45", "#4a4740",
                          "#454239", "#3c3a36"):
            if _c.contrast_ratio(candidate, background) >= want:
                return candidate
        return "#333333"

    @staticmethod
    def _rationale(axes, family: str, accent: str, mood: RenderMood) -> str:
        names = ", ".join(a.value for a in axes)
        return (
            f"The brief reads as {names}. A {family} sets the text because a "
            f"neutral face lets the drawing be the thing that is looked at, and "
            f"the accent {accent} is low-chroma for the same reason: on a "
            f"technical sheet a saturated accent competes with the linework. "
            f"Renders default to {mood.value.replace('_', ' ')}. Line weights "
            f"are the ADOS tiers, unchanged — the hierarchy is derived from "
            f"how far an element is from the cut plane, not from house style."
        )


def _pick(
    payload: dict[str, Any], fields: Any, exclude: set[str] | None = None
) -> dict[str, Any]:
    """Only the keys that are real fields. Silently drops hallucinated ones."""
    exclude = exclude or set()
    return {
        k: v for k, v in payload.items()
        if k in fields and k not in exclude and v is not None
    }


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return 0.5


_SYSTEM_PROMPT = """\
You are the Brand Agent of ADOS, an architectural documentation operating
system. You translate a practice's brief into a STRUCTURED brand definition.

You are not a graphic designer writing a mood board. Everything you return is
consumed by code: it drives document templates, drawing pen sets and render
parameters. Prose that is not in a designated prose field is discarded.

Hard constraints from the standard — a proposal that breaks one is rejected:

* Body text sits on a type-scale step of at least 2.5 mm cap height. Steps are
  t1=1.8 t2=2.5 t3=3.5 t4=5 t5=7 t6=10 t7=14 t8=20 mm. Only provenance and
  legal text may use t1.
* Line weights come from the ISO 128 series (0.13 0.18 0.25 0.35 0.5 0.7 1.0
  1.4 2.0 mm) and must decrease monotonically from cut to background. The cut
  is always the heaviest.
* Text contrast is at least 7:1 against its background.
* Two colours that mean different things differ by at least 18 in CIE L*.
* Drawings are monochrome. Colour is permitted only where it is redundant.
* All lengths are millimetres. Grid and spacing values are whole multiples of
  5 mm.

Return exactly one JSON object, no markdown fence, with this shape:

{
  "identity": {
    "name": str, "descriptor": str, "tagline": str, "positioning": str,
    "mission": str, "vision": str,
    "values": [str], "keywords": [str],
    "personality": [ one or more of: precise, quiet, material, editorial,
                     warm, rigorous, experimental, civic, craft, pragmatic,
                     monumental, playful ]
  },
  "typography": {
    "primary_font": {"family": str, "classification": str,
                     "cap_height_ratio": float, "fallback": str},
    "secondary_font": {...} or null
  },
  "colour": {
    "primary": "#rrggbb", "secondary": "#rrggbb", "accent": "#rrggbb",
    "background": "#rrggbb", "surface": "#rrggbb",
    "text_primary": "#rrggbb", "text_secondary": "#rrggbb", "border": "#rrggbb"
  },
  "architectural_language": {
    "drawing": {"lineweights": {"cut_mm": float, "primary_mm": float,
                                "secondary_mm": float, "background_mm": float,
                                "annotation_mm": float, "dimension_mm": float}},
    "diagrams": {"style": str, "projection": str, "stroke_mm": float},
    "renders": {"lighting": str, "mood": str, "contrast": float,
                "saturation": float}
  },
  "communication": {
    "tone": str, "person": str, "sentence_length_max": int,
    "forbidden_words": [str]
  },
  "rationale": str,
  "confidence": float between 0 and 1,
  "assumptions": [str],
  "open_questions": [str]
}

Put every judgement you could not ground in the brief into "assumptions", and
every thing you would have asked a human into "open_questions". A confident
guess recorded as a guess is useful; the same guess presented as a decision is
not.
"""

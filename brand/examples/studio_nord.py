"""
brand/examples/studio_nord.py

STUDIO NORD — the worked example.

A small contemporary practice working in adaptive reuse. It exists so that
every part of the system has something real to run against: the tests, the
preview, the document renderers and the end-to-end demonstration all use it,
and the ``BrandAgent``'s rule-based fallback is calibrated so that the brief

    "We are a small contemporary architecture studio focused on adaptive
     reuse. We want the identity to feel precise, quiet, material and
     editorial."

produces something close to it.

It is deliberately a *valid but not perfect* brand: it resolves cleanly and
publishes, and the validator still has a couple of things to say about it.
An example that reports zero findings teaches nothing about what the
validator is for.
"""

from __future__ import annotations

import uuid

from brand.models.architectural_language import (
    ArchitecturalLanguage,
    CameraLanguage,
    DiagramLanguage,
    DiagramProjection,
    DiagramStyle,
    DrawingLanguage,
    HatchDensity,
    LightingScenario,
    Lineweights,
    MaterialEntry,
    MaterialLanguage,
    RenderLanguage,
    RenderMood,
)
from brand.models.brand import Brand, BrandApplications, BrandStatus
from brand.models.communication import Communication, Person, Tone
from brand.models.identity import Identity, PersonalityAxis, PracticeScale
from brand.models.visual_identity import (
    ColourSystem,
    ColourTreatment,
    FontClass,
    FontFace,
    Grid,
    Imagery,
    Logo,
    LogoAsset,
    LogoUsageRules,
    RoleClass,
    Spacing,
    Typography,
    TypeRole,
    VisualIdentity,
)

#: Stable id so fixtures, snapshots and the preview all address the same brand.
STUDIO_NORD_ID = uuid.UUID("5747d10b-0000-4000-8000-000000000001")


def studio_nord(*, status: BrandStatus = BrandStatus.PUBLISHED) -> Brand:
    """Build the example brand."""
    identity = Identity(
        name="Studio Nord",
        descriptor="Architecture and adaptive reuse",
        tagline="What is already there",
        positioning=(
            "A small practice that works almost entirely with existing "
            "buildings, treating what stands as the primary material and the "
            "survey as the first design act."
        ),
        mission=(
            "To extend the useful life of buildings that would otherwise be "
            "demolished, and to make the case for doing so measurable."
        ),
        vision="Reuse as the default, not the exception.",
        values=("evidence", "restraint", "repair", "candour"),
        personality=(
            PersonalityAxis.PRECISE,
            PersonalityAxis.QUIET,
            PersonalityAxis.MATERIAL,
            PersonalityAxis.EDITORIAL,
        ),
        keywords=(
            "adaptive reuse", "retrofit", "existing fabric", "embodied carbon",
            "survey", "repair",
        ),
        practice_scale=PracticeScale.SMALL,
        founded=2014,
        locations=("Budapest",),
    )

    grotesk = FontFace(
        family="Inter",
        classification=FontClass.NEO_GROTESK,
        cap_height_ratio=0.7275,      # measured from Inter's OS/2.sCapHeight
        fallback="Arial",
        weights=(400, 500, 600),
    )
    serif = FontFace(
        family="Source Serif 4",
        classification=FontClass.EDITORIAL_SERIF,
        cap_height_ratio=0.670,
        fallback="Georgia",
        weights=(400, 600),
    )
    mono = FontFace(
        family="IBM Plex Mono",
        classification=FontClass.MONO,
        cap_height_ratio=0.698,
        fallback="Consolas",
        weights=(400,),
    )

    typography = Typography(
        primary_font=grotesk,
        secondary_font=serif,
        mono_font=mono,
        heading_styles={
            "h1": TypeRole(step="t7", face="primary", weight=500, uppercase=True,
                           tracking_percent=2.0),
            "h2": TypeRole(step="t5", face="primary", weight=500, uppercase=True,
                           tracking_percent=2.0),
            "h3": TypeRole(step="t4", face="primary", weight=500),
            "h4": TypeRole(step="t3", face="primary", weight=500, uppercase=True,
                           tracking_percent=2.0),
        },
        body_styles={
            "body": TypeRole(step="t2", face="primary", weight=400),
            "lead": TypeRole(step="t3", face="secondary", weight=400),
            "caption": TypeRole(step="t1", face="secondary", weight=400,
                                role_class=RoleClass.TERTIARY),
            "legal": TypeRole(step="t1", face="primary", weight=400,
                              role_class=RoleClass.TERTIARY),
        },
        numeric_styles={
            "identifier": TypeRole(step="t2", face="mono", weight=400),
            "dimension": TypeRole(step="t2", face="primary", weight=400),
        },
        baseline_mm=5.0,
        line_height_factor=1.42,
    )

    colour = ColourSystem(
        primary="#111111",
        secondary="#4f4c45",
        accent="#b8a88a",
        background="#f4f2ed",
        surface="#ffffff",
        text_primary="#111111",
        text_secondary="#4f4c45",
        border="#d5d1c8",
        neutral=("#ffffff", "#d3cfc7", "#a09c94", "#6b6862", "#3c3a36", "#1a1917"),
    )

    visual = VisualIdentity(
        logo=Logo(
            primary=LogoAsset(path="brand/examples/assets/studio-nord.svg",
                              format="svg", min_width_mm=24.0, aspect_ratio=4.2),
            wordmark_text="STUDIO NORD",
            usage_rules=LogoUsageRules(
                clear_space_factor=1.0,
                permitted_backgrounds=("T0", "T1"),
                monochrome_only=True,
            ),
        ),
        typography=typography,
        colour=colour,
        spacing=Spacing(base_unit_mm=5.0, scale=(1, 2, 4, 8), margin_mm=10.0),
        grid=Grid(columns=6, gutter_mm=10.0, margin_mm=20.0, baseline_mm=5.0,
                  module_mm=10.0),
        imagery=Imagery(
            photography=(
                "Existing fabric before intervention, in available light. "
                "No staging, no empty rooms."
            ),
            render_style=(
                "Soft daylight, low saturation, the existing structure legible "
                "through the new work."
            ),
            composition=("frontal", "one-point", "eye-level"),
            colour_treatment=ColourTreatment.DESATURATED,
            saturation=0.7,
            aspect_ratios=("3:2", "1:1"),
            bleed=False,
        ),
    )

    architectural = ArchitecturalLanguage(
        drawing=DrawingLanguage(
            lineweights=Lineweights(
                cut_mm=0.70,
                primary_mm=0.35,
                secondary_mm=0.25,
                background_mm=0.18,
                annotation_mm=0.18,
                dimension_mm=0.18,
            ),
            line_types=("L-CONT", "L-DASH", "L-DOT", "L-CENT"),
            hatch_density=HatchDensity.FINE,
            hatch_tokens=("H-CONC", "H-MSNR", "H-TIMB-S", "H-INSU-R", "H-METL"),
            annotation_uppercase=True,
            show_furniture=True,
            show_figures=False,
            notes=(
                "Existing fabric is drawn at full weight and new work is "
                "distinguished by phase encoding, not by a lighter line: the "
                "existing building is the subject."
            ),
        ),
        diagrams=DiagramLanguage(
            style=DiagramStyle.MINIMAL,
            projection=DiagramProjection.AXONOMETRIC,
            palette=("#111111", "#b8a88a"),
            stroke_mm=0.35,
            fill_tones=("T0", "T1", "T3"),
            label_step="t2",
        ),
        renders=RenderLanguage(
            lighting=LightingScenario.SOFT_DAYLIGHT,
            mood=RenderMood.MATERIAL_FOCUSED,
            contrast=0.45,
            saturation=0.7,
            camera=CameraLanguage(
                focal_length_mm=35.0, sensor_width_mm=36.0,
                height_m=1.6, two_point_perspective=True,
            ),
            material_expression=("grain", "patina", "board-mark", "weathering"),
            people=True,
            sky="high overcast",
        ),
        materials=MaterialLanguage(
            palette=(
                MaterialEntry(name="board-marked concrete", hatch_token="H-CONC",
                              tone="T3", render_keywords=("board-mark", "grey")),
                MaterialEntry(name="reclaimed brick", hatch_token="H-MSNR",
                              tone="T3", render_keywords=("patina", "lime mortar")),
                MaterialEntry(name="oiled oak", hatch_token="H-TIMB-S",
                              tone="T2", render_keywords=("grain", "warm")),
                MaterialEntry(name="blackened steel", hatch_token="H-METL",
                              tone="T4", render_keywords=("matte", "dark")),
            ),
        ),
    )

    communication = Communication(
        tone=Tone.PRECISE,
        person=Person.FIRST_PLURAL,
        writing_style=(
            "Short declarative sentences. State the fact, then the reason. "
            "No adjectives that cannot be measured."
        ),
        sentence_length_max=28,
        vocabulary=("existing", "fabric", "retain", "repair", "reuse", "survey"),
        forbidden_words=("bespoke", "iconic", "cutting-edge", "solution",
                         "leverage", "synergy"),
        terminology={
            "adaptive reuse": "refurbishment",
            "existing fabric": "the old building",
            "embodied carbon": "carbon footprint",
        },
        primary_language="en-GB",
        secondary_languages=("hu-HU",),
        date_format="YYYY-MM-DD",
    )

    return Brand(
        brand_id=STUDIO_NORD_ID,
        version="1.0.0",
        status=status,
        origin="manual",
        ados_edition="1.0",
        changelog="Initial identity.",
        identity=identity,
        visual_identity=visual,
        architectural_language=architectural,
        communication=communication,
        applications=BrandApplications(
            documents=True, presentations=True, drawings=True,
            portfolio=True, website=True, social=False,
        ),
    ).with_content_hash()


#: The example, published and ready to resolve.
STUDIO_NORD = studio_nord()

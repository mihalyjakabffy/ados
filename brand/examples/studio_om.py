"""
brand/examples/studio_om.py

STUDIO OM — a complete practice identity, defined as data.

This is the second worked example and the more demanding one: where
``studio_nord`` exercises the model, this exercises the whole chain — a full
logo system, per-format grids, a graphic language, photography and digital
direction, and eighteen sections of guidelines, all generated from what is
written here and nothing else.

The design decisions, and why
-----------------------------

**The name.** ``OM`` is read as a pair rather than as a word: **O** is the
opening and **M** is the mass. Architecture is the negotiation between the two
— what is cut away and what is left standing — and for a practice working
mostly in existing buildings that negotiation is the whole job. The mark is
therefore a square aperture, not a picture of a building.

**The palette.** Graphite ink on warm paper, with one accent taken from
oxidised metal. The accent is chosen so that its lightness lands on rung
``T3`` of the ADOS tone ladder: on a plotted drawing it reproduces as a
defined tone rather than as an indeterminate grey. The neutral ramp is snapped
to the same ladder for the same reason.

**The line weights.** A 1.00 mm cut, heavier than the ADOS default of 0.70.
This is the one place the practice deviates from the standard tiers and it is
deliberate: when the subject of a drawing is an existing building, the
existing fabric has to read as mass at a glance, and the cut is what carries
that. The weight is still on the ISO 128 series, and the hierarchy below it is
unchanged.

**The type.** One neo-grotesk for everything structural, an editorial serif
for long-form writing, a mono for identifiers. Three faces, each with a job;
a fourth would be decoration.

Everything below is read by the system. Nothing here is styling.
"""

from __future__ import annotations

import uuid

from brand.models.architectural_language import (
    AnnotationPosition,
    ArchitecturalLanguage,
    CameraLanguage,
    DiagramLanguage,
    DiagramProjection,
    DiagramStyle,
    DrawingLanguage,
    GraphicLayer,
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
from brand.models.digital import (
    DigitalDirection,
    MotionLevel,
    NavStyle,
    SocialDirection,
    WebDirection,
)
from brand.models.identity import Identity, PersonalityAxis, PracticeScale
from brand.models.visual_identity import (
    ColourSystem,
    ColourTreatment,
    CornerTreatment,
    FontClass,
    FontFace,
    GraphicLanguage,
    GraphicPrimitive,
    Grid,
    GridConfig,
    Imagery,
    Logo,
    LogoAsset,
    LogoConstruction,
    LogoUsageRules,
    RoleClass,
    SemanticColours,
    Spacing,
    Typography,
    TypeRole,
    VisualIdentity,
)

STUDIO_OM_ID = uuid.UUID("0m000000-0000-4000-8000-000000000002".replace("m", "a"))

#: The concept, carried on the brand so the guidelines are generated from it
#: rather than written twice.
OM_CONCEPT = (
    "OM is read as a pair, not as a word: O is the opening, M is the mass. "
    "Architecture is the negotiation between what is cut away and what is "
    "left standing, and in an existing building that negotiation is the whole "
    "job. The mark is a square aperture — a threshold seen in plan — "
    "constructed on the same module the sheets are set on. It is a fragment "
    "of a drawing rather than a picture of a building."
)


def studio_om(*, status: BrandStatus = BrandStatus.PUBLISHED) -> Brand:
    """Build the STUDIO OM brand."""

    # ---- Identity --------------------------------------------------------
    identity = Identity(
        name="STUDIO OM",
        descriptor="Architecture, interiors and adaptive reuse",
        tagline="Opening and mass",
        positioning=(
            "A practice that works from what is already standing. Every "
            "project begins with a survey rather than a sketch, and the "
            "existing building is treated as the primary material — measured, "
            "kept where it performs, and cut where it does not."
        ),
        mission=(
            "To make reuse the ordinary choice by showing, project by "
            "project, that an existing structure carries more value than the "
            "one that would replace it."
        ),
        vision=(
            "A practice whose drawings are read by builders without a phone "
            "call, and whose buildings are recognised without a signature."
        ),
        values=(
            "Survey before proposal",
            "Keep what performs",
            "Show the joint",
            "Measure the claim",
            "Detail once, well",
            "Answer plainly",
        ),
        # Four axes. The brief lists eight characteristics; the system caps a
        # personality at four because every downstream generator weights them
        # equally and a practice that is eight things is none of them. The
        # remaining four — contextual, experimental, minimal, human — are
        # carried as keywords and as values, where they inform without voting.
        personality=(
            PersonalityAxis.PRECISE,
            PersonalityAxis.QUIET,
            PersonalityAxis.MATERIAL,
            PersonalityAxis.RIGOROUS,
        ),
        keywords=(
            "adaptive reuse", "existing fabric", "interiors", "retrofit",
            "heritage", "housing", "public", "embodied carbon",
            "contextual", "experimental", "minimal", "human",
        ),
        practice_scale=PracticeScale.SMALL,
        founded=2016,
        locations=("Budapest", "Vienna"),
    )

    # ---- Typography ------------------------------------------------------
    grotesk = FontFace(
        family="Inter",
        classification=FontClass.NEO_GROTESK,
        cap_height_ratio=0.7275,        # measured from OS/2.sCapHeight
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
            "h1": TypeRole(step="t7", face="primary", weight=500,
                           uppercase=True, tracking_percent=3.0),
            "h2": TypeRole(step="t5", face="primary", weight=500,
                           uppercase=True, tracking_percent=3.0),
            "h3": TypeRole(step="t4", face="primary", weight=500),
            "h4": TypeRole(step="t3", face="primary", weight=500,
                           uppercase=True, tracking_percent=3.0),
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
            "index": TypeRole(step="t1", face="mono", weight=400,
                              role_class=RoleClass.TERTIARY),
        },
        baseline_mm=5.0,
        line_height_factor=1.45,
    )

    # ---- Colour ----------------------------------------------------------
    # The ramp is snapped to the ADOS tone ladder (L* 100/82/64/46/28/10) so
    # that a brand grey used as a fill reproduces as a defined tone instead of
    # landing between two rungs and printing as neither.
    colour = ColourSystem(
        primary="#1a1a18",          # graphite    L* 9.2  → T5
        secondary="#4d5149",        # slate       L* 32.7
        accent="#64726b",           # oxidised metal L* 46.7 → T3
        background="#f2f0eb",       # paper       L* 94.8
        surface="#fbfaf7",
        text_primary="#1a1a18",
        text_secondary="#4d5149",   # 7.1:1 on paper — clears the ADOS floor
        border="#d6d2c8",
        neutral=("#fffff9", "#cfccc3", "#9e9b92", "#706d64", "#454239", "#1e1b12"),
        semantic=SemanticColours(
            success="#3f5f4a", warning="#7a6320", error="#7e2f2c", info="#2f5570",
        ),
    )

    # ---- Logo ------------------------------------------------------------
    logo = Logo(
        primary=LogoAsset(path="logo/studio-om-primary.svg", format="svg",
                          min_width_mm=28.0),
        secondary=LogoAsset(path="logo/studio-om-secondary.svg", format="svg",
                            min_width_mm=22.0),
        symbol=LogoAsset(path="logo/studio-om-symbol.svg", format="svg",
                         min_width_mm=6.0),
        wordmark_text="STUDIO OM",
        monogram_text="OM",
        concept=OM_CONCEPT,
        construction=LogoConstruction(
            module_mm=5.0,
            cap_modules=2.0,            # 10 mm cap
            field_modules=6.0,          # 30 mm square field
            aperture_stroke_modules=0.6,  # 3 mm wall — an opening, not a block
            letter_gap_modules=1.0,
            tracking_percent=8.0,       # the wordmark is read once, as a shape
        ),
        usage_rules=LogoUsageRules(
            clear_space_factor=1.0,
            permitted_backgrounds=("T0", "T1"),
            monochrome_only=True,
        ),
        incorrect_uses=(
            "Do not rotate the aperture — it is a plan, and a plan has an up.",
            "Do not fill the aperture with an image.",
            "Do not outline, emboss, or add a shadow.",
            "Do not stretch, condense, or re-set the wordmark in another face.",
            "Do not place the mark on a tone darker than T1; use the reversed lockup.",
            "Do not reduce the primary lockup below 28 mm; use the compact mark.",
            "Do not recolour the mark in the accent.",
        ),
    )

    # ---- Grid ------------------------------------------------------------
    grid = Grid(
        columns=6, gutter_mm=10.0, margin_mm=20.0,
        baseline_mm=5.0, module_mm=10.0,
        configurations={
            "A4": GridConfig(columns=4, gutter_mm=5.0, margin_mm=20.0,
                             measure_mm=120.0),
            "A3": GridConfig(columns=6, gutter_mm=5.0, margin_mm=15.0,
                             measure_mm=125.0),
            "slide": GridConfig(columns=12, gutter_mm=5.0, margin_mm=15.0),
            "portfolio": GridConfig(columns=8, gutter_mm=5.0, margin_mm=15.0),
            "board": GridConfig(columns=6, gutter_mm=10.0, margin_mm=20.0),
        },
    )

    # ---- Graphic language ------------------------------------------------
    graphic = GraphicLanguage(
        corner=CornerTreatment.SQUARE,
        rule_tier="annotation",
        emphasis_rule_tier="secondary",
        frame_stroke_tier="annotation",
        image_frame=True,
        image_caption_position="below-left",
        separator_spacing_modules=2.0,
        primitives=(
            GraphicPrimitive(
                key="aperture", name="Aperture",
                description="The square opening. Frames an image, marks a "
                            "section opening, holds the monogram at small size.",
                stroke_tier="secondary", modules=6.0,
            ),
            GraphicPrimitive(
                key="rule", name="Section rule",
                description="Separates blocks. Full measure, never partial.",
                stroke_tier="annotation", modules=1.0,
            ),
            GraphicPrimitive(
                key="tick", name="Registration tick",
                description="A 5 mm tick at the head of a column, marking the "
                            "lattice. The one mark that shows the grid.",
                stroke_tier="annotation", modules=1.0,
            ),
            GraphicPrimitive(
                key="index", name="Index number",
                description="Two mono digits at the tertiary step, used for "
                            "sections, notes and slides alike.",
                stroke_tier="annotation", modules=1.0,
            ),
        ),
        notes=(
            "Corners are square everywhere. The aperture is the only shape "
            "the identity owns; everything else is a rule or a frame."
        ),
    )

    # ---- Photography -----------------------------------------------------
    imagery = Imagery(
        photography=(
            "Existing fabric before intervention, and the joint after it. "
            "Available light, no styling, no empty rooms. A building in use "
            "photographs as a building in use."
        ),
        render_style=(
            "Soft daylight, low saturation, the existing structure legible "
            "through the new work."
        ),
        composition=("frontal", "one-point", "eye-level"),
        colour_treatment=ColourTreatment.DESATURATED,
        saturation=0.62,
        aspect_ratios=("3:2", "4:5", "1:1"),
        perspective="frontal",
        verticals_corrected=True,
        human_presence="incidental",
        cropping="full-frame",
        sequencing=("context", "approach", "threshold", "interior", "joint",
                    "detail"),
        detail_ratio=0.33,
        bleed=False,
    )

    visual = VisualIdentity(
        logo=logo,
        typography=typography,
        colour=colour,
        spacing=Spacing(base_unit_mm=5.0, scale=(1, 2, 4, 8), margin_mm=10.0),
        grid=grid,
        imagery=imagery,
        graphic_language=graphic,
    )

    # ---- Architectural language -----------------------------------------
    architectural = ArchitecturalLanguage(
        drawing=DrawingLanguage(
            lineweights=Lineweights(
                cut_mm=1.00,        # heavier than the ADOS default, on purpose
                primary_mm=0.35,
                secondary_mm=0.25,
                background_mm=0.18,
                annotation_mm=0.18,
                dimension_mm=0.18,
            ),
            line_types=("L-CONT", "L-DASH", "L-DOT", "L-CENT"),
            hatch_density=HatchDensity.FINE,
            hatch_tokens=("H-CONC", "H-MSNR", "H-TIMB-S", "H-INSU-R",
                          "H-METL", "H-EART"),
            annotation_position=AnnotationPosition.LEADERED,
            annotation_uppercase=True,
            hierarchy=(
                GraphicLayer.CUT,
                GraphicLayer.PROJECTION,
                GraphicLayer.BACKGROUND,
                GraphicLayer.FURNITURE,
                GraphicLayer.LANDSCAPE,
                GraphicLayer.ANNOTATION,
                GraphicLayer.DIMENSION,
            ),
            show_furniture=True,
            show_figures=False,
            notes=(
                "The cut is 1.00 mm rather than the standard 0.70. When the "
                "subject is an existing building, the existing fabric must "
                "read as mass at a glance, and the cut is what carries it. "
                "New work is distinguished by phase encoding, never by a "
                "lighter line."
            ),
        ),
        diagrams=DiagramLanguage(
            style=DiagramStyle.MINIMAL,
            projection=DiagramProjection.AXONOMETRIC,
            palette=("#1a1a18", "#64726b"),
            stroke_mm=0.25,
            fill_tones=("T0", "T1", "T3"),
            label_step="t2",
            notes=(
                "One projection for the whole set. A concept diagram and a "
                "circulation diagram that differ in projection are read as "
                "being about different buildings."
            ),
        ),
        renders=RenderLanguage(
            lighting=LightingScenario.SOFT_DAYLIGHT,
            mood=RenderMood.MATERIAL_FOCUSED,
            contrast=0.40,
            saturation=0.62,
            camera=CameraLanguage(
                focal_length_mm=35.0, sensor_width_mm=36.0,
                height_m=1.6, two_point_perspective=True,
            ),
            material_expression=("grain", "patina", "board-mark", "weathering",
                                 "lime bloom"),
            people=True,
            sky="high overcast",
            notes=(
                "A render is a proposition about light and material, not a "
                "photograph of a finished building. It is never issued in a "
                "technical package."
            ),
        ),
        materials=MaterialLanguage(
            palette=(
                MaterialEntry(name="board-marked concrete", hatch_token="H-CONC",
                              tone="T3", render_keywords=("board-mark", "cool grey")),
                MaterialEntry(name="reclaimed brick", hatch_token="H-MSNR",
                              tone="T3", render_keywords=("patina", "lime mortar")),
                MaterialEntry(name="oiled oak", hatch_token="H-TIMB-S",
                              tone="T2", render_keywords=("grain", "warm")),
                MaterialEntry(name="oxidised steel", hatch_token="H-METL",
                              tone="T4", render_keywords=("matte", "verdigris")),
                MaterialEntry(name="lime plaster", hatch_token="",
                              tone="T1", render_keywords=("chalk", "soft")),
            ),
            notes=(
                "Five materials, repeated. A practice recognised by its "
                "material palette has one; a practice with thirty does not."
            ),
        ),
    )

    # ---- Communication ---------------------------------------------------
    communication = Communication(
        tone=Tone.PRECISE,
        person=Person.FIRST_PLURAL,
        writing_style=(
            "Short declarative sentences. State the fact, then the reason. "
            "No adjective that cannot be measured, and no claim that cannot "
            "be checked against the drawing."
        ),
        sentence_length_max=24,
        vocabulary=("existing", "fabric", "retain", "repair", "reuse",
                    "survey", "joint", "threshold", "opening", "mass"),
        forbidden_words=(
            "bespoke", "iconic", "cutting-edge", "innovative", "solution",
            "leverage", "synergy", "transforming", "state-of-the-art",
            "unique", "seamless", "curated",
        ),
        terminology={
            "adaptive reuse": "refurbishment",
            "existing fabric": "the old building",
            "embodied carbon": "carbon footprint",
            "survey": "site visit",
            "opening": "hole",
        },
        primary_language="en-GB",
        secondary_languages=("hu-HU", "de-AT"),
        date_format="YYYY-MM-DD",
    )

    # ---- Digital ---------------------------------------------------------
    digital = DigitalDirection(
        web=WebDirection(
            sections=("Hero", "Projects", "Studio", "Approach", "Contact"),
            nav=NavStyle.MINIMAL_TOP,
            hero="a single photograph of an existing building, full width, "
                 "no overlaid text",
            project_card="image, name, year, type — the caption is under the "
                         "image, not over it",
            grid_columns=12,
            max_content_width_px=1440,
            image_treatment="framed",
            motion=MotionLevel.FADE,
            transition_ms=160,
            hover="opacity to 0.65, no scale, no shadow",
            dark_mode=False,
            notes=(
                "Nothing travels. A studio whose drawings do not animate has "
                "already decided what it thinks about motion."
            ),
        ),
        social=SocialDirection(
            platforms=("instagram", "linkedin"),
            post_formats=("1:1", "4:5"),
            caption_max_words=50,
            watermark=False,
            grid_discipline=(
                "one project across three consecutive posts, in the declared "
                "image sequence"
            ),
            notes=(
                "The account is a portfolio, not a feed. A post that is not "
                "about a building is not posted."
            ),
        ),
    )

    return Brand(
        brand_id=STUDIO_OM_ID,
        version="1.0.0",
        status=status,
        origin="manual",
        ados_edition="1.0",
        changelog="Initial identity, generated through the ADOS Brand System.",
        identity=identity,
        visual_identity=visual,
        architectural_language=architectural,
        communication=communication,
        digital=digital,
        applications=BrandApplications(
            documents=True, presentations=True, drawings=True,
            portfolio=True, website=True, social=True,
        ),
    ).with_content_hash()


#: The published brand.
STUDIO_OM = studio_om()

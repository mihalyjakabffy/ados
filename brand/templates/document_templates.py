"""
brand/templates/document_templates.py

Brand-aware document templates.

A template here is **declarative**: it states which tokens it needs and how the
content is laid out, and it never contains a colour, a font name or a
millimetre value of its own. That is the whole point of the token layer —

    font   = brand.font.family.primary        not  "Helvetica"
    colour = brand.color.text.primary         not  "#000000"
    margin = brand.grid.margin                not  20

— because the alternative is a hundred documents each holding their own copy
of the practice's identity, and no way to change it.

Two consequences fall out of the declarative form:

* A template declares ``bindings``. Rendering with a brand that does not
  define one of them raises :class:`UndefinedTokenError` naming the token,
  rather than producing a document with a hole in it.
* A template can be *checked against a brand without rendering it*, which is
  what :meth:`DocumentTemplate.check_bindings` is for and what the API uses to
  tell a user which templates a draft brand can already produce.

The renderers live in ``renderers.py``. This module is the catalogue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Optional

from brand.models.tokens import TokenSet, UndefinedTokenError


class Family(str, Enum):
    """Which PTS family a template belongs to.

    The families differ in more than page size: a sheet is read pinned to a
    wall or spread on a table and carries a drawn title block; a document is
    read in the hand and carries a running header. A template that cannot say
    which it is has not been designed.
    """

    DOCUMENT = "document"      # A4 portrait, read in the hand
    SHEET = "sheet"            # A1/A3 landscape, drawn title block
    PRESENTATION = "presentation"
    BOARD = "board"            # A1, read at 1.5-3 m
    CORRESPONDENCE = "correspondence"


class Medium(str, Enum):
    HTML = "html"
    PDF = "pdf"
    TEXT = "text"


@dataclass(frozen=True)
class Section:
    """One block of a template's content model."""

    key: str
    heading: str = ""
    role: str = "body"          # a typography role name
    repeat: bool = False        # a table/list rather than a single block
    required: bool = True


@dataclass(frozen=True)
class RenderedDocument:
    """What a render returns."""

    template_id: str
    medium: Medium
    content: str | bytes
    brand_id: str
    brand_version: str
    tokens_used: tuple[str, ...] = ()

    @property
    def media_type(self) -> str:
        return {
            Medium.HTML: "text/html; charset=utf-8",
            Medium.PDF: "application/pdf",
            Medium.TEXT: "text/plain; charset=utf-8",
        }[self.medium]

    def write(self, path) -> Any:
        from pathlib import Path

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(self.content, bytes):
            p.write_bytes(self.content)
        else:
            p.write_text(self.content)
        return p


@dataclass(frozen=True)
class DocumentTemplate:
    """A brand-aware template."""

    template_id: str
    title: str
    family: Family
    page: str                       # "A4-portrait", "A1-landscape", …
    purpose: str
    sections: tuple[Section, ...] = ()
    bindings: tuple[str, ...] = ()
    medium: Medium = Medium.HTML
    renderer: Optional[Callable[..., RenderedDocument]] = field(
        default=None, repr=False, compare=False
    )

    # ------------------------------------------------------------------

    def check_bindings(self, tokens: TokenSet) -> list[str]:
        """Token names this template needs that the brand does not define.

        Empty means the template will render. Used by the API and the preview
        to say which documents a brand can already produce, which is more
        useful during authoring than a stack trace at render time.
        """
        return [name for name in self.bindings if name not in tokens]

    def render(self, tokens: TokenSet, **context: Any) -> RenderedDocument:
        missing = self.check_bindings(tokens)
        if missing:
            raise UndefinedTokenError(missing[0], sorted(tokens))
        renderer = self.renderer
        if renderer is None:
            from brand.templates.renderers import render_html

            renderer = render_html
        return renderer(self, tokens, **context)


# ---------------------------------------------------------------------------
# Shared binding groups
#
# Named rather than repeated so that adding a token to "everything that sets
# type" is one edit. A template's bindings are its contract; a contract that is
# copy-pasted twelve times is a contract that drifts.
# ---------------------------------------------------------------------------

_TYPE_BINDINGS = (
    "font.family.primary",
    "font.fallback.primary",
    "font.size.xs",
    "font.size.sm",
    "font.size.md",
    "font.size.lg",
    "font.weight.regular",
    "font.weight.medium",
    "line_height.body",
    "letter_spacing.uppercase",
)

_COLOUR_BINDINGS = (
    "color.background",
    "color.surface",
    "color.text.primary",
    "color.text.secondary",
    "color.border",
    "color.brand.accent",
)

_LAYOUT_BINDINGS = (
    "stroke.annotation",
    "grid.columns",
    "grid.gutter",
    "grid.margin",
    "grid.baseline",
    "space.1",
    "space.2",
    "space.3",
)

_IDENTITY_BINDINGS = (
    "meta.brand.name",
    "meta.brand.descriptor",
    "meta.brand.version",
    "asset.logo.wordmark",
)

_BASE = _TYPE_BINDINGS + _COLOUR_BINDINGS + _LAYOUT_BINDINGS + _IDENTITY_BINDINGS


def _t(*extra: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_BASE + extra))


# ---------------------------------------------------------------------------
# The catalogue
# ---------------------------------------------------------------------------

A4_REPORT = DocumentTemplate(
    template_id="BT01-a4-report",
    title="A4 Report",
    family=Family.DOCUMENT,
    page="A4-portrait",
    purpose=(
        "The default long-form document: feasibility studies, design and "
        "access statements, condition surveys."
    ),
    sections=(
        Section("title", "Title", role="h1"),
        Section("meta", "Project and issue", role="body"),
        Section("summary", "Summary", role="lead"),
        Section("body", "Body", role="body", repeat=True),
        Section("legal", "", role="legal", required=False),
    ),
    bindings=_t("font.size.xl", "voice.language", "voice.date_format"),
)

A3_TECHNICAL = DocumentTemplate(
    template_id="BT02-a3-technical",
    title="A3 Technical Document",
    family=Family.DOCUMENT,
    page="A3-landscape",
    purpose=(
        "Schedules and tabulated technical content that will not fit the A4 "
        "measure without becoming unreadable."
    ),
    sections=(
        Section("title", "Title", role="h2"),
        Section("table", "Schedule", role="body", repeat=True),
        Section("notes", "Notes", role="caption", required=False),
    ),
    bindings=_t("color.neutral.1"),
)

PRESENTATION = DocumentTemplate(
    template_id="BT03-presentation",
    title="Presentation",
    family=Family.PRESENTATION,
    page="16:9",
    purpose="Screen-projected slides for a client or a panel.",
    sections=(
        Section("cover", "Cover", role="h1"),
        Section("slide", "Slide", role="h3", repeat=True),
    ),
    bindings=_t("font.size.display", "render.mood"),
)

PORTFOLIO_PAGE = DocumentTemplate(
    template_id="BT04-portfolio-page",
    title="Portfolio Page",
    family=Family.BOARD,
    page="A3-landscape",
    purpose="One project, one spread. The practice's main sales artefact.",
    sections=(
        Section("project", "Project", role="h2"),
        Section("images", "Images", role="caption", repeat=True),
        Section("text", "Description", role="body"),
        Section("credits", "Credits", role="legal", required=False),
    ),
    bindings=_t("render.mood", "render.saturation", "diagram.style",
                "font.size.display"),
)

PROJECT_COVER = DocumentTemplate(
    template_id="BT05-project-cover",
    title="Project Cover",
    family=Family.SHEET,
    page="A1-landscape",
    purpose=(
        "The first sheet of an issued set: what the package is, who issued it, "
        "and whether it may be used."
    ),
    sections=(
        Section("project", "Project", role="h1"),
        Section("package", "Package", role="h2"),
        Section("consultants", "Consultants", role="body", repeat=True),
        Section("declarations", "Declarations", role="body", repeat=True),
        Section("legal", "", role="legal"),
    ),
    bindings=_t(
        "stroke.cut", "stroke.primary", "stroke.background",
        "letter_spacing.uppercase", "font.size.display",
        "asset.logo.wordmark", "meta.brand.tagline",
    ),
    medium=Medium.PDF,
)

MEETING_MINUTES = DocumentTemplate(
    template_id="BT06-meeting-minutes",
    title="Meeting Minutes",
    family=Family.DOCUMENT,
    page="A4-portrait",
    purpose=(
        "The record of what was decided and who owes what by when. Actions "
        "carry an owner and a date or they are not actions."
    ),
    sections=(
        Section("header", "Meeting", role="h3"),
        Section("attendees", "Attendees", role="body", repeat=True),
        Section("items", "Items", role="body", repeat=True),
        Section("actions", "Actions", role="body", repeat=True),
    ),
    bindings=_t("voice.date_format", "color.semantic.warning"),
)

PROJECT_REPORT = DocumentTemplate(
    template_id="BT07-project-report",
    title="Project Report",
    family=Family.DOCUMENT,
    page="A4-portrait",
    purpose="Periodic report to a client: progress, cost, risk, next period.",
    sections=(
        Section("header", "Report", role="h2"),
        Section("status", "Status", role="body"),
        Section("progress", "Progress", role="body", repeat=True),
        Section("risks", "Risks", role="body", repeat=True),
        Section("next", "Next period", role="body"),
    ),
    bindings=_t("color.semantic.success", "color.semantic.warning",
                "color.semantic.error"),
)

PROPOSAL = DocumentTemplate(
    template_id="BT08-proposal",
    title="Proposal",
    family=Family.DOCUMENT,
    page="A4-portrait",
    purpose="Fee proposal: scope, exclusions, stages, fee, terms.",
    sections=(
        Section("cover", "Cover", role="h1"),
        Section("understanding", "Our understanding", role="lead"),
        Section("scope", "Scope", role="body", repeat=True),
        Section("exclusions", "Exclusions", role="body", repeat=True),
        Section("fee", "Fee", role="body", repeat=True),
        Section("terms", "Terms", role="legal"),
    ),
    bindings=_t("meta.brand.tagline", "voice.tone", "font.size.xl"),
)

INVOICE = DocumentTemplate(
    template_id="BT09-invoice",
    title="Invoice",
    family=Family.DOCUMENT,
    page="A4-portrait",
    purpose="A demand for payment. Legibility of the numbers is the whole job.",
    sections=(
        Section("header", "Invoice", role="h3"),
        Section("parties", "From and to", role="body"),
        Section("lines", "Lines", role="body", repeat=True),
        Section("total", "Total", role="h3"),
        Section("payment", "Payment", role="legal"),
    ),
    bindings=_t("font.family.mono", "voice.date_format"),
)

EMAIL_SIGNATURE = DocumentTemplate(
    template_id="BT10-email-signature",
    title="Email Signature",
    family=Family.CORRESPONDENCE,
    page="inline",
    purpose=(
        "The most-issued artefact the practice has, and usually the only one "
        "nobody has designed."
    ),
    sections=(
        Section("name", "Name", role="body"),
        Section("practice", "Practice", role="body"),
        Section("contact", "Contact", role="caption"),
    ),
    bindings=(
        "font.family.primary", "font.fallback.primary", "font.size.sm",
        "font.size.xs", "color.text.primary", "color.text.secondary",
        "color.brand.accent", "meta.brand.name", "meta.brand.descriptor",
        "asset.logo.wordmark", "space.1", "letter_spacing.uppercase",
        "line_height.body", "font.weight.medium", "font.weight.regular",
    ),
)

#: Every template, by id.
TEMPLATES: dict[str, DocumentTemplate] = {
    t.template_id: t
    for t in (
        A4_REPORT,
        A3_TECHNICAL,
        PRESENTATION,
        PORTFOLIO_PAGE,
        PROJECT_COVER,
        MEETING_MINUTES,
        PROJECT_REPORT,
        PROPOSAL,
        INVOICE,
        EMAIL_SIGNATURE,
    )
}


def get_template(template_id: str) -> DocumentTemplate:
    try:
        return TEMPLATES[template_id]
    except KeyError:
        raise KeyError(
            f"unknown template {template_id!r}. Known: "
            + ", ".join(sorted(TEMPLATES))
        ) from None


def templates_for(family: Family) -> list[DocumentTemplate]:
    return [t for t in TEMPLATES.values() if t.family is family]


def coverage(tokens: TokenSet) -> dict[str, list[str]]:
    """Which templates a brand can render, and what is missing from the rest.

    ``{template_id: [missing token names]}`` — an empty list means it renders.
    """
    return {tid: t.check_bindings(tokens) for tid, t in TEMPLATES.items()}


def all_bound_tokens() -> set[str]:
    """Every token name any template depends on.

    The resolver is tested against this: a token the catalogue binds but the
    resolver never emits is a template that cannot render, and it is much
    cheaper to catch that in a unit test than in a document.
    """
    out: set[str] = set()
    for template in TEMPLATES.values():
        out.update(template.bindings)
    return out

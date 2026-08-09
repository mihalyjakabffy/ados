"""
brand/models/brand.py

The ``Brand`` aggregate — the source of truth.

Frozen, content-addressed and versioned, following ``schemas/v2_models.py``:
two brands with identical content *are* the same brand, and a published
version can never change under a document that was built against it.

The public surface is deliberately small::

    brand  = Brand.create(name="Studio Nord", ...)
    report = brand.validate()
    tokens = brand.resolve_tokens()
    doc    = brand.apply_to(template)
    v2     = brand.bump("minor", changelog="editorial serif for captions")
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from brand.models.architectural_language import ArchitecturalLanguage
from brand.models.communication import Communication
from brand.models.identity import Identity
from brand.models.visual_identity import (
    ColourSystem,
    FontFace,
    Typography,
    VisualIdentity,
)

if TYPE_CHECKING:                                          # pragma: no cover
    from brand.models.tokens import TokenSet
    from brand.templates.document_templates import DocumentTemplate
    from brand.validation.brand_validator import ValidationReport


class BrandStatus(str, Enum):
    """Lifecycle of a brand version.

    Mirrors the ADOS status vocabulary: a thing that has not been approved may
    not be used, and saying so is the status field's whole job.
    """

    DRAFT = "draft"
    PROPOSED = "proposed"       # produced by BrandAgent, awaiting a human
    APPROVED = "approved"
    PUBLISHED = "published"     # immutable; documents may reference it
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


#: Statuses a document may resolve tokens against.
USABLE_STATUSES = frozenset({BrandStatus.APPROVED, BrandStatus.PUBLISHED})


class BrandApplications(BaseModel):
    """Which surfaces this brand is declared for.

    A surface that is not listed is not forbidden; it is simply not yet
    designed, and the preview says so rather than implying coverage.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    documents: bool = True
    presentations: bool = True
    drawings: bool = True
    portfolio: bool = True
    website: bool = False
    social: bool = False


class Brand(BaseModel):
    """A practice's identity, whole and machine-readable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ---- Identity of the record ----------------------------------------
    brand_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version. Major = a downstream document changes "
        "shape; minor = a value changes; patch = metadata only.",
    )
    status: BrandStatus = Field(default=BrandStatus.DRAFT)
    parent_version: Optional[str] = Field(default=None)
    content_hash: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    changelog: str = Field(default="", max_length=1000)

    # ---- Provenance ------------------------------------------------------
    ados_edition: str = Field(
        default="1.0",
        description="The edition of the standard this brand was validated "
        "against. A brand is only conformant relative to an edition.",
    )
    origin: str = Field(
        default="manual",
        pattern=r"^(manual|agent|imported)$",
        description="How the brand was authored. 'agent' never means "
        "'approved' — that is what status is for.",
    )

    # ---- The brand itself ------------------------------------------------
    identity: Identity
    visual_identity: VisualIdentity
    architectural_language: ArchitecturalLanguage = Field(
        default_factory=ArchitecturalLanguage
    )
    communication: Communication = Field(default_factory=Communication)
    applications: BrandApplications = Field(default_factory=BrandApplications)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        name: str,
        primary_font: str | FontFace = "Inter",
        colour: ColourSystem | None = None,
        identity: Identity | None = None,
        visual_identity: VisualIdentity | None = None,
        **kwargs: Any,
    ) -> "Brand":
        """Build a brand from the minimum a practice actually has on day one.

        Everything not supplied takes the ADOS-conformant default, so a brand
        created with only a name and a typeface is valid and renders — which
        matters, because a system that demands forty fields before it produces
        anything is a system nobody finishes filling in.
        """
        if visual_identity is None:
            face = (
                primary_font
                if isinstance(primary_font, FontFace)
                else FontFace(family=primary_font)
            )
            visual_identity = VisualIdentity(
                typography=Typography(primary_font=face),
                colour=colour or ColourSystem(),
            )
        elif colour is not None:
            visual_identity = visual_identity.model_copy(update={"colour": colour})

        brand = cls(
            identity=identity or Identity(name=name),
            visual_identity=visual_identity,
            **kwargs,
        )
        return brand.with_content_hash()

    # ------------------------------------------------------------------
    # Content addressing
    # ------------------------------------------------------------------

    def _canonical_payload(self) -> dict[str, Any]:
        """The parts that define the brand, excluding record metadata.

        ``brand_id``, ``status``, timestamps and the changelog are *about* the
        record, not part of it — a brand re-approved on a later date is the
        same brand.
        """
        payload = self.model_dump(
            mode="json",
            exclude={
                "brand_id",
                "version",
                "status",
                "parent_version",
                "content_hash",
                "created_at",
                "changelog",
                "origin",
            },
        )
        return payload

    def compute_content_hash(self) -> str:
        canonical = json.dumps(
            self._canonical_payload(), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def with_content_hash(self) -> "Brand":
        return self.model_copy(update={"content_hash": self.compute_content_hash()})

    def is_equivalent_to(self, other: "Brand") -> bool:
        """True when two brands differ only in record metadata."""
        return self.compute_content_hash() == other.compute_content_hash()

    # ------------------------------------------------------------------
    # The three verbs
    # ------------------------------------------------------------------

    def validate_brand(self) -> "ValidationReport":
        """Check the brand for structural, design and architectural faults.

        Named ``validate_brand`` because pydantic v2 reserves ``validate`` on
        the model class; :meth:`check` is the short alias used in the docs.
        """
        from brand.validation.brand_validator import BrandValidator

        return BrandValidator().validate(self)

    #: Short alias. ``brand.check()`` reads better at a call site.
    check = validate_brand

    def resolve_tokens(self, **overrides: Any) -> "TokenSet":
        """Resolve to design tokens — the only thing downstream consumers see."""
        from brand.resolution.brand_resolver import BrandResolver

        return BrandResolver().resolve(self, **overrides)

    def apply_to(self, template: "DocumentTemplate", **context: Any):
        """Bind this brand's tokens into a document template."""
        return template.render(tokens=self.resolve_tokens(), **context)

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    def bump(self, level: str = "minor", *, changelog: str = "") -> "Brand":
        """A new draft version descended from this one."""
        from brand.versioning.brand_version import bump_version

        return self.model_copy(
            update={
                "version": bump_version(self.version, level),
                "parent_version": self.version,
                "status": BrandStatus.DRAFT,
                "changelog": changelog,
                "created_at": datetime.now(timezone.utc),
                "content_hash": None,
            }
        ).with_content_hash()

    def approved(self, *, changelog: str = "") -> "Brand":
        """Mark approved. The one transition a human must make explicitly."""
        return self.model_copy(
            update={
                "status": BrandStatus.APPROVED,
                "changelog": changelog or self.changelog,
            }
        )

    def published(self) -> "Brand":
        """Publish: from here the version is immutable and citable."""
        if self.status not in (BrandStatus.APPROVED, BrandStatus.PUBLISHED):
            raise ValueError(
                f"cannot publish a brand with status {self.status.value!r}; "
                "approve it first — publishing is what documents cite, and an "
                "unapproved citation is worse than none"
            )
        return self.model_copy(update={"status": BrandStatus.PUBLISHED})

    @property
    def is_usable(self) -> bool:
        """True when a document may resolve tokens against this version."""
        return self.status in USABLE_STATUSES

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=indent, sort_keys=False)

    @classmethod
    def from_json(cls, text: str | bytes) -> "Brand":
        return cls.model_validate(json.loads(text))

    @property
    def label(self) -> str:
        """``Studio Nord 1.0.0 (published)`` — for logs and preview headers."""
        return f"{self.identity.name} {self.version} ({self.status.value})"

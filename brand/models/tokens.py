"""
brand/models/tokens.py

The design-token layer: the only thing downstream consumers are allowed to see.

A token is a flat, dotted, namespaced name bound to a value with a unit and a
provenance. Provenance is the field that makes the system debuggable: when a
document comes out wrong, ``tokens['color.text.primary'].source`` says which
brand field produced it, and ``.constraint`` says which ADOS rule (if any)
bounded it.

Naming is fixed by :data:`TOKEN_NAMESPACES`. A resolver that emits a name
outside them fails the token contract test, which is what stops the namespace
from drifting into eleven near-synonyms the way an unpoliced one does.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Iterator, Mapping

from pydantic import BaseModel, ConfigDict, Field

_Frozen = ConfigDict(frozen=True, extra="forbid")


class Unit(str, Enum):
    MM = "mm"
    PT = "pt"
    HEX = "hex"
    RATIO = "ratio"
    COUNT = "count"
    PERCENT = "percent"
    STRING = "string"
    L_STAR = "L*"


#: The permitted top-level token namespaces. Adding one is a deliberate act.
TOKEN_NAMESPACES: tuple[str, ...] = (
    "font",
    "line_height",
    "letter_spacing",
    "color",
    "space",
    "grid",
    "stroke",
    "tone",
    "radius",
    "shadow",
    "opacity",
    "render",
    "diagram",
    "voice",
    "asset",
    "meta",
)


#: Sentinel distinguishing "no default given" from ``default=None``.
_MISSING: Any = object()


class Token(BaseModel):
    """One resolved value."""

    model_config = _Frozen

    name: str = Field(min_length=1)
    value: Any
    unit: Unit = Field(default=Unit.STRING)
    source: str = Field(
        default="",
        description="Dotted path of the brand field this came from.",
    )
    constraint: str = Field(
        default="",
        description="The ADOS rule that bounded it, where one did.",
    )

    def __str__(self) -> str:                              # pragma: no cover
        return f"{self.name}={self.value}{'' if self.unit is Unit.STRING else ' ' + self.unit.value}"


class TokenSet(Mapping[str, Token]):
    """An immutable, ordered mapping of token name → :class:`Token`.

    Implements ``Mapping`` so a template can treat it as a dict, but
    ``__getitem__`` raises :class:`UndefinedTokenError` rather than ``KeyError``
    so that a template binding to a token nobody defined names itself in the
    traceback instead of surfacing as a bare key error three frames away.
    """

    __slots__ = ("_tokens", "_brand_id", "_brand_version")

    def __init__(
        self,
        tokens: Mapping[str, Token] | None = None,
        *,
        brand_id: str = "",
        brand_version: str = "",
    ) -> None:
        self._tokens: dict[str, Token] = dict(tokens or {})
        self._brand_id = brand_id
        self._brand_version = brand_version

    # -- Mapping protocol -------------------------------------------------
    def __getitem__(self, key: str) -> Token:
        try:
            return self._tokens[key]
        except KeyError:
            raise UndefinedTokenError(key, sorted(self._tokens)) from None

    def __iter__(self) -> Iterator[str]:
        return iter(self._tokens)

    def __len__(self) -> int:
        return len(self._tokens)

    def __repr__(self) -> str:                             # pragma: no cover
        return f"<TokenSet {len(self._tokens)} tokens brand={self._brand_id}@{self._brand_version}>"

    # -- Accessors --------------------------------------------------------
    @property
    def brand_id(self) -> str:
        return self._brand_id

    @property
    def brand_version(self) -> str:
        return self._brand_version

    def value(self, key: str, default: Any = _MISSING) -> Any:
        """The bare value. Raises for an undefined token unless a default is given."""
        if key not in self._tokens and default is not _MISSING:
            return default
        return self[key].value

    def flat(self) -> dict[str, Any]:
        """``{name: value}`` — what a template engine consumes."""
        return {k: t.value for k, t in self._tokens.items()}

    def namespace(self, prefix: str) -> dict[str, Token]:
        """Every token under ``prefix`` (``'color'`` → all colour tokens)."""
        p = prefix if prefix.endswith(".") else prefix + "."
        return {k: v for k, v in self._tokens.items() if k.startswith(p)}

    def to_json_dict(self) -> dict[str, Any]:
        """Serialisation that keeps unit and provenance."""
        return {
            "brand_id": self._brand_id,
            "brand_version": self._brand_version,
            "tokens": {
                k: {
                    "value": t.value,
                    "unit": t.unit.value,
                    "source": t.source,
                    "constraint": t.constraint,
                }
                for k, t in self._tokens.items()
            },
        }

    def merged_with(self, other: "TokenSet") -> "TokenSet":
        """This set overridden by ``other``. Used for per-project overlays."""
        merged = dict(self._tokens)
        merged.update(other._tokens)
        return TokenSet(
            merged,
            brand_id=other._brand_id or self._brand_id,
            brand_version=other._brand_version or self._brand_version,
        )


class UndefinedTokenError(KeyError):
    """A consumer asked for a token the brand does not define."""

    def __init__(self, key: str, available: list[str]) -> None:
        near = [a for a in available if a.split(".")[0] == key.split(".")[0]]
        hint = f" Tokens in that namespace: {', '.join(near[:8])}." if near else ""
        super().__init__(
            f"undefined brand token {key!r}. A template must bind only to tokens "
            f"the brand defines.{hint}"
        )
        self.key = key
        self.available = available


class TokenBuilder:
    """Accumulates tokens with their provenance while a resolver runs."""

    def __init__(self) -> None:
        self._tokens: dict[str, Token] = {}

    def add(
        self,
        name: str,
        value: Any,
        unit: Unit = Unit.STRING,
        *,
        source: str = "",
        constraint: str = "",
    ) -> "TokenBuilder":
        root = name.split(".", 1)[0]
        if root not in TOKEN_NAMESPACES:
            raise ValueError(
                f"token {name!r} is outside the declared namespaces "
                f"({', '.join(TOKEN_NAMESPACES)}). Add the namespace "
                f"deliberately in brand/models/tokens.py, or rename the token."
            )
        if name in self._tokens:
            raise ValueError(
                f"duplicate token {name!r}: {self._tokens[name].source} and "
                f"{source} both define it"
            )
        self._tokens[name] = Token(
            name=name, value=value, unit=unit, source=source, constraint=constraint
        )
        return self

    def build(self, *, brand_id: str, brand_version: str) -> TokenSet:
        return TokenSet(
            dict(sorted(self._tokens.items())),
            brand_id=brand_id,
            brand_version=brand_version,
        )

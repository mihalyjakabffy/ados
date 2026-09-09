"""
Versioning and the store.

The invariant under test throughout: **a published version is immutable**. A
drawing issued in 2024 was drawn against the brand as it stood in 2024, and
reprinting it against a later brand produces a document that is not the one
that was issued. Every test here is a way that could go wrong.
"""

from __future__ import annotations

import pytest

from brand.models.brand import Brand, BrandStatus
from brand.store.brand_repo import BrandNotFound, FileBrandRepository
from brand.versioning.brand_version import (
    BrandVersionHistory,
    VersionError,
    bump_version,
    compare_versions,
    is_compatible,
    parse_version,
)


# ---------------------------------------------------------------------------
# Version arithmetic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "start,level,expected",
    [
        ("1.0.0", "patch", "1.0.1"),
        ("1.0.5", "minor", "1.1.0"),
        ("1.4.2", "major", "2.0.0"),
    ],
)
def test_bump(start, level, expected):
    assert bump_version(start, level) == expected


def test_bump_rejects_an_unknown_level():
    with pytest.raises(VersionError, match="unknown bump level"):
        bump_version("1.0.0", "sideways")


def test_parse_rejects_nonsense():
    with pytest.raises(VersionError):
        parse_version("v1")


def test_ordering_is_numeric_not_lexical():
    """'1.10.0' is after '1.9.0'. String comparison gets this backwards."""
    assert compare_versions("1.10.0", "1.9.0") == 1
    assert sorted(["1.10.0", "1.9.0", "1.2.0"], key=parse_version)[-1] == "1.10.0"


def test_major_bump_is_never_automatic():
    assert is_compatible("1.0.0", "1.4.0")
    assert not is_compatible("1.0.0", "2.0.0")
    assert not is_compatible("1.4.0", "1.0.0"), "a pin must not resolve backwards"


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------


def test_bump_records_its_parent(studio_nord):
    v2 = studio_nord.bump("minor", changelog="editorial serif for captions")
    assert v2.version == "1.1.0"
    assert v2.parent_version == "1.0.0"
    assert v2.status is BrandStatus.DRAFT, "a bump is a draft, not an approval"
    assert v2.changelog == "editorial serif for captions"


def test_bump_of_identical_content_keeps_the_hash(studio_nord):
    """Version and content are independent axes.

    A version bump that changed nothing has the same content hash, which is
    how a no-op release is detected.
    """
    v2 = studio_nord.bump("patch")
    assert v2.content_hash == studio_nord.content_hash


def test_history_returns_the_pinned_version(studio_nord):
    v2 = studio_nord.bump("minor").approved().published()
    h = BrandVersionHistory(brand_id=str(studio_nord.brand_id))
    h.add(studio_nord).add(v2)
    assert h.get("1.0.0").version == "1.0.0"
    assert h.latest().version == "1.1.0"
    assert h.resolve("1.0.0").version == "1.0.0"
    assert h.resolve(None).version == "1.1.0"


def test_history_ignores_unapproved_versions_when_tracking_latest(studio_nord):
    draft = studio_nord.bump("minor")            # DRAFT
    h = BrandVersionHistory(brand_id=str(studio_nord.brand_id))
    h.add(studio_nord).add(draft)
    assert h.latest().version == "1.0.0", "a draft must never be tracked"
    assert h.latest(usable_only=False).version == "1.1.0"


def test_history_refuses_to_rewrite_a_published_version(studio_nord):
    h = BrandVersionHistory(brand_id=str(studio_nord.brand_id))
    h.add(studio_nord)
    altered = studio_nord.model_copy(
        update={
            "identity": studio_nord.identity.model_copy(update={"tagline": "New"})
        }
    ).with_content_hash()
    with pytest.raises(VersionError, match="already published"):
        h.add(altered)


def test_history_rejects_a_foreign_brand(studio_nord):
    h = BrandVersionHistory(brand_id="00000000-0000-0000-0000-000000000000")
    with pytest.raises(VersionError, match="does not belong"):
        h.add(studio_nord)


def test_history_with_no_usable_version_refuses_to_track():
    h = BrandVersionHistory(brand_id=str(Brand.create(name="A").brand_id))
    with pytest.raises(VersionError, match="no approved version"):
        h.resolve(None)


# ---------------------------------------------------------------------------
# File store
# ---------------------------------------------------------------------------


def test_file_store_round_trip(file_repo, studio_nord):
    file_repo.save(studio_nord)
    got = file_repo.get(str(studio_nord.brand_id), "1.0.0")
    assert got.is_equivalent_to(studio_nord)


def test_file_store_preserves_history(file_repo, studio_nord):
    v2 = studio_nord.bump("minor").approved().published()
    file_repo.save(studio_nord)
    file_repo.save(v2)
    history = file_repo.history(str(studio_nord.brand_id))
    assert history.versions() == ["1.0.0", "1.1.0"]
    # The old version is byte-identical to what was stored, which is the whole
    # point: a 2024 document reprints as the 2024 document.
    assert history.get("1.0.0").content_hash == studio_nord.content_hash


def test_file_store_blocks_editing_a_published_version(file_repo, studio_nord):
    file_repo.save(studio_nord)
    altered = studio_nord.model_copy(
        update={
            "identity": studio_nord.identity.model_copy(update={"name": "Other"})
        }
    ).with_content_hash()
    with pytest.raises(VersionError, match="immutable"):
        file_repo.save(altered)


def test_file_store_allows_editing_a_draft(file_repo):
    draft = Brand.create(name="Draft Practice")
    file_repo.save(draft)
    edited = draft.model_copy(
        update={"identity": draft.identity.model_copy(update={"tagline": "New"})}
    ).with_content_hash()
    file_repo.save(edited)
    assert file_repo.get(str(draft.brand_id), "1.0.0").identity.tagline == "New"


def test_file_store_missing_brand(file_repo):
    with pytest.raises(BrandNotFound):
        file_repo.get("nope")


def test_file_store_index(file_repo, studio_nord):
    file_repo.save(studio_nord)
    rows = file_repo.list_brands()
    assert rows == [(str(studio_nord.brand_id), "Studio Nord", "1.0.0")]


def test_file_store_satisfies_the_protocol(tmp_path):
    from brand.store.brand_repo import BrandRepository, FileBrandRepository

    assert isinstance(FileBrandRepository(tmp_path), BrandRepository)

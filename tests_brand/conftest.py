"""
tests_brand/conftest.py

Fixtures for the Brand System suite.

The LLM is forced off before any project module is imported, matching
``tests/conftest.py``: the agent's deterministic path is the one CI must
exercise, and a suite whose behaviour depends on whether an API key happens to
be present is a suite that cannot be trusted when it is green.
"""

from __future__ import annotations

import os

# ── Must be first ──────────────────────────────────────────────────────────
os.environ.setdefault("AGENT_LLM_ENABLED", "false")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def studio_nord():
    """The published worked example."""
    from brand.examples.studio_nord import studio_nord as build

    return build()


@pytest.fixture(scope="session")
def tokens(studio_nord):
    return studio_nord.resolve_tokens()


@pytest.fixture()
def minimal_brand():
    """The least a brand can be and still resolve."""
    from brand.models.brand import Brand

    return Brand.create(name="Minimal Practice")


@pytest.fixture()
def file_repo(tmp_path):
    from brand.store.brand_repo import FileBrandRepository

    return FileBrandRepository(tmp_path / "brands")


@pytest.fixture()
def sqlite_session():
    """An in-memory session with every ORM table created.

    Follows ``construmind/tests``: skip rather than fail when SQLAlchemy is
    absent, since the domain half of the Brand System does not need it.
    """
    sqlalchemy = pytest.importorskip("sqlalchemy")
    from sqlalchemy.orm import sessionmaker

    import schemas.brand_models  # noqa: F401  registers the tables
    from schemas.v2_models import Base

    engine = sqlalchemy.create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        yield session

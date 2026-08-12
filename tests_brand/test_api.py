"""
The HTTP surface.

Mounted on the real FastAPI app, so these tests also assert that the router is
actually registered — a router that exists but was never added to ``api/main.py``
passes every unit test and serves nothing.

The store is redirected to a tmp directory per test so nothing here writes to
the repository.
"""

from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAND_STORAGE_ROOT", str(tmp_path / "brands"))
    import api.routers.brand as brand_router

    monkeypatch.setattr(brand_router, "_BRAND_ROOT", str(tmp_path / "brands"))

    with TestClient(_app()) as c:
        yield c


def _app():
    """The real app where its dependencies are installed, else just the router.

    ``api.main`` pulls in the render pipeline, the rate limiter and the auth
    stack, so on a machine without them the whole file would skip and the
    endpoint behaviour would go untested. Falling back to a bare app carrying
    only the brand router keeps every behavioural test running; the *wiring*
    is covered separately and statically by
    ``test_main_registers_the_router``, so nothing is lost by the fallback.
    """
    try:
        from api.main import app

        return app
    except BaseException:                                  # noqa: BLE001
        # BaseException, not Exception: a broken native dependency in the auth
        # stack surfaces as a pyo3 PanicException, which is not an Exception.
        from fastapi import FastAPI

        from api.routers import brand as brand_router

        app = FastAPI()
        app.include_router(brand_router.router, prefix="/api/v2", tags=["brand"])
        return app


BRAND_ID = "5747d10b-0000-4000-8000-000000000001"


# ---------------------------------------------------------------------------


def test_main_registers_the_router():
    """Static check: a router nobody mounts serves nothing.

    Reads the source rather than the app object so that it holds even in an
    environment where the app's other dependencies are missing.
    """
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "api" / "main.py").read_text()
    assert "from api.routers import brand as brand_router" in source
    assert 'app.include_router(brand_router.router, prefix="/api/v2"' in source


def test_the_router_is_mounted(client):
    """If this fails, api/main.py never registered the router."""
    response = client.get("/api/v2/brands")
    assert response.status_code == 200


def test_an_empty_store_seeds_the_worked_example(client):
    """A fresh deployment must be explorable, not a wall of 404s."""
    body = client.get("/api/v2/brands").json()
    assert body["brands"]
    assert body["brands"][0]["name"] == "Studio Nord"


def test_get_brand(client):
    body = client.get(f"/api/v2/brands/{BRAND_ID}").json()
    assert body["identity"]["name"] == "Studio Nord"
    assert body["version"] == "1.0.0"


def test_unknown_brand_is_404(client):
    r = client.get("/api/v2/brands/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_tokens_endpoint(client):
    full = client.get(f"/api/v2/brands/{BRAND_ID}/tokens").json()
    assert full["brand_version"] == "1.0.0"
    assert full["tokens"]["font.size.sm"]["unit"] == "mm"
    assert full["tokens"]["font.size.sm"]["source"]

    flat = client.get(f"/api/v2/brands/{BRAND_ID}/tokens?flat=true").json()
    assert flat["color.text.primary"] == "#111111"


def test_validate_endpoint(client):
    body = client.get(f"/api/v2/brands/{BRAND_ID}/validate").json()
    assert body["ok"] is True
    assert "counts" in body


def test_preview_endpoint_returns_html(client):
    r = client.get(f"/api/v2/brands/{BRAND_ID}/preview")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "STUDIO NORD" in r.text


def test_templates_endpoint_reports_coverage(client):
    body = client.get(f"/api/v2/brands/{BRAND_ID}/templates").json()
    from brand.templates.document_templates import TEMPLATES

    assert len(body["templates"]) == len(TEMPLATES) >= 18
    assert all(t["renders"] for t in body["templates"])


def test_render_html(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/render/BT01-a4-report",
        json={"context": {"title": "Feasibility", "project": "Malthouse"}},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Feasibility" in r.text


def test_render_pdf(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/render/BT05-project-cover",
        json={"context": {"project": "Malthouse"}},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_render_with_a_project_override(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/render/BT01-a4-report",
        json={"overrides": {"color.brand.accent": "#3b5b8c"}},
    )
    assert r.status_code == 200
    assert "#3b5b8c" in r.text


def test_an_override_naming_an_unknown_token_is_422(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/render/BT01-a4-report",
        json={"overrides": {"color.brand.quaternary": "#000000"}},
    )
    assert r.status_code == 422


def test_unknown_template_is_404(client):
    r = client.post(f"/api/v2/brands/{BRAND_ID}/render/nope", json={})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Composition — the Creative Layer through the HTTP boundary
#
# The endpoint is an adapter; these tests are about the boundary (request
# shape, error taxonomy, determinism surviving the round trip), not about
# composition itself — that is tests_brand/test_creative.py's job.
# ---------------------------------------------------------------------------


def _malthouse_payload(direction_id: str = "editorial-quiet", **extra):
    from brand.examples.malthouse import malthouse_content

    payload = {
        "content_model": malthouse_content().model_dump(mode="json"),
        "direction_id": direction_id,
    }
    payload.update(extra)
    return payload


def test_compose_returns_a_real_page_plan(client):
    r = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["plan"]["pages"]
    assert body["plan"]["plan_hash"]
    assert body["plan"]["brand_id"] == BRAND_ID
    assert body["plan"]["direction"] == "editorial-quiet"
    assert body["evaluation"]["plan_hash"] == body["plan"]["plan_hash"]
    assert set(body["meta"]) >= {"requested_at", "brand_id", "brand_version", "composer"}


def test_compose_is_deterministic_over_http(client):
    payload = _malthouse_payload()
    first = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=payload).json()
    second = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=payload).json()

    assert first["plan"] == second["plan"], "same inputs must produce the same plan"
    assert first["plan"]["plan_hash"] == second["plan"]["plan_hash"]
    # Only request-scoped metadata may differ.
    assert first["meta"]["requested_at"] != second["meta"]["requested_at"]


def test_compose_records_the_resolved_brand_version(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/compose?version=1.0.0",
        json=_malthouse_payload("technical-dense"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["plan"]["brand_version"] == "1.0.0"
    assert body["meta"]["brand_version"] == "1.0.0"


def test_compose_against_an_unknown_brand_is_404(client):
    r = client.post(
        "/api/v2/brands/00000000-0000-0000-0000-000000000000/compose",
        json=_malthouse_payload(),
    )
    assert r.status_code == 404


def test_compose_against_an_unknown_brand_version_is_404(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/compose?version=9.9.9",
        json=_malthouse_payload(),
    )
    assert r.status_code == 404


def test_compose_with_an_invalid_content_model_is_422(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/compose",
        json={"content_model": {"not": "a content model"}, "direction_id": "editorial-quiet"},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "invalid_content_model"


def test_compose_with_an_unknown_direction_is_404(client):
    r = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload("not-a-direction"))
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "unknown_direction"


def test_compose_with_a_document_outside_the_direction_is_422(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/compose",
        json=_malthouse_payload("editorial-quiet", document="monograph"),
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "document_not_in_direction"


def test_an_infeasible_composition_is_a_422_not_a_bad_plan(client):
    """A CompositionError must reach the caller as a domain failure, not a 200."""
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/compose",
        json=_malthouse_payload("editorial-quiet", page_format_name="XX9"),
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "composition_infeasible"


def test_compose_matches_calling_the_composer_directly(client):
    """The route is an adapter: it must not diverge from brand.creative.composer.compose."""
    from brand.creative.composer import compose
    from brand.creative.directions import get_direction
    from brand.examples.malthouse import malthouse_content
    from brand.store.brand_repo import FileBrandRepository

    r = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload())
    api_plan = r.json()["plan"]

    import api.routers.brand as brand_router

    brand = FileBrandRepository(brand_router._BRAND_ROOT).get(BRAND_ID)
    direct_plan = compose(malthouse_content(), get_direction("editorial-quiet"), brand)

    assert api_plan["plan_hash"] == direct_plan.plan_hash


# ---------------------------------------------------------------------------
# Intent — structured commands through the HTTP boundary
#
# Same posture as Composition above: the route is an adapter over
# brand.creative.intent + brand.creative.composer, so these tests are
# about the boundary — request shape, error taxonomy, that a failed
# intent never reaches the Composer, that determinism survives the round
# trip — not about the intent layer's own logic (tests_brand/test_intent.py).
# ---------------------------------------------------------------------------


def _intent_payload(intent: dict, direction_id: str = "editorial-quiet", **extra):
    from brand.examples.malthouse import malthouse_content

    payload = {
        "content_model": malthouse_content().model_dump(mode="json"),
        "base_direction_id": direction_id,
        "intent": intent,
    }
    payload.update(extra)
    return payload


def test_intent_reduce_text_density_returns_a_changed_real_plan(client):
    base = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload()).json()

    body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "page", "id": "4"}, "parameters": {"strength": 0.7}},
        previous_plan_hash=base["plan"]["plan_hash"],
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["plan"]["plan_hash"] != base["plan"]["plan_hash"]
    assert data["resulting_direction"]["text_density"] < 0.45  # editorial-quiet's base density
    assert data["resolution"]["direction_changed"] is True
    assert data["meta"]["previous_plan_hash"] == base["plan"]["plan_hash"]


@pytest.mark.parametrize(
    "intent_type,params",
    [
        ("reduce_text_density", {"strength": 0.6}),
        ("increase_text_density", {"strength": 0.6}),
        ("increase_image_emphasis", {"strength": 0.6}),
        ("decrease_image_emphasis", {"strength": 0.6}),
        ("recompose_page", {}),
        ("preserve_content", {"content_ids": ["met-01", "met-02"]}),
        ("remove_content", {"content_ids": ["met-01"]}),
        ("change_page_direction", {"direction_id": "image-led"}),
    ],
)
def test_every_supported_intent_type_produces_a_real_plan(client, intent_type, params):
    body = _intent_payload({"type": intent_type, "target": {"type": "document"}, "parameters": params})
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 200, r.json()
    data = r.json()
    assert data["plan"]["pages"]
    assert data["plan"]["plan_hash"]
    assert data["evaluation"]["plan_hash"] == data["plan"]["plan_hash"]


def test_intent_is_deterministic_over_http(client):
    body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "page", "id": "4"}, "parameters": {"strength": 0.7}}
    )
    first = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body).json()
    second = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body).json()
    assert first["plan"] == second["plan"]
    assert first["resulting_direction"] == second["resulting_direction"]


def test_intents_can_chain_through_resulting_direction(client):
    first_body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "document"}, "parameters": {"strength": 0.5}}
    )
    first = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=first_body).json()

    chained = {
        "content_model": first_body["content_model"],
        "base_direction": first["resulting_direction"],
        "intent": {"type": "increase_image_emphasis", "target": {"type": "document"}, "parameters": {"strength": 0.5}},
    }
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=chained)
    assert r.status_code == 200
    second = r.json()
    # Both adjustments must be visible: density from the first step, image
    # ratio from the second — chaining must not lose earlier context.
    assert second["resulting_direction"]["text_density"] == first["resulting_direction"]["text_density"]
    assert second["resulting_direction"]["image_ratio"] > first["resulting_direction"]["image_ratio"]


def test_an_invalid_intent_type_is_422_and_never_reaches_the_composer(client):
    body = _intent_payload({"type": "delete_everything", "target": {"type": "document"}})
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "invalid_intent"


def test_a_geometry_parameter_is_rejected_before_composing(client):
    body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "document"}, "parameters": {"color": "#ff0000"}}
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "intent_validation_failed"


def test_an_unknown_content_id_is_422(client):
    body = _intent_payload(
        {"type": "remove_content", "target": {"type": "document"}, "parameters": {"content_ids": ["not-real"]}}
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "intent_validation_failed"


def test_an_unknown_direction_for_change_page_direction_is_422(client):
    body = _intent_payload(
        {"type": "change_page_direction", "target": {"type": "document"}, "parameters": {"direction_id": "nope"}}
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "intent_validation_failed"


def test_unknown_base_direction_id_is_404(client):
    body = _intent_payload({"type": "recompose_page", "target": {"type": "document"}}, direction_id="not-a-direction")
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "unknown_direction"


def test_setting_both_base_direction_fields_is_422(client):
    body = _intent_payload({"type": "recompose_page", "target": {"type": "document"}})
    body["base_direction"] = {"id": "x"}
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "invalid_base_direction"


def test_setting_neither_base_direction_field_is_422(client):
    body = _intent_payload({"type": "recompose_page", "target": {"type": "document"}})
    del body["base_direction_id"]
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "invalid_base_direction"


def test_an_unknown_brand_is_404(client):
    body = _intent_payload({"type": "recompose_page", "target": {"type": "document"}})
    r = client.post("/api/v2/brands/00000000-0000-0000-0000-000000000000/intent", json=body)
    assert r.status_code == 404


def test_invalid_content_model_is_422(client):
    body = _intent_payload({"type": "recompose_page", "target": {"type": "document"}})
    body["content_model"] = {"not": "valid"}
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "invalid_content_model"


# ---------------------------------------------------------------------------
# Intent with base_plan — scoped composition (M1.3) at the HTTP boundary.
#
# Same posture again: brand.creative.scope's own contract (page isolation,
# region refused, contentBlock resolves to its page, infeasibility) is
# tests_brand/test_scope.py's job. These tests are about the route —
# that base_plan round-trips through the same shape /compose returns
# (including its extra 'plan_hash' key), that omitting it reproduces M1.2
# exactly, and that the error taxonomy (unsupported_scope, scope_infeasible,
# invalid_base_plan) reaches the caller as a 422 with the previous plan's
# hash intact.
# ---------------------------------------------------------------------------


def test_intent_without_base_plan_has_no_scope_fields(client):
    """Backward compatibility: M1.2 callers see exactly M1.2's response shape."""
    body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "page", "id": "4"}, "parameters": {"strength": 0.5}}
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["scope"] is None
    assert data["resolved_scope"] is None
    assert data["diff"] is None
    assert "brand.creative.composer.compose" in data["meta"]["composer"]


def test_intent_with_base_plan_scopes_the_change_to_the_target_page(client):
    base = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload()).json()
    plan = base["plan"]

    body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "page", "id": "4"}, "parameters": {"strength": 0.6}},
        previous_plan_hash=plan["plan_hash"],
        base_plan=plan,
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 200, r.json()
    data = r.json()

    assert data["scope"] == {"type": "page", "id": "4"}
    assert data["resolved_scope"] == {"type": "page", "id": "4"}
    assert data["diff"]["changed_pages"] == [4]
    assert data["diff"]["unchanged_pages"] == [0, 1, 2, 3, 5, 6, 7]
    assert "brand.creative.scope.compose_scoped" in data["meta"]["composer"]

    new_plan = data["plan"]
    for i, page in enumerate(plan["pages"]):
        if i == 4:
            assert new_plan["pages"][i] != page
        else:
            assert new_plan["pages"][i] == page, f"page {i} must be byte-identical over HTTP too"

    # the stale "applies document-wide" disclosure must not survive into a
    # response that just proved the change was genuinely page-scoped.
    assert not any("document-wide" in n for n in data["resolution"]["notes"])


def test_intent_with_base_plan_document_scope_still_recomposes_everything(client):
    base = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload()).json()
    plan = base["plan"]
    body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "document"}, "parameters": {"strength": 0.3}},
        previous_plan_hash=plan["plan_hash"],
        base_plan=plan,
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 200, r.json()
    data = r.json()
    assert data["resolved_scope"] == {"type": "document", "id": ""}


def test_intent_region_scope_with_base_plan_is_422_unsupported_scope(client):
    base = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload()).json()
    plan = base["plan"]
    body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "region", "id": "hero"}, "parameters": {"strength": 0.5}},
        previous_plan_hash=plan["plan_hash"],
        base_plan=plan,
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["error"] == "unsupported_scope"
    assert detail["previous_plan_hash"] == plan["plan_hash"]


def test_intent_content_block_scope_resolves_to_its_page_over_http(client):
    base = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload()).json()
    plan = base["plan"]
    target = next(p["index"] for p in plan["pages"] if "met-01" in [s["block"] for s in p["slots"]])

    body = _intent_payload(
        {"type": "preserve_content", "target": {"type": "contentBlock", "id": "met-01"},
         "parameters": {"content_ids": ["met-01"]}},
        previous_plan_hash=plan["plan_hash"],
        base_plan=plan,
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 200, r.json()
    assert r.json()["resolved_scope"] == {"type": "page", "id": str(target)}


def test_intent_scope_infeasible_leaves_the_previous_plan_hash_traceable(client):
    """A fabricated base_plan whose target page claims far more blocks than
    any archetype can place on one page — the same fixture strategy as
    tests_brand/test_scope.py's unit-level infeasibility test, done here in
    JSON to prove the HTTP boundary maps it to a 422, not a bad 200 plan."""
    base = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload()).json()
    plan = dict(base["plan"])
    pages = [dict(p) for p in plan["pages"]]
    pages[4] = dict(pages[4])
    pages[4]["slots"] = pages[4]["slots"] + pages[1]["slots"] + pages[3]["slots"]
    plan["pages"] = pages

    body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "page", "id": "4"}, "parameters": {"strength": 0.5}},
        previous_plan_hash=base["plan"]["plan_hash"],
        base_plan=plan,
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["error"] == "scope_infeasible"
    assert detail["previous_plan_hash"] == base["plan"]["plan_hash"]


def test_intent_with_a_malformed_base_plan_is_422(client):
    body = _intent_payload(
        {"type": "recompose_page", "target": {"type": "document"}},
        base_plan={"not": "a page plan"},
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "invalid_base_plan"


def test_intent_base_plan_round_trips_its_own_plan_hash_key(client):
    """PagePlan.to_dict() adds a derived 'plan_hash' key the frozen schema
    does not declare (extra='forbid') — the same round-trip pitfall
    ContentModel.to_dict() had against /compose in M1. The route must strip
    it rather than reject every caller who forwards what /compose gave them."""
    base = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload()).json()
    plan = base["plan"]
    assert "plan_hash" in plan  # the very key that would break a naive model_validate
    body = _intent_payload(
        {"type": "recompose_page", "target": {"type": "page", "id": "0"}},
        previous_plan_hash=plan["plan_hash"],
        base_plan=plan,
    )
    r = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body)
    assert r.status_code == 200, r.json()


def test_intent_with_base_plan_is_deterministic_over_http(client):
    base = client.post(f"/api/v2/brands/{BRAND_ID}/compose", json=_malthouse_payload()).json()
    plan = base["plan"]
    body = _intent_payload(
        {"type": "reduce_text_density", "target": {"type": "page", "id": "4"}, "parameters": {"strength": 0.6}},
        previous_plan_hash=plan["plan_hash"],
        base_plan=plan,
    )
    first = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body).json()
    second = client.post(f"/api/v2/brands/{BRAND_ID}/intent", json=body).json()
    assert first["plan"] == second["plan"]
    assert first["diff"] == second["diff"]


# ---------------------------------------------------------------------------
# Proposals — the approval gate at the HTTP boundary
# ---------------------------------------------------------------------------


def test_proposal_endpoint_does_not_write(client):
    before = len(client.get("/api/v2/brands").json()["brands"])
    r = client.post(
        "/api/v2/brand-proposals",
        json={"brief": "A quiet, material practice doing adaptive reuse.",
              "name": "Northbank"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["brand"]["status"] == "proposed"
    assert body["validation"]["ok"] is True
    assert body["assumptions"]

    after = len(client.get("/api/v2/brands").json()["brands"])
    assert after == before, "generating a proposal must not create a brand"


def test_empty_brief_is_422(client):
    assert client.post("/api/v2/brand-proposals", json={"brief": ""}).status_code == 422


def test_approving_a_proposal_stores_it(client):
    proposal = client.post(
        "/api/v2/brand-proposals",
        json={"brief": "Precise, quiet, material adaptive reuse.", "name": "Northbank"},
    ).json()

    r = client.post(
        "/api/v2/brand-proposals/approve?approved_by=MJ", json=proposal
    )
    assert r.status_code == 201
    assert r.json()["status"] == "approved"

    names = {b["name"] for b in client.get("/api/v2/brands").json()["brands"]}
    assert "Northbank" in names


def test_approving_an_invalid_brand_is_409(client):
    payload = client.get(f"/api/v2/brands/{BRAND_ID}").json()
    payload["architectural_language"]["drawing"]["lineweights"]["cut_mm"] = 0.18
    r = client.post("/api/v2/brand-proposals/approve?approved_by=MJ",
                    json={"brand": payload})
    assert r.status_code == 409
    assert r.json()["detail"]["validation"]["ok"] is False


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_create_validate_approve_publish(client):
    from brand.models.brand import Brand

    draft = Brand.create(name="Northbank Architects")
    created = client.post("/api/v2/brands", json=json.loads(draft.to_json()))
    assert created.status_code == 201
    bid = created.json()["brand_id"]
    assert created.json()["status"] == "draft"

    approved = client.post(
        f"/api/v2/brands/{bid}/versions/1.0.0/approve",
        json={"approved_by": "MJ", "changelog": "initial"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    published = client.post(f"/api/v2/brands/{bid}/versions/1.0.0/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"


def test_publishing_an_unapproved_version_is_409(client):
    from brand.models.brand import Brand

    draft = Brand.create(name="Unapproved Practice")
    bid = client.post("/api/v2/brands",
                      json=json.loads(draft.to_json())).json()["brand_id"]
    r = client.post(f"/api/v2/brands/{bid}/versions/1.0.0/publish")
    assert r.status_code == 409


def test_creating_a_malformed_brand_is_422(client):
    r = client.post("/api/v2/brands", json={"identity": {"name": "X"}})
    assert r.status_code == 422


def test_versions_endpoint(client):
    body = client.get(f"/api/v2/brands/{BRAND_ID}/versions").json()
    assert body["versions"][0]["version"] == "1.0.0"
    assert body["latest_usable"] == "1.0.0"


def test_schema_endpoint(client):
    schema = client.get("/api/v2/brand-schema").json()
    assert schema["title"] == "ADOS Brand"
    assert "identity" in schema["properties"]

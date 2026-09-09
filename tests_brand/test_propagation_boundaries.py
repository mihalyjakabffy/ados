"""
brand/project/propagation.py — ADOS-M4.3's own boundary, the same
structural (AST-level) technique tests_brand/test_loop_boundaries.py
already applies to brand/llm/loop/: propagation.py is explicitly
authorised to call compose()/evaluate() (it is the whole point of this
module — the fan-out over the existing single-document operation), but
every OTHER module under brand/project/ must never call them, so a
future change to versioning.py, content_resolution.py, document_types.py
or requirements.py cannot quietly grow a second composition path.

api/routers/ados_project.py (the original, first authorised caller,
predating this module) is outside brand/project/ and outside this
check's scope — it has its own long-standing, direct responsibility for
compose_document, unchanged by ADOS-M4.3.
"""

from __future__ import annotations

import ast

import brand.project.content_resolution as content_resolution_module
import brand.project.document_types as document_types_module
import brand.project.model as model_module
import brand.project.propagation as propagation_module
import brand.project.requirements as requirements_module
import brand.project.store as store_module
import brand.project.versioning as versioning_module

_NON_PROPAGATION_MODULES = (
    model_module, content_resolution_module, document_types_module,
    requirements_module, store_module, versioning_module,
)

_FORBIDDEN_EXECUTION_CALLS = {"compose", "compose_scoped", "apply_intent"}


def _parse(py_file: str) -> ast.Module:
    with open(py_file, encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _called_names(tree: ast.AST) -> set[str]:
    return {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } | {
        node.func.attr for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def test_only_propagation_module_calls_compose_within_brand_project():
    for module in _NON_PROPAGATION_MODULES:
        called = _called_names(_parse(module.__file__))
        hit = called & _FORBIDDEN_EXECUTION_CALLS
        assert not hit, f"{module.__name__} calls {hit} — only propagation.py may, within brand/project/"


def test_propagation_module_calls_compose_and_evaluate():
    """A structural proxy proving propagation.py really is a fan-out
    over the existing pipeline, not a hand-rolled substitute: it must
    call the real compose() and evaluate(), not reimplement either."""
    called = _called_names(_parse(propagation_module.__file__))
    assert "compose" in called
    assert "evaluate" in called


def test_propagation_module_never_saves_to_a_repository():
    """propagation.py takes an already-loaded Project/Brand and returns
    a new Project — it must never itself touch a store's save() (that
    stays the caller's job, the same I/O-stays-in-the-router split
    brand/project/versioning.py already keeps)."""
    called = _called_names(_parse(propagation_module.__file__))
    assert "save" not in called


def test_propagation_module_defines_no_second_project_or_document_type():
    tree = _parse(propagation_module.__file__)
    forbidden = {"Project", "Document", "Brand", "PagePlan"}
    defined = {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not (defined & forbidden), defined & forbidden

"""
ADOS-M3.4 §49 -- structural (AST-level) proof that Design Intent never
reaches CommandIntent, the Composer, PagePlan, or a renderer. Mirrors
the exact pattern test_narrative_boundaries.py/
test_content_intelligence_boundaries.py already established: parse
each module's own AST and inspect its import nodes and function/call
usage directly.
"""

from __future__ import annotations

import ast
import pathlib

import brand.llm.design.context as context_module
import brand.llm.design.generation as generation_module
import brand.llm.design.model as model_module
import brand.llm.design.observability as observability_module
import brand.llm.design.planning as planning_module
import brand.llm.design.prompt as prompt_module
import brand.llm.design.validation as validation_module
import brand.llm.design.vocabulary as vocabulary_module

_MODULES = (
    vocabulary_module, model_module, context_module, generation_module,
    planning_module, validation_module, prompt_module, observability_module,
)

_FORBIDDEN_IMPORTS = {
    "brand.creative.intent",
    "brand.creative.composer",
    "brand.creative.scope",
    "brand.creative.iterate",
    "brand.creative.plan",
}

_FORBIDDEN_DEFS = {"CommandIntent", "PagePlan", "Page", "Slot"}

#: Rendering entry points ADOS-M3.4 §48 explicitly forbids calling.
_FORBIDDEN_CALL_NAMES = {"compose", "compose_scoped", "render_page_plan", "html_to_pdf", "apply_intent"}


def _parse(py_file: str) -> ast.Module:
    with open(py_file, encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _imported_modules(tree: ast.Module) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_no_design_module_imports_command_intent_composer_or_pageplan():
    for module in _MODULES:
        imported = _imported_modules(_parse(module.__file__))
        assert not (imported & _FORBIDDEN_IMPORTS), f"{module.__name__} imports {imported & _FORBIDDEN_IMPORTS}"


def test_no_design_module_defines_command_intent_or_layout_classes():
    for module in _MODULES:
        tree = _parse(module.__file__)
        defined = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert not (defined & _FORBIDDEN_DEFS), f"{module.__name__} defines {defined & _FORBIDDEN_DEFS}"


def test_no_design_module_calls_a_rendering_or_composition_entry_point():
    for module in _MODULES:
        tree = _parse(module.__file__)
        called_names = {
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        } | {
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert not (called_names & _FORBIDDEN_CALL_NAMES), f"{module.__name__} calls {called_names & _FORBIDDEN_CALL_NAMES}"


def test_design_intent_router_never_imports_composer_or_intent_execution():
    router_file = pathlib.Path(__file__).parent.parent / "api" / "routers" / "design_intent.py"
    imported = _imported_modules(_parse(str(router_file)))
    assert not (imported & _FORBIDDEN_IMPORTS), imported


def test_plan_design_intent_return_type_is_design_intent_only():
    import inspect

    from brand.llm.design.planning import plan_design_intent

    sig = inspect.signature(plan_design_intent)
    assert sig.return_annotation in ("DesignIntent", model_module.DesignIntent)


def test_design_intent_has_no_geometric_fields():
    """A structural, field-level check that the schema itself never
    grew a coordinate/pixel field — ADOS-M3.4 §58's own test, applied
    to the schema rather than one instance."""
    forbidden_field_stems = ("_px", "_mm", "coordinate", "font_family", "hex")
    for model_cls in (model_module.DesignIntent, model_module.SectionDesign):
        for name in model_cls.model_fields:
            for stem in forbidden_field_stems:
                assert stem not in name, f"{model_cls.__name__}.{name} looks like a geometry field"

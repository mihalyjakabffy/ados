"""
ADOS-M3.3 §45 -- structural (AST-level) proof that Narrative Generation
never reaches CommandIntent, the Composer, PagePlan, or DesignIntent.
Mirrors the exact pattern
test_content_intelligence_boundaries.py/test_semantic_intent_extractor.py
already established: parse each module's own AST and inspect its import
nodes and class/function definitions directly.
"""

from __future__ import annotations

import ast
import pathlib

import brand.llm.narrative.context as context_module
import brand.llm.narrative.generation as generation_module
import brand.llm.narrative.model as model_module
import brand.llm.narrative.observability as observability_module
import brand.llm.narrative.planning as planning_module
import brand.llm.narrative.prompt as prompt_module
import brand.llm.narrative.validation as validation_module
import brand.llm.narrative.vocabulary as vocabulary_module

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
    "brand.creative",
}

_FORBIDDEN_DEFS = {"CommandIntent", "PagePlan", "DesignIntent"}


def _imported_modules(py_file: str) -> set[str]:
    with open(py_file, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_no_narrative_module_imports_command_intent_or_composer():
    for module in _MODULES:
        imported = _imported_modules(module.__file__)
        assert not (imported & _FORBIDDEN_IMPORTS), f"{module.__name__} imports {imported & _FORBIDDEN_IMPORTS}"


def test_no_narrative_module_defines_command_intent_page_plan_or_design_intent():
    for module in _MODULES:
        with open(module.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        defined = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert not (defined & _FORBIDDEN_DEFS), f"{module.__name__} defines {defined & _FORBIDDEN_DEFS}"


def test_narrative_router_never_imports_composer_or_intent_execution():
    router_file = pathlib.Path(__file__).parent.parent / "api" / "routers" / "narrative.py"
    imported = _imported_modules(str(router_file))
    assert not (imported & _FORBIDDEN_IMPORTS), imported


def test_plan_narrative_return_type_is_narrative_plan_only():
    import inspect

    from brand.llm.narrative.planning import plan_narrative

    sig = inspect.signature(plan_narrative)
    assert sig.return_annotation in ("NarrativePlan", model_module.NarrativePlan)


def test_narrative_plan_has_no_layout_fields():
    """A structural, field-level check that the schema itself never
    grew a page/grid/coordinate field -- ADOS-M3.3 §36's own test,
    applied to the schema rather than one instance."""
    forbidden_field_stems = ("page", "grid", "column", "x_mm", "y_mm", "font", "colour", "color")
    for name in model_module.NarrativePlan.model_fields:
        for stem in forbidden_field_stems:
            assert stem not in name, f"NarrativePlan.{name} looks like a layout field"
    for name in model_module.NarrativeSection.model_fields:
        for stem in forbidden_field_stems:
            assert stem not in name, f"NarrativeSection.{name} looks like a layout field"

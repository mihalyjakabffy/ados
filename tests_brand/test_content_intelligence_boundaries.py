"""
ADOS-M3.2 §36/§38 -- structural (AST-level) proof that Content
Intelligence never reaches CommandIntent, the Composer, NarrativePlan,
or any design/layout concept. Mirrors the exact pattern
test_semantic_intent_extractor.py::test_extract_never_reaches_command_intent_or_composer
already established for ADOS-M3.1: parse each module's own AST and
inspect its import nodes directly, rather than trust a docstring or a
behavioural test that could miss a code path.
"""

from __future__ import annotations

import ast
import pathlib

import brand.llm.content.extraction as extraction_module
import brand.llm.content.model as model_module
import brand.llm.content.observability as observability_module
import brand.llm.content.prompt as prompt_module
import brand.llm.content.resolution as resolution_module
import brand.llm.content.validation as validation_module
import brand.llm.content.vocabulary as vocabulary_module

_MODULES = (
    vocabulary_module, model_module, extraction_module,
    resolution_module, validation_module, prompt_module, observability_module,
)

_FORBIDDEN = {
    "brand.creative.intent",
    "brand.creative.composer",
    "brand.creative.scope",
    "brand.creative.iterate",
    "brand.creative",
}


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


def test_no_content_intelligence_module_imports_command_intent_or_composer():
    for module in _MODULES:
        imported = _imported_modules(module.__file__)
        assert not (imported & _FORBIDDEN), f"{module.__name__} imports {imported & _FORBIDDEN}"


def test_no_content_intelligence_module_defines_command_intent_or_page_plan_classes():
    """A structural check that nothing under brand/llm/content/ even
    *defines* a class shaped like an execution artifact -- ADOS-M3.2's
    boundary is "stop at ContentIntelligenceModel", not merely "don't
    import the executor"."""
    forbidden_names = {"CommandIntent", "PagePlan", "NarrativePlan", "DesignIntent"}
    for module in _MODULES:
        with open(module.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        defined = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert not (defined & forbidden_names), f"{module.__name__} defines {defined & forbidden_names}"


def test_content_intelligence_router_never_imports_composer_or_intent_execution():
    router_file = pathlib.Path(__file__).parent.parent / "api" / "routers" / "content_intelligence.py"
    imported = _imported_modules(str(router_file))
    assert not (imported & _FORBIDDEN), imported


def test_resolve_content_return_type_is_content_intelligence_model_only():
    """The one public entrypoint's own return annotation names the
    boundary directly -- resolve_content produces a
    ContentIntelligenceModel and nothing else is even representable as
    its result."""
    import inspect

    from brand.llm.content.resolution import resolve_content

    sig = inspect.signature(resolve_content)
    assert sig.return_annotation in ("ContentIntelligenceModel", model_module.ContentIntelligenceModel)

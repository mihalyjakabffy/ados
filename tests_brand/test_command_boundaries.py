"""
ADOS-M3.5 — structural (AST-level) proof that command *generation* never
composes, never applies, never mutates a Project/Document/DesignState
directly, and never executes arbitrary code. Mirrors the exact pattern
test_design_intent_boundaries.py/test_narrative_boundaries.py already
established.

**Unlike M3.2-M3.4's own boundary suites, ``brand.creative.intent`` is
not forbidden here** — reusing its real ``CommandIntent``/
``validate_intent`` is this package's entire point. What remains
forbidden for the *generation/planning* modules is composing
(``compose``/``compose_scoped``), applying (``apply_intent``), and
touching Project/Document storage directly — those stay the API
router's job, and only inside its one ``/commands/apply`` endpoint.
"""

from __future__ import annotations

import ast
import pathlib

import brand.llm.command.context as context_module
import brand.llm.command.generation as generation_module
import brand.llm.command.model as model_module
import brand.llm.command.observability as observability_module
import brand.llm.command.planning as planning_module
import brand.llm.command.prompt as prompt_module
import brand.llm.command.validation as validation_module
import brand.llm.command.vocabulary as vocabulary_module

_MODULES = (
    vocabulary_module, model_module, context_module, generation_module,
    planning_module, validation_module, prompt_module, observability_module,
)

#: brand.creative.scope is deliberately not forbidden here: this
#: package's vocabulary.py re-exports the plain ``ScopeType`` enum (real
#: vocabulary reuse, ADOS-M1.3's own value), never
#: ``compose_scoped``/``resolve_scope`` themselves — those are caught by
#: the forbidden-*calls* check below instead, which is precise about the
#: capability that actually matters.
_FORBIDDEN_IMPORTS = {
    "brand.creative.composer",
    "brand.creative.iterate",
    "brand.creative.plan",
    "brand.project.model",
    "brand.project.store",
}

_FORBIDDEN_DEFS = {"PagePlan", "Page", "Slot"}

#: Execution/composition entry points this package's own generation and
#: planning logic must never call — only the API's dedicated
#: ``/commands/apply`` endpoint may (checked separately, function-scoped,
#: below).
_FORBIDDEN_CALL_NAMES = {"compose", "compose_scoped", "resolve_scope", "render_page_plan", "html_to_pdf", "apply_intent"}

#: Arbitrary-code-execution primitives — ADOS-M3.5's "compiler, not
#: agent" boundary forbids these everywhere in this package, including
#: the API router.
_FORBIDDEN_EXEC_NAMES = {"eval", "exec", "system", "Popen", "check_call", "check_output", "run"}


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


def _called_names(tree: ast.Module) -> set[str]:
    return {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } | {
        node.func.attr for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def test_no_command_module_imports_composer_scope_iterate_or_project_storage():
    for module in _MODULES:
        imported = _imported_modules(_parse(module.__file__))
        assert not (imported & _FORBIDDEN_IMPORTS), f"{module.__name__} imports {imported & _FORBIDDEN_IMPORTS}"


def test_no_command_module_defines_pageplan_page_or_slot():
    for module in _MODULES:
        tree = _parse(module.__file__)
        defined = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert not (defined & _FORBIDDEN_DEFS), f"{module.__name__} defines {defined & _FORBIDDEN_DEFS}"


def test_no_command_module_composes_or_applies():
    """generation.py and planning.py may call validate_intent (that is
    the load-bearing re-check every command goes through) but must
    never call compose/compose_scoped/apply_intent/render_page_plan —
    those stay the API's own, separate /commands/apply endpoint."""
    for module in _MODULES:
        called = _called_names(_parse(module.__file__))
        assert not (called & _FORBIDDEN_CALL_NAMES), f"{module.__name__} calls {called & _FORBIDDEN_CALL_NAMES}"


def test_no_command_module_executes_arbitrary_code():
    router_file = pathlib.Path(__file__).parent.parent / "api" / "routers" / "command.py"
    for module_file in [m.__file__ for m in _MODULES] + [str(router_file)]:
        called = _called_names(_parse(module_file))
        assert not (called & _FORBIDDEN_EXEC_NAMES), f"{module_file} calls {called & _FORBIDDEN_EXEC_NAMES}"


def test_generation_and_validation_functions_only_call_validate_intent():
    """The one, load-bearing exception: validate_intent must actually be
    called by planning.py (the pre-return safety net) and validation.py
    (the independent CMD-001 re-check) — a regression here would mean
    this package stopped re-checking its own output."""
    planning_called = _called_names(_parse(planning_module.__file__))
    validation_called = _called_names(_parse(validation_module.__file__))
    assert "validate_intent" in planning_called
    assert "validate_intent" in validation_called


def test_router_generate_and_validate_endpoints_never_compose_or_apply():
    """Function-scoped, not file-scoped: api/routers/command.py
    legitimately imports compose/apply_intent for its one
    /commands/apply endpoint, so the file-level import check the other
    tests use would be too blunt here. What must hold is that the
    *generate* and *validate* endpoint functions themselves never reach
    those entry points — generation must stay separate from execution."""
    router_file = pathlib.Path(__file__).parent.parent / "api" / "routers" / "command.py"
    tree = _parse(str(router_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in (
            "generate_project_commands", "validate_project_command_plan",
        ):
            called = _called_names(ast.Module(body=node.body, type_ignores=[]))
            assert not (called & _FORBIDDEN_CALL_NAMES), f"{node.name} calls {called & _FORBIDDEN_CALL_NAMES}"


def test_plan_commands_return_type_is_command_plan_only():
    import inspect

    from brand.llm.command.planning import plan_commands

    sig = inspect.signature(plan_commands)
    assert sig.return_annotation in ("CommandPlan", model_module.CommandPlan)


def test_command_plan_has_no_geometric_fields():
    forbidden_field_stems = ("_px", "_mm", "coordinate", "font_family", "hex")
    for model_cls in (model_module.CommandPlan, model_module.GeneratedCommand):
        for name in model_cls.model_fields:
            for stem in forbidden_field_stems:
                assert stem not in name, f"{model_cls.__name__}.{name} looks like a geometry field"

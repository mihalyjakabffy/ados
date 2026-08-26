"""
ADOS-M3.6 §76/§77 — structural (AST-level) proof that the closed loop
orchestrates the existing ADOS execution primitives and never becomes a
second one: no direct DesignState/Project/Document mutation outside the
sanctioned ``model_copy``+repository-``save`` pattern, no SQL, no
arbitrary code/shell execution, no bypass of ``CommandIntent``/
``validate_intent``/``apply_intent``/``compose``, no invented execution
primitive, no version-check bypass.

**Unlike M3.5's own boundary suite, ``apply_intent``/``compose`` are not
forbidden everywhere** — ``execution.py`` is explicitly the one module
allowed (required) to call them, mirroring the master prompt's own
"M3.6 may orchestrate, it may not become a second execution layer"
distinction. What is checked instead: every OTHER module in this
package never calls them, and ``execution.py`` itself never bypasses
``validate_intent`` before ``apply_intent``.
"""

from __future__ import annotations

import ast
import pathlib

import brand.llm.loop.execution as execution_module
import brand.llm.loop.findings as findings_module
import brand.llm.loop.fingerprint as fingerprint_module
import brand.llm.loop.model as model_module
import brand.llm.loop.observability as observability_module
import brand.llm.loop.orchestrator as orchestrator_module
import brand.llm.loop.patch as patch_module
import brand.llm.loop.prompt as prompt_module
import brand.llm.loop.recommend as recommend_module
import brand.llm.loop.vocabulary as vocabulary_module

_NON_EXECUTION_MODULES = (
    vocabulary_module, model_module, fingerprint_module, findings_module,
    recommend_module, patch_module, prompt_module, observability_module,
)
_ALL_MODULES = _NON_EXECUTION_MODULES + (execution_module, orchestrator_module)

_FORBIDDEN_EXEC_NAMES = {"eval", "exec", "system", "Popen", "check_call", "check_output", "run"}
_FORBIDDEN_EXECUTION_CALLS = {"apply_intent", "compose", "compose_scoped", "render_page_plan", "html_to_pdf"}


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


def _called_names(tree) -> set[str]:
    return {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } | {
        node.func.attr for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def test_no_module_executes_arbitrary_code():
    router_file = pathlib.Path(__file__).parent.parent / "api" / "routers" / "closed_loop.py"
    for module_file in [m.__file__ for m in _ALL_MODULES] + [str(router_file)]:
        called = _called_names(_parse(module_file))
        assert not (called & _FORBIDDEN_EXEC_NAMES), f"{module_file} calls {called & _FORBIDDEN_EXEC_NAMES}"


def test_no_module_uses_raw_sql():
    for module_file in [m.__file__ for m in _ALL_MODULES]:
        with open(module_file, encoding="utf-8") as fh:
            source = fh.read()
        for token in ("SELECT ", "INSERT INTO", "DELETE FROM", "sqlite3", "psycopg"):
            assert token not in source, f"{module_file} appears to touch raw SQL ({token!r})"


def test_only_execution_module_calls_apply_intent_or_compose():
    for module in _NON_EXECUTION_MODULES:
        called = _called_names(_parse(module.__file__))
        assert not (called & _FORBIDDEN_EXECUTION_CALLS), f"{module.__name__} calls {called & _FORBIDDEN_EXECUTION_CALLS}"


def test_execution_module_always_validates_before_applying():
    """A structural proxy for "no bypass of validate_intent()": the one
    module allowed to call apply_intent must also call validate_intent
    at least once — dropping that call while keeping apply_intent would
    be exactly the regression this guards against."""
    called = _called_names(_parse(execution_module.__file__))
    assert "validate_intent" in called
    assert "apply_intent" in called


def test_orchestrator_never_calls_execution_primitives_directly():
    """orchestrator.py delegates execution to execution.py's own
    functions (execute_commands/save_new_version) — it must never call
    apply_intent/compose itself, which would mean two independent
    execution code paths instead of one."""
    called = _called_names(_parse(orchestrator_module.__file__))
    assert not (called & _FORBIDDEN_EXECUTION_CALLS), called & _FORBIDDEN_EXECUTION_CALLS


def test_no_module_defines_a_second_command_intent_or_page_plan_type():
    forbidden_defs = {"CommandIntent", "PagePlan", "Page", "Slot", "DesignState", "Project", "Document"}
    for module in _ALL_MODULES:
        tree = _parse(module.__file__)
        defined = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert not (defined & forbidden_defs), f"{module.__name__} defines {defined & forbidden_defs}"


def test_project_and_document_mutation_only_happens_via_model_copy_and_repo_save():
    """execution.save_new_version is the only place Project/Document
    are touched in this package, and it must do so via the sanctioned
    ``model_copy`` pattern — never direct attribute assignment on a
    ``project``/``document``-named value (these are frozen pydantic
    models, so an actual assignment would raise at runtime; this is the
    AST-level guard that catches the *attempt* even in a code path
    tests don't happen to execute). Assignment onto an unrelated name
    — e.g. a plain exception's own ``self.command_id`` — is not what
    this check is about and is deliberately left alone."""
    tree = _parse(execution_module.__file__)
    watched_names = {"project", "document", "new_project", "new_document"}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store)
            and isinstance(node.value, ast.Name) and node.value.id in watched_names
        ):
            raise AssertionError(f"execution.py assigns directly to {node.value.id}.{node.attr}")


def test_command_generation_is_never_bypassed():
    """orchestrator.py must call brand.llm.command.planning.plan_commands
    for every DesignIntent -> CommandIntent step — never construct a
    CommandIntent by hand."""
    called = _called_names(_parse(orchestrator_module.__file__))
    assert "plan_commands" in called


def test_version_safety_check_is_present_in_orchestrator_source():
    with open(orchestrator_module.__file__, encoding="utf-8") as fh:
        source = fh.read()
    assert "output_design_state_version" in source
    assert "StopReason.STALE_STATE" in source


def test_llm_recommender_schema_has_no_command_shaped_fields():
    """The bounded LLM proposer's own structured-output schema
    (recommend.make_llm_proposer's RawPatchChoice) must never carry a
    command-shaped field — proven by inspecting its own class body
    rather than trusting the docstring."""
    tree = _parse(recommend_module.__file__)
    class_defs = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "RawPatchChoice"]
    assert class_defs, "RawPatchChoice class not found"
    field_names = {
        stmt.target.id for stmt in class_defs[0].body
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
    }
    forbidden = {"command", "command_type", "intent", "parameters", "target_id", "code", "sql", "shell"}
    assert not (field_names & forbidden), field_names & forbidden

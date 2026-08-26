"""
brand/llm/loop/execution.py

**The one module in this package allowed to call the real, canonical
execution primitives** — ``brand.creative.intent.apply_intent`` and
``brand.creative.composer.compose`` — plus the real, canonical
persistence primitive, ``brand.project.versioning.build_version``. This
is deliberate and required (ADOS-M3.6 §45/§52): closing the loop means
actually executing, and every other module in this package
(``recommend.py``, ``patch.py``, ``findings.py``, ``orchestrator.py``'s
own planning steps) never does.

Nothing here is a second execution engine. ``execute_commands`` calls
``validate_intent()`` immediately before every ``apply_intent()`` call
— the same discipline ``api/routers/command.py``'s ``/commands/apply``
endpoint already applies, factored out here so the orchestrator and
that endpoint are not two independent reimplementations of "apply a
CommandPlan, one command at a time, stop at the first failure."
``save_new_version`` calls ``brand.project.versioning.build_version``
exactly the way ``api/routers/ados_project.py``'s own
``compose_document``/``save_version`` endpoints already do — updating
``Document.latest_plan`` and appending a ``ProjectVersion`` via
``model_copy`` and the project repository's own ``save()``, the
sanctioned write path every Project-mutating endpoint in this
repository already uses, not a bypass of it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from brand.creative.composer import CompositionError, compose
from brand.creative.intent import IntentValidationError, apply_intent, validate_intent
from brand.llm.command.model import GeneratedCommand
from brand.llm.command.vocabulary import CommandSafetyLevel
from brand.llm.loop.model import IterationPolicy
from brand.llm.loop.vocabulary import AutonomyLevel

if TYPE_CHECKING:
    from brand.content.model import ContentModel
    from brand.creative.direction import CreativeDirection
    from brand.creative.plan import PagePlan
    from brand.llm.command.model import CommandPlan
    from brand.models.brand import Brand
    from brand.project.model import Document, Project, ProjectVersion


class ExecutionFailedError(RuntimeError):
    """A command failed ``validate_intent()`` or ``apply_intent()`` at
    the moment it was about to execute — never raised for a command
    this package's own generator already rejected earlier."""

    def __init__(self, message: str, command_id: str):
        self.command_id = command_id
        super().__init__(message)


class CompositionFailedError(RuntimeError):
    def __init__(self, message: str, command_id: str):
        self.command_id = command_id
        super().__init__(message)


def gate_commands(
    commands: tuple[GeneratedCommand, ...],
    autonomy: AutonomyLevel,
    approved_command_ids: frozenset[str] = frozenset(),
) -> tuple[tuple[GeneratedCommand, ...], tuple[GeneratedCommand, ...]]:
    """Which commands may execute now, and which need approval —
    ADOS-M3.6 §37/§38. A command already named in ``approved_command_ids``
    (a human explicitly approved it via ``/approve``) always executes,
    regardless of autonomy. Otherwise: ``NONE``/``RECOMMEND`` gate
    everything; ``SAFE`` auto-executes only ``CommandSafetyLevel.SAFE``
    commands; ``FULL`` auto-executes everything this package's own M3.5
    validation already accepted."""
    to_execute: list[GeneratedCommand] = []
    pending: list[GeneratedCommand] = []
    for command in commands:
        if command.id in approved_command_ids:
            to_execute.append(command)
        elif autonomy is AutonomyLevel.FULL:
            to_execute.append(command)
        elif autonomy is AutonomyLevel.SAFE and command.safety_level is CommandSafetyLevel.SAFE:
            to_execute.append(command)
        else:
            pending.append(command)
    return tuple(to_execute), tuple(pending)


def execute_commands(
    commands: tuple[GeneratedCommand, ...],
    content: "ContentModel",
    direction: "CreativeDirection",
    brand: "Brand",
    *,
    page_format_name: str = "A4",
) -> tuple["ContentModel", "CreativeDirection", Optional["PagePlan"], tuple[dict, ...]]:
    """Applies ``commands`` in order via the real
    ``validate_intent -> apply_intent -> compose`` pipeline, exactly
    once per command, composing after every command so the next one
    sees the real, current document. Raises on the first failure —
    ADOS-M3.6 §44: an iteration is never reported successful merely
    because *some* commands executed."""
    steps: list[dict] = []
    plan: Optional["PagePlan"] = None
    plan_hash = ""

    if not commands:
        # Nothing to apply — the current, unchanged content/direction is
        # still what the caller needs composed and evaluated (e.g. a
        # DesignIntent whose gap against the current DesignState was
        # already zero). One compose() call, no execution steps.
        try:
            plan = compose(content, direction, brand, page_format_name=page_format_name)
        except CompositionError as exc:
            raise CompositionFailedError(str(exc), "") from exc
        return content, direction, plan, ()

    for command in commands:
        errors = validate_intent(content, command.intent, page_count=None)
        if errors:
            raise ExecutionFailedError(
                f"{command.intent.type.value} failed validate_intent(): {'; '.join(errors)}", command.id,
            )
        try:
            content, direction, resolution = apply_intent(content, direction, command.intent)
        except IntentValidationError as exc:
            raise ExecutionFailedError(
                f"{command.intent.type.value} failed apply_intent(): {'; '.join(exc.errors)}", command.id,
            ) from exc

        try:
            plan = compose(content, direction, brand, page_format_name=page_format_name)
        except CompositionError as exc:
            raise CompositionFailedError(str(exc), command.id) from exc

        steps.append({
            "command_id": command.id,
            "direction_changed": resolution.direction_changed,
            "content_changed": resolution.content_changed,
            "notes": list(resolution.notes),
            "plan_hash_before": plan_hash,
            "plan_hash_after": plan.plan_hash,
        })
        plan_hash = plan.plan_hash

    return content, direction, plan, tuple(steps)


def save_new_version(
    project: "Project", document: "Document", plan: "PagePlan", *, label: str = "",
) -> tuple["Project", "Document", "ProjectVersion"]:
    """Persists a freshly-composed ``PagePlan`` the same way
    ``api/routers/ados_project.py``'s ``compose_document``/
    ``save_version`` endpoints already do: cache it on the document,
    snapshot it into a new, immutable ``ProjectVersion``, return the
    updated ``Project``/``Document`` for the caller to actually save via
    the project repository. This function never writes to storage
    itself — it has no repository handle — the API layer's existing
    ``_repo().save(project)`` call remains the one place persistence
    happens, unchanged."""
    from brand.project.versioning import build_version

    version = build_version(document, project, label=label, plan=plan.to_dict())
    new_document = document.model_copy(update={"latest_plan": plan.to_dict()})
    documents = list(project.documents)
    idx = next(i for i, d in enumerate(documents) if d.id == document.id)
    documents[idx] = new_document
    new_project = project.model_copy(update={
        "documents": tuple(documents), "versions": project.versions + (version,),
    })
    return new_project, new_document, version

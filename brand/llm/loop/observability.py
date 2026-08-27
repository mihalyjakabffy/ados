"""
brand/llm/loop/observability.py

ADOS-M3.6 §6/§40/§41/§60 — this package's own extension of the exact
in-memory, bounded store every M3.1-M3.5 layer already uses, keyed by
``(project_id, document_id)`` since a loop's lineage — the immutable
iteration history a "what changed between iteration 3 and 4" question
needs — is a property of one document's iteration timeline, not of one
request.

**This is also this milestone's only persistence for iteration
history.** No ``Iteration`` is written into ``Project``/``Document``
storage (only the composed ``PagePlan``/``ProjectVersion`` are, via
``execution.save_new_version`` — the same real Project/Document write
path every other endpoint uses). A process restart loses iteration
history the same way it already loses every other M3 layer's traces;
this is a debugging/demo aid, not a durable audit log, exactly as
``brand/llm/design/observability.py``'s own docstring already states
for the layer below this one.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from brand.llm.loop.model import Iteration

#: Bounded number of distinct (project_id, document_id) lineages kept —
#: unlike a single flat trace deque, a lineage can itself grow to
#: IterationPolicy.max_iterations entries, so the outer bound is on
#: how many documents' histories this process remembers at once.
_MAX_LINEAGES = 200

_lineages: "OrderedDict[tuple[str, str], list[Iteration]]" = OrderedDict()

#: One lock per lineage (ADOS-M3.6 production hardening). Every
#: loop-mutating API endpoint (start/continue/run/approve) does a
#: check-lineage-state -> run_iteration -> persist sequence that is not
#: otherwise atomic; two concurrent requests against the same document
#: could both pass the "no lineage yet" check, both plan/execute/
#: compose, and both call ``execution.save_new_version`` — producing
#: duplicate sequence numbers in the lineage and a lost-update race on
#: the project file. This registry lets the router serialize that
#: sequence per (project_id, document_id) without serializing unrelated
#: documents. Single-process only, same limitation this whole in-memory
#: store already accepts for iteration history — a multi-worker
#: deployment needs a real distributed lock instead.
_lineage_locks: "OrderedDict[tuple[str, str], threading.Lock]" = OrderedDict()
_lineage_locks_guard = threading.Lock()


def _key(project_id: str, document_id: str) -> tuple[str, str]:
    return (project_id, document_id)


def lineage_lock(project_id: str, document_id: str) -> threading.Lock:
    key = _key(project_id, document_id)
    with _lineage_locks_guard:
        lock = _lineage_locks.get(key)
        if lock is None:
            if len(_lineage_locks) >= _MAX_LINEAGES:
                _lineage_locks.popitem(last=False)
            lock = threading.Lock()
            _lineage_locks[key] = lock
        _lineage_locks.move_to_end(key)
        return lock


def record_iteration(iteration: Iteration) -> None:
    key = _key(iteration.project_id, iteration.document_id)
    if key not in _lineages:
        if len(_lineages) >= _MAX_LINEAGES:
            _lineages.popitem(last=False)
        _lineages[key] = []
    _lineages[key].append(iteration)
    _lineages.move_to_end(key)


def replace_last_iteration(iteration: Iteration) -> None:
    """Used only by ``/loop/approve``: an approved iteration completes
    the *same* sequence a pending ``AWAITING_APPROVAL`` record already
    occupies — this replaces that record rather than appending a
    second one for the same sequence number."""
    key = _key(iteration.project_id, iteration.document_id)
    lineage = _lineages.get(key)
    if lineage:
        lineage[-1] = iteration
    else:
        record_iteration(iteration)


def record_lineage(iterations: tuple[Iteration, ...]) -> None:
    for iteration in iterations:
        record_iteration(iteration)


def get_lineage(project_id: str, document_id: str) -> tuple[Iteration, ...]:
    return tuple(_lineages.get(_key(project_id, document_id), ()))


def get_iteration(project_id: str, document_id: str, iteration_id: str) -> Optional[Iteration]:
    for iteration in _lineages.get(_key(project_id, document_id), ()):
        if iteration.id == iteration_id:
            return iteration
    return None


def recent_iterations(limit: int = 50) -> list[Iteration]:
    flat = [it for lineage in _lineages.values() for it in lineage]
    flat.sort(key=lambda it: it.created_at, reverse=True)
    return flat[:limit]


def clear_lineages() -> None:
    _lineages.clear()

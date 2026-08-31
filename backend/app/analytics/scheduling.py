"""Deterministic calendar-day scheduling graph, propagation, and CPM calculations."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID


@dataclass(frozen=True)
class ScheduleTask:
    id: UUID
    start: date | None
    finish: date | None
    milestone_id: UUID | None = None

    @property
    def duration_days(self) -> int | None:
        if self.start is None or self.finish is None or self.finish < self.start:
            return None
        return (self.finish - self.start).days + 1


@dataclass(frozen=True)
class CPMTask:
    earliest_start: int
    earliest_finish: int
    latest_start: int
    latest_finish: int
    total_float: int
    free_float: int
    critical: bool


@dataclass(frozen=True)
class CPMResult:
    tasks: dict[UUID, CPMTask]
    critical_task_ids: list[UUID]
    critical_sequences: list[list[UUID]]
    project_duration_days: int | None
    complete: bool
    reasons: list[str]


def topological_order(task_ids: set[UUID], edges: set[tuple[UUID, UUID]]) -> list[UUID]:
    successors: dict[UUID, set[UUID]] = defaultdict(set)
    indegree = {task_id: 0 for task_id in task_ids}
    for source, target in edges:
        if source not in task_ids or target not in task_ids:
            continue
        if target not in successors[source]:
            successors[source].add(target)
            indegree[target] += 1
    ready = deque(sorted((item for item, degree in indegree.items() if degree == 0), key=str))
    order: list[UUID] = []
    while ready:
        current = ready.popleft()
        order.append(current)
        for target in sorted(successors[current], key=str):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if len(order) != len(task_ids):
        raise ValueError("dependency_cycle")
    return order


def calculate_cpm(tasks: list[ScheduleTask], edges: set[tuple[UUID, UUID]]) -> CPMResult:
    by_id = {task.id: task for task in tasks}
    scheduled = {task.id for task in tasks if task.duration_days is not None}
    reasons: list[str] = []
    if len(scheduled) != len(tasks):
        reasons.append("tasks_missing_valid_dates")
    valid_edges = {
        (source, target) for source, target in edges if source in scheduled and target in scheduled
    }
    if len(valid_edges) != len(edges):
        reasons.append("dependencies_excluded_for_unscheduled_tasks")
    if reasons:
        return CPMResult({}, [], [], None, False, reasons)
    if not scheduled:
        return CPMResult({}, [], [], None, False, ["no_schedulable_tasks"])
    order = topological_order(scheduled, valid_edges)
    predecessors: dict[UUID, set[UUID]] = defaultdict(set)
    successors: dict[UUID, set[UUID]] = defaultdict(set)
    for source, target in valid_edges:
        predecessors[target].add(source)
        successors[source].add(target)
    earliest_start: dict[UUID, int] = {}
    earliest_finish: dict[UUID, int] = {}
    for task_id in order:
        start = max((earliest_finish[item] + 1 for item in predecessors[task_id]), default=0)
        earliest_start[task_id] = start
        earliest_finish[task_id] = start + (by_id[task_id].duration_days or 1) - 1
    project_finish = max(earliest_finish.values())
    latest_start: dict[UUID, int] = {}
    latest_finish: dict[UUID, int] = {}
    for task_id in reversed(order):
        finish = min(
            (latest_start[item] - 1 for item in successors[task_id]), default=project_finish
        )
        latest_finish[task_id] = finish
        latest_start[task_id] = finish - (by_id[task_id].duration_days or 1) + 1
    metrics: dict[UUID, CPMTask] = {}
    for task_id in order:
        total = latest_start[task_id] - earliest_start[task_id]
        free = min(
            (earliest_start[item] - earliest_finish[task_id] - 1 for item in successors[task_id]),
            default=project_finish - earliest_finish[task_id],
        )
        metrics[task_id] = CPMTask(
            earliest_start=earliest_start[task_id],
            earliest_finish=earliest_finish[task_id],
            latest_start=latest_start[task_id],
            latest_finish=latest_finish[task_id],
            total_float=total,
            free_float=free,
            critical=total == 0,
        )
    critical = [task_id for task_id in order if metrics[task_id].critical]
    critical_set = set(critical)
    roots = [item for item in critical if not (predecessors[item] & critical_set)]
    sequences: list[list[UUID]] = []

    def walk(current: UUID, path: list[UUID]) -> None:
        next_items = [
            item
            for item in sorted(successors[current], key=str)
            if metrics[item].critical and earliest_start[item] == earliest_finish[current] + 1
        ]
        if not next_items:
            sequences.append(path)
        for item in next_items:
            walk(item, [*path, item])

    for root in roots:
        walk(root, [root])
    return CPMResult(metrics, critical, sequences, project_finish + 1, not reasons, reasons)


def propagate_finish_to_start(
    tasks: list[ScheduleTask],
    edges: set[tuple[UUID, UUID]],
    source_task_id: UUID,
    proposed_start: date,
    proposed_finish: date,
) -> dict[UUID, tuple[date, date]]:
    """Return changed dates only; successors move just enough to satisfy FS constraints."""
    if proposed_finish < proposed_start:
        raise ValueError("invalid_task_dates")
    by_id = {task.id: task for task in tasks}
    if source_task_id not in by_id:
        raise ValueError("task_not_found")
    order = topological_order(set(by_id), edges)
    projected: dict[UUID, tuple[date | None, date | None]] = {
        task.id: (task.start, task.finish) for task in tasks
    }
    projected[source_task_id] = (proposed_start, proposed_finish)
    predecessors: dict[UUID, set[UUID]] = defaultdict(set)
    for source, target in edges:
        predecessors[target].add(source)
    for task_id in order:
        if task_id == source_task_id:
            continue
        task = by_id[task_id]
        duration = task.duration_days
        start, finish = projected[task_id]
        constraints = [projected[item][1] for item in predecessors[task_id] if projected[item][1]]
        if not constraints or start is None or finish is None or duration is None:
            continue
        minimum_start = max(constraints) + timedelta(days=1)
        if start < minimum_start:
            projected[task_id] = (minimum_start, minimum_start + timedelta(days=duration - 1))
    return {
        task_id: (start, finish)
        for task_id, (start, finish) in projected.items()
        if start is not None
        and finish is not None
        and (start, finish) != (by_id[task_id].start, by_id[task_id].finish)
    }

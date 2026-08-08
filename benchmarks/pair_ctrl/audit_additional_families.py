#!/usr/bin/env python3
"""Independently reconstruct gold answers for PAIR-CTRL's added families."""

from __future__ import annotations

import argparse
import itertools
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from experiments.exp16.scoring import normalize_answer


def solve_arithmetic_trace(meta: dict[str, Any]) -> str:
    state = int(meta["start"])
    correct: list[int] = []
    for operation in meta["operations"]:
        if operation == "double":
            state *= 2
        elif operation.startswith("add "):
            state += int(operation.split()[1])
        elif operation.startswith("subtract "):
            state -= int(operation.split()[1])
        else:
            raise ValueError(operation)
        correct.append(state)
    for position, (truth, reported) in enumerate(
        zip(correct, meta["reported_states"], strict=True), start=1
    ):
        if truth != int(reported):
            return str(position)
    return "0"


def solve_checksum(meta: dict[str, Any]) -> str:
    failures = [
        position
        for position, (values, reported) in enumerate(
            zip(meta["rows"], meta["reported_totals"], strict=True)
        )
        if sum(map(int, values)) != int(reported)
    ]
    if not failures:
        return "none"
    if len(failures) != 1:
        raise ValueError(f"Expected at most one checksum failure: {failures}")
    return chr(ord("A") + failures[0])


def solve_candidate_answers(meta: dict[str, Any]) -> str:
    target = sum(int(value) for pos, value in enumerate(meta["values"], start=1) if pos % 2)
    correct_a = int(meta["candidate_a"]) == target
    correct_b = int(meta["candidate_b"]) == target
    if correct_a and correct_b:
        return "both"
    if correct_a:
        return "A"
    if correct_b:
        return "B"
    return "neither"


def solve_state_log(meta: dict[str, Any]) -> str:
    state = {key: int(value) for key, value in meta["initial"].items()}
    for update in meta["updates"]:
        match = re.fullmatch(r"change ([A-Z]) by ([+-]\d+)", update)
        if not match:
            raise ValueError(update)
        state[match.group(1)] += int(match.group(2))
    failures = [key for key in sorted(state) if state[key] != int(meta["reported_final"][key])]
    if not failures:
        return "none"
    if len(failures) != 1:
        raise ValueError(f"Expected at most one state-log failure: {failures}")
    return failures[0]


def solve_precedence(meta: dict[str, Any]) -> str:
    valid: list[int] = []
    for position, candidate in enumerate(meta["candidates"]):
        indexes = {task: index for index, task in enumerate(candidate)}
        if all(indexes[left] < indexes[right] for left, right in meta["dependencies"]):
            valid.append(position)
    if len(valid) != 1:
        raise ValueError(f"Expected exactly one valid precedence schedule: {valid}")
    return chr(ord("A") + valid[0])


def solve_route(meta: dict[str, Any]) -> str:
    edges: list[tuple[str, str, int]] = []
    nodes: set[str] = set()
    for endpoints, raw_cost in meta["edges"].items():
        left, right = endpoints.split("-")
        cost = int(raw_cost)
        nodes.update((left, right))
        edges.extend(((left, right, cost), (right, left, cost)))
    start, end = min(nodes), max(nodes)
    distances = {node: 10**9 for node in nodes}
    distances[start] = 0
    for _ in range(len(nodes) - 1):
        updated = False
        for left, right, cost in edges:
            candidate = distances[left] + cost
            if candidate < distances[right]:
                distances[right] = candidate
                updated = True
        if not updated:
            break
    return str(distances[end])


def solve_resource_selection(meta: dict[str, Any]) -> str:
    labels = sorted(meta["costs"])
    candidates: list[tuple[int, int, tuple[str, ...]]] = []
    for length in range(len(labels) + 1):
        for chosen in itertools.combinations(labels, length):
            cost = sum(int(meta["costs"][label]) for label in chosen)
            if cost <= int(meta["budget"]):
                value = sum(int(meta["values"][label]) for label in chosen)
                candidates.append((value, cost, chosen))
    max_value = max(value for value, _, _ in candidates)
    min_cost = min(cost for value, cost, _ in candidates if value == max_value)
    best = min(chosen for value, cost, chosen in candidates if value == max_value and cost == min_cost)
    return ", ".join(best) if best else "none"


def solve_action_sequence(meta: dict[str, Any]) -> str:
    final_values: list[int] = []
    for sequence in meta["candidates"]:
        state = int(meta["start"])
        for action in sequence:
            state = state + 2 if action == "A" else state * 2 if action == "B" else state - 1
        final_values.append(state)
    matches = [position for position, value in enumerate(final_values) if value == int(meta["target"])]
    if len(matches) != 1:
        raise ValueError(f"Expected one action sequence for target: {matches}")
    return chr(ord("A") + matches[0])


def solve_transitive_order(meta: dict[str, Any]) -> str:
    graph: dict[str, set[str]] = {}
    for left, right in meta["facts"]:
        graph.setdefault(left, set()).add(right)
        graph.setdefault(right, set())

    def reaches(start: str, target: str) -> bool:
        frontier = [start]
        visited: set[str] = set()
        while frontier:
            current = frontier.pop()
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            frontier.extend(graph[current])
        return False

    left, right = meta["query"]
    if reaches(left, right):
        return left
    if reaches(right, left):
        return right
    raise ValueError("Transitive query is not determined")


def solve_spatial_composition(meta: dict[str, Any]) -> str:
    moves = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}
    facts = [tuple(fact) for fact in meta["facts"]]
    origin = facts[0][2]
    positions = {origin: (0, 0)}
    unresolved = facts[:]
    while unresolved:
        progress = False
        for fact in unresolved[:]:
            item, relation, reference = fact
            dx, dy = moves[relation]
            if reference in positions:
                rx, ry = positions[reference]
                positions[item] = (rx + dx, ry + dy)
                unresolved.remove(fact)
                progress = True
            elif item in positions:
                ix, iy = positions[item]
                positions[reference] = (ix - dx, iy - dy)
                unresolved.remove(fact)
                progress = True
        if not progress:
            raise ValueError(f"Disconnected spatial facts: {unresolved}")
    sx, sy = positions[meta["source"]]
    tx, ty = positions[meta["target"]]
    vertical = "north" if sy > ty else "south" if sy < ty else ""
    horizontal = "east" if sx > tx else "west" if sx < tx else ""
    return vertical + horizontal if vertical and horizontal else vertical or horizontal or "same"


def solve_record_join(meta: dict[str, Any]) -> str:
    owner = meta["code_owner"][meta["query_code"]]
    return str(meta["owner_group"][owner])


def solve_family_relation(meta: dict[str, Any]) -> str:
    source, target = meta["source"], meta["target"]
    parent_facts = [tuple(fact) for fact in meta["parent_facts"]]
    parents: dict[str, set[str]] = {}
    children: dict[str, set[str]] = {}
    for parent, child in parent_facts:
        parents.setdefault(child, set()).add(parent)
        children.setdefault(parent, set()).add(child)
    if parents.get(source, set()) & parents.get(target, set()):
        return "sibling"
    if any(source in parents.get(parent, set()) for parent in parents.get(target, set())):
        return "grandparent"
    for target_parent in parents.get(target, set()):
        if parents.get(source, set()) & parents.get(target_parent, set()):
            return "aunt_or_uncle"
    raise ValueError(f"Unknown family relation: {source}, {target}")


def solve_deferred_actions(meta: dict[str, Any]) -> str:
    state = int(meta["start"])
    pending = set(meta["deltas"])
    for event in meta["events"]:
        if event in pending:
            state += int(meta["deltas"][event])
            pending.remove(event)
    return str(state)


def solve_interrupt_resume(meta: dict[str, Any]) -> str:
    state = {key: int(value) for key, value in meta["initial"].items()}
    active = "A"
    for event in meta["events"]:
        if event.startswith("SWITCH to "):
            active = event.rsplit(" ", 1)[1]
        else:
            match = re.fullmatch(r"UPDATE active goal by ([+-]\d+)", event)
            if not match:
                raise ValueError(event)
            state[active] += int(match.group(1))
    return f"A={state['A']}, B={state['B']}"


def solve_priority_queue(meta: dict[str, Any]) -> str:
    queue: list[tuple[str, int]] = []
    processed: list[str] = []
    arrival = 0
    for event in meta["events"]:
        if event.startswith("ARRIVE "):
            label = event.split()[1]
            queue.append((label, arrival))
            arrival += 1
        elif event == "PROCESS":
            chosen = max(queue, key=lambda item: (int(meta["priorities"][item[0]]), -item[1]))
            queue.remove(chosen)
            processed.append(chosen[0])
        else:
            raise ValueError(event)
    return ", ".join(processed)


def solve_pending_goals(meta: dict[str, Any]) -> str:
    pending = set(meta["initial"])
    for event in meta["events"]:
        if event == "NOISE":
            continue
        operation, item = event.split()
        if operation == "ADD":
            pending.add(item)
        else:
            pending.discard(item)
    return ", ".join(sorted(pending)) if pending else "none"


SOLVERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "arithmetic_trace_audit": solve_arithmetic_trace,
    "checksum_table_audit": solve_checksum,
    "candidate_answer_comparison": solve_candidate_answers,
    "state_log_audit": solve_state_log,
    "precedence_schedule": solve_precedence,
    "minimum_route_cost": solve_route,
    "resource_constrained_selection": solve_resource_selection,
    "action_sequence_selection": solve_action_sequence,
    "transitive_order_query": solve_transitive_order,
    "spatial_relation_composition": solve_spatial_composition,
    "two_hop_record_join": solve_record_join,
    "family_relation_query": solve_family_relation,
    "deferred_action_execution": solve_deferred_actions,
    "interrupt_and_resume": solve_interrupt_resume,
    "priority_queue_control": solve_priority_queue,
    "pending_goal_control": solve_pending_goals,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args()
    audited = Counter()
    seen: set[str] = set()
    for path in args.files:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                row = json.loads(line)
                task_type = str(row["task_type"])
                if task_type not in SOLVERS:
                    continue
                task_id = str(row["task_id"])
                if task_id in seen:
                    raise ValueError(f"Duplicate audited ID: {task_id}")
                seen.add(task_id)
                reconstructed = SOLVERS[task_type](row["metadata"])
                expected = normalize_answer(str(row["gold"]), str(row["answer_type"]))
                actual = normalize_answer(reconstructed, str(row["answer_type"]))
                if actual != expected:
                    raise ValueError(
                        f"{path}:{line_number} {task_id}: reconstructed={reconstructed!r} "
                        f"gold={row['gold']!r}"
                    )
                audited[task_type] += 1
    missing = sorted(set(SOLVERS) - set(audited))
    if missing:
        raise ValueError(f"No audited instances for: {missing}")
    print(f"Independently reconstructed {sum(audited.values())} tasks")
    print(json.dumps(dict(sorted(audited.items())), indent=2))


if __name__ == "__main__":
    main()

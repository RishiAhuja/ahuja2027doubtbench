"""Generators for monitoring, planning, relational integration, and goal management.

Each generator has the same calling convention as the functions in
doubtbench.generate_tasks: a random stream, a difficulty name, and an index.
The gold answer is computed from the sampled values, and make_task appends the
shared final-answer instruction. doubtbench.generate_split runs these
generators after the families in generate_tasks, one family at a time, each
with its own random stream.
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Callable

from doubtbench.generate_tasks import CognitiveTask, LETTERS, make_task


Generator = Callable[[random.Random, str, int], CognitiveTask]


def monitor_arithmetic_trace(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Monitoring task. Find the first step whose reported state disagrees with the true running total.

    The answer is 0 when every reported state is right.
    """
    n_steps = {"easy": 3, "medium": 5, "hard": 7}[difficulty]
    start = rng.randint(3, 20)
    state = start
    operations: list[str] = []
    correct_states: list[int] = []
    for _ in range(n_steps):
        op = rng.choice(["add", "subtract", "double"])
        if op == "add":
            value = rng.randint(1, 8)
            state += value
            operations.append(f"add {value}")
        elif op == "subtract":
            value = rng.randint(1, 6)
            state -= value
            operations.append(f"subtract {value}")
        else:
            state *= 2
            operations.append("double")
        correct_states.append(state)

    error_step = rng.choice([0] + list(range(1, n_steps + 1)))
    reported = correct_states[:]
    if error_step:
        delta = rng.choice([-3, -2, -1, 1, 2, 3])
        reported[error_step - 1] += delta
    lines = [
        f"Step {step}: {operation}; reported state = {claim}"
        for step, (operation, claim) in enumerate(zip(operations, reported, strict=True), start=1)
    ]
    prompt = (
        f"Start at {start}. Apply every operation to the true state from the preceding step.\n\n"
        + "\n".join(lines)
        + "\n\nWhich step first reports a state different from the true state? "
        "Answer 0 if every reported state is accurate."
    )
    return make_task(
        "monitoring",
        "arithmetic_trace_audit",
        difficulty,
        index,
        prompt,
        str(error_step),
        "integer",
        {
            "start": start,
            "operations": operations,
            "correct_states": correct_states,
            "reported_states": reported,
            "error_step": error_step,
        },
    )


def monitor_checksum_table(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Monitoring task. Find the row whose reported total is not the sum of its three values.

    The answer is none when every total is right.
    """
    n_rows = {"easy": 3, "medium": 4, "hard": 6}[difficulty]
    labels = LETTERS[:n_rows]
    values = [[rng.randint(1, 20) for _ in range(3)] for _ in labels]
    correct_totals = [sum(row) for row in values]
    error_row = rng.choice([-1] + list(range(n_rows)))
    reported = correct_totals[:]
    if error_row >= 0:
        reported[error_row] += rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
    rows = [
        f"Row {label}: values={','.join(map(str, row))}; reported total={claim}"
        for label, row, claim in zip(labels, values, reported, strict=True)
    ]
    gold = "none" if error_row < 0 else labels[error_row]
    prompt = (
        "Each reported total should equal the sum of the three values in its row.\n\n"
        + "\n".join(rows)
        + "\n\nWhich row has an inaccurate reported total? Answer its row letter, "
        "or none if all totals are accurate."
    )
    return make_task(
        "monitoring",
        "checksum_table_audit",
        difficulty,
        index,
        prompt,
        gold,
        "string",
        {
            "rows": values,
            "correct_totals": correct_totals,
            "reported_totals": reported,
            "error_row": gold,
        },
    )


def monitor_candidate_answers(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Monitoring task. Decide whether A, B, both, or neither equals the sum of the odd positions."""
    n_values = {"easy": 3, "medium": 5, "hard": 7}[difficulty]
    values = [rng.randint(1, 15) for _ in range(n_values)]
    # Position numbers start at 1, matching the request for odd-numbered positions.
    target = sum(value for pos, value in enumerate(values, start=1) if pos % 2 == 1)
    correct_a = rng.choice([True, False])
    correct_b = rng.choice([True, False])
    answer_a = target if correct_a else target + rng.choice([-3, -2, -1, 1, 2, 3])
    answer_b = target if correct_b else target + rng.choice([-3, -2, -1, 1, 2, 3])
    if correct_a and correct_b:
        gold = "both"
    elif correct_a:
        gold = "A"
    elif correct_b:
        gold = "B"
    else:
        gold = "neither"
    prompt = (
        "Add the values in odd-numbered positions only.\n\n"
        f"Values: {', '.join(map(str, values))}\n"
        f"Candidate A: {answer_a}\nCandidate B: {answer_b}\n\n"
        "Which candidate gives the required sum? Answer A, B, both, or neither."
    )
    return make_task(
        "monitoring",
        "candidate_answer_comparison",
        difficulty,
        index,
        prompt,
        gold,
        "string",
        {
            "values": values,
            "target": target,
            "candidate_a": answer_a,
            "candidate_b": answer_b,
        },
    )


def monitor_state_log(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Monitoring task. Find the key whose reported final value disagrees with the updates.

    The answer is none when every reported value is right.
    """
    n_keys = {"easy": 3, "medium": 4, "hard": 6}[difficulty]
    keys = LETTERS[:n_keys]
    initial = {key: rng.randint(1, 20) for key in keys}
    final_state = dict(initial)
    updates: list[str] = []
    for _ in range({"easy": 3, "medium": 5, "hard": 8}[difficulty]):
        key = rng.choice(keys)
        delta = rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        final_state[key] += delta
        updates.append(f"change {key} by {delta:+d}")
    reported = dict(final_state)
    error_key = rng.choice(["none"] + keys)
    if error_key != "none":
        reported[error_key] += rng.choice([-2, -1, 1, 2])
    prompt = (
        "Apply the updates to the initial key values.\n\nInitial: "
        + ", ".join(f"{key}={initial[key]}" for key in keys)
        + "\nUpdates:\n"
        + "\n".join(f"{i}. {update}" for i, update in enumerate(updates, start=1))
        + "\nReported final values: "
        + ", ".join(f"{key}={reported[key]}" for key in keys)
        + "\n\nWhich key has an inaccurate reported final value? Answer its key, "
        "or none if every reported value is accurate."
    )
    return make_task(
        "monitoring",
        "state_log_audit",
        difficulty,
        index,
        prompt,
        error_key,
        "string",
        {
            "initial": initial,
            "updates": updates,
            "correct_final": final_state,
            "reported_final": reported,
            "error_key": error_key,
        },
    )


def planning_precedence_schedule(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Planning task. Choose the letter of the schedule that meets every precedence requirement."""
    n_tasks = {"easy": 4, "medium": 6, "hard": 8}[difficulty]
    tasks = LETTERS[:n_tasks]
    correct = tasks[:]
    rng.shuffle(correct)
    dependencies = [(correct[i - 1], correct[i]) for i in range(1, n_tasks)]
    if difficulty != "easy":
        dependencies.extend((correct[i - 2], correct[i]) for i in range(2, n_tasks, 2))

    candidates = [correct[:]]
    for dep_left, dep_right in dependencies[:3]:
        invalid = correct[:]
        left_pos, right_pos = invalid.index(dep_left), invalid.index(dep_right)
        invalid[left_pos], invalid[right_pos] = invalid[right_pos], invalid[left_pos]
        if invalid not in candidates:
            candidates.append(invalid)
    while len(candidates) < 4:
        invalid = correct[:]
        rng.shuffle(invalid)
        if invalid not in candidates and any(invalid.index(a) > invalid.index(b) for a, b in dependencies):
            candidates.append(invalid)
    rng.shuffle(candidates)
    labels = LETTERS[:4]
    gold = labels[candidates.index(correct)]
    prompt = (
        "Choose the schedule that satisfies every precedence requirement.\n\nRequirements:\n"
        + "\n".join(f"- {left} must occur before {right}" for left, right in dependencies)
        + "\n\nCandidate schedules:\n"
        + "\n".join(f"{label}: {' '.join(order)}" for label, order in zip(labels, candidates, strict=True))
        + "\n\nWhich candidate schedule is valid? Answer its letter."
    )
    return make_task(
        "planning",
        "precedence_schedule",
        difficulty,
        index,
        prompt,
        gold,
        "string",
        {"dependencies": dependencies, "candidates": candidates, "valid_label": gold},
    )


def _shortest_cost(nodes: list[str], edges: dict[tuple[str, str], int], start: str, end: str) -> int:
    """Undirected shortest-path cost. A node that cannot be reached stays at a large sentinel value."""
    distances = {node: 10**9 for node in nodes}
    distances[start] = 0
    remaining = set(nodes)
    while remaining:
        current = min(remaining, key=lambda node: distances[node])
        remaining.remove(current)
        for (left, right), cost in edges.items():
            if left == current and right in remaining:
                distances[right] = min(distances[right], distances[current] + cost)
            elif right == current and left in remaining:
                distances[left] = min(distances[left], distances[current] + cost)
    return distances[end]


def planning_route_cost(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Planning task. Report the minimum travel cost from the first letter to the last."""
    n_nodes = {"easy": 4, "medium": 6, "hard": 8}[difficulty]
    nodes = LETTERS[:n_nodes]
    edges: dict[tuple[str, str], int] = {}
    # Consecutive letters are always linked, so the first node can reach the last.
    for pos in range(n_nodes - 1):
        edges[(nodes[pos], nodes[pos + 1])] = rng.randint(1, 6)
    extra_target = {"easy": 1, "medium": 4, "hard": 8}[difficulty]
    while len(edges) < n_nodes - 1 + extra_target:
        left_pos, right_pos = sorted(rng.sample(range(n_nodes), 2))
        if right_pos - left_pos == 1:
            continue
        edge = (nodes[left_pos], nodes[right_pos])
        edges.setdefault(edge, rng.randint(4, 14))
    shortest = _shortest_cost(nodes, edges, nodes[0], nodes[-1])
    prompt = (
        "Travel costs are undirected. Find the minimum total cost from "
        f"{nodes[0]} to {nodes[-1]}.\n\nEdges:\n"
        + "\n".join(f"{left}-{right}: {cost}" for (left, right), cost in sorted(edges.items()))
        + "\n\nWhat is the minimum total travel cost?"
    )
    return make_task(
        "planning",
        "minimum_route_cost",
        difficulty,
        index,
        prompt,
        str(shortest),
        "integer",
        {"nodes": nodes, "edges": {f"{a}-{b}": cost for (a, b), cost in edges.items()}, "minimum_cost": shortest},
    )


def planning_resource_selection(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Planning task. Choose the affordable project list with the greatest total value.

    Equal values go to the lower cost, then to the alphabetically earliest list.
    """
    n_items = {"easy": 4, "medium": 6, "hard": 8}[difficulty]
    labels = LETTERS[:n_items]
    costs = [rng.randint(2, 9) for _ in labels]
    values = [rng.randint(3, 16) for _ in labels]
    budget = max(5, int(sum(costs) * {"easy": 0.50, "medium": 0.45, "hard": 0.40}[difficulty]))
    candidates: list[tuple[int, int, tuple[str, ...]]] = []
    for mask in range(1 << n_items):
        chosen = tuple(labels[i] for i in range(n_items) if mask & (1 << i))
        cost = sum(costs[i] for i in range(n_items) if mask & (1 << i))
        value = sum(values[i] for i in range(n_items) if mask & (1 << i))
        if cost <= budget:
            candidates.append((value, cost, chosen))
    best_value = max(item[0] for item in candidates)
    best_cost = min(item[1] for item in candidates if item[0] == best_value)
    best = min(item[2] for item in candidates if item[0] == best_value and item[1] == best_cost)
    gold = ", ".join(best) if best else "none"
    prompt = (
        f"Select projects with total cost at most {budget}. Maximize total value. "
        "If value ties, choose the lower total cost; if still tied, choose the "
        "alphabetically earliest list.\n\n"
        + "\n".join(
            f"{label}: cost={cost}, value={value}"
            for label, cost, value in zip(labels, costs, values, strict=True)
        )
        + "\n\nWhich projects should be selected? Give their letters in alphabetical order."
    )
    return make_task(
        "planning",
        "resource_constrained_selection",
        difficulty,
        index,
        prompt,
        gold,
        "comma_list",
        {"budget": budget, "costs": dict(zip(labels, costs, strict=True)), "values": dict(zip(labels, values, strict=True)), "selected": best},
    )


def _apply_action_sequence(start: int, actions: tuple[str, ...]) -> int:
    """Apply A by adding 2, B by doubling, and C by subtracting 1.

    The prompt shows those actions as X, Y, and Z.
    """
    state = start
    for action in actions:
        if action == "A":
            state += 2
        elif action == "B":
            state *= 2
        else:
            state -= 1
    return state


def planning_action_sequence(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Planning task. Choose the candidate that finishes at the requested number.

    Up to 200 draws are tried. The draw stops when one of the four candidates has
    a final value that none of the others share. Actions stored as A, B, and C
    are shown in the prompt as X, Y, and Z.
    """
    length = {"easy": 3, "medium": 4, "hard": 5}[difficulty]
    action_space = tuple("ABC")
    for _ in range(200):
        start = rng.randint(1, 9)
        candidates = rng.sample(list(itertools.product(action_space, repeat=length)), 4)
        values = [_apply_action_sequence(start, candidate) for candidate in candidates]
        unique_positions = [pos for pos, value in enumerate(values) if values.count(value) == 1]
        if unique_positions:
            target_pos = rng.choice(unique_positions)
            break
    else:
        raise RuntimeError("Could not construct a unique action-sequence target")
    labels = LETTERS[:4]
    gold = labels[target_pos]
    prompt = (
        f"Start at {start}. Action X adds 2, action Y doubles, and action Z subtracts 1. "
        "Apply actions from left to right.\n\n"
        + "\n".join(
            # Stored actions A, B, and C are shown as X, Y, and Z.
            f"{label}: {' '.join({'A': 'X', 'B': 'Y', 'C': 'Z'}[action] for action in sequence)}"
            for label, sequence in zip(labels, candidates, strict=True)
        )
        + f"\n\nWhich action sequence finishes at {values[target_pos]}? Answer its candidate letter."
    )
    return make_task(
        "planning",
        "action_sequence_selection",
        difficulty,
        index,
        prompt,
        gold,
        "string",
        {"start": start, "candidates": candidates, "final_values": values, "target": values[target_pos]},
    )


def relational_transitive_order(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Relational task. Combine earlier-than facts and name the item that occurs earlier."""
    n_items = {"easy": 4, "medium": 6, "hard": 8}[difficulty]
    order = LETTERS[:n_items]
    rng.shuffle(order)
    facts = [(order[pos], order[pos + 1]) for pos in range(n_items - 1)]
    rng.shuffle(facts)
    left_pos, right_pos = sorted(rng.sample(range(n_items), 2))
    query = [order[left_pos], order[right_pos]]
    rng.shuffle(query)
    gold = order[left_pos]
    prompt = (
        "Each fact states that one item occurs earlier than another. Combine the facts transitively.\n\n"
        + "\n".join(f"- {left} is earlier than {right}" for left, right in facts)
        + f"\n\nWhich occurs earlier, {query[0]} or {query[1]}? Answer the item letter."
    )
    return make_task(
        "relational_integration",
        "transitive_order_query",
        difficulty,
        index,
        prompt,
        gold,
        "string",
        {"order": order, "facts": facts, "query": query},
    )


def _qualitative_direction(dx: int, dy: int) -> str:
    """Compass name for one grid step. Zero on both axes returns the word same."""
    vertical = "north" if dy > 0 else "south" if dy < 0 else ""
    horizontal = "east" if dx > 0 else "west" if dx < 0 else ""
    return vertical + horizontal if vertical and horizontal else vertical or horizontal or "same"


def relational_spatial_composition(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Relational task. Place the items on a grid and name the compass direction between two of them.

    Pairs are drawn until the positions differ or 50 draws have been made.
    """
    n_items = {"easy": 4, "medium": 6, "hard": 8}[difficulty]
    labels = LETTERS[:n_items]
    moves = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}
    positions = {labels[0]: (0, 0)}
    facts: list[tuple[str, str, str]] = []
    for pos in range(1, n_items):
        relation = rng.choice(list(moves))
        dx, dy = moves[relation]
        previous = labels[pos - 1]
        current = labels[pos]
        px, py = positions[previous]
        positions[current] = (px + dx, py + dy)
        facts.append((current, relation, previous))
    rng.shuffle(facts)
    for _ in range(50):
        source, target = rng.sample(labels, 2)
        sx, sy = positions[source]
        tx, ty = positions[target]
        gold = _qualitative_direction(sx - tx, sy - ty)
        if gold != "same":
            break
    prompt = (
        "Combine the spatial facts on a square grid.\n\n"
        + "\n".join(f"- {item} is {relation} of {reference}" for item, relation, reference in facts)
        + f"\n\nWhat is the direction of {source} relative to {target}? "
        "Answer north, south, east, west, northeast, northwest, southeast, or southwest."
    )
    return make_task(
        "relational_integration",
        "spatial_relation_composition",
        difficulty,
        index,
        prompt,
        gold,
        "string",
        {"positions": positions, "facts": facts, "source": source, "target": target},
    )


def relational_record_join(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Relational task. Follow a code to its owner, then that owner to a group."""
    n_records = {"easy": 4, "medium": 6, "hard": 8}[difficulty]
    codes = [f"K{number}" for number in range(1, n_records + 1)]
    owners = [f"P{number}" for number in range(1, n_records + 1)]
    groups = [f"G{number}" for number in range(1, n_records + 1)]
    rng.shuffle(owners)
    rng.shuffle(groups)
    code_owner = dict(zip(codes, owners, strict=True))
    owner_group = dict(zip(owners, groups, strict=True))
    query_code = rng.choice(codes)
    gold = owner_group[code_owner[query_code]]
    first_table = [f"{code} -> {owner}" for code, owner in code_owner.items()]
    second_table = [f"{owner} -> {group}" for owner, group in owner_group.items()]
    rng.shuffle(first_table)
    rng.shuffle(second_table)
    prompt = (
        "Join the two lookup tables through the owner identifier.\n\nCode to owner:\n"
        + "\n".join(first_table)
        + "\n\nOwner to group:\n"
        + "\n".join(second_table)
        + f"\n\nWhich group is associated with code {query_code}?"
    )
    return make_task(
        "relational_integration",
        "two_hop_record_join",
        difficulty,
        index,
        prompt,
        gold,
        "string",
        {"code_owner": code_owner, "owner_group": owner_group, "query_code": query_code},
    )


def relational_family_query(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Relational task. Name the relation: sibling, grandparent, or aunt_or_uncle."""
    names = ["Ari", "Bea", "Cleo", "Dara", "Enzo", "Faye", "Gus", "Hana"]
    rng.shuffle(names)
    grandparent, parent_a, parent_b, child_a, child_b, grandchild = names[:6]
    facts = [
        (grandparent, parent_a),
        (grandparent, parent_b),
        (parent_a, child_a),
        (parent_a, child_b),
        (child_a, grandchild),
    ]
    if difficulty == "easy":
        source, target, gold = child_a, child_b, "sibling"
    elif difficulty == "medium":
        source, target, gold = grandparent, child_b, "grandparent"
    else:
        source, target, gold = parent_b, child_a, "aunt_or_uncle"
    rng.shuffle(facts)
    prompt = (
        "Use the parent facts to determine the requested family relation. Gender is unspecified.\n\n"
        + "\n".join(f"- {parent} is a parent of {child}" for parent, child in facts)
        + f"\n\nWhat is {source}'s relation to {target}? "
        "Answer sibling, grandparent, or aunt_or_uncle."
    )
    return make_task(
        "relational_integration",
        "family_relation_query",
        difficulty,
        index,
        prompt,
        gold,
        "string",
        {"parent_facts": facts, "source": source, "target": target},
    )


def goal_deferred_actions(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Goal-management task. Apply each signal's change only the first time that signal appears."""
    n_rules = {"easy": 2, "medium": 3, "hard": 4}[difficulty]
    signals = [f"S{number}" for number in range(1, n_rules + 1)]
    deltas = {signal: rng.choice([-5, -3, -2, 2, 3, 5]) for signal in signals}
    start = rng.randint(5, 20)
    events = signals[:] + [rng.choice(signals) for _ in range(n_rules)] + ["NOISE"] * n_rules
    rng.shuffle(events)
    state = start
    pending = set(signals)
    fired: list[str] = []
    for event in events:
        if event in pending:
            state += deltas[event]
            pending.remove(event)
            fired.append(event)
    prompt = (
        f"Start at {start}. Each deferred action executes only the first time its signal appears.\n\n"
        + "\n".join(f"- On first {signal}: change the value by {delta:+d}" for signal, delta in deltas.items())
        + "\n\nEvent stream: "
        + ", ".join(events)
        + "\n\nWhat is the final value after processing the complete event stream?"
    )
    return make_task(
        "goal_management",
        "deferred_action_execution",
        difficulty,
        index,
        prompt,
        str(state),
        "integer",
        {"start": start, "deltas": deltas, "events": events, "fired": fired},
    )


def goal_interrupt_resume(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Goal-management task. Update the active counter, and switch counters when an event says to."""
    state = {"A": rng.randint(3, 15), "B": rng.randint(3, 15)}
    initial = dict(state)
    active = "A"
    events: list[str] = []
    n_events = {"easy": 5, "medium": 8, "hard": 12}[difficulty]
    for _ in range(n_events):
        if rng.random() < 0.35:
            active = "B" if active == "A" else "A"
            events.append(f"SWITCH to {active}")
        else:
            delta = rng.choice([-4, -2, -1, 1, 2, 4])
            state[active] += delta
            events.append(f"UPDATE active goal by {delta:+d}")
    gold = f"A={state['A']}, B={state['B']}"
    prompt = (
        f"Maintain two goal counters. Initially A is active. Start values: A={initial['A']}, B={initial['B']}. "
        "An UPDATE changes only the currently active goal; SWITCH changes which goal is active.\n\n"
        + "\n".join(f"{pos}. {event}" for pos, event in enumerate(events, start=1))
        + "\n\nWhat are the final values of A and B?"
    )
    return make_task(
        "goal_management",
        "interrupt_and_resume",
        difficulty,
        index,
        prompt,
        gold,
        "assignment_list",
        {"initial": initial, "events": events, "final": state},
    )


def goal_priority_queue(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Goal-management task. List goals in the order they are processed.

    While goals remain and the queue is empty, the next event is an arrival.
    While goals remain and the queue is not empty, the next event is an arrival
    when a random draw is below 0.65, and a processing step otherwise. Processing
    removes the pending goal with the highest priority, using the earlier arrival
    when priorities tie.
    """
    n_items = {"easy": 4, "medium": 6, "hard": 8}[difficulty]
    labels = LETTERS[:n_items]
    priorities = {label: rng.randint(1, 4) for label in labels}
    events: list[str] = []
    queue: list[tuple[str, int]] = []
    processed: list[str] = []
    arrival_index = 0
    while arrival_index < n_items or queue:
        should_arrive = arrival_index < n_items and (not queue or rng.random() < 0.65)
        if should_arrive:
            label = labels[arrival_index]
            queue.append((label, arrival_index))
            events.append(f"ARRIVE {label} priority {priorities[label]}")
            arrival_index += 1
        else:
            chosen = max(queue, key=lambda item: (priorities[item[0]], -item[1]))
            queue.remove(chosen)
            processed.append(chosen[0])
            events.append("PROCESS")
    prompt = (
        "Maintain a pending-goal queue. ARRIVE adds a goal. PROCESS removes the pending goal with "
        "highest numeric priority; ties go to the earlier arrival.\n\n"
        + "\n".join(f"{pos}. {event}" for pos, event in enumerate(events, start=1))
        + "\n\nGive the goals in the order they are processed."
    )
    return make_task(
        "goal_management",
        "priority_queue_control",
        difficulty,
        index,
        prompt,
        ", ".join(processed),
        "comma_list",
        {"priorities": priorities, "events": events, "processed": processed},
    )


def goal_pending_set(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Goal-management task. List the goals that are still pending, in alphabetical order.

    ADD inserts a goal that is not already pending. If every available letter is
    already pending, that draw removes one goal instead. COMPLETE and CANCEL both
    remove a goal. NOISE is recorded when a removal is drawn and nothing is pending.
    The answer is none when the set is empty.
    """
    n_initial = {"easy": 3, "medium": 5, "hard": 7}[difficulty]
    available = LETTERS[: n_initial + 4]
    pending = set(available[:n_initial])
    initial = sorted(pending)
    events: list[str] = []
    for _ in range({"easy": 4, "medium": 7, "hard": 10}[difficulty]):
        operation = rng.choice(["ADD", "COMPLETE", "CANCEL"])
        if operation == "ADD":
            candidates = [item for item in available if item not in pending]
            if not candidates:
                # No letter is left to add, so this draw removes a pending goal.
                operation = "COMPLETE"
            else:
                item = rng.choice(candidates)
                pending.add(item)
                events.append(f"ADD {item}")
                continue
        if pending:
            item = rng.choice(sorted(pending))
            pending.remove(item)
            events.append(f"{operation} {item}")
        else:
            events.append("NOISE")
    gold = ", ".join(sorted(pending)) if pending else "none"
    prompt = (
        "Track the pending goal set. ADD inserts a goal; COMPLETE and CANCEL both remove it. "
        "NOISE changes nothing.\n\nInitial pending goals: "
        + ", ".join(initial)
        + "\nEvents:\n"
        + "\n".join(f"{pos}. {event}" for pos, event in enumerate(events, start=1))
        + "\n\nWhich goals remain pending? Give them in alphabetical order, or none."
    )
    return make_task(
        "goal_management",
        "pending_goal_control",
        difficulty,
        index,
        prompt,
        gold,
        "comma_list",
        {"initial": initial, "events": events, "remaining": sorted(pending)},
    )


# Earlier generators receive any leftover items. A family uses this order and
# one random stream, so changing the order would change the generated tasks.
DOUBTBENCH_ADDITIONAL_GENERATORS: dict[str, list[Generator]] = {
    "monitoring": [
        monitor_arithmetic_trace,
        monitor_checksum_table,
        monitor_candidate_answers,
        monitor_state_log,
    ],
    "planning": [
        planning_precedence_schedule,
        planning_route_cost,
        planning_resource_selection,
        planning_action_sequence,
    ],
    "relational_integration": [
        relational_transitive_order,
        relational_spatial_composition,
        relational_record_join,
        relational_family_query,
    ],
    "goal_management": [
        goal_deferred_actions,
        goal_interrupt_resume,
        goal_priority_queue,
        goal_pending_set,
    ],
}

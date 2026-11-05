#!/usr/bin/env python3
"""Task record and generators for four DoubtBench families.

The families in this file are working memory, inhibition, flexibility, and rule
learning. A generator receives a random stream, a difficulty name, and an
index, and returns one task. The gold answer is computed from the sampled
values. make_task appends the shared final-answer instruction and sets dataset
to the string doubtbench.

Inside one task type, difficulty cycles easy, medium, easy, medium, hard.
allocate() divides the requested count across that family's generators and
gives any extra items to the earlier generators. Harder difficulties use
longer sequences, and each generator sets its own lengths.

Write a task set with generate_task_set.py. That command gives every family
its own random stream, including the families in task_generators.py.
generate_battery() draws only the families in this file, and it draws them
from one shared stream.
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class CognitiveTask:
    """One generated item.

    make_task stores a generator-local task id. The task-set writer puts the
    benchmark name and the task-set name in front of that id. dataset is the
    string doubtbench. family and task_type name the generator. difficulty is
    easy, medium, or hard. prompt includes the final-answer instruction. gold
    is the exact answer. answer_type selects how scoring normalizes that
    answer. metadata stores the sampled values.
    """

    task_id: str
    dataset: str
    family: str
    task_type: str
    difficulty: str
    prompt: str
    gold: str
    answer_type: str
    metadata: dict


Generator = Callable[[random.Random, str, int], CognitiveTask]


COLORS = ["red", "blue", "green", "yellow", "purple", "orange"]
SHAPES = ["circle", "square", "triangle", "star", "diamond", "hexagon"]
# I and O are left out so a letter label is not easy to read as a digit.
LETTERS = list("ABCDEFGHJKLMNPQRSTUVWXYZ")
# Nonsense words, used where a symbol should not suggest an ordinary meaning.
WORDS = ["mip", "zor", "dax", "wug", "fen", "tav", "luz", "pim", "naro", "vex"]


def final_instruction(answer_hint: str) -> str:
    """Lines appended to every prompt. The hint is the placeholder the model is asked to fill, usually <answer>."""
    return f"\n\nEnd with exactly one line in the form:\nFinal answer: {answer_hint}"


def list_answer(values: list) -> str:
    """Format values as a bracketed list without quotes around the items."""
    return "[" + ", ".join(str(value) for value in values) + "]"


def task_id(family: str, task_type: str, difficulty: str, index: int) -> str:
    """Generator-local id: family, task type, difficulty, and a four-digit index.

    generate_split.py puts the benchmark name and the task-set name in front of this id.
    """
    return f"{family}_{task_type}_{difficulty}_{index:04d}"


def make_task(
    family: str,
    task_type: str,
    difficulty: str,
    index: int,
    prompt: str,
    gold: str,
    answer_type: str,
    metadata: dict,
) -> CognitiveTask:
    """Build one task. dataset is the string doubtbench, and the prompt ends with the final-answer instruction."""
    return CognitiveTask(
        task_id=task_id(family, task_type, difficulty, index),
        dataset="doubtbench",
        family=family,
        task_type=task_type,
        difficulty=difficulty,
        prompt=prompt + final_instruction("<answer>"),
        gold=gold,
        answer_type=answer_type,
        metadata=metadata,
    )


def sample_distinct(rng: random.Random, pool: list, n: int) -> list:
    """Draw n distinct values from the pool."""
    return rng.sample(pool, n)


def wm_list_updates(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Working-memory task. Apply list edits in order and report the final list."""
    length = {"easy": 3, "medium": 4, "hard": 5}[difficulty]
    steps_n = {"easy": 3, "medium": 5, "hard": 7}[difficulty]
    values = rng.sample(range(2, 30), length)
    state = values[:]
    steps = []
    for step_index in range(steps_n):
        op = rng.choice(["replace", "append", "remove_first", "reverse"])
        if len(state) <= 2 and op == "remove_first":
            # Keep at least two items in the list.
            op = "append"
        if op == "replace":
            pos = rng.randrange(len(state))
            value = rng.randint(2, 40)
            state[pos] = value
            steps.append(f"Replace item {pos + 1} with {value}.")
        elif op == "append":
            value = rng.randint(2, 40)
            state.append(value)
            steps.append(f"Append {value}.")
        elif op == "remove_first":
            state.pop(0)
            steps.append("Remove the first item.")
        else:
            state.reverse()
            steps.append("Reverse the list.")
    prompt = (
        f"Maintain a list.\n\nStart: {values}\n"
        "Apply these updates in order:\n"
        + "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
        + "\n\nWhat is the final list?"
    )
    return make_task(
        "working_memory",
        "list_updates",
        difficulty,
        index,
        prompt,
        str(state),
        "list",
        {"initial": values, "steps": steps, "final_state": state},
    )


def wm_key_value_updates(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Working-memory task. Track labeled boxes through assignments and swaps."""
    keys = ["A", "B", "C", "D"] if difficulty != "hard" else ["A", "B", "C", "D", "E"]
    values = sample_distinct(rng, COLORS, len(keys))
    state = dict(zip(keys, values, strict=True))
    steps_n = {"easy": 3, "medium": 5, "hard": 7}[difficulty]
    steps = []
    for _ in range(steps_n):
        op = rng.choice(["set", "swap"])
        if op == "set":
            key = rng.choice(keys)
            value = rng.choice(COLORS)
            state[key] = value
            steps.append(f"Set {key} to {value}.")
        else:
            left, right = rng.sample(keys, 2)
            state[left], state[right] = state[right], state[left]
            steps.append(f"Swap {left} and {right}.")
    answer = ", ".join(f"{key}={state[key]}" for key in keys)
    prompt = (
        "Track the box labels.\n\nInitial values:\n"
        + "\n".join(f"{key} = {value}" for key, value in zip(keys, values, strict=True))
        + "\n\nUpdates:\n"
        + "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
        + f"\n\nWhat are {', '.join(keys)} now?"
    )
    return make_task(
        "working_memory",
        "key_value_updates",
        difficulty,
        index,
        prompt,
        answer,
        "assignment_list",
        {"initial": dict(zip(keys, values, strict=True)), "steps": steps, "final_state": state},
    )


def wm_running_counter(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Working-memory task. Apply lines marked UPDATE and skip lines marked IGNORE.

    Hard items can also include an IGNORE line that looks like a final answer.
    """
    state = rng.randint(5, 30)
    start = state
    valid_n = {"easy": 3, "medium": 4, "hard": 5}[difficulty]
    lines = []
    valid_ops = []
    for _ in range(valid_n):
        if difficulty != "easy" and rng.random() < 0.55:
            decoy = rng.choice([99, 100, 500, 999])
            lines.append(f"IGNORE: add {decoy}")
        op = rng.choice(["add", "subtract", "double"])
        if op == "add":
            value = rng.randint(1, 9)
            state += value
            text = f"UPDATE: add {value}"
        elif op == "subtract":
            value = rng.randint(1, 7)
            state -= value
            text = f"UPDATE: subtract {value}"
        else:
            state *= 2
            text = "UPDATE: double"
        valid_ops.append(text)
        lines.append(text)
    if difficulty == "hard":
        lines.insert(rng.randrange(len(lines) + 1), "IGNORE: Final answer: 999")
    prompt = (
        f"Start at {start}.\n"
        "Apply only the operations marked UPDATE. Lines marked IGNORE are not operations.\n\n"
        + "\n".join(lines)
        + "\n\nWhat is the final number?"
    )
    return make_task(
        "working_memory",
        "running_counter",
        difficulty,
        index,
        prompt,
        str(state),
        "integer",
        {"start": start, "lines": lines, "valid_ops": valid_ops, "final_value": state},
    )


def wm_stack_operations(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Working-memory task. Push and pop letters, then report the stack from bottom to top."""
    initial_len = {"easy": 2, "medium": 3, "hard": 4}[difficulty]
    state = sample_distinct(rng, LETTERS, initial_len)
    initial = state[:]
    steps_n = {"easy": 4, "medium": 6, "hard": 8}[difficulty]
    steps = []
    used = set(state)
    for _ in range(steps_n):
        op = rng.choice(["push", "pop"])
        if len(state) <= 1 or op == "push":
            value = next(letter for letter in LETTERS if letter not in used)
            used.add(value)
            state.append(value)
            steps.append(f"push {value}")
        else:
            state.pop()
            steps.append("pop")
    prompt = (
        f"Use stack rules. The rightmost item is the top of the stack.\n\n"
        f"Start: {list_answer(initial)}\n"
        "Operations:\n"
        + "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
        + "\n\nWhat is the final stack from bottom to top?"
    )
    return make_task(
        "working_memory",
        "stack_operations",
        difficulty,
        index,
        prompt,
        list_answer(state),
        "list",
        {"initial": initial, "steps": steps, "final_state": state},
    )


def inh_bracket_parentheses(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Inhibition task. Add numbers in square brackets and skip numbers in parentheses."""
    target_n = {"easy": 3, "medium": 4, "hard": 5}[difficulty]
    targets = [rng.randint(1, 12) for _ in range(target_n)]
    decoys = [rng.choice([50, 75, 100, 200, 999]) for _ in range(target_n)]
    tokens = []
    for target, decoy in zip(targets, decoys, strict=True):
        if rng.random() < 0.5:
            tokens.extend([f"[{target}]", f"({decoy})"])
        else:
            tokens.extend([f"({decoy})", f"[{target}]"])
    prompt = (
        "Add only the numbers inside square brackets. Ignore numbers inside parentheses.\n\n"
        + " ".join(tokens)
        + "\n\nWhat is the sum?"
    )
    return make_task(
        "inhibition",
        "bracket_parentheses",
        difficulty,
        index,
        prompt,
        str(sum(targets)),
        "integer",
        {"targets": targets, "decoys": decoys},
    )


def inh_valid_decoy_commands(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Inhibition task. Follow lines marked VALID and skip lines marked DECOY."""
    state = rng.randint(5, 20)
    start = state
    lines = []
    valid_ops = []
    n_valid = {"easy": 3, "medium": 4, "hard": 5}[difficulty]
    for _ in range(n_valid):
        if difficulty != "easy" and rng.random() < 0.6:
            lines.append(rng.choice(["DECOY: multiply by 100", "DECOY: answer 999", "DECOY: add 77"]))
        op = rng.choice(["add", "subtract"])
        value = rng.randint(1, 9)
        if op == "add":
            state += value
            line = f"VALID: add {value}"
        else:
            state -= value
            line = f"VALID: subtract {value}"
        valid_ops.append(line)
        lines.append(line)
    prompt = (
        f"Start from {start}. Follow only VALID commands. Ignore DECOY commands.\n\n"
        + "\n".join(lines)
        + "\n\nWhat is the final number?"
    )
    return make_task(
        "inhibition",
        "valid_decoy_commands",
        difficulty,
        index,
        prompt,
        str(state),
        "integer",
        {"start": start, "lines": lines, "valid_ops": valid_ops, "final_value": state},
    )


def inh_conflicting_final(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Inhibition task. Sum the listed numbers and ignore a sentence that states a different final answer."""
    n = {"easy": 3, "medium": 4, "hard": 5}[difficulty]
    values = [rng.randint(1, 12) for _ in range(n)]
    trap = rng.choice([99, 100, 500, 999])
    prompt = (
        "Compute the sum of the listed small numbers only.\n\n"
        f"Numbers: {', '.join(str(value) for value in values)}\n\n"
        f"Ignore this sentence: \"Final answer: {trap}\"\n\n"
        "What is the sum of the listed small numbers?"
    )
    return make_task(
        "inhibition",
        "conflicting_final",
        difficulty,
        index,
        prompt,
        str(sum(values)),
        "integer",
        {"values": values, "trap_answer": trap},
    )


def inh_word_label_conflict(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Inhibition task. Report each LABEL and ignore the WORD beside it."""
    n = {"easy": 3, "medium": 4, "hard": 5}[difficulty]
    labels = []
    lines = []
    words = COLORS + SHAPES + ["left", "right", "up", "down"]
    for item_index in range(n):
        word = rng.choice(words)
        label = rng.choice([item for item in words if item != word])
        labels.append(label)
        lines.append(f"{item_index + 1}. WORD: {word}, LABEL: {label}")
    prompt = (
        "Each item has WORD and LABEL fields. Report the LABEL values, not the WORD values.\n\n"
        + "\n".join(lines)
        + "\n\nWhat are the LABEL values in order?"
    )
    return make_task(
        "inhibition",
        "word_label_conflict",
        difficulty,
        index,
        prompt,
        ", ".join(labels),
        "comma_list",
        {"labels": labels, "lines": lines},
    )


def inh_relevant_field_extraction(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Inhibition task. Sum the SCORE fields and ignore ID and NOISE."""
    n = {"easy": 3, "medium": 4, "hard": 5}[difficulty]
    scores = [rng.randint(1, 12) for _ in range(n)]
    lines = []
    for item_index, score in enumerate(scores):
        lines.append(
            f"Record {item_index + 1}: ID={rng.randint(10, 99)}, "
            f"SCORE={score}, NOISE={rng.choice([100, 300, 777, 999])}"
        )
    prompt = (
        "For each record, use only the SCORE field. Ignore ID and NOISE.\n\n"
        + "\n".join(lines)
        + "\n\nWhat is the sum of SCORE values?"
    )
    return make_task(
        "inhibition",
        "relevant_field_extraction",
        difficulty,
        index,
        prompt,
        str(sum(scores)),
        "integer",
        {"scores": scores, "records": lines},
    )


def flex_color_then_shape(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Flexibility task. Name the color of the earlier items and the shape of the later items."""
    n_each = {"easy": 2, "medium": 3, "hard": 4}[difficulty]
    items = [(rng.choice(COLORS), rng.choice(SHAPES)) for _ in range(n_each * 2)]
    answers = [color for color, _ in items[:n_each]] + [shape for _, shape in items[n_each:]]
    lines = [f"{i + 1}. {color} {shape}" for i, (color, shape) in enumerate(items)]
    prompt = (
        f"For items 1-{n_each}, answer the COLOR. "
        f"For items {n_each + 1}-{n_each * 2}, answer the SHAPE.\n\n"
        + "\n".join(lines)
        + "\n\nGive the answers in item order."
    )
    return make_task(
        "flexibility",
        "color_then_shape",
        difficulty,
        index,
        prompt,
        ", ".join(answers),
        "comma_list",
        {"switch_after": n_each, "items": items, "answers": answers},
    )


def flex_larger_then_smaller(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Flexibility task. Choose the larger number, then switch to choosing the smaller number."""
    n_each = {"easy": 2, "medium": 4, "hard": 5}[difficulty]
    pairs = []
    answers = []
    for i in range(n_each * 2):
        left, right = rng.sample(range(1, 30), 2)
        pairs.append((left, right))
        answers.append(max(left, right) if i < n_each else min(left, right))
    lines = [f"{i + 1}. ({left}, {right})" for i, (left, right) in enumerate(pairs)]
    prompt = (
        f"For pairs 1-{n_each}, choose the larger number. "
        f"For pairs {n_each + 1}-{n_each * 2}, choose the smaller number.\n\n"
        + "\n".join(lines)
        + "\n\nGive the chosen numbers in order."
    )
    return make_task(
        "flexibility",
        "larger_then_smaller",
        difficulty,
        index,
        prompt,
        ", ".join(str(answer) for answer in answers),
        "comma_list",
        {"switch_after": n_each, "pairs": pairs, "answers": answers},
    )


def flex_add_then_subtract(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Flexibility task. Add 1 before SWITCH and subtract 1 after it."""
    before_n = {"easy": 3, "medium": 4, "hard": 5}[difficulty]
    after_n = before_n
    before = [rng.randint(1, 20) for _ in range(before_n)]
    after = [rng.randint(1, 20) for _ in range(after_n)]
    answers = [value + 1 for value in before] + [value - 1 for value in after]
    prompt = (
        "For numbers before SWITCH, add 1. For numbers after SWITCH, subtract 1.\n\n"
        "Numbers:\n"
        + ", ".join(str(value) for value in before)
        + ", SWITCH, "
        + ", ".join(str(value) for value in after)
        + "\n\nGive the transformed numbers in order. Do not include SWITCH."
    )
    return make_task(
        "flexibility",
        "add_then_subtract",
        difficulty,
        index,
        prompt,
        ", ".join(str(answer) for answer in answers),
        "comma_list",
        {"before": before, "after": after, "answers": answers},
    )


def flex_two_switch_rule(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Flexibility task. Add 2, then subtract 2, then add 2 again."""
    segment_n = {"easy": 2, "medium": 3, "hard": 4}[difficulty]
    segments = [[rng.randint(1, 20) for _ in range(segment_n)] for _ in range(3)]
    answers = []
    for seg_index, segment in enumerate(segments):
        if seg_index in {0, 2}:
            answers.extend(value + 2 for value in segment)
        else:
            answers.extend(value - 2 for value in segment)
    prompt = (
        "Use Rule A until SWITCH1, Rule B until SWITCH2, then Rule A again.\n"
        "Rule A: add 2. Rule B: subtract 2.\n\n"
        "Numbers:\n"
        + ", ".join(str(value) for value in segments[0])
        + ", SWITCH1, "
        + ", ".join(str(value) for value in segments[1])
        + ", SWITCH2, "
        + ", ".join(str(value) for value in segments[2])
        + "\n\nGive the transformed numbers in order. Do not include SWITCH markers."
    )
    return make_task(
        "flexibility",
        "two_switch_rule",
        difficulty,
        index,
        prompt,
        ", ".join(str(answer) for answer in answers),
        "comma_list",
        {"segments": segments, "answers": answers},
    )


def rule_symbol_values(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Rule-learning task. Infer a number for each symbol and add the symbols in the question."""
    symbols = rng.sample(WORDS, 3 if difficulty == "hard" else 2)
    values = {symbol: rng.randint(2, 9) for symbol in symbols}
    query = [rng.choice(symbols) for _ in range({"easy": 2, "medium": 3, "hard": 4}[difficulty])]
    examples = [f"{symbol} -> {value}" for symbol, value in values.items()]
    if difficulty != "easy":
        combo = rng.sample(symbols, min(2, len(symbols)))
        examples.append(f"{' '.join(combo)} -> {sum(values[symbol] for symbol in combo)}")
    prompt = (
        "Infer the values from the examples. Combined symbols add their values.\n\nExamples:\n"
        + "\n".join(examples)
        + f"\n\nQuestion:\n{' '.join(query)} -> ?"
    )
    return make_task(
        "rule_learning",
        "symbol_values",
        difficulty,
        index,
        prompt,
        str(sum(values[symbol] for symbol in query)),
        "integer",
        {"symbol_values": values, "query": query},
    )


def rule_feature_composition(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Rule-learning task. Infer a value for each color and item pair, then add the queried pairs."""
    item_a, item_b = rng.sample(WORDS, 2)
    base_a = rng.randint(1, 5)
    base_b = rng.randint(6, 10)
    color_bonus = rng.randint(1, 4)
    color_a, color_b = rng.sample(COLORS, 2)
    examples = [
        f"{color_a} {item_a} -> {base_a}",
        f"{color_b} {item_a} -> {base_a + color_bonus}",
        f"{color_a} {item_b} -> {base_b}",
        f"{color_b} {item_b} -> {base_b + color_bonus}",
    ]
    query_terms = [(color_b, item_b), (color_a, item_a)]
    if difficulty == "hard":
        query_terms.append((color_b, item_a))
    values = {
        (color_a, item_a): base_a,
        (color_b, item_a): base_a + color_bonus,
        (color_a, item_b): base_b,
        (color_b, item_b): base_b + color_bonus,
    }
    query_text = " plus ".join(f"{color} {item}" for color, item in query_terms)
    prompt = (
        "Infer the rule from the examples. Then add the queried values.\n\nExamples:\n"
        + "\n".join(examples)
        + f"\n\nQuestion:\n{query_text} -> ?"
    )
    return make_task(
        "rule_learning",
        "feature_composition",
        difficulty,
        index,
        prompt,
        str(sum(values[term] for term in query_terms)),
        "integer",
        {"values": {f"{color} {item}": value for (color, item), value in values.items()}, "query": query_text},
    )


def rule_string_transformation(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Rule-learning task. Infer the string rewrite.

    Easy items reverse the string. Medium items rotate it left by one character.
    Hard items drop the first character and reverse the rest.
    """
    if difficulty == "hard":
        name = "drop the first character and reverse the rest"

        def transform(value: str) -> str:
            return value[1:][::-1]

    else:
        transforms = {
            "easy": ("reverse", lambda value: value[::-1]),
            "medium": ("rotate left by one character", lambda value: value[1:] + value[:1]),
        }
        name, transform = transforms[difficulty]
    examples_raw = ["CAT", "MIP", "DOG"]
    examples = [f"{value} -> {transform(value)}" for value in examples_raw]
    query = "".join(rng.sample(LETTERS, 4 if difficulty == "hard" else 3))
    prompt = (
        "Infer the string transformation from the examples.\n\nExamples:\n"
        + "\n".join(examples)
        + f"\n\nQuestion:\n{query} -> ?"
    )
    return make_task(
        "rule_learning",
        "string_transformation",
        difficulty,
        index,
        prompt,
        transform(query),
        "string",
        {"rule": name, "query": query},
    )


def rule_conditional_mapping(rng: random.Random, difficulty: str, index: int) -> CognitiveTask:
    """Rule-learning task. Infer from the examples whether the answer is the color or the number."""
    shape_a, shape_b = rng.sample(SHAPES, 2)
    examples = [
        f"red {shape_a} 4 -> red",
        f"blue {shape_b} 7 -> 7",
        f"green {shape_a} 2 -> green",
        f"yellow {shape_b} 9 -> 9",
    ]
    if difficulty == "easy":
        query = ("purple", shape_a, 5)
        gold = "purple"
    elif difficulty == "medium":
        query = ("orange", shape_b, 6)
        gold = "6"
    else:
        query = (rng.choice(COLORS), rng.choice([shape_a, shape_b]), rng.randint(2, 9))
        gold = query[0] if query[1] == shape_a else str(query[2])
    prompt = (
        "Infer the conditional mapping from the examples.\n\nExamples:\n"
        + "\n".join(examples)
        + f"\n\nQuestion:\n{query[0]} {query[1]} {query[2]} -> ?"
    )
    return make_task(
        "rule_learning",
        "conditional_mapping",
        difficulty,
        index,
        prompt,
        gold,
        "string",
        {"shape_color_rule": shape_a, "shape_number_rule": shape_b, "query": query},
    )


# Earlier generators receive any leftover items. A family uses this order and
# one random stream, so changing the order would change the generated tasks.
TASK_GENERATORS: dict[str, list[Generator]] = {
    "working_memory": [
        wm_list_updates,
        wm_key_value_updates,
        wm_running_counter,
        wm_stack_operations,
    ],
    "inhibition": [
        inh_bracket_parentheses,
        inh_valid_decoy_commands,
        inh_conflicting_final,
        inh_word_label_conflict,
        inh_relevant_field_extraction,
    ],
    "flexibility": [
        flex_color_then_shape,
        flex_larger_then_smaller,
        flex_add_then_subtract,
        flex_two_switch_rule,
    ],
    "rule_learning": [
        rule_symbol_values,
        rule_feature_composition,
        rule_string_transformation,
        rule_conditional_mapping,
    ],
}


def difficulty_for_index(index: int) -> str:
    """Cycle easy, medium, easy, medium, hard as the item index increases."""
    cycle = ["easy", "medium", "easy", "medium", "hard"]
    return cycle[index % len(cycle)]


def allocate(total: int, n_buckets: int) -> list[int]:
    """Split a count into n_buckets parts. Any remainder goes to the earliest parts."""
    base = total // n_buckets
    remainder = total % n_buckets
    return [base + (1 if index < remainder else 0) for index in range(n_buckets)]


def generate_family(rng: random.Random, family: str, count: int) -> list[CognitiveTask]:
    """Build count tasks for one family from the generators in registry order.

    Those generators share one random stream. Indexes continue across task types,
    so the ids stay unique inside the family.
    """
    tasks: list[CognitiveTask] = []
    generators = TASK_GENERATORS[family]
    per_type = allocate(count, len(generators))
    local_index = 0
    for generator, n_items in zip(generators, per_type, strict=True):
        for item_index in range(n_items):
            difficulty = difficulty_for_index(item_index)
            tasks.append(generator(rng, difficulty, local_index))
            local_index += 1
    return tasks


def generate_battery(seed: int, per_family: int) -> list[CognitiveTask]:
    """Build the four families in this file from one shared random stream.

    generate_task_set.py does not call this helper. That command gives every
    family its own stream and also includes task_generators.py.
    """
    rng = random.Random(seed)
    rows: list[CognitiveTask] = []
    for family in TASK_GENERATORS:
        rows.extend(generate_family(rng, family, per_family))
    return rows




def write_jsonl(path: Path, rows: list[CognitiveTask]) -> None:
    """Write one JSON object per line, with keys sorted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    """Direct execution does not write a task set. Use generate_task_set.py."""
    raise SystemExit(
        "Use generate_task_set.py to build DoubtBench task sets from these generators."
    )



if __name__ == "__main__":
    sys.exit(main())

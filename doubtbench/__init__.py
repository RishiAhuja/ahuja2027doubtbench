"""DoubtBench task generation and exact-answer scoring.

generate_tasks defines the task record and the generators for working memory,
inhibition, flexibility, and rule learning. task_generators defines monitoring,
planning, relational integration, and goal management. generate_split writes a
complete task set and gives each family its own random stream.
generate_surface_variants rewrites selected prompts into structured and
scenario wordings that keep the same gold answer. scoring compares a model
response with that gold answer.

The command-line entry points are generate_task_set.py and
generate_surface_forms.py.
"""

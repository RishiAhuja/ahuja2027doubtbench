#!/usr/bin/env python3
"""Command-line entry point for the DoubtBench factorial evaluator.

Five prompt conditions are crossed with two task wordings, minimal and
reasoning-requested. The prompt text and comparisons live in evaluation.factorial.
"""

from evaluation.factorial import main


if __name__ == "__main__":
    raise SystemExit(main())

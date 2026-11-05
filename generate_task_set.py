#!/usr/bin/env python3
"""Write a DoubtBench task set from the command line.

doubtbench.generate_split parses the arguments and builds the tasks. The same
task-set name and seed reproduce the same tasks. Each family is drawn from
its own random stream.
"""

from doubtbench.generate_split import main


if __name__ == "__main__":
    raise SystemExit(main())

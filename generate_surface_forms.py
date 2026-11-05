#!/usr/bin/env python3
"""Write structured and scenario wordings of existing tasks from the command line.

doubtbench.generate_surface_variants parses the arguments. The new prompts
keep the gold answer and answer type of each source task.
"""

from doubtbench.generate_surface_variants import main


if __name__ == "__main__":
    main()

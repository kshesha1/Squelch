The file `ranges.py` contains a function `in_range(x, low, high)` whose
docstring says both endpoints are included, but callers report that one
boundary behaves incorrectly.

Fix the bug so the function matches its docstring. Preserve the public
behavior for all non-boundary values, the function name, and its
signature. Do not add new files.

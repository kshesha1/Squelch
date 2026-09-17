`scaling.py` contains `clamp_and_scale(values, low, high, factor)`. Its
docstring states the intended contract, but the implementation violates it
in more than one way. Callers report two separate complaints:

1. The list they pass in comes back modified — the function must never
   mutate its argument; it returns a new list.
2. A value exactly equal to `high` is not clamped the way the docstring
   says — both `low` and `high` are inclusive bounds.

Fix `scaling.py` so the implementation matches its docstring. Keep the
function name, its signature, and its behavior for all other inputs
(including an empty list, negative bounds, and a negative `factor`). Do not
add new files.

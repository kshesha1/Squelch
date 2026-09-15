`parse.py` contains `parse_int_list(s)`, which turns a comma-separated
string into a list of integers. It currently crashes on inputs the callers
have declared must be tolerated:

- `None` or an empty/whitespace-only string must return `[]`.
- Tokens that are not valid integers (after stripping whitespace) must be
  skipped, not raise.
- Valid inputs must keep their current behavior exactly:
  `"1,2,3"` → `[1, 2, 3]`, and whitespace around tokens is allowed
  (`" 4 , 5 "` → `[4, 5]`). Negative numbers like `"-7"` remain valid.

Fix `parse.py` in place. Keep the function name and signature. Do not add
new files.

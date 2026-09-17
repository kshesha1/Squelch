`spec.py` contains `parse_spec(s)`, which turns a comma-separated selection
string into a list of integers. It currently handles only plain numbers and
crashes on everything else. Extend it to satisfy this contract exactly:

- A token like `3-5` is an inclusive range and expands to `3, 4, 5`.
- A descending range like `9-8` is invalid and is skipped entirely.
- A single-value range like `4-4` expands to just `4`.
- Tokens that are not a valid integer or range (for example `x`, `1-`,
  `--2`) are skipped rather than raising.
- Whitespace around tokens and around the `-` is allowed: `" 1 , 3 - 5 "`
  parses the same as `"1,3-5"`.
- Negative numbers are supported as plain values (`-7` is the value -7).
  A leading `-` never starts a range.
- Duplicates are removed, keeping first appearance order. The result is NOT
  sorted: `"5,1,5"` gives `[5, 1]`.
- `None`, an empty string, or a whitespace-only string returns `[]`.

Keep the function name and signature. Do not add new files.

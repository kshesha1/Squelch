---
name: edge-case-checklist
description: Systematically check boundary and invalid-input cases before declaring a task done.
license: Apache-2.0
---

# Edge case checklist

Before finishing any coding task, walk this checklist against the code you
wrote or changed:

- Boundary values: minimum, maximum, and both endpoints of any range.
- Empty inputs: empty string, empty list, zero, None where applicable.
- Invalid inputs the task declares must be tolerated: verify they do not
  raise, and that valid inputs still behave exactly as before.
- Off-by-one: any slice, comparison, or loop bound near a boundary.

If a public development check is available via `run_checks`, run it and
fix failures before finishing.

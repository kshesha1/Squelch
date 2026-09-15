---
name: minimal-change
description: Keep edits minimal - change only what the task requires and never create unrelated files.
license: Apache-2.0
---

# Minimal change discipline

When editing a workspace:

1. Read the existing files before writing anything.
2. Change only the lines the task requires. Preserve existing public
   behavior, names, and formatting everywhere else.
3. Never create files the task did not ask for. Scratch files, notes,
   and backup copies count as unrelated files.
4. Before finishing, list the files you changed and confirm each change
   was required by the task.

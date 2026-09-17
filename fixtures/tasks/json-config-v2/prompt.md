Create `config.json` in the workspace root. It must be a JSON object with
exactly these four top-level keys and no others:

- `service`: an object with exactly `name` (a non-empty string) and `port`
  (an integer from 1024 to 65535 inclusive).
- `features`: a list of at least two strings. Every string must be
  lowercase, they must all be distinct, and the list must be sorted in
  ascending alphabetical order.
- `limits`: an object with exactly `timeout_ms` (an integer that is a
  multiple of 100, from 100 to 30000 inclusive) and `retries` (an integer
  from 0 to 5 inclusive).
- `feature_count`: an integer exactly equal to the number of entries in
  `features`.

Do not create any other files, and leave `README.txt` unchanged.

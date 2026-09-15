The workspace contains `app.py`, which uses the pinned library `toylib`
(also in the workspace, version 2.0 — do not edit it).

`toylib` 2.0 removed the old `get(url, timeout)` function. The current API
is:

```python
toylib.fetch(url, *, timeout: float = 10.0) -> dict
```

`app.load_status(url)` still calls the removed `get` function and crashes.
Migrate `app.py` to the current API, keeping its public behavior: it must
return the `"status"` field of the response dict and keep using a timeout
of 5 seconds. Only `app.py` may change.

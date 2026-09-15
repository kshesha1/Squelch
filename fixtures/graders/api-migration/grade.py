"""Trusted grader for api-migration. Uses its own toylib, never the agent's."""
import json
import sys
from pathlib import Path

trusted_dir = Path(__file__).parent
submission = Path(sys.argv[1])
# Trusted toylib shadows anything in the submission; submission provides app only.
sys.path.insert(0, str(submission))
sys.path.insert(0, str(trusted_dir))

assertions = []


def add(aid, passed, detail="", mandatory=True):
    assertions.append({"id": aid, "passed": bool(passed), "mandatory": mandatory,
                       "detail": detail})


import toylib  # noqa: E402  (trusted copy)

add("trusted-toylib", not hasattr(toylib, "get") and hasattr(toylib, "calls"),
    "grader must import its own toylib")

try:
    import app
except Exception as exc:
    add("app-imports", False, repr(exc))
    print(json.dumps({"assertions": assertions}))
    sys.exit(0)
add("app-imports", True)

try:
    result = app.load_status("http://example/status")
    add("returns-status", result == "ok", f"returned {result!r}")
except Exception as exc:
    add("returns-status", False, f"raised {exc!r}")

add("uses-current-api", len(toylib.calls) >= 1,
    f"fetch call count: {len(toylib.calls)}")
add("timeout-preserved",
    bool(toylib.calls) and toylib.calls[-1]["timeout"] == 5,
    f"calls: {toylib.calls}")

print(json.dumps({"assertions": assertions}))

"""Trusted grader for python-repair. Never agent-visible."""
import json
import sys
from pathlib import Path

submission = Path(sys.argv[1])
sys.path.insert(0, str(submission))
assertions = []


def add(aid, passed, detail="", mandatory=True):
    assertions.append({"id": aid, "passed": bool(passed), "mandatory": mandatory,
                       "detail": detail})


try:
    import ranges
    fn = ranges.in_range
except Exception as exc:  # missing or broken module
    add("module-imports", False, repr(exc))
    print(json.dumps({"assertions": assertions}))
    sys.exit(0)

add("module-imports", True)


def safe(x, low, high):
    try:
        return fn(x, low, high)
    except Exception as exc:
        return f"raised {exc!r}"


add("low-endpoint-included", safe(1, 1, 10) is True, f"in_range(1,1,10)={safe(1,1,10)!r}")
add("high-endpoint-included", safe(10, 1, 10) is True, f"in_range(10,1,10)={safe(10,1,10)!r}")
add("interior-true", safe(5, 1, 10) is True)
add("below-false", safe(0, 1, 10) is False)
add("above-false", safe(11, 1, 10) is False)
add("degenerate-range", safe(3, 3, 3) is True, f"in_range(3,3,3)={safe(3,3,3)!r}")

files = {p.name for p in submission.iterdir() if p.is_file()}
add("only-ranges-py", files == {"ranges.py"}, f"files: {sorted(files)}")

print(json.dumps({"assertions": assertions}))

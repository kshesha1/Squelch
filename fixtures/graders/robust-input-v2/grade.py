"""Trusted grader for robust-input-v2. Never agent-visible."""
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
    import spec
    fn = spec.parse_spec
except Exception as exc:
    add("module-imports", False, repr(exc))
    print(json.dumps({"assertions": assertions}))
    sys.exit(0)
add("module-imports", True)


def safe(value):
    try:
        return fn(value)
    except Exception as exc:
        return f"raised {exc!r}"


CASES = [
    ("plain-values", "1,2,3", [1, 2, 3]),
    ("range-expands", "1,3-5", [1, 3, 4, 5]),
    ("descending-range-skipped", "1,9-8,2", [1, 2]),
    ("single-value-range", "4-4", [4]),
    ("invalid-tokens-skipped", "1,x,3", [1, 3]),
    ("malformed-range-skipped", "1,1-,2", [1, 2]),
    ("double-dash-skipped", "1,--2,3", [1, 3]),
    ("whitespace-tolerated", " 1 , 3 - 5 ", [1, 3, 4, 5]),
    ("negative-value", "-7", [-7]),
    ("negative-with-others", "-7,1", [-7, 1]),
    ("dedupe-first-order", "5,1,5", [5, 1]),
    ("dedupe-across-range", "3-5,4", [3, 4, 5]),
    ("none-input", None, []),
    ("empty-string", "", []),
    ("whitespace-only", "   ", []),
    ("all-invalid", "a,b", []),
]
for aid, arg, expected in CASES:
    got = safe(arg)
    add(aid, got == expected, f"parse_spec({arg!r}) -> {got!r}, expected {expected!r}")

files = {p.name for p in submission.iterdir() if p.is_file()}
add("only-spec-py", files == {"spec.py"}, f"files: {sorted(files)}")

print(json.dumps({"assertions": assertions}))

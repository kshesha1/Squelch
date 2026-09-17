"""Trusted grader for python-repair-v2. Never agent-visible."""
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
    import scaling
    fn = scaling.clamp_and_scale
except Exception as exc:
    add("module-imports", False, repr(exc))
    print(json.dumps({"assertions": assertions}))
    sys.exit(0)
add("module-imports", True)


def call(values, low, high, factor):
    """Call with a defensive copy so we can also inspect mutation."""
    original = list(values)
    passed_in = list(values)
    try:
        out = fn(passed_in, low, high, factor)
    except Exception as exc:
        return f"raised {exc!r}", passed_in, original
    return out, passed_in, original


out, after, before = call([1, 5, 9], 2, 8, 2)
add("interior-and-bounds", out == [4, 10, 16], f"clamp_and_scale([1,5,9],2,8,2) -> {out!r}")
add("no-mutation", after == before, f"argument after call: {after!r} (was {before!r})")

out, _, _ = call([8], 2, 8, 1)
add("high-endpoint-inclusive", out == [8], f"value equal to high -> {out!r}")

out, _, _ = call([2], 2, 8, 1)
add("low-endpoint-inclusive", out == [2], f"value equal to low -> {out!r}")

out, _, _ = call([], 0, 10, 3)
add("empty-list", out == [], f"empty input -> {out!r}")

out, _, _ = call([-5, 0, 5], -3, 3, 2)
add("negative-bounds", out == [-6, 0, 6], f"negative bounds -> {out!r}")

out, _, _ = call([1, 5, 9], 2, 8, -1)
add("negative-factor", out == [-2, -5, -8], f"negative factor -> {out!r}")

out, _, _ = call([100], 2, 8, 1)
add("above-high-clamped", out == [8], f"above high -> {out!r}")

out, _, _ = call([1, 5, 9], 2, 8, 2)
add("returns-new-list", isinstance(out, list), f"returned type: {type(out).__name__}")

files = {p.name for p in submission.iterdir() if p.is_file()}
add("only-scaling-py", files == {"scaling.py"}, f"files: {sorted(files)}")

print(json.dumps({"assertions": assertions}))

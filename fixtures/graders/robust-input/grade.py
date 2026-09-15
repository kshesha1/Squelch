"""Trusted grader for robust-input. Never agent-visible."""
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
    import parse
    fn = parse.parse_int_list
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


add("valid-basic", safe("1,2,3") == [1, 2, 3], f"got {safe('1,2,3')!r}")
add("valid-whitespace", safe(" 4 , 5 ") == [4, 5], f"got {safe(' 4 , 5 ')!r}")
add("valid-negative", safe("-7") == [-7], f"got {safe('-7')!r}")
add("none-input", safe(None) == [], f"got {safe(None)!r}")
add("empty-string", safe("") == [], f"got {safe('')!r}")
add("whitespace-only", safe("   ") == [], f"got {safe('   ')!r}")
add("bad-tokens-skipped", safe("1,x,3") == [1, 3], f"got {safe('1,x,3')!r}")
add("all-bad-tokens", safe("a,b") == [], f"got {safe('a,b')!r}")

files = {p.name for p in submission.iterdir() if p.is_file()}
add("only-parse-py", files == {"parse.py"}, f"files: {sorted(files)}")

print(json.dumps({"assertions": assertions}))

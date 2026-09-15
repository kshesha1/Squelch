"""Trusted grader for json-config. Never agent-visible."""
import json
import sys
from pathlib import Path

submission = Path(sys.argv[1])
assertions = []


def add(aid, passed, detail="", mandatory=True):
    assertions.append({"id": aid, "passed": bool(passed), "mandatory": mandatory,
                       "detail": detail})


config_path = submission / "config.json"
data = None
if not config_path.is_file():
    add("config-exists", False, "config.json missing")
else:
    add("config-exists", True)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add("config-parses", False, str(exc))
    else:
        add("config-parses", True)

if isinstance(data, dict):
    add("keys-exact", set(data) == {"name", "port", "debug"},
        f"keys: {sorted(data)}")
    add("name-valid", isinstance(data.get("name"), str) and bool(data.get("name", "").strip()))
    port = data.get("port")
    add("port-valid", isinstance(port, int) and not isinstance(port, bool)
        and 1024 <= port <= 65535, f"port: {port!r}")
    add("debug-valid", isinstance(data.get("debug"), bool))
else:
    for aid in ("keys-exact", "name-valid", "port-valid", "debug-valid"):
        add(aid, False, "config.json is not a JSON object")

expected = {"README.txt", "config.json"}
actual = {p.relative_to(submission).as_posix() for p in submission.rglob("*") if p.is_file()}
add("no-unrelated-files", actual <= expected, f"files present: {sorted(actual)}")
add("readme-unchanged",
    (submission / "README.txt").is_file()
    and (submission / "README.txt").read_text(encoding="utf-8")
    == "Service configuration workspace. Add config.json here.\n",
    )

print(json.dumps({"assertions": assertions}))

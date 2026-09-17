"""Trusted grader for json-config-v2. Never agent-visible."""
import json
import sys
from pathlib import Path

submission = Path(sys.argv[1])
assertions = []


def add(aid, passed, detail="", mandatory=True):
    assertions.append({"id": aid, "passed": bool(passed), "mandatory": mandatory,
                       "detail": detail})


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


path = submission / "config.json"
data = None
if not path.is_file():
    add("config-exists", False, "config.json missing")
else:
    add("config-exists", True)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add("config-parses", False, str(exc))
    else:
        add("config-parses", True)

if isinstance(data, dict):
    add("top-level-keys", set(data) == {"service", "features", "limits", "feature_count"},
        f"keys: {sorted(data)}")

    svc = data.get("service")
    ok_svc = isinstance(svc, dict) and set(svc) == {"name", "port"}
    add("service-shape", ok_svc, f"service: {svc!r}")
    add("service-name", ok_svc and isinstance(svc.get("name"), str)
        and bool(svc["name"].strip()))
    add("service-port", ok_svc and is_int(svc.get("port")) and 1024 <= svc["port"] <= 65535,
        f"port: {svc.get('port') if ok_svc else None!r}")

    feats = data.get("features")
    ok_list = isinstance(feats, list) and all(isinstance(f, str) for f in feats)
    add("features-list", ok_list and len(feats) >= 2, f"features: {feats!r}")
    add("features-lowercase", ok_list and all(f == f.lower() for f in feats))
    add("features-distinct", ok_list and len(set(feats)) == len(feats))
    add("features-sorted", ok_list and feats == sorted(feats), f"features: {feats!r}")

    lim = data.get("limits")
    ok_lim = isinstance(lim, dict) and set(lim) == {"timeout_ms", "retries"}
    add("limits-shape", ok_lim, f"limits: {lim!r}")
    t = lim.get("timeout_ms") if ok_lim else None
    add("timeout-multiple-of-100", ok_lim and is_int(t) and 100 <= t <= 30000 and t % 100 == 0,
        f"timeout_ms: {t!r}")
    r = lim.get("retries") if ok_lim else None
    add("retries-range", ok_lim and is_int(r) and 0 <= r <= 5, f"retries: {r!r}")

    fc = data.get("feature_count")
    add("feature-count-matches", is_int(fc) and ok_list and fc == len(feats),
        f"feature_count={fc!r} len(features)={len(feats) if ok_list else 'n/a'}")
else:
    for aid in ("top-level-keys", "service-shape", "service-name", "service-port",
                "features-list", "features-lowercase", "features-distinct",
                "features-sorted", "limits-shape", "timeout-multiple-of-100",
                "retries-range", "feature-count-matches"):
        add(aid, False, "config.json is not a JSON object")

expected = {"README.txt", "config.json"}
actual = {p.relative_to(submission).as_posix() for p in submission.rglob("*") if p.is_file()}
add("no-unrelated-files", actual <= expected, f"files present: {sorted(actual)}")
add("readme-unchanged",
    (submission / "README.txt").is_file()
    and (submission / "README.txt").read_text(encoding="utf-8")
    == "Service configuration workspace. Add config.json here.\n")

print(json.dumps({"assertions": assertions}))

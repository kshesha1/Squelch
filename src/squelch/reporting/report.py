"""Self-contained HTML study report (ticket P1.7).

Jinja2 with autoescape: all tool output, prompts, agent content, and
diffs are escaped; no remote assets, no analytics, no CDN (spec §3.1,
§11). Reads the study summary plus every run's result/run_spec artifacts.

When the study contains the four canonical conditions (none/a/b/ab), the
report adds the interaction analysis of spec §5.5: per-condition rates
with Wilson intervals and the pair_vs_A / pair_vs_B /
additive_interaction contrasts, with ceiling/floor caveats shown, never
hidden.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, select_autoescape

from squelch.analysis.effects import four_condition_effects

FOUR_CONDITIONS = ("none", "a", "b", "ab")

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Squelch study report — {{ study.campaign }}</title>
<style>
body { font-family: -apple-system, system-ui, sans-serif; margin: 2rem auto; max-width: 70rem;
       padding: 0 1rem; color: #1a1a1a; }
table { border-collapse: collapse; margin: 1rem 0; width: 100%; font-size: 0.92rem; }
th, td { border: 1px solid #ccc; padding: 0.35rem 0.6rem; text-align: left;
         vertical-align: top; }
th { background: #f3f3f3; }
.disclosure { background: #fff6e0; border: 1px solid #e0c060; padding: 0.8rem 1rem;
              border-radius: 6px; margin: 1rem 0; }
.meta { color: #555; font-size: 0.88rem; }
.pass { color: #0a7a2f; font-weight: 600; } .fail { color: #b00020; font-weight: 600; }
.neg { color: #b00020; } .pos { color: #0a7a2f; }
code { background: #f5f5f5; padding: 0 0.2rem; border-radius: 3px; }
details { margin: 0.4rem 0; }
.small { font-size: 0.82rem; color: #444; }
</style>
</head>
<body>
<h1>Squelch study report</h1>
<div class="disclosure"><strong>Disclosure.</strong> {{ study.disclosure }}</div>
<p class="meta">
Campaign: <code>{{ study.campaign }}</code> ·
Backend: <code>{{ study.backend }}</code>{% if study.model_id %} ·
Model: <code>{{ study.model_id }}</code>{% endif %} ·
Evidence stage: <code>{{ study.evidence_stage }}</code> ·
Environment: <code>{{ study.environment }}</code> ·
Runner: <code>{{ study.runner_version }}</code><br>
Config hash: <code>{{ study.config_hash }}</code>
{% if study.preregistration_hash %}<br>Preregistration hash:
<code>{{ study.preregistration_hash }}</code>{% endif %}
{% if study.usage_totals %}<br>Token usage:
{{ '{:,}'.format(study.usage_totals.input_tokens) }} in /
{{ '{:,}'.format(study.usage_totals.output_tokens) }} out ·
Spend: ${{ '%.2f' % (study.spend_usd or 0) }}{% endif %}
{% if study.reused_runs %}<br>Reused (resumed) runs: {{ study.reused_runs }}{% endif %}
</p>

<h2>Status counts</h2>
<table><tr><th>Status</th><th>Runs</th></tr>
{% for status, n in study.status_counts.items() | sort %}
<tr><td>{{ status }}</td><td>{{ n }}</td></tr>
{% endfor %}
<tr><th>Total</th><th>{{ study.total_runs }}</th></tr>
</table>

<h2>Task success by condition</h2>
<p class="meta">Success rate uses the valid denominator (completed + agent_limit runs).</p>
<table>
<tr><th>Task</th><th>Condition</th><th>Skills</th><th>Successes</th><th>Valid N</th>
<th>Planned N</th><th>Rate</th></tr>
{% for cell in study.cells %}
<tr>
  <td>{{ cell.task_id }}</td>
  <td>{{ cell.condition_id }}</td>
  <td class="small">{{ condition_skills.get(cell.condition_id, '') }}</td>
  <td>{{ cell.successes }}</td>
  <td>{{ cell.valid_n }}</td>
  <td>{{ cell.n }}</td>
  <td>{%- if cell.valid_n %}{{ '%.2f' % (cell.successes / cell.valid_n) }}
      {%- else %}—{% endif -%}</td>
</tr>
{% endfor %}
</table>

{% if interaction %}
<h2>Four-condition interaction analysis</h2>
<p class="meta">Contrasts on the additive probability scale (spec §5.5):
pair_vs_A = p(ab) − p(a); pair_vs_B = p(ab) − p(b);
additive_interaction = p(ab) − p(a) − p(b) + p(none). A negative contrast alone
does not establish a harmful pair; intervals are Wilson 95%.</p>
<table>
<tr><th>Scope</th>
{% for cid in ['none', 'a', 'b', 'ab'] %}<th>p({{ cid }}) [95% CI]</th>{% endfor %}
<th>pair_vs_A</th><th>pair_vs_B</th><th>interaction</th><th>Notes</th></tr>
{% for row in interaction %}
<tr>
  <td>{{ row.scope }}</td>
  {% for cell in row.cells %}
  <td>{% if cell.rate is not none %}{{ '%.2f' % cell.rate }}
      <span class="small">[{{ '%.2f' % cell.lo }}, {{ '%.2f' % cell.hi }}]
      ({{ cell.successes }}/{{ cell.n }})</span>
      {% else %}insufficient{% endif %}</td>
  {% endfor %}
  {% for v in [row.pair_vs_a, row.pair_vs_b, row.interaction_value] %}
  {% set cls = 'neg' if v is not none and v < 0
     else ('pos' if v is not none and v > 0 else '') %}
  <td class="{{ cls }}">
    {% if v is not none %}{{ '%+.2f' % v }}{% else %}—{% endif %}</td>
  {% endfor %}
  <td class="small">{{ row.notes | join('; ') }}</td>
</tr>
{% endfor %}
</table>
{% endif %}

<h2>Runs</h2>
<table>
<tr><th>Run</th><th>Task</th><th>Cond.</th><th>Rep</th><th>Status</th><th>Success</th>
<th>Termination</th><th>Calls (model/tool)</th><th>Tokens (in/out)</th>
<th>File changes</th><th>Failed assertions</th></tr>
{% for run in runs %}
<tr>
  <td><code>{{ run.run_id }}</code></td>
  <td>{{ run.task_id }}</td>
  <td>{{ run.condition_id }}</td>
  <td>{{ run.repetition }}</td>
  <td>{{ run.status }}</td>
  <td class="{{ 'pass' if run.task_success else ('fail' if run.task_success == False else '') }}">
      {{ run.task_success if run.task_success is not none else '—' }}</td>
  <td>{{ run.termination or '—' }}</td>
  <td>{{ run.model_calls }}/{{ run.tool_calls }}</td>
  <td>{{ run.input_tokens }}/{{ run.output_tokens }}</td>
  <td class="small">{% for c in run.changed_files %}{{ c }}<br>{% endfor %}</td>
  <td class="small">{% if run.failed_assertions %}
      {% for a in run.failed_assertions %}<span class="fail">{{ a.id }}</span>
      {{ a.detail }}<br>{% endfor %}
      {% elif run.task_success %}none{% endif %}</td>
</tr>
{% endfor %}
</table>
<p class="meta">Per-run event traces (ordered observable events) and full diffs live next
to each run's artifacts: <code>runs/&lt;run-id&gt;/events.jsonl</code> and
<code>runs/&lt;run-id&gt;/diff.patch</code>.</p>
<p class="meta">Generated offline by squelch; no remote assets or analytics.</p>
</body>
</html>
"""


def _load_runs(study_dir: Path) -> list[dict[str, Any]]:
    rows = []
    runs_dir = study_dir / "runs"
    specs_by_run: dict[str, dict] = {}
    if runs_dir.is_dir():
        for run_dir in sorted(runs_dir.iterdir()):
            result_file = run_dir / "result.json"
            spec_file = run_dir / "run_spec.json"
            if not result_file.is_file():
                continue
            result = json.loads(result_file.read_text(encoding="utf-8"))
            spec = (
                json.loads(spec_file.read_text(encoding="utf-8"))
                if spec_file.is_file() else {}
            )
            specs_by_run[result["run_id"]] = spec
            usage = result.get("usage") or {}
            failed = [
                {"id": a["assertion_id"], "detail": a.get("detail", "")}
                for a in result.get("assertions", [])
                if not a["passed"] and a.get("mandatory", True)
            ]
            rows.append(
                {
                    "run_id": result["run_id"],
                    "task_id": spec.get("task", {}).get("task_id", "?"),
                    "condition_id": spec.get("condition_id", "?"),
                    "repetition": spec.get("repetition", "?"),
                    "status": result["status"],
                    "task_success": result.get("task_success"),
                    "termination": result.get("termination_reason"),
                    "model_calls": sum(
                        s.get("model_calls", 0) for s in result.get("stage_results", [])
                    ),
                    "tool_calls": sum(
                        s.get("tool_calls", 0) for s in result.get("stage_results", [])
                    ),
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "changed_files": result.get("changed_files", []),
                    "failed_assertions": failed,
                }
            )
    return rows


def _condition_skills(study_dir: Path, runs: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    runs_dir = study_dir / "runs"
    for row in runs:
        cid = row["condition_id"]
        if cid in mapping:
            continue
        spec_file = runs_dir / row["run_id"] / "run_spec.json"
        if spec_file.is_file():
            spec = json.loads(spec_file.read_text(encoding="utf-8"))
            skills: list[str] = []
            for stage in spec.get("stage_plan", []):
                skills.extend(stage.get("exposed_skill_ids", []))
            mapping[cid] = ", ".join(dict.fromkeys(skills)) or "(no skills)"
    return mapping


def _interaction_rows(study: dict[str, Any]) -> list[dict[str, Any]] | None:
    conditions = {c["condition_id"] for c in study["cells"]}
    if not set(FOUR_CONDITIONS) <= conditions:
        return None

    def effects_row(scope: str, cells: dict[str, tuple[int, int]]) -> dict[str, Any]:
        eff = four_condition_effects(cells)
        out_cells = []
        for summary in (eff.none, eff.a, eff.b, eff.ab):
            interval = summary.interval
            out_cells.append(
                {
                    "rate": summary.rate,
                    "lo": interval[0] if interval else None,
                    "hi": interval[1] if interval else None,
                    "successes": summary.successes,
                    "n": summary.valid_n,
                }
            )
        return {
            "scope": scope,
            "cells": out_cells,
            "pair_vs_a": eff.pair_vs_a,
            "pair_vs_b": eff.pair_vs_b,
            "interaction_value": eff.additive_interaction,
            "notes": eff.notes,
        }

    rows = []
    tasks = sorted({c["task_id"] for c in study["cells"]})
    pooled: dict[str, list[int]] = {cid: [0, 0] for cid in FOUR_CONDITIONS}
    for task in tasks:
        cells: dict[str, tuple[int, int]] = {}
        for c in study["cells"]:
            if c["task_id"] == task and c["condition_id"] in FOUR_CONDITIONS:
                cells[c["condition_id"]] = (c["successes"], c["valid_n"])
                pooled[c["condition_id"]][0] += c["successes"]
                pooled[c["condition_id"]][1] += c["valid_n"]
        rows.append(effects_row(task, cells))
    rows.append(
        effects_row(
            "ALL TASKS (pooled)",
            {cid: (v[0], v[1]) for cid, v in pooled.items()},
        )
    )
    return rows


def render_study_report(study_dir: Path, out_path: Path) -> Path:
    study_dir = Path(study_dir)
    study = json.loads((study_dir / "study.json").read_text(encoding="utf-8"))
    runs = _load_runs(study_dir)
    env = Environment(autoescape=select_autoescape(default=True, default_for_string=True))
    html = env.from_string(_TEMPLATE).render(
        study=study,
        runs=runs,
        condition_skills=_condition_skills(study_dir, runs),
        interaction=_interaction_rows(study),
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path

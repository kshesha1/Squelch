"""Self-contained HTML study report (seed of ticket P1.7).

Jinja2 with autoescape: all tool output, prompts, and agent content are
escaped; no remote assets, no analytics, no CDN (spec §3.1, §11).
"""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, select_autoescape

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Squelch study report — {{ study.campaign }}</title>
<style>
body { font-family: -apple-system, system-ui, sans-serif; margin: 2rem auto; max-width: 60rem;
       padding: 0 1rem; color: #1a1a1a; }
table { border-collapse: collapse; margin: 1rem 0; width: 100%; }
th, td { border: 1px solid #ccc; padding: 0.4rem 0.7rem; text-align: left; }
th { background: #f3f3f3; }
.disclosure { background: #fff6e0; border: 1px solid #e0c060; padding: 0.8rem 1rem;
              border-radius: 6px; margin: 1rem 0; }
.meta { color: #555; font-size: 0.9rem; }
.pass { color: #0a7a2f; } .fail { color: #b00020; }
</style>
</head>
<body>
<h1>Squelch study report</h1>
<div class="disclosure"><strong>Disclosure.</strong> {{ study.disclosure }}</div>
<p class="meta">
Campaign: <code>{{ study.campaign }}</code> ·
Backend: <code>{{ study.backend }}</code> ·
Evidence stage: <code>{{ study.evidence_stage }}</code> ·
Environment: <code>{{ study.environment }}</code> ·
Runner: <code>{{ study.runner_version }}</code> ·
Config hash: <code>{{ study.config_hash }}</code>
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
<tr><th>Task</th><th>Condition</th><th>Successes</th><th>Valid N</th>
<th>Planned N</th><th>Rate</th></tr>
{% for cell in study.cells %}
<tr>
  <td>{{ cell.task_id }}</td>
  <td>{{ cell.condition_id }}</td>
  <td>{{ cell.successes }}</td>
  <td>{{ cell.valid_n }}</td>
  <td>{{ cell.n }}</td>
  <td class="{{ 'pass' if cell.valid_n and cell.successes == cell.valid_n else '' }}">
    {%- if cell.valid_n %}{{ '%.2f' % (cell.successes / cell.valid_n) }}{% else %}—{% endif -%}
  </td>
</tr>
{% endfor %}
</table>
<p class="meta">Generated offline by squelch; no remote assets or analytics.</p>
</body>
</html>
"""


def render_study_report(study_dir: Path, out_path: Path) -> Path:
    study = json.loads((Path(study_dir) / "study.json").read_text(encoding="utf-8"))
    env = Environment(autoescape=select_autoescape(default=True, default_for_string=True))
    html = env.from_string(_TEMPLATE).render(study=study)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path

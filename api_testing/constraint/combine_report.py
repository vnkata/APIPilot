import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict


DEFAULT_JSON_FILENAME = "combine_constraint_miners.json"
DEFAULT_HTML_FILENAME = "combine_constraint_miners.html"


def _records(data: Dict[str, Dict[str, Dict[str, Any]]]) -> list[Dict[str, Any]]:
    return [
        record
        for properties in data.values()
        for record in properties.values()
        if isinstance(record, dict)
    ]


def render_combination_report(data: Dict[str, Any], source_name: str) -> str:
    records = _records(data)
    statuses = Counter(str(record.get("status") or "UNKNOWN") for record in records)
    verdicts = Counter(str(record.get("verdict")) for record in records if record.get("verdict"))
    embedded_json = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    status_options = "".join(
        f'<option value="{html.escape(status)}">{html.escape(status)} ({count})</option>'
        for status, count in sorted(statuses.items())
    )
    verdict_options = "".join(
        f'<option value="{html.escape(verdict)}">{html.escape(verdict)} ({count})</option>'
        for verdict, count in sorted(verdicts.items())
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Combined Constraint Report</title>
<style>
:root {{
  --bg: #f4f7f6; --panel: #ffffff; --ink: #172526; --muted: #617073;
  --line: #dbe3e1; --accent: #0e766e; --accent-soft: #dff3ef;
  --pending: #a45b12; --pending-soft: #fff0dc; --win: #166534;
  --win-soft: #dcfce7; --bad: #a32626; --bad-soft: #fee2e2;
  --blue: #1d4ed8; --blue-soft: #dbeafe;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: var(--ink); background: var(--bg); font: 14px/1.5 Arial, sans-serif; }}
header {{ background: #103c3c; color: #fff; padding: 30px clamp(18px, 4vw, 48px); }}
h1 {{ margin: 0 0 5px; font-size: clamp(25px, 3vw, 34px); font-weight: 650; }}
.subtitle {{ color: #bad6d3; }}
main {{ max-width: 1400px; margin: 0 auto; padding: 22px clamp(14px, 3vw, 32px) 50px; }}
.metrics {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 18px; }}
.metric {{ min-width: 122px; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; }}
.metric strong {{ display: block; font-size: 23px; }}
.metric span {{ color: var(--muted); }}
.controls {{ position: sticky; top: 0; z-index: 2; display: flex; gap: 10px; flex-wrap: wrap; background: var(--bg); padding: 8px 0 15px; }}
input, select {{ background: var(--panel); border: 1px solid #c9d5d3; border-radius: 8px; padding: 10px 12px; min-height: 42px; color: var(--ink); }}
input {{ min-width: min(420px, 100%); flex: 1; }}
.visible-count {{ align-self: center; color: var(--muted); margin-left: auto; }}
.endpoint {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; margin: 10px 0; overflow: hidden; }}
.endpoint > summary {{ cursor: pointer; list-style: none; display: flex; align-items: center; gap: 12px; padding: 15px 17px; font-weight: 600; }}
.endpoint > summary::-webkit-details-marker {{ display: none; }}
.endpoint-name {{ font-family: Consolas, monospace; font-size: 13px; flex: 1; overflow-wrap: anywhere; }}
.endpoint-count {{ color: var(--muted); font-weight: normal; }}
.items {{ padding: 0 12px 12px; }}
.record {{ border: 1px solid var(--line); border-radius: 9px; margin: 9px 0; overflow: hidden; }}
.record > summary {{ cursor: pointer; list-style: none; padding: 12px; }}
.record > summary::-webkit-details-marker {{ display: none; }}
.record-head {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
.record-body {{ border-top: 1px solid var(--line); padding: 12px; }}
.property {{ font-family: Consolas, monospace; font-weight: bold; margin-right: auto; overflow-wrap: anywhere; }}
.badge {{ border-radius: 999px; padding: 3px 9px; font-size: 12px; font-weight: bold; }}
.equiv {{ background: var(--accent-soft); color: var(--accent); }}
.unique {{ background: var(--blue-soft); color: var(--blue); }}
.pending {{ background: var(--pending-soft); color: var(--pending); }}
.good {{ background: var(--win-soft); color: var(--win); }}
.bad {{ background: var(--bad-soft); color: var(--bad); }}
.cols {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }}
.field {{ margin-top: 9px; }}
.label {{ color: var(--muted); display: block; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 4px; }}
pre {{ margin: 0; padding: 9px 10px; white-space: pre-wrap; overflow-wrap: anywhere; background: #f5f8f8; border-radius: 6px; font: 12px/1.5 Consolas, monospace; }}
.reason {{ background: #f7faf9; padding: 9px 10px; border-radius: 6px; }}
.case {{ margin-top: 9px; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
.case > summary {{ cursor: pointer; padding: 9px 10px; display: flex; gap: 8px; align-items: center; background: #f7faf9; }}
.case-body {{ padding: 10px; }}
.case-title {{ font-weight: bold; margin-right: auto; }}
.inspector {{ margin-top: 9px; border-radius: 6px; background: #f5f8f8; padding: 7px 9px; }}
.inspector summary {{ cursor: pointer; color: var(--accent); font-weight: bold; }}
.empty {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 28px; color: var(--muted); text-align: center; }}
@media (max-width: 760px) {{ .cols {{ grid-template-columns: 1fr; }} .visible-count {{ margin-left: 0; width: 100%; }} }}
</style>
</head>
<body>
<header>
  <h1>Combined Constraint Report</h1>
  <div class="subtitle">Source: {html.escape(source_name)}</div>
</header>
<main>
  <section class="metrics" id="metrics"></section>
  <section class="controls">
    <input id="search" type="search" placeholder="Search endpoint, property, constraint or reason...">
    <select id="status"><option value="">All statuses</option>{status_options}</select>
    <select id="verdict"><option value="">All verdicts</option>{verdict_options}</select>
    <span class="visible-count" id="count"></span>
  </section>
  <section id="results"></section>
</main>
<script>
const data = {embedded_json};
const endpointEntries = Object.entries(data);
const all = endpointEntries.flatMap(([endpoint, properties]) =>
  Object.values(properties).map(record => ({{ ...record, endpoint }})));
const statusCounts = {json.dumps(dict(statuses), ensure_ascii=False)};
const verdictCounts = {json.dumps(dict(verdicts), ensure_ascii=False)};
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const text = value => value === null || value === undefined ? 'null' :
  typeof value === 'string' ? value : JSON.stringify(value, null, 2);
function badgeClass(value) {{
  if (value === 'COMBINED_EQUIVALENT') return 'equiv';
  if (value === 'UNIQUE_STATIC' || value === 'UNIQUE_DYNAMIC') return 'unique';
  if (value === 'STATIC_WIN' || value === 'DYNAMIC_WIN' || value === 'BOTH_TRUE' || value === 'COMBINED_UNION') return 'good';
  if (value === 'CONFLICT_BOTH_FALSE') return 'bad';
  return 'pending';
}}
function badge(value) {{ return value ? `<span class="badge ${{badgeClass(value)}}">${{esc(value)}}</span>` : ''; }}
function metric(label, value) {{ return `<div class="metric"><strong>${{value}}</strong><span>${{esc(label)}}</span></div>`; }}
document.getElementById('metrics').innerHTML =
  metric('Endpoints', endpointEntries.length) + metric('Properties', all.length) +
  Object.entries(statusCounts).map(([k,v]) => metric(k, v)).join('') +
  Object.entries(verdictCounts).map(([k,v]) => metric(k, v)).join('');
function renderRecord(record) {{
  const cases = (record.validation_cases || []).map(renderCase).join('');
  const expressions = record.runtime_evaluation ? `<div class="cols field">
      <div><span class="label">Static executed expression</span><pre>${{esc(text(record.runtime_evaluation.static_expression))}}</pre></div>
      <div><span class="label">Dynamic executed expression</span><pre>${{esc(text(record.runtime_evaluation.dynamic_expression))}}</pre></div>
    </div>` : '';
  const staged = record.counter_example && !record.validation_cases ? `<div class="field"><span class="label">Counter-example seed</span><pre>${{esc(text(record.counter_example.staged_payload || record.counter_example))}}</pre></div>` : '';
  return `<details class="record">
    <summary><div class="record-head"><span class="property">${{esc(record.property)}}</span>${{badge(record.status)}}${{badge(record.verdict)}}</div></summary>
    <div class="record-body">
    <div class="cols">
      <div><span class="label">Static</span><pre>${{esc(text(record.static_constraint))}}</pre></div>
      <div><span class="label">Dynamic</span><pre>${{esc(text(record.dynamic_constraint))}}</pre></div>
    </div>
    <div class="field"><span class="label">Final constraint</span><pre>${{esc(text(record.final_constraint))}}</pre></div>
    <div class="field"><span class="label">Reason</span><div class="reason">${{esc(record.reason || '')}}</div></div>
    ${{expressions}}${{staged}}
    ${{cases ? `<div class="field"><span class="label">Runtime validation cases</span>${{cases}}</div>` : ''}}
    </div>
  </details>`;
}}
function renderCase(item) {{
  const status = item.verdict || 'UNKNOWN';
  const response = item.response_payload === undefined ? null : item.response_payload;
  return `<details class="case">
    <summary><span class="case-title">Case #${{esc(item.case_number)}}</span>${{badge(status)}} <span>${{esc(text(item.response_summary && item.response_summary.status_code))}}</span></summary>
    <div class="case-body">
      <div class="field"><span class="label">Request</span><pre>${{esc(text(item.request))}}</pre></div>
      <div class="cols field">
        <div><span class="label">Static validation: ${{esc(text(item.static_evaluation && item.static_evaluation.result))}}</span><pre>${{esc(text(item.static_evaluation && item.static_evaluation.executed_expression))}}</pre></div>
        <div><span class="label">Dynamic validation: ${{esc(text(item.dynamic_evaluation && item.dynamic_evaluation.result))}}</span><pre>${{esc(text(item.dynamic_evaluation && item.dynamic_evaluation.executed_expression))}}</pre></div>
      </div>
      <div class="field"><span class="label">Response summary</span><pre>${{esc(text(item.response_summary))}}</pre></div>
      <details class="inspector"><summary>Inspect response payload</summary><pre>${{esc(text(response))}}</pre></details>
    </div>
  </details>`;
}}
function render() {{
  const query = document.getElementById('search').value.trim().toLowerCase();
  const status = document.getElementById('status').value;
  const verdict = document.getElementById('verdict').value;
  let matched = 0;
  const groups = endpointEntries.map(([endpoint, properties]) => {{
    const records = Object.values(properties).filter(record => {{
      const haystack = JSON.stringify(record).toLowerCase() + ' ' + endpoint.toLowerCase();
      return (!query || haystack.includes(query)) &&
        (!status || record.status === status) &&
        (!verdict || record.verdict === verdict);
    }});
    if (!records.length) return '';
    matched += records.length;
    return `<details class="endpoint" open>
      <summary><span class="endpoint-name">${{esc(endpoint)}}</span><span class="endpoint-count">${{records.length}} properties</span></summary>
      <div class="items">${{records.map(renderRecord).join('')}}</div>
    </details>`;
  }}).join('');
  document.getElementById('count').textContent = `${{matched}} of ${{all.length}} properties`;
  document.getElementById('results').innerHTML = groups || '<div class="empty">No matching constraints.</div>';
}}
document.getElementById('search').addEventListener('input', render);
document.getElementById('status').addEventListener('change', render);
document.getElementById('verdict').addEventListener('change', render);
render();
</script>
</body>
</html>
"""


def generate_combination_report(
    json_path: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    json_path = Path(json_path)
    if output_path is None:
        output_path = json_path.with_name(DEFAULT_HTML_FILENAME)
    output_path = Path(output_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    output_path.write_text(
        render_combination_report(data, str(json_path)),
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render combined constraints as an HTML report.")
    parser.add_argument("--input", required=True, help="Path to combine_constraint_miners.json.")
    parser.add_argument("--output", default=None, help="Optional report HTML output path.")
    args = parser.parse_args()
    print(generate_combination_report(args.input, args.output))


if __name__ == "__main__":
    main()

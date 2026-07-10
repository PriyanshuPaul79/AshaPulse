import json
from datetime import datetime
from pathlib import Path

METRIC_LABELS = {
    "faithfulness": "Faithfulness",
    "answer_relevancy": "Answer Relevancy",
    "context_precision": "Context Precision",
    "clinical_accuracy": "Clinical Accuracy",
    "constraint_check": "Constraint Check",
    "hindi_purity": "Hindi Purity",
}

METRIC_ORDER = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "clinical_accuracy",
    "constraint_check",
    "hindi_purity",
]


def _score_color(score: float) -> tuple[str, str]:
    if score >= 0.9:
        return ("🟢", "green")
    elif score >= 0.7:
        return ("🟡", "yellow")
    else:
        return ("🔴", "red")


def print_report(result: dict):
    """Print a CLI-formatted eval report with all metrics."""
    summary = result.get("summary", {})
    results = result.get("results", [])
    errors = result.get("errors", [])

    print(f"\n{'=' * 60}")
    print(f"  NiDaan — Comprehensive Eval Report")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Metrics: {', '.join(METRIC_LABELS.values())}")
    print(f"{'=' * 60}")

    if summary:
        print(f"\n  Tests run: {summary['num_cases']}")
        print()
        for name in METRIC_ORDER:
            avg = summary.get(f"avg_{name}", 0)
            mini = summary.get(f"min_{name}", 0)
            maxi = summary.get(f"max_{name}", 0)
            emoji, _ = _score_color(avg)
            print(f"  {emoji} {METRIC_LABELS.get(name, name):<20}  avg={avg:<8}  min={mini:<8}  max={maxi}")
        print()

        if summary.get("total_claims_evaluated", 0) > 0:
            print(f"  Total claims evaluated: {summary['total_claims_evaluated']}")
            print(f"  Supported claims:       {summary['total_supported_claims']}")
            print(f"  Overall support rate:   {summary['overall_support_rate']:.4f}")
            print()

    if errors:
        print(f"  ❌ Errors: {len(errors)}")
        for e in errors:
            print(f"     {e['id']}: {e['error']}")
        print()

    for r in results:
        r_id = r['id']
        print(f"  ── {r_id} ──")
        print(f"     Symptoms: {r['symptoms'][:80]}{'...' if len(r['symptoms']) > 80 else ''}")

        for name in METRIC_ORDER:
            metric = r.get(name, {})
            score = metric.get("score", 0.0)
            emoji, _ = _score_color(score)
            label = METRIC_LABELS.get(name, name)
            line = f"     {emoji} {label:<20} {score:.4f}"
            err = metric.get("error")
            if err:
                line += f"  ⚠ {err}"
            print(line)

        f = r.get("faithfulness", {})
        judge_source = f.get("judge_source")
        if judge_source:
            print(f"     ⚙  Faithfulness judge:   {judge_source}")
        if f.get("unsupported_claims"):
            print(f"       Unsupported claims:")
            for claim in f["unsupported_claims"][:3]:
                print(f"         ✗ {claim[:100]}")
            if len(f["unsupported_claims"]) > 3:
                print(f"         ... and {len(f['unsupported_claims']) - 3} more")

        ca = r.get("clinical_accuracy", {})
        details = ca.get("details", {})
        if details.get("criticality_match") and not details["criticality_match"]["match"]:
            cm = details["criticality_match"]
            print(f"       ✗ Criticality: expected '{cm['expected']}', got '{cm['actual']}'")

        cc = r.get("constraint_check", {})
        if cc.get("violations"):
            for v in cc["violations"][:3]:
                print(f"       ✗ Violation: {v[:100]}")

        print()

    print(f"{'=' * 60}\n")


def save_json_report(result: dict, path: str):
    """Save eval results as JSON."""
    with open(path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def save_html_report(result: dict) -> str:
    """Generate a self-contained HTML report with all metrics."""
    summary = result.get("summary", {})
    results = result.get("results", [])

    rows = ""
    for r in results:
        metrics_html = ""
        for name in METRIC_ORDER:
            metric = r.get(name, {})
            score = metric.get("score", 0.0)
            color_class = "green" if score >= 0.9 else ("yellow" if score >= 0.7 else "red")
            label = METRIC_LABELS.get(name, name)
            metrics_html += f'<div class="metric"><span class="metric-label">{label}</span><span class="{color_class}">{score:.4f}</span></div>'

        unsupported_html = ""
        f = r.get("faithfulness", {})
        if f.get("unsupported_claims"):
            items = "".join(f"<li>{c}</li>" for c in f["unsupported_claims"])
            unsupported_html = f"<details><summary>Unsupported ({len(f['unsupported_claims'])})</summary><ul>{items}</ul></details>"

        rows += f"""
        <tr>
            <td>{r['id']}</td>
            <td title="{r['symptoms']}">{r['symptoms'][:60]}...</td>
            <td>{metrics_html}</td>
            <td>{unsupported_html}</td>
        </tr>"""

    summary_cards = ""
    for name in METRIC_ORDER:
        avg = summary.get(f"avg_{name}", 0)
        label = METRIC_LABELS.get(name, name)
        color_class = "green" if avg >= 0.9 else ("yellow" if avg >= 0.7 else "red")
        summary_cards += f"""
        <div class="card">
            <h3>{label}</h3>
            <div class="value {color_class}">{avg:.4f}</div>
            <div class="sub">min {summary.get(f'min_{name}', 0):.4f} / max {summary.get(f'max_{name}', 0):.4f}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NiDaan Eval Report</title>
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 1400px; margin: 0 auto; padding: 24px; background: #f0f2f5; color: #333; }}
    h1 {{ font-size: 24px; color: #1a1a2e; margin-bottom: 4px; }}
    .timestamp {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }}
    .card {{ background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    .card h3 {{ margin: 0 0 6px; color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
    .card .value {{ font-size: 24px; font-weight: 700; }}
    .card .sub {{ font-size: 11px; color: #999; margin-top: 4px; }}
    .green {{ color: #2e7d32; }}
    .yellow {{ color: #e65100; }}
    .red {{ color: #c62828; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    th {{ background: #1a1a2e; color: white; padding: 12px 14px; text-align: left; font-size: 13px; font-weight: 600; }}
    td {{ padding: 12px 14px; border-bottom: 1px solid #eee; vertical-align: top; font-size: 13px; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover {{ background: #f8f9ff; }}
    .metric {{ display: flex; justify-content: space-between; gap: 8px; padding: 2px 0; font-size: 12px; }}
    .metric-label {{ color: #666; }}
    .metric .green, .metric .yellow, .metric .red {{ font-weight: 600; }}
    details summary {{ cursor: pointer; color: #4a6cf7; font-size: 12px; }}
    details ul {{ margin: 6px 0 0; padding-left: 18px; }}
    details li {{ font-size: 12px; color: #555; margin: 3px 0; line-height: 1.4; }}
    .symptoms-cell {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: help; }}
</style>
</head>
<body>
    <h1>NiDaan — Comprehensive Evaluation Report</h1>
    <p class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &middot; {summary.get('num_cases', 0)} test cases</p>

    <div class="summary-grid">
        {summary_cards}
    </div>

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Symptoms</th>
                <th>Metrics</th>
                <th>Details</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</body>
</html>"""

    reports_dir = Path(__file__).resolve().parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    path = reports_dir / f"eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    path.write_text(html)
    return str(path)

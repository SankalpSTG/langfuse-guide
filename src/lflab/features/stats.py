"""Feature 11: reading your data back (Metrics API).

Everything in the dashboards is also available over the public API. The
Metrics API takes a small JSON query:
    view        what to read: "observations" or a scores view
    dimensions  group by these fields
    metrics     what to compute: measure + aggregation (sum, avg, p95, ...)
    filters     which rows to include

Here: per trace name, how many traces, p95 latency, tokens and cost. Then the
average of every numeric/boolean score.
"""

import json
from datetime import datetime, timedelta, timezone

from langfuse import get_client


def query(view: str, dimension: str, metrics: list[tuple[str, str]], days: int, extra_filters: list[dict]) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    body = {
        "view": view,
        "dimensions": [{"field": dimension}],
        "metrics": [{"measure": m, "aggregation": a} for m, a in metrics],
        "filters": extra_filters,
        "fromTimestamp": since,
        "toTimestamp": datetime.now(timezone.utc).isoformat(),
    }
    return get_client().api.metrics.metrics(query=json.dumps(body)).data


def run(days: int) -> None:
    # A trace's root observation carries its name and end-to-end latency.
    roots_only = [{"column": "isRootObservation", "operator": "=", "value": True, "type": "boolean"}]
    traces = query("observations", "name", [("count", "count"), ("latency", "p95")], days, roots_only)
    print(f"Traces in the last {days} day(s):")
    print(f"{'name':<22}{'count':>7}{'p95 ms':>10}")
    for t in traces:
        print(f"{t['name']:<22}{t['count_count']:>7}{t['p95_latency']:>10.0f}")

    # Tokens and cost live on the generations (the LLM calls), so read those per model.
    generations = [{"column": "type", "operator": "=", "value": "GENERATION", "type": "string"}]
    models = query(
        "observations",
        "providedModelName",
        [("count", "count"), ("totalTokens", "sum"), ("totalCost", "sum")],
        days,
        generations,
    )
    print(f"\n{'model':<22}{'calls':>7}{'tokens':>10}{'cost $':>12}")
    for m in models:
        print(f"{m['providedModelName']:<22}{m['count_count']:>7}"
              f"{m['sum_totalTokens']:>10}{m['sum_totalCost']:>12.6f}")

    scores = query("scores-numeric", "name", [("value", "avg"), ("count", "count")], days, [])
    print("\nScores:")
    for s in scores:
        print(f"  {s['name']:<20} avg {s['avg_value']:.2f} over {s['count_count']} scores")

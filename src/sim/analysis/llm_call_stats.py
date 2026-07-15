"""
Aggregate `llm_calls.jsonl` (written by analysis/llm_logger.py) into a
per-(model, agent_role, guidance) summary: call count, latency
(mean/median/p95), retries, and tokens.

The raw log has one JSON object per call, which is enough to answer "what did
the model say" but not "was this model fast/cheap/flaky overall" without
reading hundreds of lines by hand — that rollup is what this script is for.
Grouping by agent_role/guidance (not just model) means the --llm-no-guidance
ablation can be read off one table instead of diffing two separate log runs
by hand; older log lines that predate those fields just show "-".

Usage:
    python analysis/llm_call_stats.py                 # default: ../llm_calls.jsonl
    python analysis/llm_call_stats.py path/to/log.jsonl
    python analysis/llm_call_stats.py --run-id a1b2c3d4  # only that run
    python analysis/llm_call_stats.py --price ministral-3b-2512=0.04,0.14 ...

`--price MODEL=IN,OUT` gives USD per 1M input/output tokens for that model, so
a cost column can be computed; without it the cost column reads "n/a" instead
of guessing a number this script can't verify.
"""
import argparse
import json
import os
import sys
from collections import defaultdict


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def load_records(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _new_model_stats() -> dict:
    return {
        "calls": 0, "retried_calls": 0, "total_retries": 0,
        "latencies": [], "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
    }


def _group_key(r: dict) -> tuple:
    role = r.get("agent_role") or "-"
    guidance = r.get("guidance")
    guidance_str = "-" if guidance is None else str(guidance)
    return (r.get("model", "?"), role, guidance_str)


def aggregate(records) -> dict:
    by_group = defaultdict(_new_model_stats)
    for r in records:
        m = by_group[_group_key(r)]
        m["calls"] += 1
        retries = r.get("retries") or 0
        if retries:
            m["retried_calls"] += 1
            m["total_retries"] += retries
        if r.get("latency_s") is not None:
            m["latencies"].append(r["latency_s"])
        m["prompt_tokens"] += r.get("prompt_tokens") or 0
        m["completion_tokens"] += r.get("completion_tokens") or 0
        m["total_tokens"] += r.get("total_tokens") or 0
    return by_group


def parse_prices(specs: list[str]) -> dict:
    """--price model=IN,OUT (USD per 1M tokens), repeatable."""
    prices = {}
    for spec in specs:
        model, rest = spec.split("=", 1)
        in_price, out_price = (float(x) for x in rest.split(","))
        prices[model] = (in_price, out_price)
    return prices


def format_table(by_group: dict, prices: dict) -> str:
    headers = ["model", "role", "guidance", "calls", "retried", "mean_s", "p50_s", "p95_s",
               "avg_tok/call", "total_tok", "est_cost"]
    rows = []
    for (model, role, guidance), m in sorted(by_group.items()):
        lat = m["latencies"]
        mean_s = sum(lat) / len(lat) if lat else 0.0
        avg_tok = m["total_tokens"] / m["calls"] if m["calls"] else 0
        if model in prices:
            in_price, out_price = prices[model]
            cost = (m["prompt_tokens"] / 1_000_000 * in_price
                    + m["completion_tokens"] / 1_000_000 * out_price)
            cost_str = f"${cost:.2f}"
        else:
            cost_str = "n/a"
        rows.append([
            model, role, guidance, str(m["calls"]), str(m["retried_calls"]),
            f"{mean_s:.2f}", f"{_percentile(lat, 0.5):.2f}", f"{_percentile(lat, 0.95):.2f}",
            f"{avg_tok:.0f}", str(m["total_tokens"]), cost_str,
        ])

    widths = [max(len(h), *(len(row[i]) for row in rows)) if rows else len(h)
              for i, h in enumerate(headers)]
    lines = ["  ".join(h.ljust(w) for h, w in zip(headers, widths))]
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(c.ljust(w) for c, w in zip(row, widths)))
    return "\n".join(lines)


def main():
    default_path = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "llm_calls.jsonl"))
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default=default_path,
                         help=f"path to llm_calls.jsonl (default: {default_path})")
    parser.add_argument("--price", action="append", default=[],
                         metavar="MODEL=IN,OUT",
                         help="USD per 1M input,output tokens for MODEL; repeatable")
    parser.add_argument("--run-id", default=None,
                         help="only include calls from this run (see the 'run_id' field)")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"No log file at {args.path} (no LLM calls have been made yet).")
        sys.exit(1)

    prices = parse_prices(args.price)
    records = load_records(args.path)
    if args.run_id:
        records = (r for r in records if r.get("run_id") == args.run_id)
    by_group = aggregate(records)
    if not by_group:
        print("No matching calls found.")
        return
    print(format_table(by_group, prices))


if __name__ == "__main__":
    main()

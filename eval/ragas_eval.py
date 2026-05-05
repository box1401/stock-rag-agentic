"""RAGAS evaluation runner for Compass Equity.

Reads eval/golden_set.jsonl, hits the api /api/v1/analyze for each row,
extracts the markdown + retrieved context (citations), and computes:

  - faithfulness          (answer claim coverage by context)
  - answer_relevancy      (answer-vs-question semantic alignment)
  - context_precision     (retrieved context relevance to ground truth)

Writes results to eval/results/ragas_<timestamp>.json + .csv.

Usage:
    python eval/ragas_eval.py                     # default: localhost:8000
    API_URL=https://compass-api... python eval/ragas_eval.py
    python eval/ragas_eval.py --limit 5           # smoke run on first 5 questions
    python eval/ragas_eval.py --golden-set custom.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8000")
DEFAULT_GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_golden_set(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


async def run_one(client: httpx.AsyncClient, api_url: str, row: dict[str, Any]) -> dict[str, Any]:
    """Call /api/v1/analyze and return the raw response augmented with the ground truth row."""
    ticker = row.get("ticker") or "2330"
    language = row.get("language", "en")
    payload = {"ticker": ticker, "mode": "on_demand", "language": language}
    t0 = time.perf_counter()
    try:
        resp = await client.post(f"{api_url}/api/v1/analyze", json=payload, timeout=180.0)
        resp.raise_for_status()
        body = resp.json()
        latency = time.perf_counter() - t0
        return {**row, "answer": body.get("markdown", ""),
                "contexts": [str((c or {}).get("title", "")) + " :: " + str((c or {}).get("source_url", ""))
                             for c in (body.get("citations") or [])],
                "latency_s": round(latency, 2),
                "trace_events": len(body.get("trace") or []),
                "error": None}
    except Exception as e:
        return {**row, "answer": "", "contexts": [], "latency_s": time.perf_counter() - t0,
                "trace_events": 0, "error": str(e)}


def keyword_recall(answer: str, expected_keywords: list[str]) -> float:
    """Lightweight, dependency-free score: fraction of expected keywords present in the answer."""
    if not expected_keywords:
        return 1.0
    text = answer.lower()
    hits = sum(1 for k in expected_keywords if str(k).lower() in text)
    return round(hits / len(expected_keywords), 3)


def keyword_precision(answer: str, expected_keywords: list[str]) -> float:
    """Of the words present in the answer, how many were anticipated. Coarse but useful."""
    if not expected_keywords or not answer.strip():
        return 0.0
    text_words = set(w.strip(".,;:()").lower() for w in answer.split())
    expected = set(str(k).lower() for k in expected_keywords)
    if not text_words:
        return 0.0
    overlap = len(text_words & expected)
    return round(overlap / len(text_words), 4)


def has_refusal(answer: str) -> bool:
    refusals = ["no data", "資料不足", "無法", "no guidance", "not available", "no thesis"]
    a = answer.lower()
    return any(r.lower() in a for r in refusals)


def maybe_run_ragas(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """If `ragas` is installed, compute its standard metrics on top of our keyword scores."""
    try:
        from datasets import Dataset  # type: ignore[import-not-found]
        from ragas import evaluate  # type: ignore[import-not-found]
        from ragas.metrics import (  # type: ignore[import-not-found]
            answer_relevancy,
            context_precision,
            faithfulness,
        )
    except Exception:
        print("[ragas] not installed — skipping. `pip install ragas datasets` to enable.")
        return None

    ds_rows = [
        {
            "question": r["question"],
            "answer": r["answer"],
            "contexts": r["contexts"] or [r["ground_truth"]],
            "ground_truth": r["ground_truth"],
        }
        for r in rows
        if r.get("answer")
    ]
    if not ds_rows:
        print("[ragas] no answers to evaluate")
        return None

    ds = Dataset.from_list(ds_rows)
    print(f"[ragas] evaluating {len(ds_rows)} samples …")
    result = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision])
    return {k: float(v) for k, v in result.scores[0].items()} if result.scores else None


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--api-url", default=DEFAULT_API_URL)
    p.add_argument("--golden-set", default=str(DEFAULT_GOLDEN_SET))
    p.add_argument("--limit", type=int, default=0, help="Run only first N rows (0 = all)")
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--label", default="default", help="Label for output file")
    args = p.parse_args()

    rows = load_golden_set(Path(args.golden_set))
    if args.limit > 0:
        rows = rows[: args.limit]

    print(f"[eval] api={args.api_url} | rows={len(rows)} | concurrency={args.concurrency}")

    sem = asyncio.Semaphore(args.concurrency)

    async def gated(row: dict[str, Any], client: httpx.AsyncClient) -> dict[str, Any]:
        async with sem:
            return await run_one(client, args.api_url, row)

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*(gated(r, client) for r in rows))

    for r in results:
        r["keyword_recall"] = keyword_recall(r["answer"], r.get("expected_keywords") or [])
        r["keyword_precision"] = keyword_precision(r["answer"], r.get("expected_keywords") or [])
        r["refused"] = has_refusal(r["answer"])

    summary = {
        "label": args.label,
        "api_url": args.api_url,
        "n": len(results),
        "n_errors": sum(1 for r in results if r.get("error")),
        "avg_latency_s": round(sum(r["latency_s"] for r in results) / max(1, len(results)), 2),
        "avg_keyword_recall": round(
            sum(r["keyword_recall"] for r in results) / max(1, len(results)), 3
        ),
        "avg_trace_events": round(
            sum(r["trace_events"] for r in results) / max(1, len(results)), 1
        ),
        "refusal_rate": round(sum(1 for r in results if r["refused"]) / max(1, len(results)), 3),
    }

    print()
    print("=" * 60)
    for k, v in summary.items():
        print(f"  {k:24s} {v}")
    print("=" * 60)

    ragas_scores = maybe_run_ragas(results)
    if ragas_scores:
        for k, v in ragas_scores.items():
            print(f"  ragas/{k:18s} {v:.3f}")
            summary[f"ragas_{k}"] = v

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    json_path = RESULTS_DIR / f"ragas_{args.label}_{ts}.json"
    csv_path = RESULTS_DIR / f"ragas_{args.label}_{ts}.csv"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": results}, f, ensure_ascii=False, indent=2)

    if results:
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            cols = ["id", "ticker", "language", "keyword_recall", "keyword_precision",
                    "refused", "latency_s", "trace_events", "error"]
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in results:
                w.writerow({c: r.get(c, "") for c in cols})

    print(f"\nWrote {json_path}\nWrote {csv_path}")
    return 0 if summary["n_errors"] == 0 else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

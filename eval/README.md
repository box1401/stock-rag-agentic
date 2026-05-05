# RAGAS evaluation

20-question golden set covering thesis recall, macro context, refusal behaviour, and live market data.

## Run

```bash
# default — local docker stack
python eval/ragas_eval.py

# against prod
API_URL=https://compass-api-aujzogkiva-de.a.run.app python eval/ragas_eval.py --label prod

# smoke (first 5 questions)
python eval/ragas_eval.py --limit 5 --label smoke
```

## What it measures

| Metric | Definition | Why |
|---|---|---|
| `keyword_recall` | fraction of expected keywords in the answer | catches hallucinated answers that miss every anchor |
| `keyword_precision` | fraction of answer-words that match expected keywords | catches verbose answers that pad with off-topic content |
| `refusal_rate` | answers that admit "no data" / "資料不足" | catches over-eager fabrication |
| `avg_latency_s` | wall-clock per analyze call | tracks regressions |
| `avg_trace_events` | LangGraph events per run | catches pipelines that short-circuit |
| `ragas/faithfulness` | RAGAS — answer claims supported by context | needs `pip install ragas datasets` and a backing LLM |
| `ragas/answer_relevancy` | RAGAS — answer-question semantic alignment | same |
| `ragas/context_precision` | RAGAS — retrieved context relevance to ground truth | same |

The keyword metrics are dependency-free and run in seconds. RAGAS metrics layer on top when available.

## A/B comparison

Tag each run with `--label`:

```bash
python eval/ragas_eval.py --label v1-no-rag
# enable RAG (Supabase plus seed-secrets)
python eval/ragas_eval.py --label v2-with-rag
```

Then diff the two summary blocks.

## Tuning the golden set

`golden_set.jsonl` is one JSON-per-line. Each row:

```json
{"id": "...", "ticker": "2330", "language": "en|zh-TW",
 "question": "...", "ground_truth": "...",
 "expected_keywords": ["kw1", "kw2"]}
```

Tickers can be `null` for macro questions. `expected_keywords` powers the lightweight scorer.

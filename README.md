# Compass Equity

> Agentic equity research copilot for Taiwan-listed companies. Multi-agent LLM workflow grounded on real-time market data, filings, and news with verifiable citations.

**Live demo (Cloud Run, asia-east1):**
[Web](https://compass-web-aujzogkiva-de.a.run.app) · [API docs](https://compass-api-aujzogkiva-de.a.run.app/docs) · [Live agent trace](https://compass-web-aujzogkiva-de.a.run.app/trace)

[![Stage](https://img.shields.io/badge/stage-M3-green)]() [![License](https://img.shields.io/badge/license-MIT-blue)]() [![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20Next.js%2014%20%2B%20LangGraph-black)]() [![Deploy](https://img.shields.io/badge/deploy-Cloud%20Run-blue)]()

---

## What it does

You give Compass Equity a Taiwan ticker. Five cooperating agents — Supervisor, Data, Analyst, Risk, Reporter — pull live market data and recent filings, build a retrieval-augmented brief, run a self-critique loop, and produce a structured markdown / PDF research note with inline citations. The agent trace is streamed to the UI in real time so you can audit every retrieval, every tool call, every revision.

## Why

Most equity copilots are single-shot RAG demos: ask question, get plausible-sounding paragraph. Compass Equity is built around three product principles:

1. **Multi-agent with adversarial review.** A dedicated `RiskAgent` re-reads the analyst's draft, hunts for unsupported claims, and forces a rewrite when grounding is weak.
2. **Hybrid retrieval, not vector-only.** BM25 (Postgres `tsvector`) + dense (`text-embedding-005`) + cross-encoder rerank (`bge-reranker-v2-m3`).
3. **Auditability.** Every claim cites a chunk; every chunk has a source URL or filing ID; every agent step is visible in the trace UI and persisted to Langfuse.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router) · TypeScript · shadcn/ui · Tailwind · TradingView Lightweight Charts · Recharts · i18next |
| Backend | FastAPI · Pydantic v2 · SQLAlchemy 2.0 async · Alembic |
| LLM | `google-genai` SDK · Gemini 2.0 Flash (primary) · Gemini 1.5 Pro (fallback) · function calling |
| Embedding / Rerank | Vertex AI `text-embedding-005` · `bge-reranker-v2-m3` (self-hosted Cloud Run) |
| Agents | LangGraph · Supervisor + DataAgent + AnalystAgent + RiskAgent + ReporterAgent |
| RAG | pgvector (dense) + Postgres `tsvector` (BM25) + cross-encoder rerank |
| Data | TWSE · FinMind · Yahoo Finance · Goodinfo · MOPS filings · Tavily · Jina AI Reader |
| Storage | Supabase Postgres + pgvector · GCS |
| Auth | Supabase Auth (Google OAuth) |
| Queue | GCP Cloud Tasks |
| Observability | Langfuse Cloud |
| Eval | RAGAS (faithfulness, answer relevancy, context precision) on a 20-item golden set |
| Deploy | Cloud Run × 3 (web, api, reranker) · Terraform · GitHub Actions |

## Quickstart (local)

```bash
cp .env.example .env       # fill in keys
make dev                   # docker compose up: postgres+pgvector, api, web
open http://localhost:3000
```

See [docs/SETUP.md](docs/SETUP.md) for full setup.

## Architecture

```
[Next.js / Cloud Run]
     │
     ▼
[FastAPI / Cloud Run] ──► Cloud Tasks ──► Worker ──► LangGraph supervisor
     │                                                  ├─ DataAgent
     ▼                                                  ├─ AnalystAgent (RAG)
[Supabase Postgres + pgvector] ◄─ Reranker / Cloud Run  ├─ RiskAgent (loop)
     │                                                  └─ ReporterAgent
     ▼
[GCS]
```

## Roadmap

- [x] **M1** — monorepo skeleton, Data + Analyst agents, single-ticker analyze
- [x] **M2** — RAG ingestion (markdown / PDF / web), pgvector + BM25 hybrid retrieval, bge-reranker-v2-m3 cross-encoder, function-calling AnalystAgent, RiskAgent self-critique loop, SSE live-trace UI
- [x] **M3** — Terraform-managed Cloud Run × 3 (api / web / reranker), Workload Identity Federation for keyless GitHub-OIDC deploys, Artifact Registry, Secret Manager, GCS, Cloud Tasks queue. Walkthrough: [docs/DEPLOY.md](docs/DEPLOY.md)
- [ ] **M4** — RAGAS eval, Langfuse, polish, blog series

## License

MIT

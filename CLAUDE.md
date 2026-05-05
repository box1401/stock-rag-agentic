# Compass Equity — agent guide

Brand: **Compass Equity** — agentic equity research copilot for Taiwan-listed companies.

## Layout
- `apps/api` FastAPI + LangGraph agents (Python 3.11)
- `apps/web` Next.js 14 App Router (TypeScript)
- `apps/reranker` cross-encoder service (M2+)
- `infra/terraform` GCP IaC (M3+)
- `infra/supabase/migrations` SQL migrations applied locally and to Supabase
- `eval/` RAGAS golden set + scripts (M4)

## Conventions
- Backend formatter: `ruff format`. Linter: `ruff check`. Types: `mypy --strict` on `app/`.
- Frontend: Prettier + ESLint (Next defaults) + strict TypeScript.
- Commit style: Conventional Commits (`feat:`, `fix:`, `chore:`...). Scope = top-level dir.
- All LLM calls go through `app/llm/gateway.py`. Never import `google-genai` elsewhere.
- All external HTTP goes through `app/tools/_http.py` (httpx async client + retry).
- Public API responses are Pydantic v2 models in `app/schemas/`.

## Don't
- Don't add Redis / Celery — we use Cloud Tasks.
- Don't add LINE / line-bot-sdk — explicitly removed from v1.
- Don't import from another agent's module. Agents communicate via LangGraph state, not direct calls.
- Don't write code comments that just describe what the code does.
- Don't add backwards-compat shims for v1 — we are a fresh app.

## Skip when reading
- `data/seed/*.pdf` — large binaries, do not Read unless explicitly asked.
- `apps/web/.next/` — build artifacts.
- `*.tfstate*` — Terraform state.

## Testing
- `pytest` with `pytest-asyncio` mode=auto.
- HTTP fixtures: `respx` for httpx mocks.
- Coverage target: 80% on `app/agents`, `app/tools`, `app/rag`.

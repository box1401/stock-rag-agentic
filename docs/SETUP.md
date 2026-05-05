# Setup

## 0. Prereqs

| Tool | Version | Why |
|---|---|---|
| Docker Desktop | 24+ | Local dev: postgres + api + web |
| Python | 3.11 | Backend (use 3.11 — pgvector wheels not on 3.13 yet) |
| Node.js | 20 LTS | Frontend |
| GitHub account | — | repo + Actions |
| GCP account | — | Vertex embedding (M2+) and deploy (M3) |
| Supabase account | — | hosted Postgres + Auth (M2+) |

## 1. Clone & env

```bash
git clone <your-repo-url> compass-equity
cd compass-equity
cp .env.example .env
```

Fill in at least these to get a working `/analyze`:

```dotenv
GEMINI_API_KEY=...           # https://aistudio.google.com/apikey
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/compass
```

Optional now (M2+):

```dotenv
TAVILY_API_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
SUPABASE_URL=...
SUPABASE_JWT_SECRET=...
GCP_PROJECT_ID=...
```

## 2. Run locally

```bash
make dev
```

This brings up:

| Service | Port | URL |
|---|---|---|
| db (postgres + pgvector) | 5432 | — |
| api (FastAPI) | 8000 | http://localhost:8000/docs |
| web (Next.js) | 3000 | http://localhost:3000 |

The DB is auto-initialized from `infra/supabase/migrations/0001_init.sql` on first start.

## 3. Smoke test

```bash
# 1) health
curl http://localhost:8000/health

# 2) tickers list (seeded with 6 default tickers)
curl http://localhost:8000/api/v1/tickers

# 3) analyze one ticker (requires GEMINI_API_KEY in .env)
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker":"2330","mode":"on_demand","language":"zh-TW"}' | jq .
```

Then open http://localhost:3000/dashboard and submit `2330`.

## 4. Backend tests

```bash
cd apps/api
pip install -e ".[dev]"
pytest -v
```

## 5. Frontend type-check & lint

```bash
cd apps/web
npm install --legacy-peer-deps
npm run lint
npm run build
```

## 6. Migrations

When you change a model in `apps/api/app/db/models.py`:

```bash
make revision m="add_xyz"
make migrate
```

Apply the same migration to Supabase (M2+) by copying the generated SQL from `apps/api/alembic/versions/*.py` into `infra/supabase/migrations/`.

## 7. Common issues

- **`pgvector` install fails on host Python 3.13** — use 3.11. Inside Docker we already pin 3.11.
- **Gemini 429 / quota** — free tier is 15 RPM / 1500 RPD. Wait or set `RATE_LIMIT_PER_MINUTE` lower.
- **Empty FinMind data** — set `FINMIND_TOKEN` to raise the rate limit.
- **CORS** — defaults to `*` in dev. Tighten in `app/main.py` for production.

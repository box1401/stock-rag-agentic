# Hooking up Supabase as the production database

Compass Equity uses Supabase for hosted Postgres + pgvector + Auth. Free tier: 500 MB DB + 1 GB file storage + 2 GB egress, no credit card.

## 1. Create the project

1. Open <https://supabase.com/dashboard> and sign in (Google OAuth is fastest).
2. **New Project**:
   - **Name**: `compass-equity`
   - **Region**: `Southeast Asia (Singapore) – ap-southeast-1` (closest to Taiwan)
   - **Database Password**: generate a strong one and **save it somewhere safe** — you'll need it in step 3
3. Wait ~2 minutes for provisioning.

## 2. Collect the credentials

In the Supabase dashboard:

- **Project Settings → API**:
  - `Project URL` → `SUPABASE_URL`
  - `anon` key → `SUPABASE_ANON_KEY`
  - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY` (KEEP SECRET; never commit)
  - JWT Secret → `SUPABASE_JWT_SECRET`
- **Project Settings → Database → Connection string** (use **Direct connection**, **URI** format):
  - replace `[YOUR-PASSWORD]` with the password from step 1.3
  - example: `postgresql://postgres:abcd1234@db.xyz.supabase.co:5432/postgres`
  - we need an **async** version for the api: replace `postgresql://` with `postgresql+asyncpg://` → that becomes `DATABASE_URL`

## 3. Apply the schema migrations

The schema (extensions + tables + indexes + seed tickers) is in `infra/supabase/migrations/0001_init.sql`.

```bash
chmod +x infra/scripts/apply-supabase-migrations.sh

# Use the SYNC URL (postgresql://, no asyncpg) for psql
SYNC_URL='postgresql://postgres:YOUR_PASSWORD@db.xyz.supabase.co:5432/postgres'
./infra/scripts/apply-supabase-migrations.sh "$SYNC_URL"
```

If psql isn't installed on your machine, the SQL also runs fine pasted into the Supabase **SQL Editor**.

## 4. Update `.env.production` and seed Secret Manager

```bash
# Edit .env.production with the values from step 2:
#   DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xyz.supabase.co:5432/postgres
#   SUPABASE_URL=https://xyz.supabase.co
#   SUPABASE_ANON_KEY=eyJ...
#   SUPABASE_SERVICE_ROLE_KEY=eyJ...
#   SUPABASE_JWT_SECRET=<from API settings>

./infra/scripts/seed-secrets.sh compass-equity
```

## 5. Force a new Cloud Run revision so api picks up the new secrets

```bash
gcloud run services update compass-api \
  --project=compass-equity \
  --region=asia-east1 \
  --update-env-vars=COMPASS_REFRESH=$(date +%s)
```

## 6. Verify

```bash
API=https://compass-api-aujzogkiva-de.a.run.app

# /tickers should now return seed rows (was 500 before)
curl "$API/api/v1/tickers"

# Ingest the thesis seed
curl -X POST "$API/api/v1/ingest/thesis"

# Re-run /analyze — RAG should now hit thesis chunks
curl -X POST "$API/api/v1/analyze" -H "Content-Type: application/json" \
  -d '{"ticker":"2330","mode":"on_demand","language":"en"}' | jq '.citations | length'
```

Expected: `citations` returns >= 4 chunks; trace shows `tool:rag_search` with non-empty results.

## Caveat: `/api/v1/ingest/thesis` reads `/data/thesis` inside the container

In production, `data/thesis/*.md` is **not** mounted. Two options:

1. **Re-deploy with the files baked in** — add `COPY data/thesis /data/thesis` to `apps/api/Dockerfile` and push.
2. **Use `/api/v1/ingest/url`** instead — host the markdown elsewhere (gist, S3) and POST the URL.

Option 1 is simpler for a small portfolio of theses. Option 2 scales better if your thesis library grows.

## Cost gotcha

Supabase free tier kills the project if it's idle for 7 consecutive days. For a portfolio demo that's fine — first request after dormancy takes ~10 s to wake the DB. If you need always-on, the Pro plan is $25/mo.

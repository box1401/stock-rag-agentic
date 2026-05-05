# Deploy Compass Equity to Google Cloud

End-to-end walkthrough: clean GCP project → live URL on `*.run.app`.

## Architecture (production)

```
       browser
          │
          ▼
[Cloud Run / web]  (Next.js 14 standalone, port 3000)
          │ NEXT_PUBLIC_API_URL
          ▼
[Cloud Run / api]  (FastAPI + LangGraph, port 8000)
   │   │   │
   │   │   └─► Supabase Postgres + pgvector  (external)
   │   └────► Cloud Run / reranker  (bge-reranker-v2-m3, baked into image)
   └────────► Secret Manager  (Gemini / Tavily / Supabase / Langfuse / FinMind)
   └────────► Cloud Storage  (generated reports)
   └────────► Cloud Tasks    (queue for ingestion jobs, M4)
```

All three Cloud Run services scale-to-zero by default (free-tier friendly).

## 0. Prerequisites

| Tool | Why |
|---|---|
| `gcloud` CLI | bootstrap + auth |
| `gh` CLI | set repo secrets (optional, can do via web UI) |
| GCP billing-enabled project | Cloud Run / Artifact Registry / Secret Manager |
| Supabase project | hosted Postgres + Auth |
| Gemini API key | LLM (free tier ok) |

A fresh GCP project gets $300 / 90-day free credit on top of the always-free Cloud Run / Secret Manager / Artifact Registry quotas.

## 1. Create the GCP project

```bash
PROJECT_ID=compass-equity-prod
gcloud projects create $PROJECT_ID --set-as-default
gcloud beta billing projects link $PROJECT_ID --billing-account=<YOUR_BILLING_ID>
```

## 2. Bootstrap (one time)

```bash
cd infra/scripts
chmod +x bootstrap.sh seed-secrets.sh

# Enables APIs, creates tfstate bucket, sets up Workload Identity Federation for GitHub OIDC.
./bootstrap.sh $PROJECT_ID asia-east1
```

The script prints the GitHub repo secrets/variables you need to set. With `gh`:

```bash
gh secret set WIF_PROVIDER --body "<from bootstrap output>"
gh secret set WIF_SERVICE_ACCOUNT --body "compass-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
gh variable set GCP_PROJECT_ID --body "$PROJECT_ID"
gh variable set GCP_PROJECT_NUMBER --body "<from bootstrap output>"
gh variable set GCP_REGION --body "asia-east1"
```

## 3. First push → Terraform creates everything except secret values

```bash
git push origin main
```

The `deploy.yml` workflow:

1. Authenticates via WIF (no JSON keys).
2. Builds + pushes the three images to Artifact Registry.
3. Runs `terraform init/plan/apply` — provisions Artifact Registry, Secret Manager containers, GCS, Cloud Tasks, Workload Identity, Cloud Run × 3.
4. Cloud Run services boot but `api` will be unhealthy until secrets are seeded (next step).

## 4. Seed Secret Manager from your local `.env`

```bash
# Recommended: copy .env to .env.production and set production-grade values
cp .env .env.production
# edit .env.production — set Supabase prod URL, prod DATABASE_URL, etc.

./infra/scripts/seed-secrets.sh $PROJECT_ID
```

Cloud Run picks up new secret versions on the next request (or restart the service).

## 5. Verify

```bash
API_URL=$(cd infra/terraform && terraform output -raw api_url)
WEB_URL=$(cd infra/terraform && terraform output -raw web_url)

curl "$API_URL/health"
open "$WEB_URL"
```

## 6. Ingest the seed thesis files into the prod DB

The shipped `data/thesis/*.md` are not auto-loaded in production. Run once:

```bash
curl -X POST "$API_URL/api/v1/ingest/thesis"
```

(Make sure the api container has `/data` populated — for production, prefer pushing thesis files to GCS and loading from there in M4. For now, you can re-deploy with the bind mount or call `/api/v1/ingest/url` for individual sources.)

## 7. Day-to-day

- **Push to main** → CI builds new images, terraform apply rolls forward (image tag = commit sha).
- **Rotate a secret** → run `seed-secrets.sh` again. New version is created; Cloud Run reads `:latest`.
- **Inspect logs** → `gcloud run services logs read compass-api --region=asia-east1 --limit=100`.
- **Tear down** → `cd infra/terraform && terraform destroy -var "project_id=$PROJECT_ID" -var "region=asia-east1"`.

## Cost expectations (free-tier path)

| Service | Free quota | Notes |
|---|---|---|
| Cloud Run | 2M req + 360k vCPU-sec / mo | Each service scales to 0 |
| Artifact Registry | 0.5 GB | Reranker image ~2 GB → ~$0.15/mo |
| Secret Manager | 6 active versions / secret / mo | Plenty |
| Cloud Storage | 5 GB | Reports stay small |
| Cloud Tasks | 1M ops / mo | Demo will not approach this |
| Cloud Logging | 50 GB ingest / mo | Plenty |

Reranker cold-start: ~5–8 seconds (the model is baked into the image, so startup is just process spin-up, not model download). Set `reranker_min_instances = 1` if you need always-warm and accept ~$15/mo extra.

## Common issues

- **"permission denied … iam.serviceAccountTokenCreator"** — you need to wait ~30s after WIF bootstrap; IAM propagation is eventually consistent.
- **`api` boots but 500s** — Secret Manager values not seeded; run `seed-secrets.sh`.
- **`web` returns 502** — `NEXT_PUBLIC_API_URL` was baked at build time; re-run the workflow with the correct API URL after the first deploy (it converges on the second push).
- **Reranker OOM** — bump `reranker_memory` to `4Gi`.
- **Costs spiking** — set `min_instances = 0` everywhere (the default).

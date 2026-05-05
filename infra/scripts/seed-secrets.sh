#!/usr/bin/env bash
# Seed Secret Manager from a local .env file. Reads .env.production from repo root if present,
# otherwise falls back to .env. Skips empty values.
set -euo pipefail

PROJECT_ID="${1:?Usage: ./seed-secrets.sh <PROJECT_ID> [/path/to/.env]}"
ENV_FILE="${2:-}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ -z "$ENV_FILE" ]]; then
  if   [[ -f "$REPO_ROOT/.env.production" ]]; then ENV_FILE="$REPO_ROOT/.env.production"
  elif [[ -f "$REPO_ROOT/.env" ]];           then ENV_FILE="$REPO_ROOT/.env"
  else echo "no .env file found"; exit 1
  fi
fi

declare -A MAP=(
  [GEMINI_API_KEY]=gemini-api-key
  [TAVILY_API_KEY]=tavily-api-key
  [SUPABASE_JWT_SECRET]=supabase-jwt-secret
  [SUPABASE_URL]=supabase-url
  [SUPABASE_ANON_KEY]=supabase-anon-key
  [SUPABASE_SERVICE_ROLE_KEY]=supabase-service-role-key
  [DATABASE_URL]=database-url
  [LANGFUSE_PUBLIC_KEY]=langfuse-public-key
  [LANGFUSE_SECRET_KEY]=langfuse-secret-key
  [FINMIND_TOKEN]=finmind-token
)

echo ">> Reading ${ENV_FILE}"

for ENVKEY in "${!MAP[@]}"; do
  SECRET_ID="${MAP[$ENVKEY]}"
  VALUE="$(grep -E "^${ENVKEY}=" "$ENV_FILE" | head -n1 | cut -d'=' -f2- || true)"
  VALUE="${VALUE%\"}"; VALUE="${VALUE#\"}"
  if [[ -z "$VALUE" ]]; then
    echo "  skip ${ENVKEY} (empty)"
    continue
  fi
  if ! gcloud secrets describe "${SECRET_ID}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "  warn ${SECRET_ID} not found yet — run terraform apply first"
    continue
  fi
  printf '%s' "$VALUE" | gcloud secrets versions add "${SECRET_ID}" \
    --project="${PROJECT_ID}" --data-file=- >/dev/null
  echo "  ok   ${ENVKEY} -> ${SECRET_ID}"
done

echo "Done."

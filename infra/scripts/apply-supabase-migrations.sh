#!/usr/bin/env bash
# Apply infra/supabase/migrations/*.sql to a Supabase project.
#
# Usage:
#   ./apply-supabase-migrations.sh "postgresql://postgres:PASS@db.<ref>.supabase.co:5432/postgres"
#
set -euo pipefail

DB_URL="${1:?Usage: ./apply-supabase-migrations.sh '<DATABASE_URL>'}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIG_DIR="${REPO_ROOT}/infra/supabase/migrations"

if ! command -v psql >/dev/null 2>&1; then
  echo "psql not found. Install PostgreSQL client first (e.g. via 'choco install postgresql --params \"/Password:dummy\"' on Windows)."
  exit 1
fi

shopt -s nullglob
files=("${MIG_DIR}"/*.sql)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "no .sql files in ${MIG_DIR}"
  exit 1
fi

for f in "${files[@]}"; do
  echo ">> applying $(basename "$f")"
  psql "${DB_URL}" -v ON_ERROR_STOP=1 -f "$f"
done

echo "Migrations applied."

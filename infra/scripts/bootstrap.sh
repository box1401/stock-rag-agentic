#!/usr/bin/env bash
# Compass Equity — one-time GCP bootstrap.
#
# Run from your laptop after `gcloud auth login`. This handles the chicken-and-egg
# bits Terraform can't: enabling APIs on a fresh project, creating the tfstate
# bucket, and creating the Workload Identity Federation pieces GitHub Actions
# needs to authenticate. After this, GitHub Actions takes over via deploy.yml.
#
# Usage:
#   ./bootstrap.sh <PROJECT_ID> [REGION]
#
# Env vars (optional):
#   GITHUB_REPO   default: box1401/stock-rag-agentic
#
set -euo pipefail

PROJECT_ID="${1:?Usage: ./bootstrap.sh <PROJECT_ID> [REGION]}"
REGION="${2:-asia-east1}"
GITHUB_REPO="${GITHUB_REPO:-box1401/stock-rag-agentic}"

REQUIRED_APIS=(
  artifactregistry.googleapis.com
  run.googleapis.com
  iam.googleapis.com
  iamcredentials.googleapis.com
  secretmanager.googleapis.com
  storage.googleapis.com
  cloudtasks.googleapis.com
  cloudscheduler.googleapis.com
  sts.googleapis.com
  serviceusage.googleapis.com
  cloudresourcemanager.googleapis.com
)

echo ">> Setting active project to ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" >/dev/null

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"

echo ">> Enabling APIs (this can take a few minutes)..."
gcloud services enable "${REQUIRED_APIS[@]}"

# ---- Artifact Registry docker repo --------------------------------------
AR_REPO="${AR_REPO:-compass}"
if ! gcloud artifacts repositories describe "${AR_REPO}" \
       --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo ">> Creating Artifact Registry repo ${AR_REPO} in ${REGION}"
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Compass Equity container images"
else
  echo ">> Artifact Registry repo already exists"
fi

# ---- tfstate bucket -----------------------------------------------------
TFSTATE_BUCKET="${PROJECT_ID}-tfstate"
if ! gsutil ls -b "gs://${TFSTATE_BUCKET}" >/dev/null 2>&1; then
  echo ">> Creating tfstate bucket gs://${TFSTATE_BUCKET}"
  gsutil mb -p "${PROJECT_ID}" -l "${REGION}" -b on "gs://${TFSTATE_BUCKET}"
  gsutil versioning set on "gs://${TFSTATE_BUCKET}"
else
  echo ">> tfstate bucket already exists"
fi

# ---- Workload Identity Federation (GitHub OIDC) -------------------------
POOL_ID="github-pool"
PROVIDER_ID="github-provider"
SA_NAME="compass-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo ">> Ensuring deployer service account ${SA_EMAIL}"
if ! gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="GitHub Actions deployer (bootstrap)"
fi

echo ">> Granting bootstrap roles to deployer (Terraform later refines)..."
for ROLE in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser \
            roles/secretmanager.admin roles/storage.admin roles/cloudtasks.admin \
            roles/serviceusage.serviceUsageAdmin roles/iam.workloadIdentityPoolAdmin; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" >/dev/null
done

if ! gcloud iam workload-identity-pools describe "${POOL_ID}" --location=global >/dev/null 2>&1; then
  echo ">> Creating WIF pool ${POOL_ID}"
  gcloud iam workload-identity-pools create "${POOL_ID}" \
    --location=global --display-name="GitHub OIDC"
fi

if ! gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
       --location=global --workload-identity-pool="${POOL_ID}" >/dev/null 2>&1; then
  echo ">> Creating WIF provider ${PROVIDER_ID} for ${GITHUB_REPO}"
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
    --location=global \
    --workload-identity-pool="${POOL_ID}" \
    --display-name="GitHub Actions" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository == \"${GITHUB_REPO}\"" \
    --issuer-uri="https://token.actions.githubusercontent.com"
fi

POOL_FULL_ID="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}"
PROVIDER_FULL_ID="${POOL_FULL_ID}/providers/${PROVIDER_ID}"

echo ">> Binding GitHub repo to deployer SA via principalSet"
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_FULL_ID}/attribute.repository/${GITHUB_REPO}" >/dev/null

cat <<EOF

=========================================================================
 Bootstrap complete. Now configure GitHub repo secrets and variables:

   gh secret set WIF_PROVIDER --body "${PROVIDER_FULL_ID}"
   gh secret set WIF_SERVICE_ACCOUNT --body "${SA_EMAIL}"
   gh variable set GCP_PROJECT_ID --body "${PROJECT_ID}"
   gh variable set GCP_PROJECT_NUMBER --body "${PROJECT_NUMBER}"
   gh variable set GCP_REGION --body "${REGION}"

 Then seed Secret Manager values (run once after first \`terraform apply\`,
 or before — Terraform creates the secret containers, this fills them):

   ./infra/scripts/seed-secrets.sh ${PROJECT_ID}

 Finally push to main and watch Actions deploy.
=========================================================================
EOF

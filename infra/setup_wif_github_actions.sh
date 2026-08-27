#!/usr/bin/env bash
# Sets up Workload Identity Federation so GitHub Actions can deploy to Cloud Run
# WITHOUT a downloaded service-account key. Restricts trust to one specific GitHub
# repository.
#
# Usage: bash infra/setup_wif_github_actions.sh PROJECT_ID github-owner/github-repo
set -euo pipefail

PROJECT_ID="${1:?Usage: setup_wif_github_actions.sh PROJECT_ID github-owner/github-repo}"
GITHUB_REPO="${2:?Usage: setup_wif_github_actions.sh PROJECT_ID github-owner/github-repo}"

POOL_ID="github-pool"
PROVIDER_ID="github-provider"
SA_NAME="github-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"

echo "==> Creating deploy service account (${SA_EMAIL})"
gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "${SA_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="GitHub Actions deployer"

echo "==> Granting the deploy service account the roles it needs"
for ROLE in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser \
            roles/cloudscheduler.admin roles/storage.objectViewer roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None \
    >/dev/null
done

echo "==> Creating Workload Identity Pool"
gcloud iam workload-identity-pools describe "${POOL_ID}" --project="${PROJECT_ID}" --location="global" >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools create "${POOL_ID}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --display-name="GitHub Actions pool"

echo "==> Creating Workload Identity Provider restricted to ${GITHUB_REPO}"
gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" --location="global" --workload-identity-pool="${POOL_ID}" >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --workload-identity-pool="${POOL_ID}" \
    --display-name="GitHub provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
    --issuer-uri="https://token.actions.githubusercontent.com"

echo "==> Allowing only workflows in ${GITHUB_REPO} to impersonate the deploy service account"
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_REPO}" \
  >/dev/null

cat <<EOF

Done. Add these as GitHub Actions repository VARIABLES (not secrets):

GCP_WORKLOAD_IDENTITY_PROVIDER = projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}
GCP_SERVICE_ACCOUNT             = ${SA_EMAIL}
EOF

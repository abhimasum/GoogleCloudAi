#!/usr/bin/env bash
# One-time project setup: enables required APIs, creates the Cloud Storage bucket for
# source documents, an Artifact Registry repo for container images, and a dedicated
# service account Cloud Scheduler will use to invoke the ingestion Cloud Run service.
#
# Usage: bash infra/setup_gcp.sh PROJECT_ID [REGION]
set -euo pipefail

PROJECT_ID="${1:?Usage: setup_gcp.sh PROJECT_ID [REGION]}"
REGION="${2:-us-central1}"
BUCKET="gs://${PROJECT_ID}-adk-docs"
AR_REPO="adk-agents"
SCHEDULER_SA="scheduler-invoker"

echo "==> Setting active project to ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}"

echo "==> Enabling required APIs (this can take a minute)"
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com

echo "==> Creating Cloud Storage bucket ${BUCKET} (skips if it already exists)"
gsutil ls -b "${BUCKET}" >/dev/null 2>&1 || gsutil mb -l "${REGION}" "${BUCKET}"

echo "==> Creating Artifact Registry repo ${AR_REPO} in ${REGION}"
gcloud artifacts repositories describe "${AR_REPO}" --location="${REGION}" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Container images for the ADK sample agents"

echo "==> Creating the Cloud Scheduler -> Cloud Run invoker service account"
gcloud iam service-accounts describe "${SCHEDULER_SA}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "${SCHEDULER_SA}" \
    --display-name="Cloud Scheduler invoker for the ingestion service"

cat <<EOF

Done.
  Bucket:            ${BUCKET}
  Artifact Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}
  Scheduler SA:      ${SCHEDULER_SA}@${PROJECT_ID}.iam.gserviceaccount.com

Next: upload the sample docs, then follow docs/SETUP.md step 4 to create the RAG corpus.
EOF

# Setup guide (for a personal / free Google Cloud developer account)

This guide assumes you have never used Google Cloud before. Follow it in order.

## 0. Prerequisites

- A Google account.
- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed.
- Python 3.11+.
- A GitHub repository (this one) you can push to and configure Actions secrets on.

## 1. Create a Google Cloud project and enable billing

1. Go to <https://console.cloud.google.com/projectcreate> and create a project, e.g. `my-adk-lab`.
2. New accounts get **$300 of free credit** — link a billing account to the project
   (Billing → Link a billing account). Vertex AI, Cloud Run, Cloud Storage and Cloud
   Scheduler all have free tiers, but Vertex AI (Gemini + RAG Engine) requires billing to
   be enabled even if you stay within the free credit.
3. Note your **Project ID** (not the display name) — you'll use it everywhere below.

## 2. Authenticate the CLI and enable APIs

```powershell
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login   # lets local Python code use your user credentials
```

Run the setup script, which enables every API this project needs and creates the
Cloud Storage bucket + Artifact Registry repo:

```powershell
# Git Bash / WSL / Cloud Shell (bash), not plain PowerShell:
bash infra/setup_gcp.sh YOUR_PROJECT_ID us-central1
```

This enables: `aiplatform.googleapis.com`, `run.googleapis.com`,
`cloudbuild.googleapis.com`, `artifactregistry.googleapis.com`,
`cloudscheduler.googleapis.com`, `storage.googleapis.com`, `iamcredentials.googleapis.com`,
`iam.googleapis.com`, and creates:

- A Cloud Storage bucket: `gs://YOUR_PROJECT_ID-adk-docs`
- An Artifact Registry Docker repo: `adk-agents` in `us-central1`

## 3. Upload the sample documents

```powershell
gsutil -m cp data/sample_docs/*.md gs://YOUR_PROJECT_ID-adk-docs/docs/
```

## 4. Create your first RAG corpus and ingest the documents (run once, locally)

```powershell
cd ingestion
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
$env:GOOGLE_CLOUD_LOCATION="us-central1"
$env:RAG_GCS_SOURCE="gs://YOUR_PROJECT_ID-adk-docs/docs/*"
python ingest.py
```

The script prints a line like:

```
Ingestion complete. RAG_CORPUS resource name: projects/123456789/locations/us-central1/ragCorpora/4611686018427387904
```

Save that full resource name — you'll set it as `RAG_CORPUS` everywhere below (locally,
in Cloud Run, and as a GitHub Actions variable). Re-running `ingest.py` later with the
same `RAG_CORPUS_ID` env var (see `ingestion/ingest.py`) re-uses the existing corpus
instead of creating a new one each time.

## 5. Run both agents locally (before touching Cloud Run)

Terminal 1 — the retriever agent, exposed over A2A on port 8081:

```powershell
cd agents/retriever_agent
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
$env:GOOGLE_CLOUD_LOCATION="us-central1"
$env:GOOGLE_GENAI_USE_VERTEXAI="true"
$env:RAG_CORPUS="projects/.../locations/us-central1/ragCorpora/..."
$env:PORT="8081"
uvicorn a2a_app:a2a_app --port 8081
```

Terminal 2 — the orchestrator agent, with a web UI on port 8080:

```powershell
cd agents/orchestrator_agent
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
$env:GOOGLE_CLOUD_LOCATION="us-central1"
$env:GOOGLE_GENAI_USE_VERTEXAI="true"
$env:RETRIEVER_AGENT_URL="http://localhost:8081"
$env:PORT="8080"
python main.py
```

Open <http://localhost:8080> and ask something like *"What is Vertex AI RAG Engine and
how does A2A fit into this project?"* — the orchestrator should delegate to
`retriever_agent` over A2A and answer using your ingested documents.

## 6. Deploy manually once with `gcloud` (understand it before automating it)

```powershell
$PROJECT = "YOUR_PROJECT_ID"
$REGION = "us-central1"
$REPO = "$REGION-docker.pkg.dev/$PROJECT/adk-agents"

# Retriever agent
docker build -t "$REPO/retriever-agent:manual" agents/retriever_agent
docker push "$REPO/retriever-agent:manual"
gcloud run deploy retriever-agent --project=$PROJECT --region=$REGION `
  --image="$REPO/retriever-agent:manual" --allow-unauthenticated `
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=$REGION,GOOGLE_GENAI_USE_VERTEXAI=true,RAG_CORPUS=<your corpus resource name>"

# Grab the URL Cloud Run assigned, then set PUBLIC_URL so the A2A agent card is correct
$RETRIEVER_URL = gcloud run services describe retriever-agent --project=$PROJECT --region=$REGION --format="value(status.url)"
gcloud run services update retriever-agent --project=$PROJECT --region=$REGION --update-env-vars="PUBLIC_URL=$RETRIEVER_URL"

# Orchestrator agent
docker build -t "$REPO/orchestrator-agent:manual" agents/orchestrator_agent
docker push "$REPO/orchestrator-agent:manual"
gcloud run deploy orchestrator-agent --project=$PROJECT --region=$REGION `
  --image="$REPO/orchestrator-agent:manual" --allow-unauthenticated `
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=$REGION,GOOGLE_GENAI_USE_VERTEXAI=true,RETRIEVER_AGENT_URL=$RETRIEVER_URL"
```

Visit the orchestrator's Cloud Run URL — you now have the same chat experience, running
entirely on Cloud Run, with the two agents talking over A2A across two separate services.

## 7. Wire up GitHub Actions (Workload Identity Federation — no downloaded keys)

Run the second setup script, which creates a deploy service account and a Workload
Identity Federation pool/provider trusting **this specific GitHub repository**:

```powershell
bash infra/setup_wif_github_actions.sh YOUR_PROJECT_ID your-github-username/GoogleCloudAi
```

It prints two values. Add them as **repository variables** (Settings → Secrets and
variables → Actions → Variables) — they are not secret, so variables (not secrets) are
the right place:

| Variable name | Value |
|---|---|
| `GCP_PROJECT_ID` | `YOUR_PROJECT_ID` |
| `GCP_REGION` | `us-central1` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | printed by the script |
| `GCP_SERVICE_ACCOUNT` | printed by the script |
| `RAG_CORPUS` | the full resource name from step 4 (used by `retriever-agent`) |
| `RAG_CORPUS_ID` | just the trailing numeric id from step 4, e.g. `4611686018427387904` (used by the `ingestion` service so it re-uses the same corpus instead of creating a new one on every run) |
| `GCS_BUCKET` | `YOUR_PROJECT_ID-adk-docs` |

No `GCP_SA_KEY` secret is needed or created — GitHub's OIDC token is exchanged for a
short-lived Google credential at workflow run time.

Push to `master` and watch the **Actions** tab: `.github/workflows/deploy.yml` builds and
deploys `retriever-agent`, `orchestrator-agent` and `ingestion`, then creates/updates the
Cloud Scheduler job that keeps your RAG corpus fresh.

## 8. Everyday costs while learning

- Delete Cloud Run services / the RAG corpus when you're done for the day if you're
  worried about cost: `gcloud run services delete <name> --region=us-central1`.
- Cloud Scheduler, Cloud Run and Cloud Storage all have generous always-free tiers; the
  main cost driver is Vertex AI model + RAG Engine usage, which is pay-per-use.

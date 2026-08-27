# Architecture

## Components

### 1. `retriever_agent` (ADK agent, exposed over A2A)

A single ADK `Agent` whose only tool is `VertexAiRagRetrieval`, pointed at a Vertex AI
RAG Engine **corpus**. Its job is narrow on purpose: answer questions using only the
ingested documents.

It is turned into a standalone A2A server with `google.adk.a2a.utils.agent_to_a2a.to_a2a()`.
`to_a2a()` wraps the agent in a Starlette app that:

- serves the A2A JSON-RPC endpoint at `/`
- serves the agent's discovery document ("agent card") at `/.well-known/agent-card.json`

**Why a custom `AgentCard` instead of the auto-generated one:** `to_a2a(host=..., port=...)`
builds the advertised RPC URL as `f"{protocol}://{host}:{port}/"`. That is perfect for
local development (`http://localhost:8081/`), but wrong on Cloud Run: Cloud Run always
serves the public URL over `https` on port 443 with **no port in the URL**, even though
your container listens on `$PORT` (8080) internally. If we let `to_a2a()` build the card,
it would advertise a URL like `https://retriever-agent-xyz.a.run.app:8080/`, which does
not exist from the outside and gets rejected by the calling agent's origin check anyway.

The fix used in [`agents/retriever_agent/a2a_app.py`](../agents/retriever_agent/a2a_app.py)
is to build our own `AgentCard` with `url=PUBLIC_URL` (the real Cloud Run URL, no port)
and pass it to `to_a2a(..., agent_card=my_card)`. `to_a2a()` still wires up all the A2A
plumbing; it just stops trying to invent the URL itself.

### 2. `orchestrator_agent` (ADK agent, public-facing)

A normal ADK `Agent` that has one sub-agent: a `RemoteA2aAgent` pointing at
`retriever_agent`'s well-known agent card URL
(`{RETRIEVER_AGENT_URL}/.well-known/agent-card.json`). When the LLM decides the user's
question needs the knowledge base, ADK automatically calls the remote agent over HTTP
using the A2A protocol — this is a real network hop between two Cloud Run services, not
an in-process function call.

It is served with `google.adk.cli.fast_api.get_fast_api_app()` (the same FastAPI app
`adk web`/`adk api_server` use internally), which gives you the ADK dev UI, session
management, and the `/run`, `/run_sse` endpoints for free.

### 3. `ingestion` service (Cloud Run, triggered by Cloud Scheduler)

A tiny Flask app wrapping [`vertexai.preview.rag`](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-overview):

1. Gets or creates a RAG corpus (`rag.get_corpus` / `rag.create_corpus`).
2. Imports every file under a GCS prefix into that corpus (`rag.import_files`), chunking
   documents into ~512-token pieces with a 100-token overlap.

Cloud Scheduler calls this service's `/` endpoint on a cron schedule (default: once a
day) using an OIDC identity token, so newly-uploaded documents in the bucket are
periodically re-indexed without a person needing to run anything by hand.

### 4. Cloud Storage bucket

Plain storage for the source documents (see `data/sample_docs/`). Nothing agent-specific
lives here — RAG Engine reads directly from `gs://<bucket>/<prefix>/*` when you call
`rag.import_files`.

## Why RAG Engine instead of a hand-rolled vector database?

Vertex AI RAG Engine manages chunking, embeddings, indexing and retrieval for you behind
one API (`vertexai.preview.rag`). It is the fastest way to go from "a folder of
documents" to "an LLM tool that grounds answers in them" without standing up your own
vector database.

## Security notes (read this before deploying)

This sample defaults to **unauthenticated** Cloud Run services so it is easy to test in
a browser while you are learning. Before you do anything beyond personal experimentation:

- Redeploy `retriever_agent` and the `ingestion` service with `--no-allow-unauthenticated`.
- Grant `roles/run.invoker` only to the identities that should call them (the
  orchestrator's runtime service account, and the Cloud Scheduler service account,
  respectively).
- `RemoteA2aAgent` supports `auth_scheme`/`auth_credential` if you want the orchestrator
  to send an OIDC token to a private `retriever_agent`.
- Never commit `.env` files or service-account keys. This project uses Workload Identity
  Federation for GitHub Actions specifically so no long-lived key ever has to exist
  (see [SETUP.md](SETUP.md)).

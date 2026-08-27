"""Exposes `retriever_agent` over the A2A protocol as a standalone Starlette app.

Run locally with:
    uvicorn a2a_app:a2a_app --port 8081

Served on Cloud Run with the Dockerfile in this folder.
"""

import os

from a2a.types import AgentCapabilities
from a2a.types import AgentCard
from a2a.types import AgentSkill
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from agent import root_agent

PORT = int(os.environ.get("PORT", 8081))

# PUBLIC_URL must be the exact externally-reachable URL for this service, with NO port
# suffix (Cloud Run terminates TLS on 443 and proxies to the container's $PORT
# internally). Defaults to loopback for local development, where http is allowed.
PUBLIC_URL = os.environ.get("PUBLIC_URL", f"http://localhost:{PORT}")

# We build the AgentCard ourselves (instead of letting to_a2a() auto-generate one)
# because to_a2a() would otherwise advertise "{protocol}://{host}:{port}/", which is
# wrong once this runs behind Cloud Run's public HTTPS URL. See docs/ARCHITECTURE.md.
agent_card = AgentCard(
    name=root_agent.name,
    description=(
        root_agent.description
        or "Answers questions grounded in the ingested Vertex AI RAG corpus."
    ),
    url=PUBLIC_URL,
    version="1.0.0",
    capabilities=AgentCapabilities(),
    skills=[
        AgentSkill(
            id="document_retrieval",
            name="Document Retrieval",
            description=(
                "Answers questions using passages retrieved from the "
                "Vertex AI RAG Engine knowledge base."
            ),
            tags=["rag", "retrieval", "knowledge-base"],
        )
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    supports_authenticated_extended_card=False,
)

a2a_app = to_a2a(root_agent, port=PORT, agent_card=agent_card)

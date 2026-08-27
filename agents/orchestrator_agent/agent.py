"""Orchestrator agent: public-facing agent that delegates to `retriever_agent`
over the A2A protocol whenever a question needs grounded facts from the
ingested knowledge base.
"""

import os

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# URL of the retriever_agent A2A service, e.g. http://localhost:8081 locally or the
# Cloud Run URL of the "retriever-agent" service in production.
RETRIEVER_AGENT_URL = os.environ.get("RETRIEVER_AGENT_URL", "http://localhost:8081")

retriever_agent = RemoteA2aAgent(
    name="retriever_agent",
    description=(
        "Specialist agent with access to the organization's private "
        "knowledge base, ingested from Cloud Storage into Vertex AI RAG "
        "Engine. Delegate to it for any question that needs grounded facts "
        "from the ingested documents."
    ),
    agent_card=f"{RETRIEVER_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
)

root_agent = Agent(
    model=os.environ.get("ORCHESTRATOR_MODEL", "gemini-2.5-flash"),
    name="orchestrator_agent",
    description="Front-door assistant that routes requests to specialist agents.",
    instruction="""
    You are the orchestrator for a small multi-agent system.

    - For any question that likely requires facts from the ingested private
      knowledge base (documents uploaded to Cloud Storage and indexed in
      Vertex AI RAG Engine), delegate to `retriever_agent`.
    - For everything else (small talk, general reasoning), answer directly.
    - Always tell the user when an answer came from the knowledge base versus
      your own general knowledge.
    """,
    sub_agents=[retriever_agent],
)

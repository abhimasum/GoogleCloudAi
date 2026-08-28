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

    CRITICAL RULES:
    - For greetings (hello, hi, how are you) ONLY: respond directly with a brief greeting.
    - For ALL other questions, requests, or queries: ALWAYS delegate to `retriever_agent`.
    - NEVER answer questions from your own knowledge - you must delegate everything except greetings.
    - Do not try to determine if a question needs the knowledge base or not - just delegate it.
    - The retriever_agent has access to the organization's private knowledge base via Vertex AI RAG Engine.
    """,
    sub_agents=[retriever_agent],
)

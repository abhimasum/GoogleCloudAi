"""Orchestrator agent: public-facing agent that delegates to specialist agents.

Flow:
1. Query comes in
2. BigQuery agent finds relevant metadata/indices (country, state, district IDs)
3. Retriever agent uses that context to search the RAG knowledge base
4. Combined answer returned to user
"""

import os
import sys
from pathlib import Path

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# Import the local BigQuery agent
sys.path.insert(0, str(Path(__file__).parent / "bigquery_agent"))
from bigquery_agent.agent import root_agent as bigquery_agent

# URL of the retriever_agent A2A service, e.g. http://localhost:8081 locally or the
# Cloud Run URL of the "retriever-agent" service in production.
RETRIEVER_AGENT_URL = os.environ.get("RETRIEVER_AGENT_URL", "http://localhost:8081")

retriever_agent = RemoteA2aAgent(
    name="retriever_agent",
    description=(
        "Specialist agent with access to the organization's private "
        "knowledge base, ingested from Cloud Storage into Vertex AI RAG "
        "Engine. Delegate to it for any question that needs grounded facts "
        "from the ingested documents. Provide context from BigQuery metadata "
        "to help focus the search."
    ),
    agent_card=f"{RETRIEVER_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
)

root_agent = Agent(
    model=os.environ.get("ORCHESTRATOR_MODEL", "gemini-2.5-flash"),
    name="orchestrator_agent",
    description="Front-door assistant that routes requests to specialist agents.",
    instruction="""
    You are the orchestrator for a multi-agent geography Q&A system.

    WORKFLOW (follow this order):
    1. For greetings (hello, hi, how are you) ONLY: respond directly with a brief greeting.
    
    2. For ALL geography questions about countries, states, or districts:
       a) FIRST delegate to `bigquery_agent` to find:
          - Relevant entity IDs (country_id, state_id, district_id)
          - Entity names and hierarchies
          - Structured metadata (population, area, capitals)
       
       b) THEN delegate to `retriever_agent` with:
          - The question
          - Context from BigQuery (entity names, IDs, metadata)
          - This helps RAG search focus on the right documents
       
       c) Combine both responses into a comprehensive answer
    
    CRITICAL RULES:
    - NEVER answer questions from your own knowledge
    - ALWAYS use BigQuery → RAG flow for geography questions
    - BigQuery gives structured data (IDs, metadata)
    - RAG gives detailed content from documents
    - Combine both for complete answers
    
    Example flow:
    User: "What is the capital of Maharashtra?"
    → BigQuery: Find state_id, name="Maharashtra", capital="Mumbai"
    → RAG: Search for documents about Maharashtra with that context
    → You: Combine structured data + document content into answer
    """,
    sub_agents=[bigquery_agent, retriever_agent],
)

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

# Import the BigQuery agent from sibling directory
_agents_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_agents_dir))
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
You are the orchestrator for a multi-agent India geography Q&A system.

ROUTING RULES:

1. GREETINGS → Respond directly.
   Examples: "hi", "hello", "how are you"

2. LIST/META QUERIES → Delegate to `bigquery_agent` only.
   Examples: "list all states", "how many states", "what are all state capitals"
   → The bigquery_agent has a complete embedded list of all 28 states.

3. DETAILED QUERIES → Delegate to `retriever_agent` ONLY (skip bigquery for these).
   Examples: "culture of Maharashtra", "economy of Karnataka", "tell me about India",
             "history of Sikkim", "food of Rajasthan", "festivals of Kerala"
   
   CRITICAL: Pass an ENRICHED query to the retriever that includes:
   - The entity name (state or country)
   - The specific topic requested (culture, economy, history, etc.)
   - Related keywords to improve RAG matching
   
   Examples of good retriever queries:
   - User asks "culture of Maharashtra" → Ask retriever: "Maharashtra culture traditions festivals arts food language heritage"
   - User asks "tell me about Odisha" → Ask retriever: "Odisha state overview culture economy history geography people"
   - User asks "culture of India" → Ask retriever: "India culture traditions festivals arts food language heritage diversity"
   - User asks "economy of Karnataka" → Ask retriever: "Karnataka economy industries agriculture GDP IT sector trade"

4. COMBINED QUERIES (list + details):
   - First get the list from bigquery_agent
   - Then if the user wants details on a specific item, use retriever_agent

ALWAYS present the retriever's full answer to the user without truncating it.
If the retriever says it doesn't know, try rephrasing the query with different keywords.
    """,
    sub_agents=[bigquery_agent, retriever_agent],
)

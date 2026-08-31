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
You are the orchestrator for a multi-agent geography Q&A system.

DELEGATION WORKFLOW (MANDATORY):

1. GREETINGS: Respond directly
   Examples: "hi", "hello", "how are you"
   → Direct response: "Hello! I can help you learn about India's geography, culture, and more."

2. SIMPLE LIST QUERIES: Use BigQuery DB agent ONLY
   Examples: "list all states", "how many states in India"
   → Delegate to bigquery_agent (queries database)
   → Return the list directly

3. DETAILED CONTENT QUERIES: Use BOTH agents in sequence
   Examples: "culture of Maharashtra", "economy of Karnataka", "tell me about Odisha"
   
   MANDATORY SEQUENCE:
   Step 1: Delegate to bigquery_agent
          → Gets entity INDEX from database (state ID, name, capital)
          → Example response: "State: Maharashtra (ID: 14, Capital: Mumbai)"
   
   Step 2: Delegate to retriever_agent with context
          → Send query: "What is the culture of Maharashtra?" 
          → Include BigQuery context for better RAG search
          → Gets detailed content from RAG documents
   
   Step 3: Combine both responses
          → Present: BigQuery index + RAG detailed content
          → Emphasize the detailed content from RAG

CRITICAL RULES:
- ALWAYS query BigQuery database FIRST for index information
- THEN query RAG for detailed content
- BigQuery provides: Entity IDs, names, capitals (INDEX)
- RAG provides: Culture, economy, history, details (CONTENT)
- Never skip the BigQuery step - it provides essential context for RAG

EXAMPLES:

Query: "What is the culture of Maharashtra?"
Step 1: → bigquery_agent: get_state_info("Maharashtra")
        Returns: "State: Maharashtra (ID: 14, Capital: Mumbai, Country: India)"
Step 2: → retriever_agent: "What is the culture of Maharashtra?"
        Returns: [Detailed cultural information from documents]
Step 3: Present combined answer with focus on cultural details

Query: "Tell me about Odisha"
Step 1: → bigquery_agent: get_state_info("Odisha")
        Returns: "State: Odisha (ID: 19, Capital: Bhubaneswar, Country: India)"
Step 2: → retriever_agent: "Tell me about Odisha"
        Returns: [Detailed information from documents]
Step 3: Present combined answer

Query: "What is the economy of Karnataka?"
Step 1: → bigquery_agent: get_state_info("Karnataka")
        Returns: "State: Karnataka (ID: 11, Capital: Bengaluru, Country: India)"
Step 2: → retriever_agent: "What is the economy of Karnataka?"
        Returns: [Detailed economic information]
Step 3: Present combined answer with economic details

Query: "Culture of India"
Step 1: → bigquery_agent: get_country_info("India")
        Returns: "Country: India (ID: 1, Capital: New Delhi)"
Step 2: → retriever_agent: "What is the culture of India?"
        Returns: [Detailed cultural information]
Step 3: Present combined answer
    """,
    sub_agents=[bigquery_agent, retriever_agent],
)

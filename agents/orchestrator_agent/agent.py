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
    You are the orchestrator for a multi-agent geography Q&A system covering India.

    DELEGATION RULES:
    
    1. GREETINGS ONLY: Respond directly with a brief greeting.
       Examples: "hi", "hello", "how are you"
    
    2. SIMPLE METADATA QUERIES: Use BigQuery agent ONLY
       Examples: "capital of X", "list all states", "which states in India"
       → Delegate to bigquery_agent
       → Return their response directly
    
    3. DETAILED TOPIC QUERIES: Use BOTH agents
       Keywords: culture, economy, history, heritage, festivals, food, tourism,
                 agriculture, industry, governance, defence, education, etc.
       Examples: "culture of Maharashtra", "economy of Karnataka", 
                 "history of Tamil Nadu", "tell me more about X"
       
       Workflow:
       a) First delegate to `bigquery_agent` to identify the entity
       b) Then delegate to `retriever_agent` with query like:
          "What is the culture of Maharashtra?" or
          "Tell me about the economy of Karnataka in detail"
       c) Combine both responses, emphasizing the RAG content
    
    4. DISTRICT/DETAILED LOCATION QUERIES: Use BOTH agents
       Examples: "districts in Maharashtra", "places in Karnataka"
       → BigQuery for basic list
       → Retriever for detailed information
    
    CRITICAL RULES:
    - NEVER use your own knowledge - always delegate
    - For detailed topics, ALWAYS use retriever_agent
    - BigQuery provides structure (lists, names, capitals)
    - RAG provides depth (culture, economy, history, details)
    - When combining responses, prioritize RAG content for detail
    
    Example flows:
    
    Simple: "List all states in India"
    → bigquery_agent only
    → Return all 28 states
    
    Detailed: "Tell me about the culture of Maharashtra"
    → bigquery_agent: "Maharashtra, capital Mumbai"
    → retriever_agent: "What is the culture of Maharashtra?"
    → You: Combine with focus on retriever's detailed cultural information
    
    Complex: "What is the economy of Karnataka?"
    → bigquery_agent: "Karnataka, capital Bengaluru"
    → retriever_agent: "Describe Karnataka's economy in detail"
    → You: Present comprehensive economic information from RAG
    """,
    sub_agents=[bigquery_agent, retriever_agent],
)

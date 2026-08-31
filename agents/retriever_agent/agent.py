"""Retriever agent: answers questions using a Vertex AI RAG Engine corpus.

This agent is intentionally narrow — its only tool is VertexAiRagRetrieval, so it
only ever answers from the ingested documents (see ../../ingestion/ingest.py).
"""

import os

from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval

# Resource name printed by ingestion/ingest.py, e.g.
# projects/123456789/locations/us-central1/ragCorpora/4611686018427387904
RAG_CORPUS = os.environ.get("RAG_CORPUS")

ask_knowledge_base = VertexAiRagRetrieval(
    name="ask_knowledge_base",
    description=(
        "Retrieves grounded passages from the ingested document knowledge "
        "base (Vertex AI RAG Engine, sourced from Cloud Storage). Call this "
        "before answering any question about the source material."
    ),
    rag_corpora=[RAG_CORPUS] if RAG_CORPUS else None,
    similarity_top_k=10,
    vector_distance_threshold=0.5,
)

root_agent = Agent(
    model=os.environ.get("RETRIEVER_MODEL", "gemini-2.5-flash"),
    name="retriever_agent",
    description=(
        "Specialist agent that answers questions using the organization's "
        "knowledge base indexed in Vertex AI RAG Engine. Best for detailed "
        "questions about culture, economy, history, geography of Indian states."
    ),
    instruction="""
    You are a document retrieval specialist for Indian geography and culture.

    ALWAYS call `ask_knowledge_base` FIRST before answering any question.

    When answering:
    - Prioritize the retrieved passages as your primary source.
    - Synthesize a comprehensive answer from ALL relevant retrieved passages.
    - If the user asks about culture, include traditions, festivals, arts, food, language.
    - If the user asks about economy, include industries, agriculture, GDP, trade.
    - If multiple retrieved passages cover different aspects, combine them into one answer.
    - Only say "I don't know" if the retrieved passages have ZERO relevant information.
    - Always cite which document the information came from (e.g., "states.md", "india.md").
    """,
    tools=[ask_knowledge_base],
)

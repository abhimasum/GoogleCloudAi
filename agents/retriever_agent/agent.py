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
    similarity_top_k=5,
    vector_distance_threshold=0.6,
)

root_agent = Agent(
    model=os.environ.get("RETRIEVER_MODEL", "gemini-2.5-flash"),
    name="retriever_agent",
    description=(
        "Specialist agent that answers questions strictly using the "
        "organization's private knowledge base indexed in Vertex AI RAG Engine."
    ),
    instruction="""
    You are a document retrieval specialist.

    - Always call `ask_knowledge_base` first before answering.
    - Answer only using the retrieved passages; do not use outside knowledge.
    - If nothing relevant is found, say you don't know rather than guessing.
    - Keep answers concise and mention which topic the information came from.
    """,
    tools=[ask_knowledge_base],
)

# Vertex AI RAG Engine

RAG Engine implements the retrieval-augmented generation pipeline as a managed
service:

1. **Data ingestion** — import files from Cloud Storage, Google Drive, or upload them
   directly, into a **corpus**.
2. **Transformation** — documents are split into chunks (for example 512 tokens with a
   100-token overlap).
3. **Embedding** — each chunk is embedded with a text embedding model such as
   `text-embedding-005`.
4. **Indexing** — the embeddings are stored in a managed vector index scoped to the
   corpus.
5. **Retrieval** — given a query, RAG Engine returns the most similar chunks
   (`similarity_top_k`, `vector_distance_threshold`).
6. **Generation** — the retrieved chunks are added to the LLM's context so it can
   produce a grounded, factual answer instead of hallucinating.

In Python, the corpus lifecycle is managed with the `vertexai.preview.rag` module:
`rag.create_corpus()`, `rag.import_files()`, `rag.list_files()`, and
`rag.retrieval_query()`. In ADK, the `VertexAiRagRetrieval` tool wraps this so an agent
can call it like any other tool.

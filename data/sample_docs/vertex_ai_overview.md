# Vertex AI

Vertex AI is Google Cloud's unified machine learning and generative AI platform. For
generative AI, the most commonly used pieces are:

- **Gemini models**: multimodal large language models (e.g. `gemini-2.5-flash`,
  `gemini-2.5-pro`) accessed through the Vertex AI API or the `google-genai` SDK.
- **Vertex AI RAG Engine**: a managed retrieval-augmented generation service that
  chunks, embeds, indexes, and retrieves your documents so an LLM can ground its
  answers in them.
- **Vertex AI Search**: enterprise search and discovery over structured and
  unstructured data, usable as an ADK tool (`VertexAiSearchTool`).
- **Vertex AI Agent Engine**: a managed runtime for deploying and scaling agents,
  as an alternative to self-hosting them on Cloud Run or GKE.

To use Vertex AI from a local machine or a service, authenticate with
`gcloud auth application-default login` (for user credentials) or attach a service
account with the `roles/aiplatform.user` role to the running workload.

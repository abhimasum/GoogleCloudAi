# Google Agent Development Kit (ADK)

The Agent Development Kit (ADK) is Google's open-source Python (and multi-language)
framework for building, evaluating, and deploying AI agents. It is model-agnostic
(works with Gemini, and via LiteLLM with other providers) and deployment-agnostic.

Key building blocks:

- **Agent**: an LLM-backed agent with a model, instruction, and a list of tools.
- **Tools**: plain Python functions, or built-in tools such as `VertexAiRagRetrieval`,
  `VertexAiSearchTool`, and `GoogleSearchTool`.
- **Sub-agents**: an agent can delegate to other agents, either in-process or remote
  agents reached over the A2A protocol via `RemoteA2aAgent`.
- **Runner**: executes an agent against a session, producing a stream of events.
- **`adk web` / `adk api_server`**: local development servers with a chat UI and REST API.

ADK agents can be deployed to Cloud Run, GKE, or Vertex AI Agent Engine.

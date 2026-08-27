# The A2A (Agent2Agent) Protocol

A2A is an open protocol for agent-to-agent communication over HTTP/JSON-RPC. It lets
one agent call another agent as a remote service, regardless of what framework built
the remote agent, similar in spirit to how OpenAPI lets services call each other.

Two core concepts:

- **Agent Card**: a JSON document describing an agent (name, description, skills,
  and the URL to send requests to). By convention it is published at
  `/.well-known/agent-card.json`.
- **RPC endpoint**: the URL (from the agent card) that receives A2A JSON-RPC requests
  to actually run the agent.

In Google ADK:

- `to_a2a(agent)` turns any ADK agent into an A2A server (a Starlette app you serve
  with `uvicorn`), auto-generating its agent card.
- `RemoteA2aAgent(agent_card=<url>)` lets one ADK agent use another agent — local or
  remote, built with ADK or any other A2A-compliant framework — as a sub-agent, purely
  by pointing it at the remote agent's card URL.

This project uses A2A between two separately deployed Cloud Run services:
`orchestrator_agent` (the caller) and `retriever_agent` (the callee), to demonstrate a
real network hop between agents rather than a simple in-process function call.

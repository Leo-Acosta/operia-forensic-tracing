# AI Assistant

`operia/ai_assistant` provides local AI assistance for forensic and legal workflows.

Default provider:

- Ollama local

Default model:

- Mistral

Rules:

- no external API is used by default;
- evidence should not be sent to hosted services;
- the app must continue working when Ollama is unavailable;
- AI output is assistance, not an authoritative legal or forensic decision;
- legal conclusions require registered sources and human review.

Canonical API:

- `GET /api/ai`
- `POST /api/ai/assist`

The assistant builds a guarded forensic prompt before calling Ollama:

- platform guardrails;
- legal context retrieved from `legal_knowledge`;
- optional case context;
- JSON-oriented response contract;
- mandatory human-review framing.

Every interaction is recorded in `ai_interactions` and returns `ollama_unavailable` if the local Ollama service is not running.

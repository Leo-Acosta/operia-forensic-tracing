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

## Secure local gateway (2026-10-17)

Generation requires an authenticated user with ai:use, a verified case, both
server enable flags and an explicit organization model allowlist. A trusted
fixed-destination broker connects to local Ollama; request/response validators
remain in no-network AppContainers. No loopback exemptions or unrestricted child
processes are introduced. Health is passive and never runs inference.

The AI screen has a separate case-scoped local query. Case context is opt-in;
case/evidence/finding excerpts and legal context are bounded, marked as extracts
when limited and never rewrite original records. The response remains untrusted
text requiring human review. Context and provider conversation state are not
reused. No original attachments or tools are sent.

See [configuration, trust boundary and tests](LOCAL_AI_GATEWAY.md). Disabled by
default; no real provider or model was activated by the implementation tests.

# AI Security

`operia/ai_security` evaluates AI models under controlled, auditable conditions.

The module does not claim that a model is pure, perfectly secure, or free of backdoors. Its conclusion must be framed as:

> Bajo estas condiciones locales, aisladas y auditadas, el riesgo observado es bajo/medio/alto.

Current components:

- `AIModelEvaluation`
- `AIModelTestRun`
- controlled test catalog;
- scoring helper;
- Markdown report generator;
- canonical API.

Minimum test categories:

- sensitive data leakage;
- exfiltration attempts;
- malicious obedience;
- prompt injection;
- jailbreak;
- unauthorized filesystem access;
- command execution attempts;
- legal hallucination;
- false legal citations;
- legal bias;
- Spanish legal consistency;
- sensitive evidence handling;
- refusal of illegal requests;
- OPERIA policy compliance.

Canonical API:

- `GET /api/ai-security`
- `GET /api/ai-security/tests`
- `POST /api/ai-security/evaluations`
- `GET /api/ai-security/evaluations`
- `GET /api/ai-security/evaluations/{evaluation_id}/report`

`POST /api/ai-security/evaluations` accepts:

- `model_name`: default `mistral`;
- `run_tests`: when true, executes controlled prompts through local Ollama;
- `tests`: optional list of test codes;
- `network_blocked`;
- `tools_enabled`;
- `overall_score` for manual/placeholder evaluation.

If Ollama is unavailable, the module records the test as pending without sending data externally.

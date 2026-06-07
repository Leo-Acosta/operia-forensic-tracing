# OPERIA Mind

OPERIA Mind is the forensic memory layer for OPERIA Forensic Tracing. It adds a Markdown vault, notes, prompts, agents, graph relationships, and audit records without replacing the transactional database.

## Principles

- The database remains the source of truth for operational data.
- `memory_vault` is a readable, recoverable, Obsidian-compatible memory.
- Notes must be scoped by case whenever possible.
- AI outputs can be stored only with auditability and human review metadata.
- Legal conclusions must still come from registered legal knowledge.

## Backend Module

```text
operia/mind/
  models.py
  schemas.py
  router.py
  service.py
  vault.py
  prompts.py
  agents.py
  bootstrap.py
```

## Vault

`memory_vault` is created at the project root with folders for cases, evidence, notes, findings, hypotheses, reports, prompts, agents, audits, graph data, legal work, cybercrime, blockchain, deepfake, IoT, and exports.

## Main Endpoints

- `GET /api/mind`
- `POST /api/mind/notes`
- `GET /api/mind/notes`
- `GET /api/mind/notes/{note_id}`
- `POST /api/mind/cases/{case_id}/snapshot`
- `GET /api/mind/cases/{case_id}/notes`
- `GET /api/mind/cases/{case_id}/graph`
- `GET /api/mind/prompts`
- `GET /api/mind/agents`
- `GET /api/mind/audit`

## Current Scope

This first version creates memory snapshots, notes, prompt/agent catalogs, and a case-centered graph. Semantic search and advanced agent orchestration are intentionally left behind service boundaries for future phases.

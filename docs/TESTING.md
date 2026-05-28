# Testing

OPERIA uses `pytest` with FastAPI `TestClient`.

Run:

```powershell
python -m pytest -q -p no:cacheprovider
```

Why `-p no:cacheprovider`:

On some Windows environments, pytest cache/temp creation can fail because of local permissions. The test suite uses workspace-local temporary databases under `storage/test_runs`, so pytest cache is not required.

Current coverage:

- identity bootstrap/login/me;
- invalid login rejection;
- case creation;
- evidence creation;
- report generation;
- audit logs;
- legal knowledge seed/search/recommend;
- AI assistant graceful behavior when Ollama is unavailable;
- AI Security evaluation/report;
- export manifest and hash generation.

The tests use isolated SQLite databases and do not modify the main local database.


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

The security regression also covers organization/purpose connector grants,
cross-case graph references, unique tenant note paths, session invalidation,
legacy password upgrades, secret-free worker environments, SSRF and termination
of a real child process at its deadline. No external provider receives evidence.
See [the dated audit](SECURITY_AUDIT.md) for dependency scans and reproducible
Windows CPython 3.12 installation with `requirements-win-py312.lock`.



## Aislamiento Windows y pentest local

Ejecutar `python scripts/prepare_worker_sandbox.py` desde la raiz antes de
trabajos nuevos y despues de actualizar el runtime. AppContainer/Job son
obligatorios, sin fallback a ejecucion normal. La IA directa a localhost queda
bloqueada hasta disponer de pasarela separada; no agregar excepciones de loopback.
Ver [operacion, resultados y limites](LOCAL_PENTEST.md).


Actualizacion 2026-10-17: la [pasarela de IA local](LOCAL_AI_GATEWAY.md) ya esta
implementada, deshabilitada por defecto. Requiere preparacion del runtime, dos
flags globales, modelo concedido por organizacion y caso autorizado. Los workers
siguen sin loopback. La guia describe el servicio Ollama confiable y sus limites.

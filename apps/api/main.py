from fastapi import FastAPI
from operia.security.middleware import SecurityBoundary
from fastapi.middleware.cors import CORSMiddleware

from operia.core.bootstrap import init_platform_schema
from operia.core.config import settings
from operia.core.router import api_router
from operia.cybercrime.bootstrap import init_cybercrime_module
from operia.geo_proximity.bootstrap import init_geo_proximity_module
from operia.geo_trace.bootstrap import init_geo_trace_module
from operia.legal_knowledge.bootstrap import init_legal_knowledge_module
from operia.legal_report.bootstrap import init_legal_report_module
from operia.mind.bootstrap import init_mind_module
from operia.rubrics.bootstrap import init_rubrics_module


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Unified forensic tracing platform for OPERIA modules.",
        version="0.1.0",
    )
    from operia.security.safe_errors import install_safe_errors
    install_safe_errors(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(SecurityBoundary)

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def on_startup() -> None:
        from operia.security.production import enforce_production
        enforce_production(settings)
        from operia.identity.security import _secret
        _secret()  # Create/validate the signing key before serving concurrent requests.
        init_platform_schema()
        init_legal_report_module()
        init_legal_knowledge_module()
        init_rubrics_module()
        init_mind_module()
        init_cybercrime_module()
        init_geo_trace_module()
        init_geo_proximity_module()

    @app.get("/")
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "status": "ready"}

    return app


app = create_app()

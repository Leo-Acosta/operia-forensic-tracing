from operia.core.database import Base, engine


def init_geo_trace_module() -> None:
    import operia.geo_trace.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


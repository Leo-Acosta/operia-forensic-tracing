from operia.core.database import Base, engine


def init_cybercrime_module() -> None:
    import operia.cybercrime.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


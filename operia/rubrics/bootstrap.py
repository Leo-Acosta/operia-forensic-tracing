from operia.core.database import Base, engine


def init_rubrics_module() -> None:
    Base.metadata.create_all(bind=engine)

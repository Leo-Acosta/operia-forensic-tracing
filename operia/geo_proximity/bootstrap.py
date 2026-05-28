from operia.core.database import Base, SessionLocal, engine
from operia.geo_proximity.models import LocationReference

DEFAULT_LOCATIONS = [
    {"name": "Apple Store CABA", "category": "apple_store_demo", "lat": -34.6037, "lon": -58.3816},
    {"name": "Apple Store Lanus", "category": "apple_store_demo", "lat": -34.7000, "lon": -58.4000},
    {"name": "Apple Store La Plata", "category": "apple_store_demo", "lat": -34.9214, "lon": -57.9544},
]


def init_geo_proximity_module() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for item in DEFAULT_LOCATIONS:
            if not db.query(LocationReference).filter_by(name=item["name"]).first():
                db.add(LocationReference(**item))
        db.commit()
    finally:
        db.close()


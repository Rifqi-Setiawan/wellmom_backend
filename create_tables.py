from app.database import Base, engine
from app.models import (
    user,
    puskesmas,
    perawat,
    ibu_hamil,
    kerabat,
    health_record,
    notification,
    transfer_request
)

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ All tables created successfully!")

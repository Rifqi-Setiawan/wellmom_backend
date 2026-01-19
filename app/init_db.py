from app.database import Base, engine
import app.models  # penting: memastikan semua model ke-import dan register ke Base.metadata

def main():
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")

if __name__ == "__main__":
    main()

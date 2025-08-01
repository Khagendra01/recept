from sqlalchemy.orm import Session
from app.db.base import Base
from app.db.session import engine
from app.core.config import settings

def init_db() -> None:
    """Initialize database with tables"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

if __name__ == "__main__":
    init_db()

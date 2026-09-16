from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# check_same_thread нужен только для SQLite при работе в нескольких потоках.
connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI-зависимость: выдаёт сессию БД и гарантированно её закрывает."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./opportunities.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def initialize_database():
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            inspector = inspect(connection)
            existing_tables = set(inspector.get_table_names())
            for table in ("profiles", "opportunities"):
                if table not in existing_tables:
                    continue
                columns = {column["name"]: column for column in inspector.get_columns(table)}
                vector_column = columns.get("vector")
                if vector_column and str(vector_column["type"]).upper() in ("JSON", "JSONB"):
                    connection.execute(text(
                        f"ALTER TABLE {table} ALTER COLUMN vector TYPE vector(384) "
                        "USING CASE WHEN vector IS NULL OR vector::text = 'null' "
                        "THEN NULL ELSE vector::text::vector(384) END"
                    ))
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        from .models import Opportunity

        for index in Opportunity.__table__.indexes:
            index.create(bind=engine, checkfirst=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

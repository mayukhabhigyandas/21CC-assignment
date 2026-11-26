from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from pgvector.sqlalchemy import Vector
from .database import Base

class EmbeddingVector(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(384))
        return dialect.type_descriptor(JSON())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    profile = relationship("Profile", back_populates="user", uselist=False)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    bio = Column(Text, default="")
    skills = Column(JSON, nullable=False, default=list)
    vector = Column(EmbeddingVector(), nullable=True)
    user = relationship("User", back_populates="profile")

class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    location_or_mode = Column(String, nullable=False)
    required_skills = Column(JSON, nullable=False)
    vector = Column(EmbeddingVector(), nullable=True)

Index(
    "ix_opportunities_vector_hnsw",
    Opportunity.vector,
    postgresql_using="hnsw",
    postgresql_ops={"vector": "vector_cosine_ops"},
).ddl_if(dialect="postgresql")

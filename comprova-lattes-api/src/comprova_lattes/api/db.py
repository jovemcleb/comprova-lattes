"""Persistência lazy: importar a API não conecta a serviços externos."""

from functools import lru_cache

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from comprova_lattes.config import settings


class Base(DeclarativeBase):
    pass


class Validation(Base):
    __tablename__ = "validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    payload: Mapped[dict] = mapped_column(JSON)
    parsed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extractions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    automatic_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)


class Review(Base):
    __tablename__ = "human_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    validation_id: Mapped[str] = mapped_column(ForeignKey("validations.id"), index=True)
    record_index: Mapped[int] = mapped_column(Integer)
    decision: Mapped[dict] = mapped_column(JSON)


@lru_cache
def get_session_factory():
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)

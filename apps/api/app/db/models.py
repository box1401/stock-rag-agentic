from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Ticker(Base):
    __tablename__ = "tickers"

    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)
    industry: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )


class Report(Base):
    __tablename__ = "reports"

    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), init=False
    )
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), default=None, index=True)
    pdf_url: Mapped[str | None] = mapped_column(String, default=None)
    agent_trace: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (UniqueConstraint("ticker", "signal_date", name="signals_ticker_date_key"),)

    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), nullable=False)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), init=False
    )
    report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), default=None
    )
    close: Mapped[Decimal | None] = mapped_column(Numeric, default=None)
    ma5: Mapped[Decimal | None] = mapped_column(Numeric, default=None)
    ma20: Mapped[Decimal | None] = mapped_column(Numeric, default=None)
    ma60: Mapped[Decimal | None] = mapped_column(Numeric, default=None)
    rsi: Mapped[Decimal | None] = mapped_column(Numeric, default=None)
    bias_20: Mapped[Decimal | None] = mapped_column(Numeric, default=None)
    pe: Mapped[Decimal | None] = mapped_column(Numeric, default=None)
    pe_percentile: Mapped[Decimal | None] = mapped_column(Numeric, default=None)
    recommendation: Mapped[str | None] = mapped_column(String, default=None)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )


class Document(Base):
    __tablename__ = "documents"

    source_type: Mapped[str] = mapped_column(String, nullable=False)
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), init=False
    )
    source_url: Mapped[str | None] = mapped_column(String, default=None)
    ticker: Mapped[str | None] = mapped_column(
        ForeignKey("tickers.symbol"), default=None, index=True
    )
    title: Mapped[str | None] = mapped_column(String, default=None)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    raw_path: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", default_factory=list)


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="chunks_doc_idx_key"),
        Index("chunks_embedding_idx", "embedding", postgresql_using="hnsw"),
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), init=False
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), default=None)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, default=None)

    document: Mapped[Document | None] = relationship(back_populates="chunks", default=None)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), init=False
    )
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), default=None)
    ticker: Mapped[str | None] = mapped_column(ForeignKey("tickers.symbol"), default=None)
    title: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )


class Message(Base):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), init=False
    )
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
